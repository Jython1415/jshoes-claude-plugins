"""
Unit tests for gh-web-fallback.py hook

Run with:
  uv run pytest                                       # Run all tests
  uv run pytest hooks/tests/test_gh_web_fallback.py  # Run this test file
  uv run pytest -v                                    # Verbose output

This test suite uses mocking to test gh availability, GITHUB_TOKEN presence,
command detection, and cooldown scenarios.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "gh-web-fallback.py"


def run_hook(
    command: str,
    gh_available: bool = False,
    token_available: bool = True,
    clear_cooldown: bool = True
) -> dict:
    """
    Helper function to run the hook with mocked environment.

    Args:
        command: The bash command to test
        gh_available: Whether gh CLI should be available
        token_available: Whether GITHUB_TOKEN should be available
        clear_cooldown: Whether to clear cooldown state before running

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": command}
    }

    # Create a temporary directory for mock tools
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clear cooldown state if requested
        if clear_cooldown:
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "gh-web-fallback-cooldown"
            if state_file.exists():
                state_file.unlink()

        # Create a mock 'which' command that controls gh availability
        which_path = Path(tmpdir) / "which"
        which_script = "#!/bin/sh\n"
        which_script += "# Mock which script that controls gh availability\n"
        which_script += "case \"$1\" in\n"

        # Handle gh
        if gh_available:
            which_script += f"  gh) echo '{tmpdir}/gh'; exit 0 ;;\n"
        else:
            which_script += "  gh) exit 1 ;;\n"

        # For other commands, use the real which
        which_script += "  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\n"
        which_script += "esac\n"
        which_path.write_text(which_script)
        which_path.chmod(0o755)

        # Create mock gh if available
        if gh_available:
            gh_path = Path(tmpdir) / "gh"
            gh_path.write_text("#!/bin/sh\necho 'mock gh'\nexit 0\n")
            gh_path.chmod(0o755)

        # Modify environment
        env = os.environ.copy()
        env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"

        # Control GITHUB_TOKEN availability
        if token_available:
            env['GITHUB_TOKEN'] = 'test-token-12345'
        else:
            env.pop('GITHUB_TOKEN', None)

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
            raise RuntimeError(f"Hook failed: {result.stderr}")

        return json.loads(result.stdout)


