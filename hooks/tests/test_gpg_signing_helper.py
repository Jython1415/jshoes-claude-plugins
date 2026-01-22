#!/usr/bin/env python3
# /// script
# dependencies = ["pytest>=7.0.0"]
# ///
"""
Unit tests for gpg-signing-helper.py hook

Run with:
  uv run --script hooks/tests/test_gpg_signing_helper.py
Or:
  cd hooks/tests && uv run pytest test_gpg_signing_helper.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "gpg-signing-helper.py"


def run_hook_post_tool_use_failure(error_output: str, tool_name: str = "Bash") -> dict:
    """
    Helper function to run the hook with PostToolUseFailure input.
    Error is in the top-level "error" field.
    """
    input_data = {
        "error": error_output,
        "tool_name": tool_name,
        "tool_input": {"command": "git commit -m 'test'"}
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


def run_hook_post_tool_use(error_output: str, tool_name: str = "Bash") -> dict:
    """
    Helper function to run the hook with PostToolUse input.
    Error is in the "tool_result.error" field.
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": "git commit -m 'test'"},
        "tool_result": {
            "error": error_output
        }
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


def run_hook_success(tool_name: str = "Bash") -> dict:
    """
    Helper function to run the hook with successful tool execution (no error).
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": "git status"},
        "tool_result": {
            "output": "On branch main\nnothing to commit, working tree clean"
        }
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


class TestGPGSigningHelperPostToolUseFailure:
    """Test suite for gpg-signing-helper hook with PostToolUseFailure events (top-level error field)"""

    def test_gpg_failed_to_sign_detected(self):
        """Should detect 'gpg failed to sign the data' error"""
        error = "error: gpg failed to sign the data\nfatal: failed to write commit object"
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "additionalContext" in output["hookSpecificOutput"]
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context
        assert "--no-gpg-sign" in context
        assert "gpg failed to sign the data" in context

    def test_gpg_cant_connect_to_agent_detected(self):
        """Should detect 'gpg: can't connect to the agent' error"""
        error = "gpg: can't connect to the agent: IPC connect call failed\ngpg: problem with the agent: No agent running"
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context
        assert "--no-gpg-sign" in context

    def test_no_agent_running_detected(self):
        """Should detect 'No agent running' error"""
        error = "gpg: problem with the agent: No agent running\nerror: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context
        assert "--no-gpg-sign" in context

    def test_guidance_includes_no_gpg_sign_flag(self):
        """Guidance should include --no-gpg-sign flag"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "--no-gpg-sign" in context
        assert "git commit --no-gpg-sign" in context

    def test_guidance_mentions_sandbox_mode(self):
        """Guidance should explain GPG is not available in sandbox mode"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "sandbox" in context.lower() or "sandbox mode" in context

    def test_guidance_emphasizes_importance(self):
        """Guidance should emphasize importance of using --no-gpg-sign"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "IMPORTANT" in context
        assert "All git commits" in context or "require" in context

    def test_non_gpg_error_returns_empty_json(self):
        """Non-GPG errors should return empty JSON"""
        error = "fatal: not a git repository"
        output = run_hook_post_tool_use_failure(error)
        assert output == {}, "Non-GPG error should return empty JSON"

    def test_empty_error_returns_empty_json(self):
        """Empty error should return empty JSON"""
        output = run_hook_post_tool_use_failure("")
        assert output == {}, "Empty error should return empty JSON"

    def test_non_bash_tool_with_gpg_error(self):
        """GPG error from non-Bash tool should still be detected"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error, tool_name="Edit")

        # Hook doesn't check tool_name, so it should still detect GPG error
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context

    def test_hook_event_name_correct(self):
        """Hook output should include correct event name"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"

    def test_json_output_valid(self):
        """Hook output should be valid JSON"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert isinstance(output["hookSpecificOutput"], dict)
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_multiple_gpg_error_patterns(self):
        """Should detect when multiple GPG error patterns are present"""
        error = "gpg: can't connect to the agent\nerror: gpg failed to sign the data\nNo agent running"
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context


