#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gh-fallback-helper: Guide Claude to use GitHub API when gh CLI fails.

Event: PostToolUseFailure (Bash)

Purpose: Detects when a `gh` CLI command fails and provides guidance on using
the GitHub REST API with curl instead. Handles two failure modes:

1. **gh not found** — gh CLI is not installed (e.g., Claude Code Web).
   Requires GITHUB_TOKEN to provide an alternative.
2. **Sandbox TLS error** — gh is installed but the sandbox blocks Go's TLS
   certificate verification on macOS (`x509: OSStatus -26276`). curl works
   through the same proxy, and unauthenticated access works for public repos.

Triggers on:
- Bash command contains `gh`
- Error contains "command not found" / "not found" (gh missing case)
- Error contains "x509:" / "tls: failed to verify certificate" (sandbox TLS case)

Does NOT trigger when:
- Command doesn't contain `gh`
- Non-Bash tools
- Error is unrelated to gh unavailability or TLS

Relationship with other hooks:
- **Complements gh-web-fallback.py**: That hook provides proactive guidance (PreToolUse)
  before gh runs; this hook provides reactive guidance (PostToolUseFailure) after gh fails
"""
import json
import sys
import os


# TLS/x509 error patterns that indicate sandbox certificate verification failure
TLS_ERROR_PATTERNS = [
    "x509:",
    "tls: failed to verify certificate",
    "OSStatus -26276",
]


def is_gh_not_found(error_output):
    """Check if the error indicates gh CLI is not installed."""
    return "command not found" in error_output or "not found" in error_output


def is_tls_sandbox_error(error_output):
    """Check if the error indicates sandbox TLS certificate verification failure."""
    return any(pattern in error_output for pattern in TLS_ERROR_PATTERNS)


def build_not_found_guidance():
    """Guidance for when gh CLI is not installed (requires GITHUB_TOKEN)."""
    return """GH CLI NOT FOUND: The `gh` command is not available in this environment.

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
     -d '{"title":"PR Title","head":"branch-name","base":"main","body":"PR description"}'
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
     -d '{"body":"Updated description"}'
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
- GitHub API docs: https://docs.github.com/en/rest"""


def build_tls_sandbox_guidance(has_token):
    """Guidance for when gh fails due to sandbox TLS certificate verification."""
    auth_note = ""
    auth_header = ""
    if has_token:
        auth_header = '-H "Authorization: token $(printenv GITHUB_TOKEN)" \\\n     '
        auth_note = "**GITHUB_TOKEN detected** — using authenticated access."
    else:
        auth_note = (
            "No GITHUB_TOKEN set — examples below use unauthenticated access "
            "(works for public repos, 60 req/hr rate limit)."
        )

    return f"""GH SANDBOX TLS ERROR: `gh` failed because Claude Code's sandbox blocks Go's TLS
certificate verification on macOS (the sandbox Seatbelt profile denies access to
`com.apple.trustd.agent`). This affects all Go CLI tools (`gh`, `gcloud`, `terraform`, etc.).

**`curl` works through the same sandbox proxy** — use the GitHub REST API with curl instead.

{auth_note}

**Equivalent curl commands:**

1. **List issues (like `gh issue list`):**
   ```bash
   curl -s {auth_header}-H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues"
   ```

2. **Create PR (like `gh pr create`):**
   ```bash
   curl -s -X POST {auth_header}-H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls" \\
     -d '{{"title":"PR Title","head":"branch-name","base":"main","body":"Description"}}'
   ```

3. **View issue/PR (like `gh issue view N`):**
   ```bash
   curl -s {auth_header}-H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues/NUMBER"
   ```

4. **Merge PR (like `gh pr merge N`):**
   ```bash
   curl -s -X PUT {auth_header}-H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls/NUMBER/merge" \\
     -d '{{"merge_method":"squash"}}'
   ```

5. **Add PR review comment (like `gh pr review`):**
   ```bash
   curl -s -X POST {auth_header}-H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls/NUMBER/reviews" \\
     -d '{{"event":"COMMENT","body":"Review comment"}}'
   ```

**Tips:**
- Derive OWNER/REPO from: `git remote get-url origin`
- Parse JSON responses with `jq` or `python3 -c "import json,sys; ..."`
- `git push` works fine (git uses its own TLS, not Go's)
- GitHub API docs: https://docs.github.com/en/rest"""


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

    # Must be a gh command
    if "gh " not in command and not command.startswith("gh"):
        print("{}")
        sys.exit(0)

    github_token = os.environ.get("GITHUB_TOKEN", "").strip()

    # Check for TLS sandbox error (doesn't require GITHUB_TOKEN)
    if is_tls_sandbox_error(error_output):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUseFailure",
                "additionalContext": build_tls_sandbox_guidance(bool(github_token)),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Check for gh not found (requires GITHUB_TOKEN)
    if is_gh_not_found(error_output) and github_token:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUseFailure",
                "additionalContext": build_not_found_guidance(),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Unrelated error or no token for not-found case
    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    main()
