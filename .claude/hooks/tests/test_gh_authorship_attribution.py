#!/usr/bin/env python3
# /// script
# dependencies = ["pytest>=7.0.0"]
# ///
"""
Unit tests for gh-authorship-attribution.py hook

Run with:
  uv run pytest                                                  # Run all tests
  uv run pytest hooks/tests/test_gh_authorship_attribution.py  # Run this test file
  uv run pytest -v                                              # Verbose output

This test suite validates that the hook properly detects git commits and GitHub API
operations that need authorship attribution.
"""
import json
import subprocess
import time
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "gh-authorship-attribution.py"


def run_hook(tool_name: str, command: str, clear_cooldown: bool = True) -> dict:
    """
    Helper function to run the hook.

    Args:
        tool_name: The name of the tool being used
        command: The bash command to test
        clear_cooldown: Whether to clear cooldown state before running

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    # Clear cooldown state if requested
    if clear_cooldown:
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-authorship-cooldown"
        if state_file.exists():
            state_file.unlink()

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestGitCommitDetection:
    """Test git commit detection and attribution checking"""

    def test_git_commit_without_attribution_triggers(self):
        """Git commit without attribution should trigger guidance"""
        output = run_hook("Bash", 'git commit -m "Add feature"')
        assert "hookSpecificOutput" in output, "Should detect git commit without attribution"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "AUTHORSHIP ATTRIBUTION REQUIRED" in output["hookSpecificOutput"]["additionalContext"]
        assert "Co-authored-by" in output["hookSpecificOutput"]["additionalContext"]

    def test_git_commit_with_heredoc_without_attribution(self):
        """Git commit with heredoc but no attribution should trigger"""
        command = """git commit -m "$(cat <<'EOF'
Add new feature

