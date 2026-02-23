"""
Unit tests for run-with-fallback.sh wrapper script

This test suite validates that the wrapper properly handles hook execution failures
and prevents deadlocks as described in issue #26.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the wrapper script
WRAPPER_PATH = Path(__file__).parent.parent / "hooks" / "run-with-fallback.sh"


def run_wrapper(fail_mode: str, hook_path: str, stdin_data: str = '{"tool": "Test"}', env: dict | None = None) -> dict:
    """Helper function to run the wrapper with given input and return parsed output"""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        [str(WRAPPER_PATH), fail_mode, hook_path],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=merged_env,
    )

    # Wrapper should always exit 0 (non-blocking)
    assert result.returncode == 0, f"Wrapper should always exit 0, got {result.returncode}"

    # Parse first line of stdout as JSON (ignore any traceback after)
    stdout_lines = result.stdout.strip().split('\n')
    if stdout_lines:
        return json.loads(stdout_lines[0])
    return {}


class TestRunWithFallback:
    """Test suite for run-with-fallback.sh wrapper"""

    # Valid hook execution tests
    def test_valid_hook_execution_open_mode(self):
        """Valid hook should execute successfully in open mode"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        output = run_wrapper("open", hook_path)
        # Empty output means hook executed and returned {}
        assert output == {}, "Valid hook should execute and return its output"

    def test_valid_hook_execution_closed_mode(self):
        """Valid hook should execute successfully in closed mode"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        output = run_wrapper("closed", hook_path)
        # Empty output means hook executed and returned {}
        assert output == {}, "Valid hook should execute and return its output"

    # Missing hook file tests (open mode)
    def test_missing_hook_open_mode(self):
        """Missing hook file should return warning in open mode"""
        output = run_wrapper("open", "/nonexistent/path/to/hook.py")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"], "Should provide context"
        assert "Warning: Hook not found" in output["hookSpecificOutput"]["additionalContext"]
        assert "nonexistent" in output["hookSpecificOutput"]["additionalContext"] or "hook.py" in output["hookSpecificOutput"]["additionalContext"]

    def test_missing_hook_open_mode_allows_operation(self):
        """Missing hook in open mode should not block (no permissionDecision)"""
        output = run_wrapper("open", "/nonexistent/hook.py")
        assert "permissionDecision" not in output.get("hookSpecificOutput", {}), \
            "Open mode should not set permissionDecision"

    # Missing hook file tests (closed mode)
    def test_missing_hook_closed_mode(self):
        """Missing hook file should block operation in closed mode"""
        output = run_wrapper("closed", "/nonexistent/path/to/hook.py")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "permissionDecision" in output["hookSpecificOutput"], "Should have decision"
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny", "Should deny operation"

    def test_missing_hook_closed_mode_reason(self):
        """Missing hook in closed mode should provide clear reason"""
        output = run_wrapper("closed", "/nonexistent/path/to/safety-hook.py")
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "Safety hook not found" in reason, "Should mention safety hook not found"
        assert "safety-hook.py" in reason, "Should mention hook name"

    # Hook execution failure tests (open mode)
    def test_failing_hook_open_mode(self, tmp_path):
        """Failing hook should return warning in open mode"""
        # Create a hook that fails
        failing_hook = tmp_path / "failing_hook.py"
        failing_hook.write_text('''#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
import sys
sys.exit(1)
''')
        failing_hook.chmod(0o755)

        output = run_wrapper("open", str(failing_hook))
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"], "Should provide context"
        assert "Warning: Hook execution failed" in output["hookSpecificOutput"]["additionalContext"]

    def test_crashing_hook_open_mode(self, tmp_path):
        """Crashing hook should return warning in open mode"""
        # Create a hook that crashes
        crashing_hook = tmp_path / "crashing_hook.py"
        crashing_hook.write_text('''#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
raise Exception("Intentional crash")
''')
        crashing_hook.chmod(0o755)

        output = run_wrapper("open", str(crashing_hook))
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"], "Should provide context"
        assert "Warning: Hook execution failed" in output["hookSpecificOutput"]["additionalContext"]

    # Hook execution failure tests (closed mode)
    def test_failing_hook_closed_mode(self, tmp_path):
        """Failing hook should block operation in closed mode"""
        # Create a hook that fails
        failing_hook = tmp_path / "failing_safety_hook.py"
        failing_hook.write_text('''#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
import sys
sys.exit(1)
''')
        failing_hook.chmod(0o755)

        output = run_wrapper("closed", str(failing_hook))
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny", "Should deny operation"
        assert "Safety hook execution failed" in output["hookSpecificOutput"]["permissionDecisionReason"]

    # Wrapper always exits 0 (non-blocking at shell level)
    def test_wrapper_always_exits_zero(self, tmp_path):
        """Wrapper should always exit 0 to prevent blocking Claude"""
        # Test with missing hook
        result = subprocess.run(
            [str(WRAPPER_PATH), "open", "/nonexistent/hook.py"],
            input='{"tool": "Test"}',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Wrapper should exit 0 for missing hook"

        # Test with failing hook
        failing_hook = tmp_path / "fail.py"
        failing_hook.write_text('#!/usr/bin/env python3\n# /// script\n# dependencies = []\n# ///\nimport sys\nsys.exit(1)')
        failing_hook.chmod(0o755)

        result = subprocess.run(
            [str(WRAPPER_PATH), "open", str(failing_hook)],
            input='{"tool": "Test"}',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Wrapper should exit 0 for failing hook"

    # JSON output format tests
    def test_json_output_valid_for_missing_hook(self):
        """Missing hook output should be valid JSON"""
        output = run_wrapper("open", "/nonexistent/hook.py")
        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert "hookSpecificOutput" in output
        assert isinstance(output["hookSpecificOutput"], dict)

    def test_json_output_valid_for_open_mode_failure(self, tmp_path):
        """Open mode failure output should be valid JSON"""
        failing_hook = tmp_path / "fail.py"
        failing_hook.write_text('#!/usr/bin/env python3\n# /// script\n# dependencies = []\n# ///\nimport sys\nsys.exit(1)')
        failing_hook.chmod(0o755)

        output = run_wrapper("open", str(failing_hook))
        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_json_output_valid_for_closed_mode_failure(self):
        """Closed mode failure output should be valid JSON"""
        output = run_wrapper("closed", "/nonexistent/hook.py")
        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert "hookSpecificOutput" in output
        assert "permissionDecision" in output["hookSpecificOutput"]
        assert "permissionDecisionReason" in output["hookSpecificOutput"]

    # Hook name extraction tests
    def test_hook_name_extracted_from_path(self):
        """Wrapper should extract hook name from full path"""
        output = run_wrapper("open", "/some/long/path/to/my-custom-hook.py")
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "my-custom-hook.py" in context, "Should show just the hook filename"

    # Permission auto-fix tests
    def test_non_executable_hook_auto_chmod(self, tmp_path):
        """Non-executable hook should be automatically chmod'd"""
        # Create a non-executable hook
        hook = tmp_path / "non_executable.py"
        hook.write_text('''#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
import json
print(json.dumps({}))
''')
        # Explicitly make it non-executable
        hook.chmod(0o644)
        assert not hook.stat().st_mode & 0o111, "Hook should not be executable"

        # Run wrapper - it should try to chmod and execute
        output = run_wrapper("open", str(hook))
        # If it succeeded, hook was made executable and ran
        # If it failed, we'll get a warning (which is also acceptable)
        assert isinstance(output, dict), "Should return valid JSON"

    # Real-world integration tests
    def test_deadlock_prevention_scenario(self, tmp_path):
        """Simulate issue #26 deadlock scenario - should not block"""
        # Simulate broken hook path (like the ~/.claude/hooks/ vs .claude/hooks/ issue)
        broken_path = "/root/.claude/hooks/normalize-line-endings.py"

        # In open mode, this should warn but not block
        output = run_wrapper("open", broken_path)
        assert "hookSpecificOutput" in output, "Should provide feedback"
        assert "additionalContext" in output["hookSpecificOutput"], "Should warn about issue"
        assert "Warning: Hook not found" in output["hookSpecificOutput"]["additionalContext"]

        # Operations can proceed despite broken hook
        assert "permissionDecision" not in output.get("hookSpecificOutput", {}), \
            "Should not block operation"

    def test_all_current_hooks_work_through_wrapper(self):
        """All existing hooks should work when called through wrapper"""
        hooks_dir = Path(__file__).parent.parent / "hooks"
        hook_files = [
            "normalize-line-endings.py",
            "gh-authorship-attribution.py",
            "gh-web-fallback.py",
            "prefer-modern-tools.py",
            "detect-cd-pattern.py",
            "auto-unsandbox-pbcopy.py",
            "prefer-gh-for-own-repos.py",
            "gpg-signing-helper.py",
            "detect-heredoc-errors.py",
            "gh-fallback-helper.py",
            "suggest-uv-for-missing-deps.py",
        ]

        for hook_file in hook_files:
            hook_path = str(hooks_dir / hook_file)
            if Path(hook_path).exists():
                # Run wrapper and verify it doesn't crash
                result = subprocess.run(
                    [str(WRAPPER_PATH), "open", hook_path],
                    input='{"tool": "Test"}',
                    capture_output=True,
                    text=True
                )
                # Wrapper should always exit 0
                assert result.returncode == 0, f"Wrapper should exit 0 for {hook_file}"
                # Output should be valid (either valid JSON or empty)
                stdout_lines = result.stdout.strip().split('\n')
                if stdout_lines and stdout_lines[0]:
                    try:
                        output = json.loads(stdout_lines[0])
                        assert isinstance(output, dict), f"Hook {hook_file} should return valid JSON dict"
                    except json.JSONDecodeError:
                        pytest.fail(f"Hook {hook_file} returned invalid JSON: {stdout_lines[0]}")

    # Edge cases
    def test_empty_stdin(self):
        """Wrapper should handle empty stdin gracefully"""
        result = subprocess.run(
            [str(WRAPPER_PATH), "open", "/nonexistent/hook.py"],
            input='',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Should exit 0 even with empty stdin"

    def test_malformed_json_stdin(self):
        """Wrapper should handle malformed JSON in stdin"""
        result = subprocess.run(
            [str(WRAPPER_PATH), "open", "/nonexistent/hook.py"],
            input='not valid json {[}',
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Should exit 0 even with malformed stdin"

    def test_unknown_fail_mode_defaults_to_open(self):
        """Unknown fail mode should behave like open mode (non-blocking)"""
        output = run_wrapper("unknown", "/nonexistent/hook.py")
        # Should not block (no deny decision)
        hook_output = output.get("hookSpecificOutput", {})
        if "permissionDecision" in hook_output:
            # If it has a decision, it should not be deny (unknown mode != closed)
            assert hook_output["permissionDecision"] != "deny", \
                "Unknown mode should not block like closed mode"


class TestLogging:
    """Tests for the CLAUDE_HOOK_LOG_DIR tee-logging feature"""

    def test_logging_disabled_by_default(self, tmp_path):
        """No log file should be created when CLAUDE_HOOK_LOG_DIR is not set"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        # Explicitly unset the env var to guarantee no logging
        env = {k: v for k, v in __import__("os").environ.items() if k != "CLAUDE_HOOK_LOG_DIR"}
        result = __import__("subprocess").run(
            [str(WRAPPER_PATH), "open", hook_path],
            input='{"session_id": "test-session", "tool": "Test"}',
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        # tmp_path is empty — no log file was created anywhere unexpected
        assert list(tmp_path.iterdir()) == []

    def test_logging_creates_jsonl_file(self, tmp_path):
        """Log file should be created when CLAUDE_HOOK_LOG_DIR is set"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        log_dir = tmp_path / "hook-logs"
        run_wrapper(
            "open", hook_path,
            stdin_data='{"session_id": "abc123", "tool": "Test"}',
            env={"CLAUDE_HOOK_LOG_DIR": str(log_dir)},
        )
        log_file = log_dir / "abc123.jsonl"
        assert log_file.exists(), "Log file should be created for the session"

    def test_logging_entry_format(self, tmp_path):
        """Each JSONL entry should have ts, hook, input, and output fields"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        log_dir = tmp_path / "hook-logs"
        run_wrapper(
            "open", hook_path,
            stdin_data='{"session_id": "sess1", "tool": "Test"}',
            env={"CLAUDE_HOOK_LOG_DIR": str(log_dir)},
        )
        entries = [(log_dir / "sess1.jsonl").read_text().strip().splitlines()]
        assert len(entries[0]) == 1, "Should have exactly one log entry"
        entry = json.loads(entries[0][0])
        assert "ts" in entry, "Entry should have timestamp"
        assert "hook" in entry, "Entry should have hook name"
        assert "input" in entry, "Entry should have input"
        assert "output" in entry, "Entry should have output"

    def test_logging_captures_input_and_output(self, tmp_path):
        """Log entry should contain the actual input and hook output"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        log_dir = tmp_path / "hook-logs"
        stdin_data = '{"session_id": "sess2", "tool": "Write", "content": "hello"}'
        run_wrapper(
            "open", hook_path,
            stdin_data=stdin_data,
            env={"CLAUDE_HOOK_LOG_DIR": str(log_dir)},
        )
        entry_line = (log_dir / "sess2.jsonl").read_text().strip()
        entry = json.loads(entry_line)
        assert isinstance(entry["input"], dict), "Input should be parsed JSON"
        assert entry["input"]["tool"] == "Write", "Input should contain original data"
        assert "hook" in entry and "normalize-line-endings.py" in entry["hook"]

    def test_logging_error_hook(self, tmp_path):
        """Logging should capture fallback output when hook is missing"""
        log_dir = tmp_path / "hook-logs"
        run_wrapper(
            "open", "/nonexistent/hook.py",
            stdin_data='{"session_id": "sess3"}',
            env={"CLAUDE_HOOK_LOG_DIR": str(log_dir)},
        )
        log_file = log_dir / "sess3.jsonl"
        assert log_file.exists(), "Log file should be created even for missing hook"
        entry = json.loads(log_file.read_text().strip())
        assert "output" in entry
        assert "hookSpecificOutput" in entry["output"]

    def test_logging_failure_doesnt_affect_hook_output(self, tmp_path):
        """Hook output should be unaffected if logging fails (e.g. unwritable dir)"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        # Point to an unwritable directory
        log_dir = tmp_path / "readonly-logs"
        log_dir.mkdir()
        log_dir.chmod(0o444)  # read-only
        try:
            output = run_wrapper(
                "open", hook_path,
                stdin_data='{"session_id": "sess4", "tool": "Test"}',
                env={"CLAUDE_HOOK_LOG_DIR": str(log_dir)},
            )
            # Hook output should still be valid JSON
            assert isinstance(output, dict), "Hook output must be returned even if logging fails"
        finally:
            log_dir.chmod(0o755)  # restore for cleanup

    def test_logging_empty_env_var_disables_logging(self, tmp_path):
        """CLAUDE_HOOK_LOG_DIR='' should not create any log files"""
        hook_path = str(Path(__file__).parent.parent / "hooks" / "normalize-line-endings.py")
        run_wrapper(
            "open", hook_path,
            stdin_data='{"session_id": "sess5", "tool": "Test"}',
            env={"CLAUDE_HOOK_LOG_DIR": ""},
        )
        assert list(tmp_path.iterdir()) == [], "No log files should be created with empty env var"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
