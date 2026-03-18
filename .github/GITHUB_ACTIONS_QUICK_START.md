# GitHub Actions Quick Start

## 🚀 Setup in 3 Steps

### Step 1: Add Secrets to GitHub

Go to **Settings → Secrets and variables → Actions** and add:

```yaml
OPENAI_API_KEY       # Your API key
OPENAI_API_BASE      # Your API base URL (e.g., https://api.openai.com/v1)
```

(Optional for Slack notifications):
```yaml
SLACK_WEBHOOK        # Your Slack webhook URL
```

### Step 2: Push to Trigger Workflows

The workflows automatically trigger on:
- ✅ Push to `main` or `develop`
- ✅ Pull requests
- ✅ Tag creation (for releases)

Just push your code:
```bash
git add .
git commit -m "Add CodeBase Intelligence Hub implementation"
git push origin main
```

### Step 3: Monitor in GitHub UI

1. Go to **Actions** tab
2. Watch the workflows run in real-time
3. Click on any workflow to see detailed logs

---

## 📋 Workflow Cheat Sheet

### On Every Push to Main/Develop

| Workflow | What It Does | Time |
|----------|------------|------|
| **CI/CD Pipeline** | Lint, type-check, build, test | ~5-10 min |
| **Code Quality** | Complexity, coverage, SAST | ~3-5 min |
| **Deploy** | Build & push Docker image | ~5 min |

### Manual Workflows

**Repository Ingestion** (Manual trigger):
```bash
# Via GitHub UI: Actions → Manual Repository Ingestion → Run workflow
```

---

## 🔍 View Workflow Results

### In GitHub UI
1. Click **Actions** tab
2. Select workflow name (e.g., "CI/CD Pipeline")
3. Click on a run to see details
4. Click job to expand logs

### Via Command Line
```bash
# Install GitHub CLI
brew install gh

# View last 5 workflow runs
gh run list

# View specific workflow
gh run list --workflow=ci.yml

# View run details with logs
gh run view <RUN_ID> --log

# Cancel a running workflow
gh run cancel <RUN_ID>
```

---

## 📊 Check Pipeline Status

### Status Badge
Add to your README:
```markdown
[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml)
```

### Via GitHub CLI
```bash
gh run view --repo YOUR_USERNAME/CodeBase-Intelligence-Hub
```

---

## 🐛 Debugging Failed Workflows

### 1. Check the logs
```bash
# View full logs for failed run
gh run view <RUN_ID> --log

# Search for error messages
gh run view <RUN_ID> --log | grep "Error\|Failed"
```

### 2. Common Issues & Solutions

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | Dependencies not installed; check `uv sync` |
| `bandit: command not found` | Dev dependencies missing; check secrets & env |
| `API_KEY not set` | Add `OPENAI_API_KEY` to Secrets |
| `Docker build failed` | Check Dockerfile; ensure file paths are correct |
| `Type check failed` | Run `uv run pyright .` locally to debug |

### 3. Run Locally to Debug
```bash
# Install dev dependencies
uv sync

# Run linting
uv run ruff check .

# Run type checking
uv run pyright .

# Run security scan
uv run bandit -r .

# Try import test
uv run python -c "from config.settings import Settings"
```

---

## 🔄 Continuous Integration Flow

```
Push to main/develop
       ↓
[CI/CD Pipeline]
  ├─ Lint & Format
  ├─ Type Check
  ├─ Build & Test
  ├─ Docker Build
  └─ Security Scan
       ↓
   All Pass?
  ↙          ↘
YES          NO
↓            ↓
Deploy    ✗ FAILED
↓           (Check logs)
[Push Docker]
↓
Monitor Slack (optional)
```

---

## 📦 Docker Image Locations

### GitHub Container Registry (GHCR)
```bash
# After successful main branch CI/CD
docker pull ghcr.io/YOUR_USERNAME/codebase-intelligence-hub:latest

# Authenticate
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Run
docker run -p 8000:8000 ghcr.io/YOUR_USERNAME/codebase-intelligence-hub:latest
```

---

## 🎯 Best Practices

### ✅ DO:
- Push frequently with clear commit messages
- Check Actions tab before major pushes
- Review workflow logs if something fails
- Keep secrets secure (never commit `.env`)
- Test locally before pushing

### ❌ DON'T:
- Commit sensitive data (API keys, tokens)
- Ignore workflow failures
- Push directly to main without testing
- Create overly large commits
- Leave broken code on main branch

---

## 🚨 Troubleshooting Checklist

- [ ] Secrets added to GitHub Settings?
- [ ] Correct GitHub repository in links?
- [ ] Workflows enabled in Actions tab?
- [ ] Latest code pushed to branch?
- [ ] Dependencies installed locally with `uv sync`?
- [ ] No uncommitted changes blocking push?
- [ ] Branch protection rules configured?
- [ ] Docker registry credentials set?

---

## 📚 Learn More

- [Full Workflow Documentation](./workflows/README.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## 💬 Getting Help

1. Check **Actions** tab for detailed logs
2. Review [Workflow README](./workflows/README.md)
3. Run commands locally to reproduce issues
4. Check [GitHub Actions Troubleshooting](https://docs.github.com/en/actions/troubleshooting)

**Next Step:** Push your code and watch the workflows run! 🎉
