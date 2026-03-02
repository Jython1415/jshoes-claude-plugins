"""
Unit tests for block-heredoc-in-bash.py hook

This test suite validates that the hook properly detects and blocks heredoc patterns
in Bash commands before they can silently corrupt data in sandbox mode.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "block-heredoc-in-bash.py"


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


class TestHeredocBlocking:
    """Test suite for block-heredoc-in-bash hook"""

    def test_blocks_unquoted_heredoc(self):
        """Unquoted heredoc should be blocked"""
        output = run_hook("Bash", "cat > file <<EOF\nsome content\nEOF")
        assert "hookSpecificOutput" in output

    def test_blocks_single_quoted_heredoc(self):
        """Single-quoted heredoc delimiter should be blocked"""
        output = run_hook("Bash", "gh issue create --body \"$(cat <<'EOF'\nsome body\nEOF\n)\"")
        assert "hookSpecificOutput" in output

    def test_blocks_double_quoted_heredoc(self):
        """Double-quoted heredoc delimiter should be blocked"""
        output = run_hook("Bash", 'cat <<"EOF"\nsome content\nEOF')
        assert "hookSpecificOutput" in output

    def test_blocks_dash_heredoc(self):
        """Dash heredoc (strip leading tabs) should be blocked"""
        output = run_hook("Bash", "cat <<-EOF\n\tsome content\nEOF")
        assert "hookSpecificOutput" in output

    def test_blocks_dash_single_quoted_heredoc(self):
        """Dash + single-quoted heredoc should be blocked"""
        output = run_hook("Bash", "cat <<-'EOF'\n\tsome content\nEOF")
        assert "hookSpecificOutput" in output

    def test_blocks_dash_double_quoted_heredoc(self):
        """Dash + double-quoted heredoc should be blocked"""
        output = run_hook("Bash", 'cat <<-"EOF"\n\tsome content\nEOF')
        assert "hookSpecificOutput" in output

    def test_no_block_for_regular_bash(self):
        """Regular bash commands without heredoc should not be blocked"""
        output = run_hook("Bash", 'git commit -m "hello"')
        assert output == {}

    def test_no_block_for_non_bash_tool(self):
        """Non-Bash tools with heredoc-like content in command should not be blocked"""
        output = run_hook("Write", "cat <<EOF\nsome content\nEOF")
        assert output == {}

    def test_block_output_has_permission_decision_field(self):
        """Blocked commands should have permissionDecision: deny in hook output"""
        output = run_hook("Bash", "cat <<EOF\nfoo\nEOF")
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_block_output_has_permission_decision_reason(self):
        """Blocked commands should have non-empty permissionDecisionReason"""
        output = run_hook("Bash", "cat <<EOF\nfoo\nEOF")
        hook_output = output["hookSpecificOutput"]
        assert "permissionDecisionReason" in hook_output
        assert len(hook_output["permissionDecisionReason"]) > 0

    def test_block_output_has_hook_event_name(self):
        """Blocked output should include hookEventName"""
        output = run_hook("Bash", "cat <<EOF\nfoo\nEOF")
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_json_output_valid_for_all_cases(self):
        """All hook outputs should be valid JSON dicts"""
        test_cases = [
            ("Bash", "cat <<EOF\nfoo\nEOF"),
            ("Bash", "git commit -m \"hello\""),
            ("Write", "cat <<EOF\nfoo\nEOF"),
        ]
        for tool_name, command in test_cases:
            output = run_hook(tool_name, command)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {command}"

    def test_no_block_for_empty_command(self):
        """Empty command should not be blocked"""
        output = run_hook("Bash", "")
        assert output == {}

    def test_blocks_heredoc_with_custom_delimiter(self):
        """Heredoc with a non-EOF delimiter should also be blocked"""
        output = run_hook("Bash", "cat <<BODY\nsome content\nBODY")
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_no_block_for_arithmetic_left_shift(self):
        """Arithmetic left shift should not trigger the heredoc blocker"""
        output = run_hook("Bash", "echo $((1 << 4))")
        assert output == {}, "Arithmetic left shift should not trigger heredoc block"

    def test_no_block_for_bitshift_with_variable(self):
        """Bitwise shift with variable operand should not trigger the heredoc blocker"""
        output = run_hook("Bash", 'python -c "x = 1 << n; print(x)"')
        assert output == {}, "Bitwise shift should not trigger heredoc block"


def main():
    """Run tests when executed as a script"""
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
