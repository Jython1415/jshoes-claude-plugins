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
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance content"

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

    @pytest.mark.parametrize("command,description", [
        ("""git commit -m "$(cat <<'EOF'
Add feature

Co-authored-by: Claude (Anthropic AI) <claude@anthropic.com>
EOF
)"
""", "Co-authored-by"),
        ('git commit -m "Add feature" -m "AI-assisted with Claude Code"', "AI-assisted note"),
        ('git commit -m "Add feature\n\nhttps://claude.ai/code/session_12345"', "session link"),
        ('git commit -m "Add feature\n\nGenerated with Claude"', "Generated with Claude note"),
    ])
    def test_git_commit_with_attribution_silent(self, command, description):
        """Git commit with various attribution patterns should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"Should not trigger with {description}"

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

    @pytest.mark.parametrize("method,endpoint,description", [
        ("POST", "pulls", "PR creation"),
        ("POST", "issues", "issue creation"),
        ("POST", "issues/10/comments", "comment creation"),
        ("PATCH", "pulls/123", "PR update"),
        ("PATCH", "issues/456", "issue update"),
    ])
    def test_api_operations_without_attribution_trigger(self, method, endpoint, description):
        """GitHub API write operations without attribution should trigger"""
        command = f"""curl -X {method} -H "Authorization: token $GITHUB_TOKEN" \\
  "https://api.github.com/repos/owner/repo/{endpoint}" \\
  -d '{{"title":"Test","body":"Content"}}'
"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"Should detect {description} without attribution"
        if method == "POST" and endpoint == "pulls":
            assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance content"

    @pytest.mark.parametrize("body,description", [
        ("Description\\n\\nAI-assisted with Claude Code", "AI-assisted note"),
        ("Description\\nhttps://claude.ai/code/session_123", "session link"),
        ("Comment\\n\\nCo-authored-by: Claude", "Co-authored-by"),
    ])
    def test_api_with_attribution_silent(self, body, description):
        """GitHub API calls with attribution should not trigger"""
        command = f"""curl -X POST \\
  "https://api.github.com/repos/owner/repo/issues" \\
  -H "Authorization: token $GITHUB_TOKEN" \\
  -d '{{"title":"Test","body":"{body}"}}'
"""
        output = run_hook("Bash", command)
        assert output == {}, f"Should not trigger with {description}"

    def test_get_request_silent(self):
        """GET requests should not trigger (not write operations)"""
        command = """curl -H "Authorization: token $GITHUB_TOKEN" \\
  "https://api.github.com/repos/owner/repo/issues"
"""
        output = run_hook("Bash", command)
        assert output == {}, "Should not trigger on GET requests"


class TestGhCliDetection:
    """Test gh CLI command detection"""

    @pytest.mark.parametrize("command,description", [
        ('gh pr create --title "New PR" --body "Description"', "pr create"),
        ('gh pr edit 123 --body "Updated description"', "pr edit"),
        ('gh issue create --title "Bug" --body "Issue description"', "issue create"),
        ('gh issue edit 456 --body "Updated issue"', "issue edit"),
        ('gh issue comment 789 --body "Comment text"', "issue comment"),
    ])
    def test_gh_cli_without_attribution_triggers(self, command, description):
        """gh CLI write operations without attribution should trigger"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"Should detect {description} without attribution"

    @pytest.mark.parametrize("command,description", [
        ('gh pr create --title "PR" --body "Description\\n\\nAI-assisted with Claude Code"', "pr with attribution"),
        ('gh issue create --title "Issue" --body "Text\\nhttps://claude.ai/code/session_123"', "issue with link"),
    ])
    def test_gh_cli_with_attribution_silent(self, command, description):
        """gh CLI operations with attribution should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"Should not trigger for {description}"

    @pytest.mark.parametrize("command,description", [
        ("gh pr list", "pr list"),
        ("gh pr view 123", "pr view"),
        ("gh issue list", "issue list"),
        ("gh issue view 456", "issue view"),
    ])
    def test_gh_cli_read_operations_silent(self, command, description):
        """gh CLI read operations should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"Should not trigger for {description}"


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

    @pytest.mark.parametrize("command,description", [
        ("git status", "git status"),
        ("git add .", "git add"),
        ("git push origin main", "git push"),
        ("git log --oneline", "git log"),
        ("git diff HEAD~1", "git diff"),
    ])
    def test_git_read_commands_silent(self, command, description):
        """Non-commit git commands should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"{description} should not trigger"

    @pytest.mark.parametrize("command,description", [
        ('curl -X POST https://example.com/api -d \'{"data":"test"}\'', "non-GitHub curl"),
        ('curl https://api.github.com/repos/owner/repo/issues', "GitHub GET request"),
        ("", "empty command"),
        ('echo "I will commit to this plan"', "'commit' in string"),
    ])
    def test_non_triggering_commands_silent(self, command, description):
        """Various non-triggering commands should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"{description} should not trigger"


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

    def test_git_guidance_presented(self):
        """Git commit should trigger guidance presentation"""
        output = run_hook("Bash", 'git commit -m "Test"')
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_api_guidance_presented(self):
        """GitHub API operations should trigger guidance presentation"""
        output = run_hook("Bash", 'curl -X POST https://api.github.com/repos/o/r/pulls -d \'{"title":"Test"}\'')
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
