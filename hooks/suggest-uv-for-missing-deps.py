#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Detect Python import/module errors and suggest using uv run with PEP 723.
Only triggers when there's an actual dependency problem.

Triggers on:
- ModuleNotFoundError, ImportError, "No module named" errors
- Direct script execution: python script.py, python3 /path/to/script.py
- Quoted paths: python "my script.py", python 'test.py'

Does NOT trigger on:
- python -m module (module execution)
- python -c "code" (one-liners)
- python --version, --help (utility commands)
- python -S script.py (flags before script - intentional limitation)
- Non-import errors (SyntaxError, NameError, etc.)
"""
import json
import sys
import re
import subprocess
import os

def is_tool_available(tool_name):
    """Check if a tool is available in PATH."""
    # Allow test override via environment variable
    test_override = os.environ.get(f"HOOK_TEST_{tool_name.upper()}_AVAILABLE")
    if test_override is not None:
        return test_override.lower() == "true"

    try:
        result = subprocess.run(["which", tool_name], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False

def generate_guidance(missing_module, has_uv):
    """Generate token-efficient guidance based on uv availability."""
    pkg = missing_module or "package-name"
    header = "**MISSING DEPENDENCY DETECTED**"

    if missing_module:
        header += f"\nThe script requires `{pkg}` which is not installed."

    if has_uv:
        # Token-efficient uv guidance
        body = f"""

**Quick fix:** `uv run --with {pkg} script.py`

**Reusable (PEP 723):**
```python
# /// script
# dependencies = ["{pkg}"]
# ///
```
Run: `uv run --script script.py`

**Alternative:** `pip install {pkg}` (use venv)"""
    else:
        # Token-efficient pip guidance
        body = f"""

**Install:** `pip install {pkg}` (venv recommended)

**Try uv:** https://docs.astral.sh/uv/ - faster package manager with PEP 723 support"""

    return header + body

def main():
    input_data = json.load(sys.stdin)

    # Only process Bash tool failures
    if input_data.get("tool_name") != "Bash":
        print("{}")
        sys.exit(0)

    # Get error from either location:
    # - PostToolUseFailure: top-level "error" field
    # - PostToolUse: "tool_result.error" field
    error_output = input_data.get("error", "")
    if not error_output:
        tool_result = input_data.get("tool_result", {})
        error_output = tool_result.get("error", "")

    # Check for dependency-related errors
    has_import_error = (
        "ModuleNotFoundError" in error_output or
        "ImportError" in error_output or
        "No module named" in error_output
    )

    if not has_import_error:
        print("{}")
        sys.exit(0)  # Not a dependency error

    # Get the command that was run
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only suggest for direct Python script execution
    # Match unquoted: python script.py, python3 /path/to/script.py
    # Match quoted: python "my script.py", python 'test.py'
    # Exclude: python -c, python -m, python --version, etc.

    # Pattern 1: Unquoted script path (no spaces in path)
    # \bpython3?\s+ - python or python3 followed by whitespace
    # [^-\s"'] - first char must not be flag (-), space, or quote
    # [\w/.\-~]* - path characters (word, slash, dot, dash, tilde)
    # \.py\b - .py extension at word boundary
    unquoted_pattern = r'\bpython3?\s+[^-\s"\'][\w/.\-~]*\.py\b'

    # Pattern 2: Quoted script path (can have spaces)
    # \bpython3?\s+ - python or python3 followed by whitespace
    # ["'] - opening quote (single or double)
    # [^"']* - anything except quotes
    # \.py - .py extension
    # ["'] - closing quote
    quoted_pattern = r'\bpython3?\s+["\'][^"\']*\.py["\']'

    is_script_execution = bool(
        re.search(unquoted_pattern, command) or
        re.search(quoted_pattern, command)
    )

    if not is_script_execution:
        print("{}")
        sys.exit(0)  # Not a script execution, skip

    # Extract the module name from error if possible
    # Try "No module named 'X'" format first
    module_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_output)

    # If not found, try "from 'module'" format (ImportError)
    # Example: "ImportError: cannot import name 'DataFrame' from 'pandas'"
    if not module_match:
        module_match = re.search(r"from ['\"]([^'\"]+)['\"]", error_output)

    missing_module = module_match.group(1) if module_match else None

    # Extract top-level module for submodules (e.g., 'sklearn.ensemble' -> 'sklearn')
    # This ensures package suggestions work (pip install sklearn, not sklearn.ensemble)
    if missing_module and '.' in missing_module:
        missing_module = missing_module.split('.')[0]

    # Check if uv is available
    has_uv = is_tool_available("uv")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": generate_guidance(missing_module, has_uv)
        }
    }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # On error, output empty JSON as per hook guidelines
        print(json.dumps({}))
        sys.exit(1)
