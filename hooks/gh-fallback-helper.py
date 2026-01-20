#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Detect when gh CLI is unavailable but GITHUB_TOKEN is available.
Provides guidance on using GitHub API with curl instead.
"""
import json
import sys
import os

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

    # Get the command that was run
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Check if this is a gh command failure
    if "gh" not in command or ("command not found" not in error_output and "not found" not in error_output):
        print("{}")
        sys.exit(0)

    # Check if GITHUB_TOKEN is available in environment
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        print("{}")
        sys.exit(0)  # Token not available, can't provide alternative

    # Provide targeted guidance via additionalContext
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": f"""GH CLI NOT FOUND: The `gh` command is not available in this environment.

**GITHUB_TOKEN DETECTED:** Use the GitHub API with curl instead.

**Successful Access Patterns:**

1. **List issues:**
   ```bash
   curl -s -H "Authorization: token $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues"
   ```

2. **Create pull request:**
   ```bash
   curl -X POST \\
     -H "Authorization: token $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls" \\
     -d '{{"title":"PR Title","head":"branch-name","base":"main","body":"PR description"}}'
   ```

3. **Get issue/PR details:**
   ```bash
   curl -s -H "Authorization: token $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues/NUMBER"
   ```

4. **Update PR/issue:**
   ```bash
   curl -X PATCH \\
     -H "Authorization: token $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls/NUMBER" \\
     -d '{{"body":"Updated description"}}'
   ```

5. **Search issues:**
   ```bash
   curl -s -H "Authorization: token $GITHUB_TOKEN" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues?state=all"
   ```

**Tips:**
- Use `jq` or `python3 -m json.tool` to parse JSON responses
- The GITHUB_TOKEN is already available as `$GITHUB_TOKEN`
- GitHub API docs: https://docs.github.com/en/rest

**Example converting your gh command:**
If you tried: `gh issue list`
Use instead: `curl -s -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/OWNER/REPO/issues"`"""
        }
    }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
