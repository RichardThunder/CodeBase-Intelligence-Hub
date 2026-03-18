# Workflow Triggers & Event Reference

Quick reference for what triggers each GitHub Actions workflow and how to customize them.

---

## 📊 Trigger Summary Table

| Workflow | Trigger Events | Branches | Default | Custom |
|----------|---|---|---|---|
| **ci.yml** | push, pull_request | main, develop | ✅ | ✅ |
| **deploy.yml** | push (main only), workflow_run | main | ✅ | ✅ |
| **code-quality.yml** | push, pull_request, schedule | main, develop | ✅ | ✅ |
| **manual-ingest.yml** | workflow_dispatch | any | N/A | Manual UI |

---

## 🔄 CI/CD Pipeline (`ci.yml`)

### Default Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
```

### What This Means

- ✅ Runs on every push to `main` or `develop`
- ✅ Runs on every pull request targeting `main` or `develop`
- ❌ Does NOT run on tags or other branches
- ❌ Does NOT run on commits to other branches

### Customize Triggers

**Run only on main:**
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

**Include all branches:**
```yaml
on:
  push:
  pull_request:
```

**Run on specific file changes:**
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'
```

**Run on tags:**
```yaml
on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
```

---

## 🚀 Deploy to Production (`deploy.yml`)

### Default Triggers

```yaml
on:
  push:
    branches: [ main ]
    tags: [ "v*" ]
  workflow_run:
    workflows: [ "CI/CD Pipeline" ]
    branches: [ main ]
    types: [ completed ]
```

### What This Means

- ✅ Runs when pushing to `main` branch
- ✅ Runs when pushing version tags (v1.0.0, v2.1.3, etc.)
- ✅ Runs after CI/CD Pipeline completes successfully
- ❌ Only pushes to registry on successful CI
- ❌ Does NOT run on develop branch

### Customize Triggers

**Deploy only on tags:**
```yaml
on:
  push:
    tags: [ 'v*' ]
```

**Deploy on every main push (without waiting for CI):**
```yaml
on:
  push:
    branches: [ main ]
```

**Add release trigger:**
```yaml
on:
  release:
    types: [ published ]
```

---

## 📊 Code Quality Analysis (`code-quality.yml`)

### Default Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

### What This Means

- ✅ Runs on push to `main` or `develop`
- ✅ Runs on pull requests
- ✅ Runs automatically every day at 2 AM UTC
- ❌ Cron schedule uses UTC timezone

### Customize Triggers

**Change schedule frequency:**

```yaml
schedule:
  - cron: '0 9 * * 1'  # Weekly Monday at 9 AM
```

**Cron Expression Reference:**
```
minute (0-59)
hour (0-23)
day of month (1-31)
month (1-12)
day of week (0-6, 0=Sunday)

Examples:
0 0 * * *      = Every day at midnight
0 9 * * 1-5    = Weekdays at 9 AM
0 */6 * * *    = Every 6 hours
0 0 1 * *      = First day of month
```

**Skip schedule, only manual + PR:**
```yaml
on:
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:
```

---

## 🎯 Manual Repository Ingestion (`manual-ingest.yml`)

### Default Triggers

```yaml
on:
  workflow_dispatch:
    inputs:
      repo_path:
        description: 'Repository path to ingest'
        required: true
        default: '.'
      collection_name:
        description: 'ChromaDB collection name'
        required: false
        default: 'codebase_v1'
      use_parser:
        type: boolean
        description: 'Use language-aware parser'
        required: false
        default: true
```

### What This Means

- ✅ Triggered manually from GitHub UI (Actions tab)
- ✅ Prompts user for `repo_path`, `collection_name`, `use_parser`
- ❌ Does NOT trigger automatically
- ❌ No branch restrictions

### Trigger from Command Line

```bash
# Using GitHub CLI
gh workflow run manual-ingest.yml \
  -f repo_path="." \
  -f collection_name="codebase_v1" \
  -f use_parser="true"
```

### Add More Input Options

```yaml
inputs:
  repo_path:
    description: 'Repository path'
    required: true
    default: '.'
  collection_name:
    description: 'Collection name'
    required: false
    default: 'codebase_v1'
  use_parser:
    type: boolean
    description: 'Use language-aware parser'
    default: true
  max_chunk_size:
    description: 'Max chunk size'
    required: false
    default: '1000'
```