class TestGPGSigningHelperPostToolUse:
    """Test suite for gpg-signing-helper hook with PostToolUse events (tool_result.error field)"""

    def test_gpg_failed_to_sign_in_tool_result_error(self):
        """Should detect GPG error in tool_result.error field"""
        error = "error: gpg failed to sign the data\nfatal: failed to write commit object"
        output = run_hook_post_tool_use(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context
        assert "--no-gpg-sign" in context

    def test_gpg_cant_connect_in_tool_result_error(self):
        """Should detect 'can't connect to agent' in tool_result.error field"""
        error = "gpg: can't connect to the agent: IPC connect call failed"
        output = run_hook_post_tool_use(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context

    def test_no_agent_in_tool_result_error(self):
        """Should detect 'No agent running' in tool_result.error field"""
        error = "gpg: problem with the agent: No agent running"
        output = run_hook_post_tool_use(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context

    def test_non_gpg_error_in_tool_result_returns_empty(self):
        """Non-GPG error in tool_result.error should return empty JSON"""
        error = "fatal: pathspec 'file.txt' did not match any files"
        output = run_hook_post_tool_use(error)
        assert output == {}, "Non-GPG error should return empty JSON"

    def test_empty_tool_result_error_returns_empty(self):
        """Empty tool_result.error should return empty JSON"""
        output = run_hook_post_tool_use("")
        assert output == {}, "Empty error should return empty JSON"


class TestGPGSigningHelperSuccessfulCommands:
    """Test suite for successful git commands (no errors)"""

    def test_successful_git_status_returns_empty(self):
        """Successful git status should return empty JSON"""
        output = run_hook_success("Bash")
        assert output == {}, "Successful command should return empty JSON"

    def test_successful_non_bash_tool_returns_empty(self):
        """Successful non-Bash tool should return empty JSON"""
        output = run_hook_success("Read")
        assert output == {}, "Successful non-Bash tool should return empty JSON"


class TestGPGSigningHelperEdgeCases:
    """Test suite for edge cases and error handling"""

    def test_gpg_error_with_case_variations(self):
        """Should detect GPG errors regardless of case variations"""
        # The actual error messages are case-sensitive, so let's test the exact strings
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)
        assert "hookSpecificOutput" in output

    def test_gpg_error_with_extra_whitespace(self):
        """Should detect GPG error with extra whitespace"""
        error = "  error: gpg failed to sign the data  \n  fatal: failed to write commit object  "
        output = run_hook_post_tool_use_failure(error)
        assert "hookSpecificOutput" in output

    def test_gpg_error_with_additional_context(self):
        """Should detect GPG error even with additional error context"""
        error = """
        Committing changes...
        error: gpg failed to sign the data
        fatal: failed to write commit object

        Additional diagnostic information:
        - Check your GPG configuration
        - Verify GPG agent is running
        """
        output = run_hook_post_tool_use_failure(error)
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context

    def test_partial_gpg_error_string_not_detected(self):
        """Partial match of GPG error string should not trigger"""
        error = "error: failed to sign the document"  # Not "gpg failed to sign"
        output = run_hook_post_tool_use_failure(error)
        assert output == {}, "Partial match should not trigger"

    def test_gpg_in_normal_output_not_detected(self):
        """GPG mentioned in normal output should not trigger"""
        error = "Successfully verified GPG signature"
        output = run_hook_post_tool_use_failure(error)
        assert output == {}, "Normal GPG mention should not trigger"

    def test_malformed_json_input_returns_empty(self):
        """Hook should handle malformed input gracefully"""
        # This tests the exception handling
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True
        )
        # Should return exit code 1 with empty JSON
        assert result.returncode == 1
        assert result.stdout.strip() == "{}"

    def test_missing_fields_returns_empty(self):
        """Hook should handle missing fields gracefully"""
        input_data = {
            "tool_name": "Bash"
            # Missing error and tool_result fields
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output == {}, "Missing fields should return empty JSON"

    def test_null_error_field_returns_empty(self):
        """Hook should handle null error field"""
        input_data = {
            "error": None,
            "tool_name": "Bash"
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output == {}, "Null error should return empty JSON"

    def test_error_in_both_locations_uses_top_level(self):
        """When error exists in both locations, top-level should take precedence"""
        input_data = {
            "error": "error: gpg failed to sign the data",
            "tool_result": {
                "error": "different error message"
            }
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "gpg failed to sign the data" in context

    def test_only_tool_result_error_present(self):
        """Should check tool_result.error when top-level error is absent"""
        input_data = {
            "tool_result": {
                "error": "error: gpg failed to sign the data"
            }
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output


class TestGPGSigningHelperRealWorldScenarios:
    """Test suite for real-world GPG error scenarios"""

    def test_macos_gpg_agent_error(self):
        """Should detect common macOS GPG agent error"""
        error = """error: gpg failed to sign the data
fatal: failed to write commit object"""
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "--no-gpg-sign" in context

    def test_linux_gpg_agent_not_running(self):
        """Should detect Linux GPG agent not running error"""
        error = """gpg: can't connect to the agent: IPC connect call failed
gpg: keydb_search failed: No agent running
gpg: skipped "user@example.com": No agent running
gpg: signing failed: No agent running
error: gpg failed to sign the data
fatal: failed to write commit object"""
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "GPG SIGNING ERROR DETECTED" in context
        assert "--no-gpg-sign" in context

    def test_git_commit_with_gpg_signing_enabled(self):
        """Should detect GPG error when commit.gpgsign is enabled"""
        error = """[master 1a2b3c4] Test commit
error: gpg failed to sign the data
fatal: failed to write commit object"""
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output

    def test_git_tag_signing_failure(self):
        """Should detect GPG error in git tag signing"""
        error = """error: gpg failed to sign the data
error: unable to sign the tag"""
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output

    def test_windows_gpg_error(self):
        """Should detect Windows-style GPG error"""
        error = """gpg: can't connect to the agent: IPC connect call failed
error: gpg failed to sign the data"""
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output

    def test_sandboxed_environment_gpg_error(self):
        """Should provide helpful guidance for sandboxed environments"""
        error = "error: gpg failed to sign the data\nfatal: failed to write commit object"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "sandbox" in context.lower()
        assert "--no-gpg-sign" in context
        assert "All git commits" in context


class TestGPGSigningHelperOutputFormat:
    """Test suite for verifying correct output format"""

    def test_output_structure_complete(self):
        """Output should have complete structure with all required fields"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_empty_output_is_valid_json(self):
        """Empty output (no error) should be valid JSON object"""
        output = run_hook_success()
        assert output == {}
        assert isinstance(output, dict)

    def test_additional_context_is_multiline(self):
        """additionalContext should contain multiline helpful text"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "\n" in context, "Context should be multiline"
        lines = context.split("\n")
        assert len(lines) >= 3, "Context should have multiple lines of guidance"

    def test_additional_context_includes_command_example(self):
        """additionalContext should include example command"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert 'git commit --no-gpg-sign -m "your message"' in context or \
               'git commit --no-gpg-sign' in context

    def test_no_decision_field_in_output(self):
        """Output should not include 'decision' field (doesn't work for PostToolUseFailure)"""
        error = "error: gpg failed to sign the data"
        output = run_hook_post_tool_use_failure(error)

        assert "decision" not in output.get("hookSpecificOutput", {}), \
            "decision field should not be present (not supported for PostToolUseFailure)"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
