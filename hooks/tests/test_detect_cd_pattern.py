#!/usr/bin/env python3
# /// script
# dependencies = ["pytest>=7.0.0"]
# ///
"""
Unit tests for detect-cd-pattern.py hook

Run with:
  uv run --script hooks/tests/test_detect_cd_pattern.py
Or:
  cd hooks/tests && uv run pytest test_detect_cd_pattern.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "detect-cd-pattern.py"


def run_hook(tool_name: str, command: str) -> dict:
    """Helper function to run the hook with given input and return parsed output"""
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestDetectCdPattern:
    """Test suite for detect-cd-pattern hook"""

    def test_subshell_pattern_allowed(self):
        """Subshell pattern (cd dir && cmd) should return {} (no warning)"""
        output = run_hook("Bash", "(cd /foo/bar && pytest tests)")
        assert output == {}, "Subshell pattern should not trigger warning"

    def test_subshell_with_spaces(self):
        """Subshell pattern with extra spaces should be allowed"""
        output = run_hook("Bash", "(  cd   /foo/bar  &&  pytest tests  )")
        assert output == {}, "Subshell pattern with spaces should not trigger warning"

    def test_global_cd_with_ampersand(self):
        """Global cd with && should trigger warning"""
        output = run_hook("Bash", "cd /foo/bar && pytest tests")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "GLOBAL CD DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_global_cd_with_semicolon(self):
        """Global cd with semicolon should trigger warning"""
        output = run_hook("Bash", "cd /foo/bar; pytest tests")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "GLOBAL CD DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_standalone_cd_at_start(self):
        """Standalone cd at command start should trigger warning"""
        output = run_hook("Bash", "cd /foo/bar")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "GLOBAL CD DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_no_cd_command(self):
        """Commands without cd should return {}"""
        output = run_hook("Bash", "pytest /foo/bar/tests")
        assert output == {}, "Commands without cd should not trigger warning"

    def test_absolute_path_usage(self):
        """Using absolute paths should return {}"""
        output = run_hook("Bash", "git -C /path/to/repo status")
        assert output == {}, "Absolute paths should not trigger warning"

    def test_non_bash_tool(self):
        """Non-Bash tools should return {}"""
        output = run_hook("Read", "cd /foo/bar && something")
        assert output == {}, "Non-Bash tools should not trigger warning"

    def test_cd_after_pipe(self):
        """cd after pipe should trigger warning"""
        output = run_hook("Bash", "echo test | cd /foo && bar")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "GLOBAL CD DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_multiple_commands_with_subshell_cd(self):
        """Multiple commands where cd is in subshell should be allowed"""
        output = run_hook("Bash", "echo start && (cd /foo && make) && echo done")
        assert output == {}, "Subshell cd in command chain should not trigger warning"

    def test_guidance_includes_target_dir(self):
        """Warning should include the target directory"""
        output = run_hook("Bash", "cd /specific/path && pytest")
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "/specific/path" in context, "Warning should mention target directory"

    def test_guidance_includes_subshell_alternative(self):
        """Warning should suggest subshell pattern as alternative"""
        output = run_hook("Bash", "cd /foo && bar")
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "(cd" in context, "Should suggest subshell pattern"
        assert "subshell" in context.lower(), "Should mention subshell"

    def test_json_output_valid(self):
        """All hook outputs should be valid JSON"""
        test_commands = [
            "cd /foo && bar",
            "(cd /foo && bar)",
            "pytest /foo/tests",
            "cd /foo; bar"
        ]
        for cmd in test_commands:
            output = run_hook("Bash", cmd)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {cmd}"

    def test_hook_event_name_correct(self):
        """Hook output should include correct event name"""
        output = run_hook("Bash", "cd /foo && bar")
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
