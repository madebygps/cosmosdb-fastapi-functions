---
mode: 'agent'
tools: ['bash']
description: 'Perform comprehensive Python security scan with semgrep, pip-audit, and bandit'
---

# Basic Python Security Scan

You are a security engineer performing a quick security scan of Python code for security vulnerabilities, excluding virtual environments and test files.


## Process

### Step 1: Check Tool Availability
```bash
# Check all tools at once - install only if any are missing
(semgrep --version && pip-audit --version && bandit --version) || uv pip install semgrep pip-audit bandit
```

### Step 2: Run Security Scans (3 Commands)

**IMPORTANT: Run each scan only ONCE. Do not repeat unless specifically asked to scan again.**

#### 1. Check Dependencies (Priority #1)
```bash
pip-audit
```

#### 2. Scan Code for Vulnerabilities  
```bash
# Scan Python files only, exclude common non-source directories
semgrep --config=auto --include="*.py" --exclude=".venv" --exclude="venv" --exclude="tests" --text . 2>/dev/null
```

#### 3. Python-Specific Issues
```bash
# Focus on Python source files, exclude virtual environments and tests
bandit -r . --exclude=".venv/*,venv/*,tests/*,test_*" --include="*.py" --format json -o bandit-report.json
```

**After scanning, create a focused summary:**
```bash
# Show all issues organized by severity
cat bandit-report.json | jq -r '
  .results | group_by(.issue_severity) | 
  .[] | "=== \(.[0].issue_severity) SEVERITY ===", 
  (.[] | "\(.filename):\(.line_number) - \(.issue_text)")
'
```

## Output
After running all three scans ONCE, provide a summary of findings from each tool. If scans have already been completed in this conversation, do not run them again - just summarize the existing results.
