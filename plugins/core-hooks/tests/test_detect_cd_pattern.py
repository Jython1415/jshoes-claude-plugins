"""
Unit tests for detect-cd-pattern.py hook

This test suite validates that the hook properly detects cd command patterns.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "detect-cd-pattern.py"


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

    @pytest.mark.parametrize("tool_name,command", [
        ("Bash", "cd /foo/bar && pytest tests"),
        ("Bash", "cd /foo/bar; pytest tests"),
        ("Bash", "cd /foo/bar"),
    ])
    def test_global_cd_detection(self, tool_name, command):
        """Global cd should trigger warning"""
        output = run_hook(tool_name, command)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_cd_after_pipe(self):
        """cd after pipe should trigger warning"""
        output = run_hook("Bash", "echo test | cd /foo && bar")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

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

    @pytest.mark.parametrize("tool_name,command", [
        ("Bash", "pytest /foo/bar/tests"),
        ("Bash", "git -C /path/to/repo status"),
        ("Read", "cd /foo/bar && something"),
        ("Bash", 'echo "cd /tmp"'),
        ("Bash", "echo 'cd /tmp'"),
        ("Bash", 'git commit -m "cd to new directory structure"'),
        ("Bash", "grep 'cd /tmp' file.txt"),
        ("Bash", "(echo start && cd /tmp && make && echo done)"),
        ("Bash", "((cd /tmp && make))"),
    ])
    def test_empty_output_cases(self, tool_name, command):
        """Commands that should return empty output (no warning)"""
        output = run_hook(tool_name, command)
        assert output == {}, f"Should not trigger warning for: {command}"

    @pytest.mark.parametrize("command", [
        "abcd efgh",
        "cdrom /dev/cdrom",
        "lcd display",
        "encoded data",
        "/path/to/cdrom"
    ])
    def test_cd_as_part_of_word(self, command):
        """cd as part of a larger word should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"'{command}' should not trigger (cd is part of word)"

    @pytest.mark.parametrize("command", [
        "cat cd.txt",
        "./cd-script.sh",
        "python3 my-cd-tool.py",
        "ls -la cd_backup",
        "rm -f old_cd.log"
    ])
    def test_cd_in_filename(self, command):
        """cd in filename should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"'{command}' should not trigger (cd in filename)"

    @pytest.mark.parametrize("command", [
        "cd -",
        "cd ~",
        "cd",
        "cd;echo test",
        "cd&&echo test",
        "cd|grep test",
        "cd ..",
        "echo test;cd /tmp",
    ])
    def test_special_cd_arguments(self, command):
        """Special cd arguments should trigger warning (they change directory)"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"{command} should trigger warning"

    def test_cd_with_variable(self):
        """cd with variable should trigger (still changes directory)"""
        output = run_hook("Bash", "cd $BUILD_DIR && make")
        assert "hookSpecificOutput" in output, "cd with variable should trigger"

    def test_cd_with_complex_path(self):
        """cd with complex path should trigger"""
        output = run_hook("Bash", "cd /var/lib/app/$(date +%Y%m%d) && process")
        assert "hookSpecificOutput" in output, "cd with command substitution should trigger"

    @pytest.mark.parametrize("command", [
        "echo $CDPATH",
        "export CD_DIR=/tmp",
        "${CD_ROOT}/bin/app"
    ])
    def test_env_var_with_cd_in_name(self, command):
        """Environment variables with cd in name should not trigger"""
        output = run_hook("Bash", command)
        assert output == {}, f"'{command}' should not trigger (env var, not cd command)"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
