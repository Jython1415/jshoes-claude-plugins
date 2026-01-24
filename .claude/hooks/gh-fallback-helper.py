#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gh-fallback-helper: Guide Claude to use GitHub API when gh CLI is unavailable.

Event: PostToolUseFailure (Bash)

Purpose: Detects when a `gh` CLI command fails due to `gh` being unavailable, and provides
guidance on using the GitHub REST API with curl instead when GITHUB_TOKEN is available.

Behavior:
- Detects failed `gh` CLI commands (when error contains "command not found" or "not found")
- Checks if `GITHUB_TOKEN` environment variable is available
- Provides comprehensive guidance on using GitHub REST API with curl
- Includes practical examples for common operations (list issues, create PR, update PR, search)
- Shows how to authenticate using the GITHUB_TOKEN
- Provides tips for parsing JSON responses with jq or python

Triggers on:
- Bash command contains `gh`
- Error output contains "command not found" or "not found"
- `GITHUB_TOKEN` environment variable is available and non-empty

Does NOT trigger when:
- `gh` CLI is available and command succeeds
- `GITHUB_TOKEN` is not available (no alternative can be provided)
- Command doesn't contain `gh`
- Non-Bash tools
- Error is not related to gh unavailability

Guidance provided:
- 5 practical curl examples with proper authentication headers:
  1. List issues
  2. Create pull request
  3. Get issue/PR details
  4. Update PR/issue
  5. Search issues
- Tips on using `-s` flag and JSON parsing with jq or python
- Link to GitHub API documentation
- Example conversion from gh command to curl equivalent

Benefits:
- Enables GitHub operations when gh CLI is unavailable
- Provides concrete, copy-paste-ready examples
- Works alongside gh-web-fallback.py as defense in depth (this hook is reactive, that one is proactive)
- Educates about GitHub REST API usage
- Includes authentication and formatting guidance

Limitations:
- Only detects curl-based workflows (not wget or other HTTP clients)
- Requires GITHUB_TOKEN to be available
- Only monitors Bash tool (not direct API operations from other tools)

Relationship with other hooks:
- **Complements gh-web-fallback.py**: That hook provides proactive guidance (PreToolUse) before
  gh fails; this hook provides reactive guidance (PostToolUseFailure) after gh fails
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
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues"
   ```

2. **Create pull request:**
   ```bash
   curl -X POST \\
     -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls" \\
     -d '{{"title":"PR Title","head":"branch-name","base":"main","body":"PR description"}}'
   ```

3. **Get issue/PR details:**
   ```bash
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues/NUMBER"
   ```

4. **Update PR/issue:**
   ```bash
   curl -X PATCH \\
     -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls/NUMBER" \\
     -d '{{"body":"Updated description"}}'
   ```

5. **Search issues:**
   ```bash
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues?state=all"
   ```

**Tips:**
- Use `jq` or `python3 -m json.tool` to parse JSON responses
- Use `$(printenv GITHUB_TOKEN)` instead of `$GITHUB_TOKEN` when using pipes
- GitHub API docs: https://docs.github.com/en/rest

**Example converting your gh command:**
If you tried: `gh issue list`
Use instead: `curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/OWNER/REPO/issues"`"""
        }
    }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