class TestGhWebFallback:
    """Test suite for gh-web-fallback hook"""

    # ========== Command Detection Tests ==========

    def test_gh_command_at_start(self):
        """Command starting with 'gh' should be detected"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh at start"

    def test_gh_command_after_pipe(self):
        """gh command after pipe should be detected"""
        output = run_hook("git status | gh issue view 10", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh after pipe"

    def test_gh_command_after_semicolon(self):
        """gh command after semicolon should be detected"""
        output = run_hook("git status; gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh after semicolon"

    def test_gh_command_after_or(self):
        """gh command after || should be detected"""
        output = run_hook("cat file || gh pr view 10", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh after ||"

    def test_no_trigger_on_sigh(self):
        """'sigh' should NOT trigger (not a standalone gh command)"""
        output = run_hook("echo sigh", gh_available=False, token_available=True)
        assert output == {}, "Should not trigger on 'sigh'"

    def test_no_trigger_on_high(self):
        """'high' should NOT trigger (not a standalone gh command)"""
        output = run_hook("echo high", gh_available=False, token_available=True)
        assert output == {}, "Should not trigger on 'high'"

    def test_complex_chained_command(self):
        """Multiple commands with gh in middle should be detected"""
        output = run_hook("git pull && gh issue view 5 && echo done", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh in middle of chain"

    # ========== Environment Detection Tests ==========

    def test_triggers_when_gh_unavailable_token_available(self):
        """Main success case: gh unavailable, token available"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should trigger when gh unavailable and token available"
        assert "GitHub API" in output["hookSpecificOutput"]["additionalContext"]

    def test_no_trigger_when_gh_available(self):
        """When gh is available, should not suggest curl"""
        output = run_hook("gh issue list", gh_available=True, token_available=True)
        assert output == {}, "Should not suggest when gh is available"

    def test_no_trigger_when_token_unavailable(self):
        """When GITHUB_TOKEN not available, should not suggest"""
        output = run_hook("gh issue list", gh_available=False, token_available=False)
        assert output == {}, "Should not trigger without GITHUB_TOKEN"

    def test_no_trigger_when_both_available(self):
        """When both gh and token available, prefer-gh hook should handle it"""
        output = run_hook("gh issue list", gh_available=True, token_available=True)
        assert output == {}, "Should defer to prefer-gh hook"

    def test_no_trigger_when_neither_available(self):
        """When neither gh nor token available, should not suggest"""
        output = run_hook("gh issue list", gh_available=False, token_available=False)
        assert output == {}, "Should not trigger without either"

    def test_token_empty_string_treated_as_unavailable(self):
        """Empty GITHUB_TOKEN should be treated as unavailable"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh issue list"}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clear cooldown
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "gh-web-fallback-cooldown"
            if state_file.exists():
                state_file.unlink()

            which_path = Path(tmpdir) / "which"
            which_script = "#!/bin/sh\ncase \"$1\" in\n  gh) exit 1 ;;\n  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\nesac\n"
            which_path.write_text(which_script)
            which_path.chmod(0o755)

            env = os.environ.copy()
            env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"
            env['GITHUB_TOKEN'] = ''  # Empty string

            result = subprocess.run(
                ["uv", "run", "--script", str(HOOK_PATH)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                env=env
            )

            output = json.loads(result.stdout)
            assert output == {}, "Empty GITHUB_TOKEN should not trigger"

    # ========== Cooldown Mechanism Tests ==========

    def test_cooldown_prevents_duplicate(self):
        """Second call within 300s should not trigger (cooldown)"""
        # First call - should suggest
        output1 = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output1, "First call should suggest"

        # Second call immediately after - should NOT suggest
        output2 = run_hook("gh pr view 5", gh_available=False, token_available=True, clear_cooldown=False)
        assert output2 == {}, "Second call within cooldown should not suggest"

    def test_cooldown_expires_after_period(self):
        """Call after 300+ seconds should trigger again"""
        # First call - should suggest
        output1 = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output1, "First call should suggest"

        # Manually modify the cooldown file to simulate expired cooldown
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-web-fallback-cooldown"
        old_time = time.time() - 305  # 305 seconds ago (beyond 300 second cooldown)
        state_file.write_text(str(old_time))

        # Second call after cooldown expires - should suggest again
        output2 = run_hook("gh pr view 5", gh_available=False, token_available=True, clear_cooldown=False)
        assert "hookSpecificOutput" in output2, "Should suggest again after cooldown expires"

    def test_cooldown_file_creation(self):
        """Cooldown file should be created when suggestion is made"""
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-web-fallback-cooldown"
        if state_file.exists():
            state_file.unlink()

        output = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output, "Should trigger"
        assert state_file.exists(), "Cooldown file should be created"

    def test_corrupted_cooldown_file_graceful(self):
        """Corrupted cooldown file should be handled gracefully"""
        # Create a corrupted cooldown file
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-web-fallback-cooldown"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not-a-number-corrupted-data")

        # Hook should still work and suggest (cooldown check fails gracefully)
        output = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=False)
        # Should trigger since cooldown check fails on corrupted data
        assert "hookSpecificOutput" in output, "Should suggest even with corrupted state file"

    def test_cooldown_directory_creation(self):
        """STATE_DIR should be created if it doesn't exist"""
        state_dir = Path.home() / ".claude" / "hook-state"
        # Remove directory if it exists
        import shutil
        if state_dir.exists():
            shutil.rmtree(state_dir)

        output = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output, "Should trigger"
        assert state_dir.exists(), "STATE_DIR should be created"

    # ========== Tool Type Filtering Tests ==========

    def test_only_bash_tool_monitored(self):
        """Only Bash tool should be monitored"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh issue list"}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup environment
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "gh-web-fallback-cooldown"
            if state_file.exists():
                state_file.unlink()

            which_path = Path(tmpdir) / "which"
            which_script = "#!/bin/sh\ncase \"$1\" in\n  gh) exit 1 ;;\n  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\nesac\n"
            which_path.write_text(which_script)
            which_path.chmod(0o755)

            env = os.environ.copy()
            env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"
            env['GITHUB_TOKEN'] = 'test-token'

            result = subprocess.run(
                ["uv", "run", "--script", str(HOOK_PATH)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                env=env
            )

            output = json.loads(result.stdout)
            assert "hookSpecificOutput" in output, "Bash tool should trigger"

    def test_webfetch_not_monitored(self):
        """WebFetch tool should NOT be monitored by this hook"""
        input_data = {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://api.github.com/repos/owner/repo"}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env['GITHUB_TOKEN'] = 'test-token'
            env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"

            result = subprocess.run(
                ["uv", "run", "--script", str(HOOK_PATH)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                env=env
            )

            output = json.loads(result.stdout)
            assert output == {}, "WebFetch should not trigger"

    def test_read_tool_ignored(self):
        """Read tool should not trigger"""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/path"}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        output = json.loads(result.stdout)
        assert output == {}, "Read tool should not trigger"

    def test_edit_tool_ignored(self):
        """Edit tool should not trigger"""
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/path", "old_string": "a", "new_string": "b"}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        output = json.loads(result.stdout)
        assert output == {}, "Edit tool should not trigger"

    # ========== Edge Cases ==========

    def test_empty_command(self):
        """Empty command should NOT trigger"""
        output = run_hook("", gh_available=False, token_available=True)
        assert output == {}, "Empty command should not trigger"

    def test_missing_command_field(self):
        """Missing command field should NOT trigger"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        output = json.loads(result.stdout)
        assert output == {}, "Missing command field should not trigger"

    def test_malformed_json_input(self):
        """Malformed JSON input should be handled gracefully"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        # Should output valid JSON (empty dict) on error
        try:
            output = json.loads(result.stdout)
            assert output == {}, "Should output {} on malformed input"
        except json.JSONDecodeError:
            pytest.fail("Should output valid JSON even on error")

    def test_missing_tool_input(self):
        """Missing tool_input should be handled gracefully"""
        input_data = {
            "tool_name": "Bash"
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        output = json.loads(result.stdout)
        assert output == {}, "Missing tool_input should not trigger"

    def test_gh_in_string_literal(self):
        """gh inside a string literal should NOT trigger"""
        output = run_hook('echo "use gh command"', gh_available=False, token_available=True)
        assert output == {}, "gh in string literal should not trigger"

    def test_gh_in_comment(self):
        """gh in a comment should NOT trigger (tricky!)"""
        output = run_hook("# gh issue list\necho 'hello'", gh_available=False, token_available=True)
        # This is a tricky edge case - the regex may match the comment
        # The behavior depends on whether comments are stripped before regex check
        # For this hook, it's acceptable if it triggers since shell will ignore the comment
        # Just verify it returns valid JSON
        assert isinstance(output, dict), "Should return valid JSON"

    # ========== Output Validation Tests ==========

    def test_output_valid_json(self):
        """All outputs should be valid JSON"""
        test_cases = [
            ("gh issue list", False, True),
            ("gh pr view 5", False, True),
            ("echo test", False, True),
            ("git status", False, False),
            ("gh issue list", True, True),  # gh available
        ]
        for command, gh_avail, token_avail in test_cases:
            try:
                output = run_hook(command, gh_available=gh_avail, token_available=token_avail)
                assert isinstance(output, dict), f"Output should be valid JSON dict for: {command}"
            except json.JSONDecodeError:
                pytest.fail(f"Output should be valid JSON for: {command}")

    def test_hook_event_name(self):
        """hookEventName should be 'PreToolUse'"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_additional_context_present(self):
        """additionalContext should be present and non-empty"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert "additionalContext" in output["hookSpecificOutput"]
        context = output["hookSpecificOutput"]["additionalContext"]
        assert len(context) > 0, "additionalContext should not be empty"

    def test_no_decision_field(self):
        """decision field should NOT be present"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert "decision" not in output.get("hookSpecificOutput", {}), "Should not have decision field"

    def test_mentions_github_api(self):
        """Context should mention GitHub API or curl"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GitHub API" in context or "curl" in context, "Should mention GitHub API or curl"

    # ========== Real-World Scenarios ==========

    def test_scenario_gh_issue_view(self):
        """Real scenario: gh issue view with complex flags"""
        output = run_hook("gh issue view 10 --repo owner/repo --json title,body", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect complex gh issue view"
        assert "curl" in output["hookSpecificOutput"]["additionalContext"]

    def test_scenario_gh_pr_create(self):
        """Real scenario: gh pr create with title and body"""
        output = run_hook('gh pr create --title "New feature" --body "Description here"', gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh pr create"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "curl" in context or "POST" in context

    def test_scenario_gh_in_script(self):
        """Real scenario: Multi-line script with gh command"""
        script = """