This is a detailed description
EOF
)"
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect git commit without attribution"

    def test_git_commit_with_coauthored_by_attribution_silent(self):
        """Git commit with Co-authored-by should not trigger"""
        command = """git commit -m "$(cat <<'EOF'
Add feature

Co-authored-by: Claude (Anthropic AI) <claude@anthropic.com>
EOF
)"
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when attribution present"

    def test_git_commit_with_ai_assisted_attribution_silent(self):
        """Git commit with AI-assisted note should not trigger"""
        command = 'git commit -m "Add feature" -m "AI-assisted with Claude Code"'
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when attribution present"

    def test_git_commit_with_session_link_attribution_silent(self):
        """Git commit with claude.ai/code link should not trigger"""
        command = 'git commit -m "Add feature\n\nhttps://claude.ai/code/session_12345"'
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when session link present"

    def test_git_commit_with_generated_note_silent(self):
        """Git commit with 'Generated with Claude' should not trigger"""
        command = 'git commit -m "Add feature\n\nGenerated with Claude"'
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when attribution present"

    def test_git_commit_case_insensitive_detection(self):
        """Git commit detection should be case-insensitive"""
        for cmd in ["GIT COMMIT -m 'test'", "Git Commit -m 'test'", "git COMMIT -m 'test'"]:
            output = run_hook("Bash", cmd)
            assert "hookSpecificOutput" in output, f"Should detect: {cmd}"

    def test_git_commit_amend_triggers(self):
        """Git commit --amend should also trigger"""
        output = run_hook("Bash", 'git commit --amend -m "Fix typo"')
        assert "hookSpecificOutput" in output, "Should detect git commit --amend"

    def test_git_commit_with_flags_triggers(self):
        """Git commit with various flags should trigger"""
        commands = [
            'git commit --no-verify -m "Add feature"',
            'git commit -a -m "Update all"',
            'git commit --allow-empty -m "Empty commit"',
        ]
        for cmd in commands:
            output = run_hook("Bash", cmd)
            assert "hookSpecificOutput" in output, f"Should detect: {cmd}"

    def test_chained_git_commit_triggers(self):
        """Git commit in chained command should trigger"""
        output = run_hook("Bash", 'git add . && git commit -m "Update"')
        assert "hookSpecificOutput" in output, "Should detect git commit in chain"


class TestGitHubAPIDetection:
    """Test GitHub API write operation detection"""

    def test_create_pr_without_attribution_triggers(self):
        """Creating PR without attribution should trigger"""
        command = """curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
  "https://api.github.com/repos/owner/repo/pulls" \\
  -d '{"title":"New PR","head":"branch","base":"main","body":"Description"}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect PR creation without attribution"
        assert "AUTHORSHIP ATTRIBUTION REQUIRED" in output["hookSpecificOutput"]["additionalContext"]

    def test_create_issue_without_attribution_triggers(self):
        """Creating issue without attribution should trigger"""
        command = """curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
  "https://api.github.com/repos/owner/repo/issues" \\
  -d '{"title":"Bug report","body":"Found a bug"}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect issue creation without attribution"

    def test_create_comment_without_attribution_triggers(self):
        """Creating comment without attribution should trigger"""
        command = """curl -X POST \\
  "https://api.github.com/repos/owner/repo/issues/10/comments" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"body":"This is my comment"}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect comment creation without attribution"

    def test_patch_pr_without_attribution_triggers(self):
        """Updating PR without attribution should trigger"""
        command = """curl -X PATCH \\
  "https://api.github.com/repos/owner/repo/pulls/123" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"body":"Updated description"}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect PR update without attribution"

    def test_patch_issue_without_attribution_triggers(self):
        """Updating issue without attribution should trigger"""
        command = """curl -X PATCH \\
  "https://api.github.com/repos/owner/repo/issues/456" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"body":"Updated issue body"}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, "Should detect issue update without attribution"

    def test_pr_with_attribution_in_body_silent(self):
        """PR creation with attribution in body should not trigger"""
        command = """curl -X POST \\
  "https://api.github.com/repos/owner/repo/pulls" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"title":"New PR","body":"Description\\n\\nAI-assisted with Claude Code"}'
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when attribution in body"

    def test_issue_with_claude_link_silent(self):
        """Issue with claude.ai/code link should not trigger"""
        command = """curl -X POST \\
  "https://api.github.com/repos/owner/repo/issues" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"title":"Bug","body":"Description\\nhttps://claude.ai/code/session_123"}'
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when session link in body"

    def test_comment_with_coauthored_silent(self):
        """Comment with Co-authored-by should not trigger"""
        command = """curl -X POST \\
  "https://api.github.com/repos/owner/repo/issues/10/comments" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{"body":"Comment\\n\\nCo-authored-by: Claude"}'
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger when attribution in comment"

    def test_get_request_silent(self):
        """GET requests should not trigger (not write operations)"""
        command = """curl -H "Authorization: token $GITHUB_TOKEN" \\
  "https://api.github.com/repos/owner/repo/issues"
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger on GET requests"


class TestCooldownMechanism:
    """Test cooldown mechanism"""

    def test_cooldown_prevents_duplicate_suggestions(self):
        """Suggestions should be rate-limited by cooldown"""
        # First call should trigger
        output1 = run_hook("Bash", 'git commit -m "First"', clear_cooldown=True)
        assert "hookSpecificOutput" in output1, "First call should trigger"

        # Second call within cooldown should not trigger
        output2 = run_hook("Bash", 'git commit -m "Second"', clear_cooldown=False)
        assert output2 == {}, "Second call should be suppressed by cooldown"

    def test_cooldown_applies_to_different_operation_types(self):
        """Cooldown should apply across both git and API operations"""
        # Trigger with git commit
        output1 = run_hook("Bash", 'git commit -m "Test"', clear_cooldown=True)
        assert "hookSpecificOutput" in output1

        # GitHub API call should also be suppressed
        output2 = run_hook(
            "Bash",
            'curl -X POST https://api.github.com/repos/o/r/issues -d \'{"title":"Test"}\'',
            clear_cooldown=False
        )
        assert output2 == {}, "API call should be suppressed by cooldown"

    def test_cooldown_state_file_created(self):
        """Cooldown state file should be created"""
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-authorship-cooldown"

        # Clear state first
        if state_file.exists():
            state_file.unlink()

        # Trigger hook
        run_hook("Bash", 'git commit -m "Test"', clear_cooldown=False)

        # Check state file was created
        assert state_file.exists(), "State file should be created"
        assert state_file.read_text().strip(), "State file should contain timestamp"


