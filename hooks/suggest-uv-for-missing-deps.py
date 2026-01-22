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

    # Build the guidance message
    guidance_parts = ["**MISSING DEPENDENCY DETECTED**"]

    if missing_module:
        guidance_parts.append(f"\nThe script requires `{missing_module}` which is not installed.")

    guidance_parts.append("""

**Consider using `uv run` with PEP 723 inline dependencies:**

1. **Add a PEP 723 header to your Python script:**
   ```python
   # /// script
   # dependencies = [
   #     "pandas",
   #     "requests>=2.28.0",
   # ]
   # ///

   import pandas as pd
   # ... rest of your script
   ```

2. **Run with uv:**
   ```bash
   uv run --script script.py
   ```

**Benefits:**
- Dependencies are declared inline with the script
- Works reliably in sandbox mode
- Creates isolated environment per script (no global installs)
- Reproducible across environments

**Alternative (not recommended in sandbox mode):**
If you prefer to use system Python or an activated virtual environment:
```bash
pip install""")

    if missing_module:
        guidance_parts.append(f" {missing_module}")
    else:
        guidance_parts.append(" <package-name>")

    guidance_parts.append("\n```")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": "".join(guidance_parts)
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
