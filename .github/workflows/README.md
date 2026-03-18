# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the CodeBase Intelligence Hub project.

## Workflows Overview

### 1. **CI/CD Pipeline** (`ci.yml`)
**Trigger:** On push to `main` or `develop`, and on pull requests

**Jobs:**
- **Lint & Format Check**: Runs `ruff` to check code style and formatting
- **Type Check**: Runs `pyright` for Python type checking
- **Build & Test**: Installs dependencies and verifies all imports
- **Docker Build**: Builds Docker image (pushes to registry on main branch)
- **Security Scan**: Runs `bandit` for security issues and `trufflesecurity` for secrets
- **Notification**: Comments on PR if CI fails

**Status Badge:**
```markdown
[![CI/CD](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml)
```

---

### 2. **Deploy to Production** (`deploy.yml`)
**Trigger:** On push to `main` branch and on successful CI/CD completion

**Jobs:**
- **Deploy**: Builds and pushes Docker image to GitHub Container Registry (GHCR)
- **Notify Slack**: Sends deployment status to Slack (optional)

**Setup:**
1. Store Docker registry credentials in GitHub Secrets
2. (Optional) Add `SLACK_WEBHOOK` secret for Slack notifications
3. (Optional) Configure cloud provider deployment (Cloud Run, Kubernetes, etc.)

**Environment Variables:**
- `REGISTRY`: `ghcr.io` (GitHub Container Registry)
- `IMAGE_NAME`: Automatically set to repository path

---

### 3. **Code Quality Analysis** (`code-quality.yml`)
**Trigger:** Push to `main`/`develop`, pull requests, and daily at 2 AM UTC

**Jobs:**
- **Complexity Analysis**: Checks cyclomatic complexity with `radon`
- **Dependency Check**: Scans for known vulnerabilities with `pip-audit`
- **Code Coverage**: Runs pytest with coverage reporting
- **SAST Analysis**: Security analysis with `semgrep` and `bandit`
- **Summary**: Generates quality report

**Artifacts Generated:**
- `code-quality-reports/` — Complexity and maintainability reports
- `dependency-audit/` — Security audit results
- `coverage-report/` — HTML coverage report
- `sast-reports/` — Security analysis results

---

### 4. **Manual Repository Ingestion** (`manual-ingest.yml`)
**Trigger:** Manual workflow dispatch via GitHub UI

**Inputs:**
- `repo_path` — Path to ingest (default: `.`)
- `collection_name` — ChromaDB collection (default: `codebase_v1`)
- `use_parser` — Use language-aware parser (default: `true`)

**Usage:**
1. Go to **Actions** tab
2. Select **Manual Repository Ingestion**
3. Click **Run workflow**
4. Fill in parameters
5. Monitor logs in workflow output

**Example:**
```
repo_path: .
collection_name: my-repo-v1
use_parser: true
```

---

## Environment & Secrets Setup

### Required Secrets

Add these to **Settings → Secrets and variables → Actions:**

```yaml
OPENAI_API_KEY       # Your LLM provider API key
OPENAI_API_BASE      # API base URL (e.g., for GLM)
GITHUB_TOKEN         # Automatically available (don't set manually)
```

### Optional Secrets

```yaml
SLACK_WEBHOOK        # For Slack notifications (deploy.yml)
DOCKER_USERNAME      # If using Docker Hub instead of GHCR
DOCKER_PASSWORD      # If using Docker Hub
```

---

## Docker Registry Setup

### Using GitHub Container Registry (GHCR) — Recommended

No additional setup needed. Workflows automatically push to:
```
ghcr.io/YOUR_USERNAME/codebase-intelligence-hub:latest
```

Pull images:
```bash
docker pull ghcr.io/YOUR_USERNAME/codebase-intelligence-hub:latest
```

Authenticate:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Using Docker Hub (Alternative)

1. Create Docker Hub account and repository
2. Add `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets
3. Update workflow images to `docker.io/YOUR_USERNAME/codebase-intelligence-hub`

---

## Local Testing

### Test Locally Before Pushing

```bash
# Install dev dependencies
uv sync --extra=dev

# Run linting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run pyright .

# Run security scan
uv run bandit -r .

# Verify imports
uv run python -c "from config.settings import Settings; print('✓ OK')"

# Build Docker image
docker build -t codebase-hub:test -f docker/Dockerfile .
```

---

## Monitoring & Troubleshooting

### View Workflow Runs

1. Navigate to **Actions** tab in repository
2. Select workflow to view details
3. Click on a run to see job logs

### Common Issues

| Issue | Solution |
|-------|----------|
| "Import not found" error | Ensure `uv sync` runs before tests |
| Docker build fails | Check Dockerfile and dependencies |
| Type check errors | Run `uv run pyright . --version` locally |
| Linting warnings | Run `uv run ruff format .` to auto-fix |
| Secrets not available | Add them to repo Settings → Secrets |

### Check Workflow Status

```bash
# View last 5 runs
gh run list --limit 5

# View specific workflow
gh run list --workflow=ci.yml

# View specific run details
gh run view <RUN_ID> --log
```

---

## Customization

### Add Custom Steps

Edit `.github/workflows/*.yml` to add:
- Additional linters or checkers
- Custom test scripts
- Integration tests
- Deployment hooks

### Change Trigger Events

Modify the `on:` section:
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
```

### Conditional Job Execution

```yaml
jobs:
  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

---

## Best Practices

1. ✅ **Keep workflows DRY** — Use composite actions for reusable steps
2. ✅ **Set timeouts** — Prevent runaway jobs
3. ✅ **Cache dependencies** — Speed up runs with `actions/cache`
4. ✅ **Fail fast** — Use `continue-on-error: true` sparingly
5. ✅ **Document changes** — Update this README when adding workflows
6. ✅ **Test in dev branch first** — Before merging to main
7. ✅ **Review logs regularly** — Monitor for pattern changes
8. ✅ **Use pinned versions** — Avoid breaking action updates

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Security Hardening](https://docs.github.com/en/actions/security-guides)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## Support

For issues or questions:
1. Check workflow logs in Actions tab
2. Review this README
3. Open an issue in the repository
4. Check [GitHub Actions troubleshooting guide](https://docs.github.com/en/actions/troubleshooting)