class TestNonTriggeringCommands:
    """Test that non-relevant commands don't trigger"""

    def test_non_bash_tools_silent(self):
        """Non-Bash tools should not trigger"""
        tools = ["Read", "Write", "Edit", "Glob", "Grep", "WebFetch"]
        for tool in tools:
            output = run_hook(tool, 'git commit -m "Test"')
            assert output == {}, f"{tool} should not trigger hook"

    def test_git_status_silent(self):
        """git status should not trigger"""
        output = run_hook("Bash", "git status")
        assert output == {}, "git status should not trigger"

    def test_git_add_silent(self):
        """git add should not trigger"""
        output = run_hook("Bash", "git add .")
        assert output == {}, "git add should not trigger"

    def test_git_push_silent(self):
        """git push should not trigger"""
        output = run_hook("Bash", "git push origin main")
        assert output == {}, "git push should not trigger"

    def test_git_log_silent(self):
        """git log should not trigger"""
        output = run_hook("Bash", "git log --oneline")
        assert output == {}, "git log should not trigger"

    def test_git_diff_silent(self):
        """git diff should not trigger"""
        output = run_hook("Bash", "git diff HEAD~1")
        assert output == {}, "git diff should not trigger"

    def test_non_github_curl_silent(self):
        """curl to non-GitHub URLs should not trigger"""
        output = run_hook("Bash", 'curl -X POST https://example.com/api -d \'{"data":"test"}\'')
        assert output == {}, "Non-GitHub curl should not trigger"

    def test_curl_without_post_patch_silent(self):
        """curl GET to GitHub should not trigger"""
        output = run_hook("Bash", 'curl https://api.github.com/repos/owner/repo/issues')
        assert output == {}, "GET request should not trigger"

    def test_empty_command_silent(self):
        """Empty command should not trigger"""
        output = run_hook("Bash", "")
        assert output == {}, "Empty command should not trigger"

    def test_command_with_commit_in_string_silent(self):
        """Command with 'commit' in a string but not git commit should not trigger"""
        output = run_hook("Bash", 'echo "I will commit to this plan"')
        assert output == {}, "Should not trigger on 'commit' in string"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_malformed_json_input_returns_empty(self):
        """Hook should handle malformed JSON gracefully"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True
        )
        # Should exit with error code but output valid JSON
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} on malformed input"

    def test_missing_tool_name_returns_empty(self):
        """Hook should handle missing tool_name field"""
        input_data = {"tool_input": {"command": "git commit -m 'test'"}}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} when tool_name missing"

    def test_missing_command_returns_empty(self):
        """Hook should handle missing command field"""
        input_data = {"tool_name": "Bash", "tool_input": {}}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} when command missing"

    def test_very_long_command_handled(self):
        """Hook should handle very long commands"""
        long_message = "A" * 10000
        command = f'git commit -m "{long_message}"'
        output = run_hook("Bash", command)
        # Should still detect and trigger
        assert "hookSpecificOutput" in output, "Should handle long commands"


class TestOutputValidation:
    """Test output format and content validation"""

    def test_output_is_valid_json(self):
        """Hook output should always be valid JSON"""
        output = run_hook("Bash", 'git commit -m "Test"')
        # Should be parseable as JSON (already done by run_hook)
        assert isinstance(output, dict)

    def test_event_name_correct(self):
        """Hook should set correct event name"""
        output = run_hook("Bash", 'git commit -m "Test"')
        if "hookSpecificOutput" in output:
            assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_git_guidance_includes_examples(self):
        """Git commit guidance should include concrete examples"""
        output = run_hook("Bash", 'git commit -m "Test"')
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "git commit" in context.lower()
        assert "Co-authored-by" in context
        assert "claude.ai/code" in context

    def test_api_guidance_includes_examples(self):
        """API guidance should include concrete examples"""
        output = run_hook("Bash", 'curl -X POST https://api.github.com/repos/o/r/pulls -d \'{"title":"Test"}\'')
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "curl" in context
        assert "github.com" in context.lower()
        assert "body" in context

    def test_guidance_mentions_transparency(self):
        """Guidance should mention transparency/attribution"""
        output = run_hook("Bash", 'git commit -m "Test"')
        context = output["hookSpecificOutput"]["additionalContext"]
        assert any(word in context.lower() for word in ["transparency", "attribution", "ai-assisted"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
