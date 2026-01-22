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
    def test_standalone_pbcopy(self):
        """Standalone pbcopy command should be auto-approved with unsandboxing"""
        output = run_hook("Bash", "pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["hookEventName"] == "PreToolUse"
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_echo_pipe_pbcopy(self):
        """echo text piped to pbcopy should be auto-approved with unsandboxing"""
        output = run_hook("Bash", 'echo "hello world" | pbcopy')
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_cat_pipe_pbcopy(self):
        """cat file piped to pbcopy should be auto-approved with unsandboxing"""
        output = run_hook("Bash", "cat file.txt | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_pbcopy_with_stdin_redirect(self):
        """pbcopy with stdin redirect should be auto-approved with unsandboxing"""
        output = run_hook("Bash", "pbcopy < file.txt")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_command_substitution_pipe_pbcopy(self):
        """Command substitution piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "git rev-parse HEAD | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_heredoc_pipe_pbcopy(self):
        """Heredoc piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "cat <<EOF | pbcopy\nsome text\nEOF")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    def test_pbcopy_in_command_chain(self):
        """pbcopy in a command chain should be auto-approved"""
        output = run_hook("Bash", "echo test && echo result | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        hook_output = output["hookSpecificOutput"]
        assert hook_output["permissionDecision"] == "allow"
        assert hook_output["updatedInput"]["dangerouslyDisableSandbox"] is True

    # Non-pbcopy commands should return empty JSON
    def test_no_pbcopy_command(self):
        """Commands without pbcopy should return {}"""
        output = run_hook("Bash", "echo 'hello world'")
        assert output == {}, "Commands without pbcopy should return empty JSON"

    def test_regular_bash_command(self):
        """Regular bash commands should return {}"""
        test_commands = [
            "ls -la",
            "git status",
            "pytest tests/",
            "make build",
            "echo test"
        ]
        for cmd in test_commands:
            output = run_hook("Bash", cmd)
            assert output == {}, f"'{cmd}' should return empty JSON"

    # Non-Bash tools should return empty JSON
    def test_non_bash_tool(self):
        """Non-Bash tools should return {}"""
        output = run_hook("Read", "pbcopy")
        assert output == {}, "Non-Bash tools should return empty JSON"

    def test_various_non_bash_tools(self):
        """Various non-Bash tools with pbcopy should return {}"""
        non_bash_tools = ["Read", "Write", "Edit", "Grep", "Glob"]
        for tool in non_bash_tools:
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
    def test_pbcopy_with_leading_whitespace(self):
        """pbcopy with leading whitespace should be auto-approved"""
        output = run_hook("Bash", "  pbcopy  ")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_pbcopy_with_newlines(self):
        """pbcopy command with newlines should be auto-approved"""
        output = run_hook("Bash", "echo test | \\\npbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_pbcopy_with_tabs(self):
        """pbcopy command with tabs should be auto-approved"""
        output = run_hook("Bash", "echo test\t|\tpbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    # Case sensitivity
    def test_pbcopy_uppercase(self):
        """Uppercase PBCOPY should not trigger (case sensitive match)"""
        output = run_hook("Bash", "echo test | PBCOPY")
        assert output == {}, "Uppercase PBCOPY should not trigger (case sensitive)"

    def test_pbcopy_mixed_case(self):
        """Mixed case PbCopy should not trigger (case sensitive match)"""
        output = run_hook("Bash", "echo test | PbCopy")
        assert output == {}, "Mixed case should not trigger (case sensitive)"

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
    def test_git_diff_pipe_pbcopy(self):
        """git diff piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "git diff | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_curl_result_pipe_pbcopy(self):
        """curl result piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "curl -s https://example.com | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_python_output_pipe_pbcopy(self):
        """Python script output piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "python3 script.py | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_jq_processing_pipe_pbcopy(self):
        """jq processing piped to pbcopy should be auto-approved"""
        output = run_hook("Bash", "cat data.json | jq '.results' | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_grep_awk_sed_pipe_pbcopy(self):
        """Complex text processing pipeline with pbcopy should be auto-approved"""
        output = run_hook("Bash", "grep ERROR logs.txt | awk '{print $1}' | sed 's/^/ERROR: /' | pbcopy")
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
