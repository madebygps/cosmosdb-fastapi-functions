---
mode: 'agent'
tools: ['problems']
description: 'Perform comprehensive Python security scan for Azure Functions project'
---

# Python Security Scan for ${workspaceFolder}

Perform a comprehensive security scan of this Azure Functions Python project using industry-standard tools. Focus on identifying vulnerabilities in dependencies, code patterns, and security configurations.

## Initial Checks

### Review Existing Problems
Check #problems for any existing security-related warnings or errors in the workspace before running security tools.

## Prerequisites

Ensure the project's virtual environment is activated:
```bash
source ${workspaceFolder}/.venv/bin/activate
```

## Security Scan Tasks

### 1. Tool Installation Check

First, verify all security tools are available:
```bash
# Check all tools at once - install only if any are missing
(semgrep --version && pip-audit --version && bandit --version) || uv pip install semgrep pip-audit bandit
```

### 2. Dependency Vulnerability Scan

Scan for known vulnerabilities in Python packages:
```bash
# Run pip-audit to check for vulnerable dependencies
pip-audit --desc --fix
```

### 3. Code Security Analysis with Semgrep

Perform static analysis for security patterns:
```bash
# Scan Python files for security issues, exclude virtual environments
semgrep --config=auto --include="*.py" --exclude=".venv,__pycache__,*.pyc" --json --output=semgrep-report.json .
```

### 4. Python Security Scan with Bandit

Run Bandit for Python-specific security issues:
```bash
# Focus on source code, exclude test files and virtual environments
bandit -r ./inventory_api ./function_app.py --exclude ".venv,tests" --format json -o bandit-report.json
```

## Report Format

After completing all scans, provide a structured security report:

### Summary
- Total vulnerabilities found (by severity)
- Critical issues requiring immediate attention
- Recommendations for security improvements