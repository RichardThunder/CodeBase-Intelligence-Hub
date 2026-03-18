# Status Badges Template

Add these badges to your main `README.md` to show CI/CD status:

## Dynamic Badges (Auto-updating)

```markdown
<!-- CI/CD Pipeline Status -->
[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/ci.yml)

<!-- Code Quality -->
[![Code Quality](https://img.shields.io/badge/code%20quality-analysis-blue)](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions/workflows/code-quality.yml)

<!-- Python Version -->
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

## Visual Result

Copy the template above and replace:
- `YOUR_USERNAME` with your GitHub username
- `CodeBase-Intelligence-Hub` with your repository name

## Example Integration

Add to the top of your main README:

```markdown
# CodeBase Intelligence Hub

[![CI/CD Pipeline](https://github.com/USER/CodeBase-Intelligence-Hub/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/USER/CodeBase-Intelligence-Hub/actions/workflows/ci.yml)
[![Code Quality](https://img.shields.io/badge/code%20quality-analysis-blue)](https://github.com/USER/CodeBase-Intelligence-Hub/actions/workflows/code-quality.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A RAG-based codebase Q&A system with multi-agent orchestration.
```

## Badge Meanings

| Badge | Meaning |
|-------|---------|
| 🟢 Green | All CI tests passing |
| 🔴 Red | One or more tests failing |
| ⚪ White | Tests not run yet or unknown status |
| 🟡 Yellow | Tests running |

## Custom Shields.io Badges

For additional metrics:

```markdown
<!-- Downloads -->
[![Downloads](https://img.shields.io/github/downloads/USER/CodeBase-Intelligence-Hub/total)](https://github.com/USER/CodeBase-Intelligence-Hub/releases)

<!-- Stars -->
[![Stars](https://img.shields.io/github/stars/USER/CodeBase-Intelligence-Hub)](https://github.com/USER/CodeBase-Intelligence-Hub)

<!-- Last Commit -->
[![Last Commit](https://img.shields.io/github/last-commit/USER/CodeBase-Intelligence-Hub)](https://github.com/USER/CodeBase-Intelligence-Hub)

<!-- Contributors -->
[![Contributors](https://img.shields.io/github/contributors/USER/CodeBase-Intelligence-Hub)](https://github.com/USER/CodeBase-Intelligence-Hub)
```

## Docker Registry Badges

```markdown
<!-- Docker Image Size -->
[![Docker Image Size](https://img.shields.io/docker/image-size/USER/codebase-intelligence-hub/latest)](https://hub.docker.com/r/USER/codebase-intelligence-hub)

<!-- Docker Pulls -->
[![Docker Pulls](https://img.shields.io/docker/pulls/USER/codebase-intelligence-hub)](https://hub.docker.com/r/USER/codebase-intelligence-hub)
```

## Health Endpoints

Include links to health checks in your documentation:

```markdown
## Service Status

- **API Health**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **GitHub Actions**: [View all workflows](https://github.com/YOUR_USERNAME/CodeBase-Intelligence-Hub/actions)
```
