"""
Unit tests for auto-unsandbox-pbcopy.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_auto_unsandbox_pbcopy.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "auto-unsandbox-pbcopy.py"


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

    # Handle empty output (e.g., when non-Bash tool exits early)
    if not result.stdout.strip():
        return {}

    return json.loads(result.stdout)


class TestAutoUnsandboxPbcopy:
    """Test suite for auto-unsandbox-pbcopy hook"""

    # Basic pbcopy detection tests
    @pytest.mark.parametrize("description,command", [
        ("standalone pbcopy", "pbcopy"),
        ("echo pipe pbcopy", 'echo "hello world" | pbcopy'),
        ("cat pipe pbcopy", "cat file.txt | pbcopy"),
        ("pbcopy with stdin redirect", "pbcopy < file.txt"),
        ("command substitution pipe pbcopy", "git rev-parse HEAD | pbcopy"),
        ("heredoc pipe pbcopy", "cat <<EOF | pbcopy\nsome text\nEOF"),
        ("pbcopy in command chain", "echo test && echo result | pbcopy"),
    ])
    def test_basic_pbcopy_detection(self, description, command):
        """Test basic pbcopy detection scenarios"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"Should return hook output for: {description}"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PreToolUse"
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    # Non-pbcopy commands should return empty JSON
    def test_no_pbcopy_command(self):
        """Commands without pbcopy should return {}"""
        output = run_hook("Bash", "echo 'hello world'")
        assert output == {}, "Commands without pbcopy should return empty JSON"

    @pytest.mark.parametrize("command", [
        "ls -la",
        "git status",
        "pytest tests/",
        "make build",
        "echo test",
    ])
    def test_regular_bash_command(self, command):
        """Regular bash commands should return {}"""
        output = run_hook("Bash", command)
        assert output == {}, f"'{command}' should return empty JSON"

    # Non-Bash tools should return empty JSON
    def test_non_bash_tool(self):
        """Non-Bash tools should return {}"""
        output = run_hook("Read", "pbcopy")
        assert output == {}, "Non-Bash tools should return empty JSON"

    @pytest.mark.parametrize("tool", [
        "Read",
        "Write",
        "Edit",
        "Grep",
        "Glob",
    ])
    def test_various_non_bash_tools(self, tool):
        """Various non-Bash tools with pbcopy should return {}"""
        output = run_hook(tool, "echo test | pbcopy")
        assert output == {}, f"{tool} tool should return empty JSON"

    # JSON output validation
    def test_json_output_valid(self):
        """All hook outputs should be valid JSON"""
        test_commands = [
            "pbcopy",
            'echo "test" | pbcopy',
            "cat file.txt | pbcopy",
            "ls -la"  # non-pbcopy command
        ]
        for cmd in test_commands:
            output = run_hook("Bash", cmd)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {cmd}"

    def test_hook_output_structure(self):
        """Hook output should have correct structure"""
        output = run_hook("Bash", "pbcopy")
        assert "hookSpecificOutput" in output
        hook_output = output["hookSpecificOutput"]

        # Check required fields
        assert "hookEventName" in hook_output
        assert "permissionDecision" in hook_output
        assert "permissionDecisionReason" in hook_output
        assert "updatedInput" in hook_output

        # Check field values
        assert hook_output["hookEventName"] == "PreToolUse"
        assert hook_output["permissionDecision"] == "allow"
        assert "auto-approved" in hook_output["permissionDecisionReason"]
        assert "unsandboxed" in hook_output["permissionDecisionReason"]

    def test_updated_input_preserves_command(self):
        """Updated input should preserve the original command"""
        original_command = 'echo "test data" | pbcopy'
        output = run_hook("Bash", original_command)
        updated_input = output["hookSpecificOutput"]["updatedInput"]
        assert updated_input["command"] == original_command

    def test_dangerously_disable_sandbox_set(self):
        """dangerouslyDisableSandbox should be set to True"""
        output = run_hook("Bash", "pbcopy")
        updated_input = output["hookSpecificOutput"]["updatedInput"]
        assert "dangerouslyDisableSandbox" in updated_input
        assert updated_input["dangerouslyDisableSandbox"] is True

    # Edge cases - pbcopy in strings and filenames
    def test_pbcopy_in_string_literal_double_quotes(self):
        """pbcopy in double-quoted string should still trigger (substring match)"""
        # Note: The hook uses simple substring matching, so this will trigger
        output = run_hook("Bash", 'echo "pbcopy is a tool"')
        assert "hookSpecificOutput" in output, "pbcopy in string literal triggers (substring match)"

    def test_pbcopy_in_string_literal_single_quotes(self):
        """pbcopy in single-quoted string should still trigger (substring match)"""
        # Note: The hook uses simple substring matching, so this will trigger
        output = run_hook("Bash", "echo 'use pbcopy to copy'")
        assert "hookSpecificOutput" in output, "pbcopy in string literal triggers (substring match)"

    def test_pbcopy_in_filename(self):
        """pbcopy in filename should still trigger (substring match)"""
        # Note: The hook uses simple substring matching, so this will trigger
        test_cases = [
            "cat pbcopy.txt",
            "./pbcopy-helper.sh",
            "rm pbcopy_backup.log"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd)
            assert "hookSpecificOutput" in output, f"'{cmd}' triggers (substring match)"

    def test_pbcopy_as_part_of_word(self):
        """pbcopy as part of a larger word should still trigger (substring match)"""
        # Note: The hook uses simple substring matching, so this will trigger
        test_cases = [
            "mypbcopy_script.sh",
            "pbcopy_wrapper",
            "use_pbcopy_here"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd)
            assert "hookSpecificOutput" in output, f"'{cmd}' triggers (substring match)"

    def test_pbcopy_in_path(self):
        """pbcopy in path should still trigger (substring match)"""
        output = run_hook("Bash", "ls /usr/local/bin/pbcopy")
        assert "hookSpecificOutput" in output, "pbcopy in path triggers (substring match)"

    def test_pbcopy_in_variable_name(self):
        """pbcopy in variable name should still trigger (substring match)"""
        test_cases = [
            "echo $pbcopy_cmd",
            "export pbcopy_path=/usr/bin/pbcopy",
            "${pbcopy_enabled}"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd)
            assert "hookSpecificOutput" in output, f"'{cmd}' triggers (substring match)"

    # Complex pipe patterns
    def test_multiple_pipe_stages_with_pbcopy(self):
        """Multiple pipe stages ending with pbcopy should be auto-approved"""
        output = run_hook("Bash", "cat file.txt | grep pattern | sed 's/foo/bar/' | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_pbcopy_with_tee(self):
        """Using tee with pbcopy should be auto-approved"""
        output = run_hook("Bash", "echo test | tee output.txt | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_subshell_with_pbcopy(self):
        """Subshell output piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "(cd /tmp && ls) | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_command_substitution_containing_pbcopy(self):
        """Command containing pbcopy in any position should be auto-approved"""
        output = run_hook("Bash", "result=$(echo test | pbcopy)")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    # Whitespace and formatting variations
    @pytest.mark.parametrize("description,command", [
        ("leading whitespace", "  pbcopy  "),
        ("newlines in command", "echo test | \\\npbcopy"),
        ("tabs in command", "echo test\t|\tpbcopy"),
    ])
    def test_whitespace_variations(self, description, command):
        """Test pbcopy detection with various whitespace and formatting"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"Should return hook output for: {description}"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    # Case sensitivity
    @pytest.mark.parametrize("description,command", [
        ("uppercase PBCOPY", "echo test | PBCOPY"),
        ("mixed case PbCopy", "echo test | PbCopy"),
    ])
    def test_case_sensitivity(self, description, command):
        """Test that pbcopy detection is case sensitive"""
        output = run_hook("Bash", command)
        assert output == {}, f"{description} should not trigger (case sensitive)"

    # Empty and minimal inputs
    def test_empty_command(self):
        """Empty command should return {}"""
        output = run_hook("Bash", "")
        assert output == {}, "Empty command should return empty JSON"

    def test_minimal_pbcopy_command(self):
        """Minimal pbcopy command should be auto-approved"""
        output = run_hook("Bash", "pbcopy")
        assert "hookSpecificOutput" in output, "Minimal pbcopy should trigger"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    # Permission decision reason
    def test_permission_reason_mentions_pbcopy(self):
        """Permission decision reason should mention pbcopy"""
        output = run_hook("Bash", "pbcopy")
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "pbcopy" in reason.lower(), "Reason should mention pbcopy"

    def test_permission_reason_mentions_unsandboxed(self):
        """Permission decision reason should mention unsandboxed mode requirement"""
        output = run_hook("Bash", "pbcopy")
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "unsandboxed" in reason.lower(), "Reason should mention unsandboxed mode"

    # Complex real-world scenarios
    @pytest.mark.parametrize("description,command", [
        ("git diff pipe pbcopy", "git diff | pbcopy"),
        ("curl result pipe pbcopy", "curl -s https://example.com | pbcopy"),
        ("python output pipe pbcopy", "python3 script.py | pbcopy"),
        ("jq processing pipe pbcopy", "cat data.json | jq '.results' | pbcopy"),
        ("grep awk sed pipe pbcopy", "grep ERROR logs.txt | awk '{print $1}' | sed 's/^/ERROR: /' | pbcopy"),
    ])
    def test_real_world_scenarios(self, description, command):
        """Test real-world scenarios with pbcopy"""
        output = run_hook("Bash", command)
        assert "hookSpecificOutput" in output, f"Should return hook output for: {description}"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