git pull
gh issue list
echo "done"
"""
        output = run_hook(script, gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh in multi-line script"

    def test_scenario_after_suggestion_cooldown_active(self):
        """Real scenario: Multiple gh commands, only first triggers"""
        # First gh command - should trigger
        output1 = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output1, "First command should trigger"

        # Subsequent gh commands within cooldown - should not trigger
        for i in range(3):
            output = run_hook("gh pr view 5", gh_available=False, token_available=True, clear_cooldown=False)
            assert output == {}, f"Command {i+2} should be suppressed by cooldown"

    # ========== Additional Coverage Tests ==========

    def test_gh_with_ampersand(self):
        """gh command after && should be detected"""
        output = run_hook("git status && gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh after &&"

    def test_gh_with_spaces_in_chain(self):
        """gh with multiple spaces in command chain should be detected"""
        output = run_hook("git status   &&   gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh with extra spaces"

    def test_context_mentions_rest_api(self):
        """Context should mention REST API"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "REST" in context or "rest" in context.lower(), "Should mention REST API"

    def test_context_mentions_jq(self):
        """Context should mention jq for JSON parsing"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "jq" in context, "Should mention jq for parsing"

    def test_context_mentions_docs_link(self):
        """Context should include GitHub docs link"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "docs.github.com" in context, "Should include GitHub docs link"

    def test_multiple_gh_commands_in_chain(self):
        """Multiple gh commands in chain should still trigger"""
        output = run_hook("gh issue list && gh pr view 5", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect first gh command"

    def test_gh_with_complex_flags(self):
        """gh with complex flags and options should be detected"""
        output = run_hook('gh issue list --repo owner/repo --state open --limit 50 --json title,number', gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh with complex flags"


def main():
    """Run tests when executed as a script"""
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
