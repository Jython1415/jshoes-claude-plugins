"""
Unit tests for normalize-line-endings.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_normalize_line_endings.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "normalize-line-endings.py"


def run_hook(tool_name: str, content: str, **extra_tool_input) -> dict:
    """Helper function to run the hook with given input and return parsed output"""
    tool_input = {"content": content}
    tool_input.update(extra_tool_input)

    input_data = {
        "tool_name": tool_name,
        "tool_input": tool_input
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


class TestNormalizeLineEndings:
    """Test suite for normalize-line-endings hook"""

    # CRLF normalization tests
    @pytest.mark.parametrize(
        "tool_name,content,extra_params,expected_output",
        [
            ("Write", "hello\r\nworld", {}, "hello\nworld"),
            ("Write", "line1\r\nline2\r\nline3\r\nline4", {}, "line1\nline2\nline3\nline4"),
            ("Write", "content\r\n", {}, "content\n"),
            ("Write", "test\r\ncontent", {"file_path": "/tmp/test.txt"}, "test\ncontent"),
            ("Edit", "new\r\nstring", {"old_string": "old", "file_path": "/tmp/test.txt"}, "new\nstring"),
        ],
        ids=[
            "crlf_single_line",
            "crlf_multiple_lines",
            "crlf_at_end_of_file",
            "crlf_in_write_operation",
            "crlf_in_edit_operation",
        ],
    )
    def test_crlf_normalization(self, tool_name, content, extra_params, expected_output):
        """CRLF content should be normalized to LF"""
        output = run_hook(tool_name, content, **extra_params)
        assert "hookSpecificOutput" in output, "Should return hook output"
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert updated == expected_output, "CRLF should be converted to LF"
        assert "\r" not in updated, "No CR characters should remain"

    # CR-only normalization tests
    @pytest.mark.parametrize(
        "content,expected_output",
        [
            ("hello\rworld", "hello\nworld"),
            ("line1\rline2\rline3", "line1\nline2\nline3"),
        ],
        ids=[
            "cr_only_single_line",
            "cr_only_multiple_lines",
        ],
    )
    def test_cr_only_normalization(self, content, expected_output):
        """Content with CR (no LF) should be normalized to LF"""
        output = run_hook("Write", content)
        assert "hookSpecificOutput" in output
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert updated == expected_output, "CR should be converted to LF"
        assert "\r" not in updated, "No CR characters should remain"

    # Mixed line endings tests
    def test_mixed_crlf_and_cr_normalized(self):
        """Content with both CRLF and CR should be normalized"""
        content = "line1\r\nline2\rline3\r\nline4"
        output = run_hook("Write", content)
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert updated == "line1\nline2\nline3\nline4", "All line endings should be LF"
        assert "\r" not in updated, "No CR characters should remain"

    def test_mixed_crlf_lf_and_cr_normalized(self):
        """Content with CRLF, LF, and CR should normalize only CRLF/CR"""
        content = "line1\r\nline2\nline3\rline4"
        output = run_hook("Write", content)
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert updated == "line1\nline2\nline3\nline4", "All line endings should be LF"
        assert "\r" not in updated, "No CR characters should remain"

    # Already-normalized content tests
    @pytest.mark.parametrize(
        "content",
        [
            "line1\nline2\nline3",
            "single line content",
            "line1\n\n\nline2",
        ],
        ids=[
            "lf_only_no_normalization",
            "no_line_endings_no_normalization",
            "multiple_lf_no_normalization",
        ],
    )
    def test_already_normalized_content(self, content):
        """Already-normalized content should return empty JSON (no action needed)"""
        output = run_hook("Write", content)
        assert output == {}, "Already-normalized content should not trigger normalization"

    # Empty and edge case content tests
    @pytest.mark.parametrize(
        "content,should_normalize,expected_output",
        [
            ("", False, None),
            ("   \n   \n   ", False, None),
            ("   \r\n   ", True, "   \n   "),
            ("\r", True, "\n"),
            ("\r\n", True, "\n"),
        ],
        ids=[
            "empty_content",
            "whitespace_only_with_lf",
            "whitespace_only_with_crlf",
            "single_cr_character",
            "single_crlf_sequence",
        ],
    )
    def test_edge_case_content(self, content, should_normalize, expected_output):
        """Edge case content should be handled appropriately"""
        output = run_hook("Write", content)
        if should_normalize:
            assert "hookSpecificOutput" in output, "Should normalize this content"
            updated = output["hookSpecificOutput"]["updatedInput"]["content"]
            assert updated == expected_output, f"Content should be normalized to {repr(expected_output)}"
        else:
            assert output == {}, "Should not trigger normalization for this content"

    # Binary-looking content tests
    def test_binary_with_cr_still_normalized(self):
        """Binary-looking content with CR should still be normalized (hook doesn't detect binary)"""
        # Current hook implementation doesn't check for binary content
        content = "binary\x00data\rwith\r\nline\rendings"
        output = run_hook("Write", content)
        assert "hookSpecificOutput" in output, "Hook normalizes all content with CR"
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert "\r" not in updated, "CRs should be normalized even in binary-looking content"

    # Permission and approval behavior tests
    def test_auto_approval_on_normalization(self):
        """Normalization should auto-approve with 'allow' decision"""
        output = run_hook("Write", "test\r\ncontent")
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_permission_decision_reason_present(self):
        """Normalized output should include decision reason"""
        output = run_hook("Write", "test\r\ncontent")
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert reason == "Normalized line endings"

    # JSON output format tests
    def test_json_output_valid_for_normalization(self):
        """Hook output for normalization should be valid JSON with correct structure"""
        output = run_hook("Write", "test\r\ncontent")
        assert isinstance(output, dict), "Output should be valid JSON dict"
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "permissionDecision" in output["hookSpecificOutput"]
        assert "permissionDecisionReason" in output["hookSpecificOutput"]
        assert "updatedInput" in output["hookSpecificOutput"]
        assert "content" in output["hookSpecificOutput"]["updatedInput"]

    def test_json_output_valid_for_no_action(self):
        """Hook output for no action should be valid empty JSON"""
        output = run_hook("Write", "test\ncontent")
        assert output == {}, "Should return empty dict"
        assert isinstance(output, dict), "Should be a dict, not other falsy value"

    def test_hook_event_name_correct(self):
        """Hook output should include correct event name"""
        output = run_hook("Write", "test\r\ncontent")
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_multiple_normalizations_all_valid_json(self):
        """All normalization scenarios should produce valid JSON"""
        test_cases = [
            "crlf\r\ntest",
            "cr\rtest",
            "lf\ntest",
            "mixed\r\ntest\rmore",
            "",
            "no line endings"
        ]
        for content in test_cases:
            output = run_hook("Write", content)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {repr(content)}"

    # Updated input preservation tests
    def test_updated_input_only_changes_content(self):
        """Hook should only update content field, not other tool_input fields"""
        output = run_hook("Write", "test\r\n", file_path="/tmp/test.txt")
        updated_input = output["hookSpecificOutput"]["updatedInput"]
        # Should only contain 'content', not file_path or other fields
        assert "content" in updated_input
        assert len(updated_input) == 1, "Should only update content field"

    # Real-world content tests
    @pytest.mark.parametrize(
        "content,expected_output",
        [
            (
                "def hello():\r\n    print('world')\r\n    return True\r\n",
                "def hello():\n    print('world')\n    return True\n",
            ),
            (
                '{\r\n  "key": "value",\r\n  "number": 42\r\n}',
                '{\n  "key": "value",\n  "number": 42\n}',
            ),
            (
                "# Title\r\n\r\nParagraph text.\r\n\r\n- List item\r\n",
                "# Title\n\nParagraph text.\n\n- List item\n",
            ),
            (
                "#!/bin/bash\r\necho 'test'\rcd /tmp\nls -la\r\n",
                "#!/bin/bash\necho 'test'\ncd /tmp\nls -la\n",
            ),
        ],
        ids=[
            "python_code_with_crlf",
            "json_content_with_crlf",
            "markdown_with_crlf",
            "shell_script_with_mixed_endings",
        ],
    )
    def test_real_world_content(self, content, expected_output):
        """Real-world content with line ending issues should be normalized"""
        output = run_hook("Write", content)
        updated = output["hookSpecificOutput"]["updatedInput"]["content"]
        assert updated == expected_output, f"Content should be normalized correctly"

    # Error handling tests
    def test_malformed_input_returns_empty_json(self):
        """Malformed input should be handled gracefully with empty JSON"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True
        )
        # Should return {} on error
        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_content_field_returns_empty_json(self):
        """Missing content field should be handled gracefully"""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/test.txt"}  # no content field
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        # Should handle missing content gracefully
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output == {}, "Missing content should be treated as empty string (no CR)"

    def test_null_content_returns_empty_json(self):
        """Null content should be handled gracefully"""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"content": None}
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        # Should handle null content gracefully (returns {} with error exit code)
        assert result.returncode == 1, "Null content causes exception, handled with exit 1"
        output = json.loads(result.stdout)
        assert output == {}, "Should return empty dict on error"


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
