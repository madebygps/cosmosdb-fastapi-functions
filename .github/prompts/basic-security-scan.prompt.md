---
mode: 'agent'
tools: ['problems']
description: 'Perform comprehensive Python security scan for Azure Functions project'
---

# Python Security Scan for ${workspaceFolder}

Perform a comprehensive security scan of this Azure Functions Python project using industry-standard tools. Focus on identifying vulnerabilities in dependencies, code patterns, and security configurations.

## Tasks

Execute the following steps in ORDER to ensure a thorough security assessment:

1. Ensure the Python Virtual Environment set in .vscode/settings.json is activated

2. Use the #problems tool to check for any existing security-related warnings or errors in the workspace

3. Check if security tools are installed, check all tools at once - install only if any are missing using this command:

```sh
    (semgrep --version && pip-audit --version && bandit --version) || uv pip install semgrep pip-audit bandit
```

4. Do a Dependency Vulnerability Scan with pip-audit using the following command:

```sh
    pip-audit --desc --fix
```

5. Scan Python files for security issues, exclude virtual environments, using the following Semgrep command:

```sh
    semgrep --config=auto --include="*.py" --exclude=".venv,__pycache__,*.pyc" --json --output=semgrep-report.json .
```

6. Scan for Python-specific issues, exclude test files and virtual environments, with the following Bandit command:

```sh
    bandit -r ./inventory_api ./function_app.py --exclude ".venv,tests" --format json -o bandit-report.json
```

7. Report your Findings with a structured security report summarizing the results of the scans. Include the following details:
    - Total vulnerabilities found (by severity)
    - Critical issues requiring immediate attention
    - Recommendations for security improvements