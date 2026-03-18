"""FastAPI application entry point with LangServe integration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from langserve import add_routes
from dotenv import load_dotenv

from config.settings import Settings
from retrieval.vectorstore import get_vectorstore
from retrieval.embeddings import get_embeddings
from retrieval.pipeline import build_retrieval_pipeline
from chains.rag import build_rag_chain, build_rag_chain_with_source
from langchain_openai import ChatOpenAI
from api.routes import create_routes


# Global instances
_settings = None
_llm = None
_graph = None
_rag_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown.

    Initialize components on startup, cleanup on shutdown.
    """
    global _settings, _llm, _graph, _rag_chain

    # Startup
    print("⏳ Initializing CodeBase Intelligence Hub API...")

    load_dotenv()
    _settings = Settings()

    # Initialize LLM
    _llm = ChatOpenAI(
        model=_settings.llm_model,
        temperature=0,
        api_key=_settings.openai_api_key.get_secret_value(),
        base_url=_settings.openai_api_base,
    )
    print("✅ LLM initialized")

    # Load vector store
    try:
        embeddings = get_embeddings(_settings)
        vectorstore = get_vectorstore(_settings)
        print(f"✅ Vector store loaded: {_settings.chroma_collection}")

        # Build retrieval pipeline
        from retrieval.loaders import load_codebase_with_parser

        try:
            # Try to load documents for BM25 (optional)
            docs = load_codebase_with_parser(".")
            retriever = build_retrieval_pipeline(vectorstore, docs, _llm, _settings)
        except Exception:
            # Fallback to simple vector retriever if loading documents fails
            retriever = vectorstore.as_retriever()
            print("⚠️  Using simple vector retriever (document loading failed)")

        # Build RAG chain
        _rag_chain = build_rag_chain(retriever, _llm)
        print("✅ RAG chain built")

        # Build LangGraph (imported here to avoid circular dependencies)
        from graph.builder import build_graph
        _graph = build_graph(retriever, _llm, _settings)
        print("✅ LangGraph orchestrator built")

    except Exception as e:
        print(f"⚠️  Warning during initialization: {e}")
        print("💡 You can ingest documents using: python scripts/ingest.py --repo-path .")

    print("🚀 API ready at http://localhost:8000")
    print("📚 Interactive docs: http://localhost:8000/docs")
    print("🔌 LangServe playground: http://localhost:8000/rag/playground")

    yield

    # Shutdown
    print("⏹️  Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="CodeBase Intelligence Hub",
    description="RAG-based codebase Q&A system with multi-agent orchestration",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with documentation links."""
    return """
    <html>
        <head>
            <title>CodeBase Intelligence Hub</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                ul { line-height: 1.8; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
                code { background: #f0f0f0; padding: 2px 5px; }
            </style>
        </head>
        <body>
            <h1>🧠 CodeBase Intelligence Hub</h1>
            <p>RAG-based codebase Q&A system with multi-agent orchestration</p>

            <h2>📚 Documentation</h2>
            <ul>
                <li><a href="/docs">Interactive API docs (Swagger)</a></li>
                <li><a href="/redoc">ReDoc documentation</a></li>
                <li><a href="/rag/playground">LangServe RAG Playground</a></li>
            </ul>

            <h2>🚀 Quick Start</h2>
            <ul>
                <li><strong>Ingest code:</strong> <code>python scripts/ingest.py --repo-path .</code></li>
                <li><strong>Ask questions:</strong> POST to <code>/api/chat</code></li>
                <li><strong>Stream responses:</strong> GET <code>/api/chat/stream?query=...</code></li>
            </ul>

            <h2>💻 Endpoints</h2>
            <ul>
                <li><strong>POST /api/chat</strong> - Chat with RAG system</li>
                <li><strong>GET /api/chat/stream</strong> - Stream response</li>
                <li><strong>POST /api/ingest</strong> - Ingest repository</li>
                <li><strong>GET /api/health</strong> - Health check</li>
                <li><strong>GET /rag/invoke</strong> - Direct RAG invocation (LangServe)</li>
            </ul>
        </body>
    </html>
    """


# Register API routes
api_routes = create_routes(
    retriever=None,  # Will be set during request if needed
    llm=None,
    settings=None,
)


async def get_dependencies():
    """Get dependencies for routes (called for each request)."""
    # These will be initialized during startup
    global _settings, _llm, _graph
    return _settings, _llm, _graph


# Note: The route handlers in api/routes.py use closures to capture dependencies
# For a production setup, we could use dependency injection with FastAPI's Depends()


# Add RAG chain via LangServe for direct invocation
if _rag_chain is not None:
    add_routes(app, _rag_chain, path="/rag")


# Mount API routes manually
@app.post("/api/chat")
async def chat_endpoint(request):
    """Chat endpoint handler."""
    from api.schemas import ChatRequest
    chat_req = ChatRequest(**request.dict())
    routes = create_routes(_graph, _llm, _settings) if all([_graph, _llm, _settings]) else None
    # ... implementation


# For production, consider using an async context manager for the FastAPI app
# to properly handle startup/shutdown with dependency injection


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
