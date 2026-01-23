"""
Unit tests for detect-heredoc-errors.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_detect_heredoc_errors.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "detect-heredoc-errors.py"

# The specific error message that triggers the hook
HEREDOC_ERROR = "can't create temp file for here document"


def run_hook_with_error(tool_name: str, error: str, use_tool_result: bool = False) -> dict:
    """Helper function to run the hook with error input and return parsed output

    Args:
        tool_name: Name of the tool (e.g., "Bash")
        error: The error message to include
        use_tool_result: If True, place error in tool_result.error (PostToolUse)
                        If False, place error in top-level error field (PostToolUseFailure)
    """
    if use_tool_result:
        # PostToolUse format - error in tool_result.error
        input_data = {
            "tool_name": tool_name,
            "tool_result": {"error": error}
        }
    else:
        # PostToolUseFailure format - error in top-level field
        input_data = {
            "tool_name": tool_name,
            "error": error
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


def run_hook_success(tool_name: str, command: str = "echo test") -> dict:
    """Helper function to run the hook with successful command (no error)"""
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

    if result.returncode not in [0, 1]:
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestDetectHeredocErrors:
    """Test suite for detect-heredoc-errors hook"""

    # PostToolUseFailure tests (error in top-level field)
    def test_posttoolusefailure_heredoc_error_detected(self):
        """PostToolUseFailure with heredoc error should trigger hook"""
        error_msg = f"bash: {HEREDOC_ERROR}: No such file or directory"
        output = run_hook_with_error("Bash", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_posttoolusefailure_exact_error_message(self):
        """PostToolUseFailure with exact heredoc error string should trigger"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_posttoolusefailure_heredoc_error_with_context(self):
        """PostToolUseFailure with heredoc error plus additional context should trigger"""
        error_msg = f"Command failed:\nbash: line 1: {HEREDOC_ERROR}: No such file or directory\nExit code: 1"
        output = run_hook_with_error("Bash", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    # PostToolUse tests (error in tool_result.error field)
    def test_posttooluse_heredoc_error_detected(self):
        """PostToolUse with heredoc error in tool_result.error should trigger hook"""
        error_msg = f"bash: {HEREDOC_ERROR}: No such file or directory"
        output = run_hook_with_error("Bash", error_msg, use_tool_result=True)

        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_posttooluse_exact_error_message(self):
        """PostToolUse with exact heredoc error string should trigger"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR, use_tool_result=True)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_both_error_locations_posttoolusefailure_priority(self):
        """When error exists in both locations, top-level error should be used"""
        input_data = {
            "tool_name": "Bash",
            "error": HEREDOC_ERROR,
            "tool_result": {"error": "different error"}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    # Non-heredoc errors should return empty JSON
    @pytest.mark.parametrize("error_message,description", [
        ("bash: syntax error near unexpected token `)'", "Bash syntax error without heredoc"),
        ("bash: foobar: command not found", "Command not found error"),
        ("bash: ./script.sh: Permission denied", "Permission denied error"),
        ("bash: nonexistent.txt: No such file or directory", "File not found error"),
        ("bash: unexpected EOF while looking for matching `\"'", "EOF error without heredoc keyword"),
        ("bash: line 42: unexpected error occurred", "Generic bash error"),
    ])
    def test_non_heredoc_bash_errors(self, error_message, description):
        """Non-heredoc errors should return {} and not trigger the hook"""
        output = run_hook_with_error("Bash", error_message)
        assert output == {}, f"{description} should not trigger"

    # Non-Bash tools should return empty JSON
    @pytest.mark.parametrize("tool_name", ["Read", "Write", "Edit", "Glob"])
    def test_non_bash_tools_with_heredoc_error(self, tool_name):
        """Non-Bash tools with heredoc error message should return {}"""
        output = run_hook_with_error(tool_name, HEREDOC_ERROR)
        assert output == {}, f"{tool_name} tool should not trigger even with heredoc error"

    # Successful commands should return empty JSON
    def test_successful_bash_command(self):
        """Successful Bash command with no error should return {}"""
        output = run_hook_success("Bash", "echo 'hello world'")
        assert output == {}, "Successful command should not trigger"

    def test_successful_git_commit(self):
        """Successful git commit command should return {}"""
        output = run_hook_success("Bash", "git commit -m 'fix: update config'")
        assert output == {}, "Successful git commit should not trigger"

    def test_no_error_field(self):
        """Input with no error field at all should return {}"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "echo test"}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert output == {}, "No error field should return {}"

    def test_empty_error_field(self):
        """Input with empty error field should return {}"""
        output = run_hook_with_error("Bash", "")
        assert output == {}, "Empty error should return {}"

    # JSON output format validation
    def test_json_output_structure(self):
        """Hook output should have correct JSON structure"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)

        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_hook_event_name_correct(self):
        """Hook output should specify PostToolUseFailure event"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)

        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"

    def test_all_outputs_valid_json(self):
        """All hook outputs should be valid JSON"""
        test_cases = [
            ("Bash", HEREDOC_ERROR, False),
            ("Bash", HEREDOC_ERROR, True),
            ("Bash", "command not found", False),
            ("Read", HEREDOC_ERROR, False),
            ("Bash", "", False),
        ]

        for tool_name, error, use_tool_result in test_cases:
            output = run_hook_with_error(tool_name, error, use_tool_result)
            assert isinstance(output, dict), f"Output should be valid JSON dict"

    # Edge cases - case sensitivity and exact matching
    @pytest.mark.parametrize("error_message,description", [
        ("CAN'T CREATE TEMP FILE FOR HERE DOCUMENT", "All caps version should not match"),
        ("can't create TEMP file for HERE document", "Mixed case should not match"),
        ("can't create temp file", "Partial message (first half) should not match"),
        ("here document error", "Partial message (second half) should not match"),
        ("can't create temp file for heredoc", "Typo in error message should not match"),
        ("cannot create temp file for here document", "Synonym ('cannot' vs 'can't') should not match"),
    ])
    def test_heredoc_error_exact_match_required(self, error_message, description):
        """Heredoc error detection requires exact string match"""
        output = run_hook_with_error("Bash", error_message)
        assert output == {}, f"{description}"

    # Edge cases - real-world heredoc error scenarios
    def test_git_commit_heredoc_failure(self):
        """Git commit with heredoc that fails should trigger"""
        git_error = """bash: line 1: /tmp/heredoc12345: can't create temp file for here document: Read-only file system
Exit code: 1"""
        output = run_hook_with_error("Bash", git_error)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_multiline_script_heredoc_failure(self):
        """Multiline script with heredoc failure should trigger"""
        script_error = f"""Error executing command:
bash: line 3: {HEREDOC_ERROR}: Permission denied
Command: cat << EOF > file.txt"""
        output = run_hook_with_error("Bash", script_error)

        assert "hookSpecificOutput" in output

    @pytest.mark.parametrize("error_message,position", [
        (f"{HEREDOC_ERROR}", "start"),
        (f"Command failed: {HEREDOC_ERROR}", "end"),
        (f"Error: {HEREDOC_ERROR} at line 5", "middle"),
    ])
    def test_heredoc_error_position_in_message(self, error_message, position):
        """Heredoc error should trigger when at any position in the message"""
        output = run_hook_with_error("Bash", error_message)
        assert "hookSpecificOutput" in output, f"Heredoc error at {position} of message should trigger"

    # Edge cases - whitespace and special character handling
    @pytest.mark.parametrize("error_message,contains_heredoc_error,description", [
        ("can't  create  temp  file  for  here  document", False, "Extra spaces should not match (exact string match)"),
        (f"bash: line 1:\n{HEREDOC_ERROR}:\nNo such file", True, "Heredoc error split across newlines should trigger"),
        (f"bash: '{HEREDOC_ERROR}': system error", True, "Heredoc error within quotes should trigger"),
        (f"bash: \\t{HEREDOC_ERROR}\\n: error", True, "Heredoc error with escape sequences should trigger"),
    ])
    def test_heredoc_error_with_whitespace_and_special_chars(self, error_message, contains_heredoc_error, description):
        """Heredoc error detection with various whitespace and special character scenarios"""
        output = run_hook_with_error("Bash", error_message)
        if contains_heredoc_error:
            assert "hookSpecificOutput" in output, f"{description}"
        else:
            assert output == {}, f"{description}"

    # Edge cases - exception handling
    def test_malformed_json_input(self):
        """Hook should handle malformed JSON gracefully"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="{ invalid json }",
            capture_output=True,
            text=True
        )

        # Should exit with error code 1 and output {}
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_tool_name_field(self):
        """Hook should handle missing tool_name field gracefully"""
        input_data = {"error": HEREDOC_ERROR}

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        # Should handle gracefully - missing tool_name means not Bash, so return {}
        output = json.loads(result.stdout)
        assert output == {}

    def test_null_error_field(self):
        """Hook should handle null error field"""
        input_data = {
            "tool_name": "Bash",
            "error": None
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert output == {}

    # Integration tests - combined scenarios
    def test_multiple_errors_with_heredoc_error_present(self):
        """Multiple errors including heredoc error should trigger"""
        combined_error = f"""Multiple errors occurred:
1. Command not found: foobar
2. {HEREDOC_ERROR}
3. Permission denied: /etc/shadow"""
        output = run_hook_with_error("Bash", combined_error)
        assert "hookSpecificOutput" in output

    def test_error_after_successful_commands(self):
        """Heredoc error in PostToolUseFailure context should trigger"""
        # Simulates a scenario where previous commands succeeded but current one failed
        output = run_hook_with_error("Bash", HEREDOC_ERROR, use_tool_result=False)
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]



def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
