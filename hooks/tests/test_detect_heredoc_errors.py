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
        assert "HEREDOC ERROR DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_posttoolusefailure_exact_error_message(self):
        """PostToolUseFailure with exact heredoc error string should trigger"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert HEREDOC_ERROR in output["hookSpecificOutput"]["additionalContext"]

    def test_posttoolusefailure_heredoc_error_with_context(self):
        """PostToolUseFailure with heredoc error plus additional context should trigger"""
        error_msg = f"Command failed:\nbash: line 1: {HEREDOC_ERROR}: No such file or directory\nExit code: 1"
        output = run_hook_with_error("Bash", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "HEREDOC ERROR DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    # PostToolUse tests (error in tool_result.error field)
    def test_posttooluse_heredoc_error_detected(self):
        """PostToolUse with heredoc error in tool_result.error should trigger hook"""
        error_msg = f"bash: {HEREDOC_ERROR}: No such file or directory"
        output = run_hook_with_error("Bash", error_msg, use_tool_result=True)

        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "HEREDOC ERROR DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_posttooluse_exact_error_message(self):
        """PostToolUse with exact heredoc error string should trigger"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR, use_tool_result=True)

        assert "hookSpecificOutput" in output
        assert HEREDOC_ERROR in output["hookSpecificOutput"]["additionalContext"]

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
        assert HEREDOC_ERROR in output["hookSpecificOutput"]["additionalContext"]

    # Non-heredoc errors should return empty JSON
    def test_bash_syntax_error_no_heredoc(self):
        """Bash syntax error without heredoc should return {}"""
        output = run_hook_with_error("Bash", "bash: syntax error near unexpected token `)'")
        assert output == {}, "Non-heredoc syntax error should not trigger"

    def test_command_not_found_error(self):
        """Command not found error should return {}"""
        output = run_hook_with_error("Bash", "bash: foobar: command not found")
        assert output == {}, "Command not found error should not trigger"

    def test_permission_denied_error(self):
        """Permission denied error should return {}"""
        output = run_hook_with_error("Bash", "bash: ./script.sh: Permission denied")
        assert output == {}, "Permission denied error should not trigger"

    def test_file_not_found_error(self):
        """File not found error should return {}"""
        output = run_hook_with_error("Bash", "bash: nonexistent.txt: No such file or directory")
        assert output == {}, "File not found error should not trigger"

    def test_eof_error_without_heredoc_keyword(self):
        """EOF error without heredoc keyword should return {}"""
        output = run_hook_with_error("Bash", "bash: unexpected EOF while looking for matching `\"'")
        assert output == {}, "EOF error without heredoc keyword should not trigger"

    def test_generic_bash_error(self):
        """Generic bash error should return {}"""
        output = run_hook_with_error("Bash", "bash: line 42: unexpected error occurred")
        assert output == {}, "Generic bash error should not trigger"

    # Non-Bash tools should return empty JSON
    def test_read_tool_with_heredoc_error(self):
        """Read tool with heredoc error message should return {}"""
        output = run_hook_with_error("Read", HEREDOC_ERROR)
        assert output == {}, "Non-Bash tool should not trigger even with heredoc error"

    def test_write_tool_with_heredoc_error(self):
        """Write tool with heredoc error message should return {}"""
        output = run_hook_with_error("Write", HEREDOC_ERROR)
        assert output == {}, "Write tool should not trigger"

    def test_edit_tool_with_heredoc_error(self):
        """Edit tool with heredoc error message should return {}"""
        output = run_hook_with_error("Edit", HEREDOC_ERROR)
        assert output == {}, "Edit tool should not trigger"

    def test_glob_tool_with_heredoc_error(self):
        """Glob tool with heredoc error message should return {}"""
        output = run_hook_with_error("Glob", HEREDOC_ERROR)
        assert output == {}, "Glob tool should not trigger"

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

    # Guidance content verification
    def test_guidance_includes_git_commit_workaround(self):
        """Guidance should mention git commit -m workaround"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert "git commit" in context, "Should mention git commit"
        assert "-m" in context, "Should mention -m flag"
        assert "multiple -m flags" in context.lower() or "multiple" in context, "Should suggest multiple -m"

    def test_guidance_includes_ansi_c_quoting(self):
        """Guidance should mention ANSI-C quoting workaround"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert "ANSI-C" in context or "$'" in context, "Should mention ANSI-C quoting or $'...'"
        assert "\\n" in context or "\\\\n" in context, "Should show newline escape example"

    def test_guidance_includes_write_tool_workaround(self):
        """Guidance should mention Write tool as alternative"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert "Write" in context, "Should mention Write tool"
        assert "create file" in context.lower() or "file first" in context.lower(), "Should suggest creating file"

    def test_guidance_warns_heredocs_dont_work(self):
        """Guidance should explicitly state heredocs don't work in sandbox"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert "sandbox" in context.lower(), "Should mention sandbox"
        assert "don't work" in context.lower() or "doesn't work" in context.lower(), "Should state heredocs don't work"

    def test_guidance_shows_practical_examples(self):
        """Guidance should include code examples"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should have code blocks or examples
        assert "```" in context, "Should include code blocks"
        # Should show actual example commands
        assert "git commit -m" in context or "command --arg" in context, "Should show example commands"

    def test_error_message_included_in_context(self):
        """The actual error message should be included in additionalContext"""
        custom_error = f"bash: line 5: {HEREDOC_ERROR}: No such file or directory"
        output = run_hook_with_error("Bash", custom_error)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert custom_error in context, "Should include the actual error message"

    # Edge cases - case sensitivity
    def test_heredoc_error_case_sensitive(self):
        """Heredoc error detection should be case-sensitive"""
        # All caps version should not match
        output = run_hook_with_error("Bash", "CAN'T CREATE TEMP FILE FOR HERE DOCUMENT")
        assert output == {}, "Should be case-sensitive - all caps should not match"

        # Mixed case in wrong places should not match
        output = run_hook_with_error("Bash", "can't create TEMP file for HERE document")
        assert output == {}, "Should be case-sensitive - mixed case should not match"

    def test_heredoc_error_partial_match(self):
        """Partial heredoc error string should not trigger"""
        output = run_hook_with_error("Bash", "can't create temp file")
        assert output == {}, "Partial error message should not trigger"

        output = run_hook_with_error("Bash", "here document error")
        assert output == {}, "Partial error message should not trigger"

    def test_heredoc_error_with_typo(self):
        """Heredoc error with typo should not trigger"""
        output = run_hook_with_error("Bash", "can't create temp file for heredoc")
        assert output == {}, "Typo in error message should not trigger"

        output = run_hook_with_error("Bash", "cannot create temp file for here document")
        assert output == {}, "Synonym in error message should not trigger"

    # Edge cases - real-world heredoc error scenarios
    def test_git_commit_heredoc_failure(self):
        """Git commit with heredoc that fails should trigger"""
        git_error = """bash: line 1: /tmp/heredoc12345: can't create temp file for here document: Read-only file system
