"""Static security analysis tools."""
import re
from pathlib import Path
from langchain.tools import tool


# Security patterns to detect
SECURITY_PATTERNS = {
    'sql_injection': [
        (r'f["\']SELECT.*{.*}', 'Potential SQL injection via f-string'),
        (r'\.format\(.*\).*SELECT', 'Potential SQL injection via .format()'),
        (r'%s.*SELECT|SELECT.*%s', 'Potential SQL injection via string formatting'),
        (r'execute\(["\'][^"\']*\+', 'SQL query concatenation detected'),
    ],
    'command_injection': [
        (r'os\.system\([^)]*\+', 'Command injection via os.system concatenation'),
        (r'subprocess\.(call|run|Popen)\([^)]*\+', 'Command injection via subprocess concatenation'),
        (r'eval\(', 'Use of eval() is dangerous'),
        (r'exec\(', 'Use of exec() is dangerous'),
    ],
    'hardcoded_secrets': [
        (r'password\s*=\s*["\'][^"\']{8,}["\']', 'Potential hardcoded password'),
        (r'api_key\s*=\s*["\'][^"\']{16,}["\']', 'Potential hardcoded API key'),
        (r'secret\s*=\s*["\'][^"\']{8,}["\']', 'Potential hardcoded secret'),
        (r'token\s*=\s*["\'][^"\']{16,}["\']', 'Potential hardcoded token'),
    ],
    'weak_crypto': [
        (r'hashlib\.(md5|sha1)\(', 'Weak hash function (MD5/SHA1) detected'),
        (r'random\.random\(', 'Using random.random() for security purposes is unsafe'),
    ],
}


@tool
def check_security(file_path: str) -> str:
    """
    Perform basic security pattern matching on a Python file.
    Detects common security issues like SQL injection, command injection, etc.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Security findings or all-clear message
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        findings = []

        for category, patterns in SECURITY_PATTERNS.items():
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            'line': line_num,
                            'category': category,
                            'description': description,
                            'code_snippet': line.strip()[:80],
                        })

        if not findings:
            return f"No security issues detected in {file_path}."

        result = f"🔒 Security Analysis for {file_path}:\n"
        result += f"Found {len(findings)} potential security issue(s):\n\n"

        for finding in findings:
            result += f"  Line {finding['line']}: [{finding['category'].upper()}]\n"
            result += f"    {finding['description']}\n"
            result += f"    Code: {finding['code_snippet']}\n\n"

        return result

    except Exception as e:
        return f"Error performing security check: {str(e)}"


@tool
def check_imports(file_path: str) -> str:
    """
    Analyze import statements for potential issues.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Import analysis results
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        import_lines = []
        unused_imports = []

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append((line_num, line))

        if not import_lines:
            return f"No imports found in {file_path}."

        result = f"Import Analysis for {file_path}:\n"
        result += f"  Total imports: {len(import_lines)}\n"

        # Check for wildcard imports
        wildcards = [line for _, line in import_lines if line.endswith('import *')]
        if wildcards:
            result += f"\n  ⚠️  Wildcard imports found (not recommended):\n"
            for line in wildcards[:3]:
                result += f"    - {line}\n"

        return result

    except Exception as e:
        return f"Error analyzing imports: {str(e)}"