---

## 🎮 Advanced Trigger Scenarios

### Scenario 1: Run CI on Feature Branches

**Requirement:** Run CI on all branches, but deploy only on main

```yaml
# ci.yml
on:
  push:
  pull_request:

# deploy.yml
on:
  push:
    branches: [ main ]
```

### Scenario 2: Skip CI for Documentation Changes

```yaml
on:
  push:
    branches: [ main ]
    paths-ignore:
      - '**.md'
      - 'docs/**'
  pull_request:
    branches: [ main ]
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

### Scenario 3: Run Security Scan Only on main

```yaml
on:
  push:
    branches: [ main ]
  workflow_dispatch:
```

### Scenario 4: Deploy on Release Creation

```yaml
on:
  release:
    types: [ published, edited ]
```

---

## 🔐 Protected Branch Rules

Configure branch protection to enforce CI/CD:

1. Go to **Settings → Branches**
2. Add rule for `main` branch
3. Enable:
   - ✅ Require CI/CD Pipeline to pass
   - ✅ Require status checks to pass
   - ✅ Require code reviews
   - ✅ Require branches to be up to date

---

## 📈 Monitoring Triggers

### View All Workflows

```bash
gh workflow list
```

### View Specific Workflow Runs

```bash
gh run list --workflow=ci.yml
gh run list --workflow=deploy.yml
```

### Watch Real-time Execution

```bash
gh run watch
```

### Check Scheduled Runs

```bash
# List upcoming scheduled runs
gh api repos/OWNER/REPO/actions/workflows --jq '.workflows[] | select(.name | contains("quality"))'
```

---

## ⏰ Timezone Reference

GitHub Actions uses **UTC for all scheduled times**.

**Convert to your timezone:**
```
UTC+0  = 0
UTC+1  = -1
UTC+2  = -2
...
UTC-5  = +5
UTC-8  = +8

Example: Run at 9 AM EST (UTC-5)
EST 9 AM = UTC 2 PM = 14 0
cron: '0 14 * * *'
```

---

## 🚨 Trigger Limitations

- **Rate limiting:** GitHub Actions has rate limits per repository
- **Concurrent runs:** Default 1 concurrent run per workflow
- **Timeout:** Individual jobs have 6-hour timeout
- **Storage:** Limited artifact storage (90 days default)
- **Schedule:** Minimum cron interval is 5 minutes

---

## ✅ Best Practices

1. **Be specific with branches:**
   ```yaml
   push:
     branches: [ main, develop ]  # ✅ Good
   ```

2. **Use path filters to save time:**
   ```yaml
   paths:
     - 'src/**'
     - 'tests/**'
   ```

3. **Avoid too many scheduled runs:**
   - Daily is usually sufficient
   - Midnight UTC can have high load

4. **Use workflow_dispatch for manual control:**
   ```yaml
   on:
     workflow_dispatch:
   ```

5. **Chain workflows efficiently:**
   ```yaml
   on:
     workflow_run:
       workflows: [ "CI/CD Pipeline" ]
       types: [ completed ]
   ```

---

## 🔍 Debugging Trigger Issues

### Workflow Not Running

```bash
# Check if workflow is enabled
gh api repos/OWNER/REPO/actions/workflows/ci.yml

# Enable workflow
gh api repos/OWNER/REPO/actions/workflows/ci.yml/enable -X PUT

# Check recent runs
gh run list --limit 20
```

### Scheduled Workflow Not Running

1. Verify cron syntax: https://crontab.guru
2. Check timezone (GitHub uses UTC)
3. Ensure workflow file is in default branch
4. Check for syntax errors in YAML

### Too Many Runs

```yaml
# Add concurrency to limit runs
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## 📚 References

- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Events That Trigger Workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Cron Expression Validator](https://crontab.guru)
- [GitHub Actions Limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)

---

## 💡 Quick Reference

**Run on every push:**
```yaml
on: push
```

**Run on pull requests:**
```yaml
on: pull_request
```

**Run on schedule:**
```yaml
on:
  schedule:
    - cron: '0 2 * * *'
```

**Run manually:**
```yaml
on: workflow_dispatch
```

**Combine all:**
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
```

---

**Ready to customize your workflows!** 🚀
