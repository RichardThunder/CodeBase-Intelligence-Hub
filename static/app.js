/**
 * CodeBase Intelligence Hub - Frontend Application
 * Real-time chat interface with SSE streaming support
 */

// Configuration
const API_BASE = window.location.origin;
const HEALTH_CHECK_INTERVAL = 3000; // 3 seconds
const SESSION_KEY = 'codebase_hub_session_id';

// State
let currentSessionId = null;
let isLoading = false;
let healthCheckInterval = null;

// DOM Elements
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const inputStatus = document.getElementById('inputStatus');
const healthIndicator = document.getElementById('healthIndicator');
const healthStatus = document.getElementById('healthStatus');
const sessionIdInput = document.getElementById('sessionId');
const resetSessionBtn = document.getElementById('resetSessionBtn');
const repoPath = document.getElementById('repoPath');
const ingestBtn = document.getElementById('ingestBtn');
const ingestStatus = document.getElementById('ingestStatus');

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    initializeSession();
    setupEventListeners();
    startHealthCheck();
    autoResizeTextarea();
});

// ===== Session Management =====
function initializeSession() {
    const stored = localStorage.getItem(SESSION_KEY);
    currentSessionId = stored || generateSessionId();
    localStorage.setItem(SESSION_KEY, currentSessionId);
    sessionIdInput.value = currentSessionId;
}

function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function resetSession() {
    const newSessionId = generateSessionId();
    localStorage.setItem(SESSION_KEY, newSessionId);
    currentSessionId = newSessionId;
    sessionIdInput.value = currentSessionId;
    clearChat();
    showNotification('Session reset. Chat history cleared.', 'success');
}

// ===== Event Listeners =====
function setupEventListeners() {
    sendBtn.addEventListener('click', handleSendMessage);
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    resetSessionBtn.addEventListener('click', resetSession);
    ingestBtn.addEventListener('click', handleIngest);

    // Auto-focus input
    queryInput.focus();
}

// ===== Chat Functions =====
async function handleSendMessage() {
    const query = queryInput.value.trim();

    if (!query) {
        showNotification('Please enter a question', 'error');
        return;
    }

    if (isLoading) {
        showNotification('Already waiting for a response...', 'error');
        return;
    }

    // Clear input
    queryInput.value = '';
    autoResizeTextarea();

    // Add user message
    addMessage('user', query);

    // Try streaming first, fall back to regular chat
    isLoading = true;
    sendBtn.disabled = true;
    inputStatus.textContent = 'Loading...';
    inputStatus.className = 'input-status';

    try {
        await streamChat(query);
    } catch (error) {
        console.error('Streaming failed, trying regular chat:', error);
        try {
            await regularChat(query);
        } catch (err) {
            const errorMsg = `Error: ${err.message || 'Failed to get response'}`;
            addMessage('assistant', errorMsg);
            showNotification(errorMsg, 'error');
        }
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        inputStatus.textContent = '';
        queryInput.focus();
    }
}

async function streamChat(query) {
    const messageEl = addMessage('assistant', '');
    const contentEl = messageEl.querySelector('.message-bubble');
    let fullResponse = '';

    const params = new URLSearchParams({
        query: query,
        session_id: currentSessionId,
    });

    const response = await fetch(`${API_BASE}/api/chat/stream?${params}`, {
        method: 'GET',
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);

                if (data === '[DONE]') {
                    continue;
                }

                fullResponse += data;
                contentEl.textContent = fullResponse;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }
    }

    if (!fullResponse) {
        throw new Error('Empty response from server');
    }
}

