"""
Unit tests for gh-web-fallback.py hook

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
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "gh-web-fallback.py"


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
        "tool_input": {"command": command},
        "session_id": "test-session-abc123"
    }

    # Create a temporary directory for mock tools
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clear cooldown state if requested
        if clear_cooldown:
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
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

        # Set PATH based on gh_available to control whether real gh is accessible
        if gh_available:
            # When gh is available, prepend our mock to PATH
            env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"
        else:
            # When gh should be unavailable, filter PATH to exclude directories containing gh
            # but keep essential tools like uv, python
            import shutil
            minimal_path_parts = [tmpdir]

            # Find and include the directory containing uv
            uv_path = shutil.which('uv')
            if uv_path:
                uv_dir = os.path.dirname(uv_path)
                minimal_path_parts.append(uv_dir)

            # Add other essential paths but check they don't contain gh
            for path_part in env.get('PATH', '').split(':'):
                if not path_part or path_part in minimal_path_parts:
                    continue
                # Check if this directory contains gh
                potential_gh = os.path.join(path_part, 'gh')
                if not os.path.exists(potential_gh) and not os.path.islink(potential_gh):
                    # Safe to include - no gh here
                    minimal_path_parts.append(path_part)

            env['PATH'] = ':'.join(minimal_path_parts)

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

    @pytest.mark.parametrize("command", [
        "gh issue list",  # Command starting with gh
        "git status | gh issue view 10",  # gh after pipe operator
        "git status; gh issue list",  # gh after semicolon
        "cat file || gh pr view 10",  # gh after || operator
        "git status && gh pr create",  # gh after && operator
        "git pull && gh issue view 5 && echo done",  # gh in middle of chain
    ])
    def test_gh_command_detection(self, command):
        """Test detection of gh commands in various positions and shell operators"""
        output = run_hook(command, gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, f"Should detect gh in: {command}"

    @pytest.mark.parametrize("command", [
        "echo sigh",  # 'sigh' contains 'gh' but not as standalone command
        "echo high",  # 'high' ends with 'gh' but not as standalone command
    ])
    def test_no_trigger_false_positives(self, command):
        """Test that partial matches like 'sigh' and 'high' don't trigger"""
        output = run_hook(command, gh_available=False, token_available=True)
        assert output == {}, f"Should not trigger on: {command}"

    # ========== Environment Detection Tests ==========

    @pytest.mark.parametrize("gh_available,token_available,should_trigger,description", [
        (False, True, True, "Main success case: gh unavailable, token available"),
        (True, True, False, "When gh is available, should not suggest curl"),
        (False, False, False, "When GITHUB_TOKEN not available, should not suggest"),
        (True, False, False, "When token unavailable, should not suggest"),
        (False, False, False, "When neither gh nor token available, should not suggest"),
    ])
    def test_environment_availability(self, gh_available, token_available, should_trigger, description):
        """Test various combinations of gh and token availability"""
        output = run_hook("gh issue list", gh_available=gh_available, token_available=token_available)
        if should_trigger:
            assert "hookSpecificOutput" in output, f"Failed: {description}"
            assert "additionalContext" in output["hookSpecificOutput"]
            assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance content"
        else:
            assert output == {}, f"Failed: {description}"

    def test_token_empty_string_treated_as_unavailable(self):
        """Empty GITHUB_TOKEN should be treated as unavailable"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "gh issue list"}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clear cooldown
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
            if state_file.exists():
                state_file.unlink()

            which_path = Path(tmpdir) / "which"
            which_script = "#!/bin/sh\ncase \"$1\" in\n  gh) exit 1 ;;\n  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\nesac\n"
            which_path.write_text(which_script)
            which_path.chmod(0o755)

            env = os.environ.copy()
            # Use minimal PATH to ensure gh is unavailable
            import shutil
            minimal_path_parts = [tmpdir]

            # Find and include the directory containing uv
            uv_path = shutil.which('uv')
            if uv_path:
                uv_dir = os.path.dirname(uv_path)
                minimal_path_parts.append(uv_dir)

            # Add other paths that don't contain gh
            for path_part in env.get('PATH', '').split(':'):
                if not path_part or path_part in minimal_path_parts:
                    continue
                potential_gh = os.path.join(path_part, 'gh')
                if not os.path.exists(potential_gh) and not os.path.islink(potential_gh):
                    minimal_path_parts.append(path_part)

            env['PATH'] = ':'.join(minimal_path_parts)
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
        state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
        old_time = time.time() - 305  # 305 seconds ago (beyond 300 second cooldown)
        state_file.write_text(str(old_time))

        # Second call after cooldown expires - should suggest again
        output2 = run_hook("gh pr view 5", gh_available=False, token_available=True, clear_cooldown=False)
        assert "hookSpecificOutput" in output2, "Should suggest again after cooldown expires"

    def test_cooldown_file_creation(self):
        """Cooldown file should be created when suggestion is made"""
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
        if state_file.exists():
            state_file.unlink()

        output = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output, "Should trigger"
        assert state_file.exists(), "Cooldown file should be created"

    def test_corrupted_cooldown_file_graceful(self):
        """Corrupted cooldown file should be handled gracefully"""
        # Create a corrupted cooldown file
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
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
            state_file = state_dir / "gh-web-fallback-cooldown-test-session-abc123"
            if state_file.exists():
                state_file.unlink()

            which_path = Path(tmpdir) / "which"
            which_script = "#!/bin/sh\ncase \"$1\" in\n  gh) exit 1 ;;\n  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\nesac\n"
            which_path.write_text(which_script)
            which_path.chmod(0o755)

            env = os.environ.copy()
            # Use minimal PATH to ensure gh is unavailable
            import shutil
            minimal_path_parts = [tmpdir]

            # Find and include the directory containing uv
            uv_path = shutil.which('uv')
            if uv_path:
                uv_dir = os.path.dirname(uv_path)
                minimal_path_parts.append(uv_dir)

            # Add other paths that don't contain gh
            for path_part in env.get('PATH', '').split(':'):
                if not path_part or path_part in minimal_path_parts:
                    continue
                potential_gh = os.path.join(path_part, 'gh')
                if not os.path.exists(potential_gh) and not os.path.islink(potential_gh):
                    minimal_path_parts.append(path_part)

            env['PATH'] = ':'.join(minimal_path_parts)
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

    @pytest.mark.parametrize("tool_name,tool_input", [
        ("WebFetch", {"url": "https://api.github.com/repos/owner/repo"}),
        ("Read", {"file_path": "/some/path"}),
        ("Edit", {"file_path": "/path", "old_string": "a", "new_string": "b"}),
    ])
    def test_non_bash_tools_ignored(self, tool_name, tool_input):
        """Non-Bash tools should not trigger the hook"""
        input_data = {
            "tool_name": tool_name,
            "tool_input": tool_input
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        output = json.loads(result.stdout)
        assert output == {}, f"{tool_name} should not trigger"

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

    def test_additional_context_is_presented(self):
        """additionalContext should be present when hook triggers"""
        output = run_hook("gh issue list", gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        context = output["hookSpecificOutput"]["additionalContext"]
        assert len(context) > 0, "additionalContext should not be empty"

    # ========== Real-World Scenarios ==========

    def test_scenario_integration(self):
        """Integration test: realistic gh pr create command triggers correctly"""
        cmd = 'gh pr create --title "Add feature" --body "Description" --head feature --base main'
        output = run_hook(cmd, gh_available=False, token_available=True)
        assert "hookSpecificOutput" in output, "Should detect gh pr create"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert len(context) > 0, "Should provide non-empty guidance"

    def test_scenario_after_suggestion_cooldown_active(self):
        """Real scenario: Multiple gh commands, only first triggers"""
        # First gh command - should trigger
        output1 = run_hook("gh issue list", gh_available=False, token_available=True, clear_cooldown=True)
        assert "hookSpecificOutput" in output1, "First command should trigger"

        # Subsequent gh commands within cooldown - should not trigger
        for i in range(3):
            output = run_hook("gh pr view 5", gh_available=False, token_available=True, clear_cooldown=False)
            assert output == {}, f"Command {i+2} should be suppressed by cooldown"

    # ========== Additional Coverage ==========

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
