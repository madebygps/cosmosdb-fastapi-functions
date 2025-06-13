---
mode: 'agent'
description: 'Perform comprehensive Python security scan with semgrep, pip-audit, and bandit'
---

# Prerequisite: activate the project's virtual environment
```bash
# Make sure you are in the workspace root and venv is created
source .venv/bin/activate
```
  
Execute these tasks in this exact order:

1. Check Tool Availability

```bash
# Check all tools at once - install only if any are missing
(semgrep --version && pip-audit --version && bandit --version) || uv pip install semgrep pip-audit bandit
```

2. Scan for Vulnerable Dependencies

```bash
pip-audit
```

3. Scan for Code Vulnerabilities

```bash
# Scan Python files only, exclude common non-source directories, output JSON
semgrep --config=auto --include="*.py" --exclude=".venv" --json . > semgrep-report.json
```

4. Scan for Security Issues in Code

```bash
# Focus on Python source files, exclude virtual environments and tests, output JSON
bandit -r ./inventory_api --exclude ".venv" --format json -o bandit-report.json
```

5. Report back findings in a structured format