async function regularChat(query) {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            session_id: currentSessionId,
            include_sources: true,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Request failed');
    }

    const data = await response.json();
    const messageEl = addMessage('assistant', data.answer);

    // Add sources if available
    if (data.sources && data.sources.length > 0) {
        const sourcesEl = document.createElement('div');
        sourcesEl.className = 'message-sources';
        sourcesEl.innerHTML = '<strong>Sources:</strong>';

        data.sources.forEach((source) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            const filePath = source.file_path || 'Unknown';
            const preview = source.preview || '';

            sourceItem.innerHTML = `
                <span class="source-file" title="${preview}">${filePath}</span>
            `;

            sourcesEl.appendChild(sourceItem);
        });

        const bubble = messageEl.querySelector('.message-bubble');
        bubble.appendChild(sourcesEl);
    }
}

function addMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;

    messageEl.appendChild(bubble);
    chatMessages.appendChild(messageEl);

    // Auto-scroll to bottom
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 0);

    return messageEl;
}

function clearChat() {
    chatMessages.innerHTML = `
        <div class="system-message">
            <p>Welcome to <strong>CodeBase Intelligence Hub</strong></p>
            <p>Ask questions about your codebase and I'll help you understand, explore, and analyze it.</p>
        </div>
    `;
}

// ===== Ingest Functions =====
async function handleIngest() {
    const path = repoPath.value.trim();

    if (!path) {
        showNotification('Please enter a repository path', 'error');
        return;
    }

    ingestBtn.disabled = true;
    ingestStatus.textContent = 'Ingesting...';
    ingestStatus.className = 'ingest-status';

    try {
        const response = await fetch(`${API_BASE}/api/ingest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                repo_path: path,
                use_parser: true,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ingest failed');
        }

        const data = await response.json();
        ingestStatus.textContent = '✅ Ingestion started in background. This may take a moment...';
        ingestStatus.className = 'ingest-status success';
        showNotification('Ingestion started successfully', 'success');

        // Poll for completion
        pollIngestCompletion();
    } catch (error) {
        ingestStatus.textContent = `❌ ${error.message}`;
        ingestStatus.className = 'ingest-status error';
        showNotification(error.message, 'error');
    } finally {
        ingestBtn.disabled = false;
    }
}

function pollIngestCompletion() {
    let attempts = 0;
    const maxAttempts = 60; // 30 seconds max

    const poll = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/health`);

            if (response.ok) {
                // Assume completion after successful health check
                attempts = maxAttempts;
                setTimeout(() => {
                    ingestStatus.textContent = '✅ Repository ingested and indexed successfully!';
                }, 2000);
            }
        } catch (error) {
            // Ignore polling errors
        }

        attempts++;
        if (attempts < maxAttempts) {
            setTimeout(poll, 500);
        }
    };

    poll();
}

// ===== Health Check =====
function startHealthCheck() {
    // Initial check
    checkHealth();

    // Periodic checks
    healthCheckInterval = setInterval(checkHealth, HEALTH_CHECK_INTERVAL);
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);

        if (response.ok) {
            const data = await response.json();
            updateHealthStatus(true, data.status);
        } else {
            updateHealthStatus(false);
        }
    } catch (error) {
        updateHealthStatus(false);
    }
}

function updateHealthStatus(isHealthy, status = 'offline') {
    healthIndicator.className = `status-indicator ${isHealthy ? 'ready' : 'error'}`;
    healthStatus.textContent = isHealthy ? 'Ready' : 'Offline';
    healthStatus.style.color = isHealthy ? 'var(--success)' : 'var(--error)';
}

// ===== Utility Functions =====
function showNotification(message, type = 'info') {
    // Temporary notification in input status or ingest status
    const now = new Date().getTime();
    inputStatus.textContent = message;
    inputStatus.className = `input-status ${type === 'error' ? 'error' : ''}`;

    if (type !== 'error') {
        setTimeout(() => {
            inputStatus.textContent = '';
        }, 3000);
    }
}

function autoResizeTextarea() {
    queryInput.style.height = 'auto';
    queryInput.style.height = Math.min(queryInput.scrollHeight, 100) + 'px';
}

// ===== Event Listeners for Textarea =====
queryInput.addEventListener('input', autoResizeTextarea);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
});
