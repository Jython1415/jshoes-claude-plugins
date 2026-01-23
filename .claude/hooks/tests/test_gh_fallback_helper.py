"""
Unit tests for gh-fallback-helper.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_gh_fallback_helper.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "gh-fallback-helper.py"


def run_hook(
    tool_name: str,
    command: str = "",
    error: str = "",
    tool_result_error: str = "",
    github_token: str = ""
) -> dict:
    """
    Helper function to run the hook with given input and return parsed output

    Args:
        tool_name: Name of the tool being used
        command: The command that was executed
        error: Top-level error field (for PostToolUseFailure)
        tool_result_error: Error from tool_result.error field (for PostToolUse)
        github_token: Value to set for GITHUB_TOKEN env var (empty = not set)

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    # Add error field if provided (PostToolUseFailure)
    if error:
        input_data["error"] = error

    # Add tool_result.error if provided (PostToolUse)
    if tool_result_error:
        input_data["tool_result"] = {"error": tool_result_error}

    # Set up environment - inherit parent env and optionally add GITHUB_TOKEN
    import os
    env = os.environ.copy()

    if github_token:
        env["GITHUB_TOKEN"] = github_token
    elif "GITHUB_TOKEN" in env:
        # Remove GITHUB_TOKEN if explicitly not provided
        del env["GITHUB_TOKEN"]

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode not in [0]:
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestGhFallbackHelper:
    """Test suite for gh-fallback-helper hook"""

    # Basic functionality tests
    @pytest.mark.parametrize("error_field,command", [
        ("tool_result", "gh issue list"),
        ("top_level", "gh pr create"),
    ])
    def test_gh_command_not_found_with_token(self, error_field, command):
        """gh command not found with GITHUB_TOKEN should provide guidance (both error field locations)"""
        if error_field == "tool_result":
            output = run_hook(
                tool_name="Bash",
                command=command,
                tool_result_error="gh: command not found",
                github_token="ghp_test123"
            )
        else:  # top_level
            output = run_hook(
                tool_name="Bash",
                command=command,
                error="bash: gh: command not found",
                github_token="ghp_test123"
            )

        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        context = output["hookSpecificOutput"]["additionalContext"]
        assert len(context) > 0, "Guidance should be non-empty"

    def test_gh_command_not_found_without_token(self):
        """gh command not found without GITHUB_TOKEN should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="gh: command not found",
            github_token=""  # No token
        )
        assert output == {}, "Should return empty JSON when GITHUB_TOKEN not available"

    def test_non_bash_tool(self):
        """Non-Bash tools should return {}"""
        output = run_hook(
            tool_name="Read",
            command="gh issue list",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert output == {}, "Non-Bash tools should not trigger hook"

    def test_non_gh_command(self):
        """Non-gh Bash commands should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="git status",
            error="git: command not found",
            github_token="ghp_test123"
        )
        assert output == {}, "Non-gh commands should not trigger hook"

    def test_successful_gh_command(self):
        """Successful gh commands (no error) should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="",  # No error
            github_token="ghp_test123"
        )
        assert output == {}, "Successful commands should not trigger hook"

    # Error detection tests
    def test_detect_command_not_found_variations(self):
        """Should detect various 'command not found' error formats"""
        test_cases = [
            "gh: command not found",
            "bash: gh: command not found",
            "/bin/bash: gh: command not found",
            "gh: not found",
            "bash: line 1: gh: command not found"
        ]

        for error_msg in test_cases:
            output = run_hook(
                tool_name="Bash",
                command="gh issue list",
                error=error_msg,
                github_token="ghp_test123"
            )
            assert "hookSpecificOutput" in output, f"Should detect: {error_msg}"

    def test_gh_command_with_different_error(self):
        """gh command with non-'not found' error should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="HTTP 401: Unauthorized (https://api.github.com/)",
            github_token="ghp_test123"
        )
        assert output == {}, "Should only trigger on 'not found' errors"

    def test_error_contains_not_found_but_not_gh_command(self):
        """Error with 'not found' but non-gh command should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="docker ps",
            error="docker: command not found",
            github_token="ghp_test123"
        )
        assert output == {}, "Should only trigger for gh commands"

    # Command pattern tests
    def test_various_gh_commands(self):
        """Should trigger for various gh CLI commands"""
        gh_commands = [
            "gh issue list",
            "gh pr create",
            "gh pr view 123",
            "gh repo clone owner/repo",
            "gh api /repos/owner/repo",
            "gh issue create --title 'Test'",
            "gh pr merge 123"
        ]

        for cmd in gh_commands:
            output = run_hook(
                tool_name="Bash",
                command=cmd,
                error="gh: command not found",
                github_token="ghp_test123"
            )
            assert "hookSpecificOutput" in output, f"Should trigger for: {cmd}"

    def test_gh_in_command_chain(self):
        """gh command in command chain should trigger"""
        output = run_hook(
            tool_name="Bash",
            command="git pull && gh pr create --fill",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert "hookSpecificOutput" in output, "Should detect gh in command chain"

    def test_gh_with_pipe(self):
        """gh command with pipe should trigger"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list | grep bug",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert "hookSpecificOutput" in output, "Should detect gh with pipe"

    # Edge cases - "gh" as part of word WILL trigger (limitation of simple substring check)
    def test_gh_as_part_of_word(self):
        """'gh' as part of a larger word will trigger (hook uses simple substring match)"""
        # Note: This is a known limitation of the hook's simple "gh" in command check
        # It will match any command containing "gh" substring, even in words like "high"
        test_cases = [
            ("echo 'high quality'", "echo: command not found"),
            ("light on", "light: command not found"),
            ("weigh options", "weigh: command not found"),
            ("knight move", "knight: command not found"),
            ("neighbor check", "neighbor: command not found")
        ]

        for cmd, error_msg in test_cases:
            output = run_hook(
                tool_name="Bash",
                command=cmd,
                error=error_msg,
                github_token="ghp_test123"
            )
            # Due to simple substring matching, these WILL trigger
            assert "hookSpecificOutput" in output, f"Hook uses simple substring match: {cmd}"

    def test_gh_in_string_literal(self):
        """'gh' inside string literal will trigger if error also contains 'not found'"""
        # The hook checks if "gh" is in the command string (simple substring match)
        # So "echo 'gh issue list'" would match because "gh" is in the command
        output = run_hook(
            tool_name="Bash",
            command="echo 'gh issue list'",
            error="echo: command not found",
            github_token="ghp_test123"
        )
        # The hook sees "gh" in command AND "command not found" in error, so it triggers
        # This is a limitation of the simple substring matching approach
        assert "hookSpecificOutput" in output, "Hook triggers on substring match"

    # Error field location tests
    @pytest.mark.parametrize("error_location,command,top_level_error,tool_result_error", [
        ("top_level", "gh issue list", "gh: command not found", ""),
        ("tool_result", "gh pr view 123", "", "gh: command not found"),
        ("both", "gh issue create", "gh: command not found", "some other error"),
    ])
    def test_error_field_locations(self, error_location, command, top_level_error, tool_result_error):
        """Should correctly read error from appropriate field(s)"""
        output = run_hook(
            tool_name="Bash",
            command=command,
            error=top_level_error,
            tool_result_error=tool_result_error,
            github_token="ghp_test123"
        )
        assert "hookSpecificOutput" in output, f"Should read error from {error_location} field"

    def test_no_error_fields(self):
        """No error in either field should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="gh status",
            error="",
            tool_result_error="",
            github_token="ghp_test123"
        )
        assert output == {}, "Should return {} when no error present"

    # Output content tests
    @pytest.mark.parametrize("command", [
        "gh issue list",
        "gh pr create",
        "gh api /repos/owner/repo",
        "gh issue view 1",
        "gh api /user",
    ])
    def test_guidance_provided_for_various_gh_commands(self, command):
        """Guidance should be provided for various gh commands"""
        output = run_hook(
            tool_name="Bash",
            command=command,
            error="gh: command not found",
            github_token="ghp_test123"
        )
        context = output["hookSpecificOutput"]["additionalContext"]

        # Test behavior: guidance exists and is non-empty
        assert len(context) > 0, f"Should provide non-empty guidance for: {command}"

    def test_guidance_differs_with_and_without_token(self):
        """Different scenarios (with/without token) should potentially provide different guidance"""
        output_with_token = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="gh: command not found",
            github_token="ghp_test123"
        )

        output_without_token = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="gh: command not found",
            github_token=""
        )

        # Test behavior: with token should provide guidance, without should not
        assert "hookSpecificOutput" in output_with_token
        assert output_without_token == {}

    # JSON output format tests
    def test_json_output_valid_with_guidance(self):
        """Hook output with guidance should be valid JSON"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert "hookSpecificOutput" in output
        assert isinstance(output["hookSpecificOutput"], dict)
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "hookEventName" in output["hookSpecificOutput"]

    def test_json_output_valid_empty(self):
        """Hook output without guidance should be valid empty JSON"""
        output = run_hook(
            tool_name="Bash",
            command="git status",
            error="git: command not found",
            github_token="ghp_test123"
        )
        assert output == {}, "Should return empty dict"
        assert isinstance(output, dict), "Should be valid JSON dict"

    def test_hook_event_name_correct(self):
        """Hook output should include correct event name"""
        output = run_hook(
            tool_name="Bash",
            command="gh pr list",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"

    def test_output_uses_additional_context_not_decision(self):
        """Hook should use additionalContext field, not decision field"""
        output = run_hook(
            tool_name="Bash",
            command="gh repo view",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "decision" not in output["hookSpecificOutput"], "Should not use decision field"

    # Edge cases and special scenarios
    def test_empty_command_string(self):
        """Empty command string should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert output == {}, "Empty command should return {}"

    def test_command_with_gh_flag_not_gh_command(self):
        """Command with --gh flag but not gh command should return {}"""
        output = run_hook(
            tool_name="Bash",
            command="some-tool --gh-mode",
            error="some-tool: command not found",
            github_token="ghp_test123"
        )
        # This will actually trigger because "gh" is in "--gh-mode"
        # and "command not found" is in error
        # The hook's check is simple: "gh" in command
        # This is a limitation of the current implementation
        # For now, document this behavior
        assert "hookSpecificOutput" in output, "Current implementation: 'gh' substring match triggers"

    def test_multiple_gh_commands_in_chain(self):
        """Multiple gh commands in chain should trigger"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list && gh pr list",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert "hookSpecificOutput" in output, "Should trigger for gh in command chain"

    def test_gh_with_complex_arguments(self):
        """gh command with complex arguments should trigger"""
        output = run_hook(
            tool_name="Bash",
            command='gh issue create --title "Bug: something broke" --body "Details here" --label bug',
            error="gh: command not found",
            github_token="ghp_test123"
        )
        assert "hookSpecificOutput" in output, "Should trigger for gh with complex args"

    def test_github_token_with_different_formats(self):
        """Should work with different GITHUB_TOKEN formats"""
        token_formats = [
            "ghp_1234567890abcdef",
            "github_pat_1234567890",
            "gho_1234567890",
            "ghs_1234567890",
            "fake_token_for_testing"
        ]

        for token in token_formats:
            output = run_hook(
                tool_name="Bash",
                command="gh api /user",
                error="gh: command not found",
                github_token=token
            )
            assert "hookSpecificOutput" in output, f"Should work with token format: {token[:10]}..."

    # Regression tests
    def test_guidance_is_substantial(self):
        """Guidance should be substantial and meaningful"""
        output = run_hook(
            tool_name="Bash",
            command="gh issue list",
            error="gh: command not found",
            github_token="ghp_test123"
        )
        context = output["hookSpecificOutput"]["additionalContext"]

        # Test behavior: guidance should be meaningful (substantial length)
        # Actual content may evolve, but should always be helpful
        assert len(context) > 50, "Guidance should be substantial"

    def test_consistency_across_multiple_runs(self):
        """Hook should produce consistent output across multiple runs"""
        outputs = []
        for _ in range(3):
            output = run_hook(
                tool_name="Bash",
                command="gh issue list",
                error="gh: command not found",
                github_token="ghp_test123"
            )
            outputs.append(json.dumps(output, sort_keys=True))

        # All outputs should be identical
        assert len(set(outputs)) == 1, "Hook should produce consistent output"

    def test_no_command_field_in_tool_input(self):
        """Missing command field should return {}"""
        import os
        input_data = {
            "tool_name": "Bash",
            "tool_input": {},  # No command field
            "error": "gh: command not found"
        }

        env = os.environ.copy()
        env["GITHUB_TOKEN"] = "ghp_test123"

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env
        )

        output = json.loads(result.stdout)
        assert output == {}, "Missing command field should return {}"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