Exit code: 1"""
        output = run_hook_with_error("Bash", git_error)

        assert "hookSpecificOutput" in output
        assert "git commit" in output["hookSpecificOutput"]["additionalContext"]

    def test_multiline_script_heredoc_failure(self):
        """Multiline script with heredoc failure should trigger"""
        script_error = f"""Error executing command:
bash: line 3: {HEREDOC_ERROR}: Permission denied
Command: cat << EOF > file.txt"""
        output = run_hook_with_error("Bash", script_error)

        assert "hookSpecificOutput" in output

    def test_heredoc_error_at_start_of_message(self):
        """Heredoc error at the start of error message should trigger"""
        output = run_hook_with_error("Bash", f"{HEREDOC_ERROR}")
        assert "hookSpecificOutput" in output

    def test_heredoc_error_at_end_of_message(self):
        """Heredoc error at the end of error message should trigger"""
        output = run_hook_with_error("Bash", f"Command failed: {HEREDOC_ERROR}")
        assert "hookSpecificOutput" in output

    def test_heredoc_error_middle_of_message(self):
        """Heredoc error in middle of error message should trigger"""
        output = run_hook_with_error("Bash", f"Error: {HEREDOC_ERROR} at line 5")
        assert "hookSpecificOutput" in output

    # Edge cases - whitespace variations
    def test_heredoc_error_with_extra_whitespace(self):
        """Heredoc error with extra spaces should still trigger"""
        error_with_spaces = "can't  create  temp  file  for  here  document"
        output = run_hook_with_error("Bash", error_with_spaces)
        assert output == {}, "Error with extra spaces should not match (exact string match required)"

    def test_heredoc_error_with_newlines(self):
        """Heredoc error split across lines should trigger if substring present"""
        error_with_newlines = f"bash: line 1:\n{HEREDOC_ERROR}:\nNo such file"
        output = run_hook_with_error("Bash", error_with_newlines)
        assert "hookSpecificOutput" in output

    # Edge cases - special characters in error
    def test_heredoc_error_with_quotes(self):
        """Heredoc error message containing quotes should trigger"""
        error_with_quotes = f"bash: '{HEREDOC_ERROR}': system error"
        output = run_hook_with_error("Bash", error_with_quotes)
        assert "hookSpecificOutput" in output

    def test_heredoc_error_with_escape_sequences(self):
        """Heredoc error with escape sequences should trigger"""
        error_with_escapes = f"bash: \\t{HEREDOC_ERROR}\\n: error"
        output = run_hook_with_error("Bash", error_with_escapes)
        assert "hookSpecificOutput" in output

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

    def test_workaround_count(self):
        """Guidance should include at least 3 workarounds"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Count numbered workarounds (1., 2., 3.)
        workaround_count = sum(1 for i in range(1, 10) if f"{i}." in context)
        assert workaround_count >= 3, "Should provide at least 3 workarounds"

    def test_guidance_format_readable(self):
        """Guidance should be well-formatted and readable"""
        output = run_hook_with_error("Bash", HEREDOC_ERROR)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should have headers/sections
        assert "**" in context or "##" in context, "Should have formatted headers"
        # Should have code blocks
        assert "```" in context, "Should have code blocks"
        # Should not be too short
        assert len(context) > 200, "Guidance should be substantial"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
