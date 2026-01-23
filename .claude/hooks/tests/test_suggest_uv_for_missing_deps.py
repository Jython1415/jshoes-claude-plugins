"""
Unit tests for suggest-uv-for-missing-deps.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_suggest_uv_for_missing_deps.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "suggest-uv-for-missing-deps.py"


def run_hook_with_error(tool_name: str, command: str, error: str, use_tool_result: bool = False, uv_available: bool = True) -> dict:
    """Helper function to run the hook with error input and return parsed output

    Args:
        tool_name: Name of the tool (e.g., "Bash")
        command: The command that was executed
        error: The error message to include
        use_tool_result: If True, place error in tool_result.error (PostToolUse)
                        If False, place error in top-level error field (PostToolUseFailure)
        uv_available: Whether uv should be treated as available
    """
    if use_tool_result:
        # PostToolUse format - error in tool_result.error
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"command": command},
            "tool_result": {"error": error}
        }
    else:
        # PostToolUseFailure format - error in top-level field
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"command": command},
            "error": error
        }

    # Use environment variable to control uv availability (no PATH hacks!)
    env = os.environ.copy()
    env["HOOK_TEST_UV_AVAILABLE"] = "true" if uv_available else "false"

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
        raise RuntimeError(f"Hook failed: {result.stderr}")

    if not result.stdout:
        raise RuntimeError(f"Hook produced no output. stderr: {result.stderr}")

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


class TestSuggestUvForMissingDeps:
    """Test suite for suggest-uv-for-missing-deps hook"""

    # PostToolUseFailure tests - Error trigger tests
    @pytest.mark.parametrize("error_msg,command,description", [
        ("ModuleNotFoundError: No module named 'pandas'", "python script.py", "ModuleNotFoundError should trigger hook"),
        ("ImportError: cannot import name 'DataFrame' from 'pandas'", "python analyze.py", "ImportError should trigger hook"),
        ("No module named 'requests'", "python fetch_data.py", "'No module named' error should trigger hook"),
    ])
    def test_dependency_error_triggers(self, error_msg, command, description):
        """Dependency errors should trigger hook"""
        output = run_hook_with_error("Bash", command, error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "MISSING DEPENDENCY DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_module_name_extracted_from_error(self):
        """Hook should extract and mention the missing module name"""
        error_msg = "ModuleNotFoundError: No module named 'numpy'"
        output = run_hook_with_error("Bash", "python compute.py", error_msg, use_tool_result=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "numpy" in context

    def test_module_name_with_single_quotes(self):
        """Module name in single quotes should be extracted"""
        error_msg = "No module named 'scipy'"
        output = run_hook_with_error("Bash", "python stats.py", error_msg, use_tool_result=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "scipy" in context

    def test_module_name_with_double_quotes(self):
        """Module name in double quotes should be extracted"""
        error_msg = 'No module named "matplotlib"'
        output = run_hook_with_error("Bash", "python plot.py", error_msg, use_tool_result=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "matplotlib" in context

    # PostToolUse tests (error in tool_result.error field)
    def test_posttooluse_module_not_found_triggers(self):
        """PostToolUse with ModuleNotFoundError should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'requests'"
        output = run_hook_with_error("Bash", "python api.py", error_msg, use_tool_result=True)

        assert "hookSpecificOutput" in output
        assert "MISSING DEPENDENCY DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_both_error_locations_posttoolusefailure_priority(self):
        """When error exists in both locations, top-level error should be used"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"},
            "error": "ModuleNotFoundError: No module named 'pandas'",
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
        assert "pandas" in output["hookSpecificOutput"]["additionalContext"]

    # Script execution detection tests
    @pytest.mark.parametrize("command,description", [
        ("python script.py", "python script.py should trigger"),
        ("python3 script.py", "python3 script.py should trigger"),
        ("python /home/user/analysis/script.py", "python /path/to/script.py should trigger"),
        ("python ./scripts/analyze.py", "python ./scripts/analyze.py should trigger"),
    ])
    def test_python_script_execution_variants_trigger(self, command, description):
        """Python script execution should trigger hook"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", command, error_msg)

        assert "hookSpecificOutput" in output

    # Exclude non-script python commands
    @pytest.mark.parametrize("command,description", [
        ("python -m pytest tests/", "python -m should not trigger (different use case)"),
        ("python -c 'import json'", "python -c should not trigger (not a script file)"),
        ("python --version", "python --version should not trigger"),
        ("python --help", "python --help should not trigger"),
        ("python -i", "python -i should not trigger"),
        ("which python", "which python should not trigger"),
        ("echo '{}' | python -c 'import json; print(json.loads(input()))'", "python -c in a pipeline should not trigger"),
        ("python -S script.py", "python -S script.py should not trigger (intentional limitation)"),
        ("python -u script.py", "python -u script.py should not trigger (intentional limitation)"),
    ])
    def test_non_script_commands_skipped(self, command, description):
        """Non-script execution patterns should not trigger hook"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", command, error_msg)

        assert output == {}

    # Non-dependency errors should not trigger
    @pytest.mark.parametrize("error_msg,tool_name,description", [
        ("SyntaxError: invalid syntax", "Bash", "SyntaxError should not trigger"),
        ("NameError: name 'foo' is not defined", "Bash", "NameError should not trigger"),
        ("ModuleNotFoundError: No module named 'pandas'", "Read", "Non-Bash tools should not trigger"),
    ])
    def test_non_dependency_errors_not_trigger(self, error_msg, tool_name, description):
        """Non-dependency errors and non-Bash tools should not trigger"""
        output = run_hook_with_error(tool_name, "python script.py", error_msg)

        assert output == {}

    # Successful commands should not trigger
    def test_no_error_field(self):
        """Input with no error field should not trigger"""
        output = run_hook_success("Bash", "python script.py")

        assert output == {}

    def test_empty_error_field(self):
        """Empty error field should not trigger"""
        output = run_hook_with_error("Bash", "python script.py", "")

        assert output == {}

    # JSON output format validation
    def test_json_output_structure(self):
        """Hook output should have correct JSON structure"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_hook_event_name_correct(self):
        """Hook output should specify PostToolUseFailure event"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure"

    def test_all_outputs_valid_json(self):
        """All hook outputs should be valid JSON"""
        test_cases = [
            ("Bash", "python script.py", "ModuleNotFoundError: No module named 'pandas'", False),
            ("Bash", "python script.py", "ImportError: No module named 'requests'", True),
            ("Bash", "python script.py", "SyntaxError: invalid syntax", False),
            ("Read", "python script.py", "ModuleNotFoundError: No module named 'numpy'", False),
            ("Bash", "python -m pytest", "ModuleNotFoundError: No module named 'pytest'", False),
        ]

        for tool_name, command, error, use_tool_result in test_cases:
            output = run_hook_with_error(tool_name, command, error, use_tool_result)
            assert isinstance(output, dict), f"Output should be valid JSON dict"

    # Guidance content verification
    def test_guidance_includes_module_name_and_content(self):
        """Guidance should include module name and substantial content"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pandas" in context
        assert len(context) > 100  # Has substantial content

    # Edge cases - complex commands
    @pytest.mark.parametrize("command,description", [
        ("python script.py --input data.csv --output results.json", "python script.py with arguments should trigger"),
        ("PYTHONPATH=/custom/path python script.py", "python with env vars should trigger"),
        ("(cd /tmp && python script.py)", "python in subshell should trigger"),
        ("python script.py > output.txt", "python with output redirection should trigger"),
        ("python process.py | grep 'result'", "python script in pipeline should trigger if it's script execution"),
    ])
    def test_complex_commands_trigger(self, command, description):
        """Complex command variations with python scripts should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", command, error_msg)

        assert "hookSpecificOutput" in output

    # Edge cases - script name variations
    @pytest.mark.parametrize("command,description", [
        ("python data_analysis-v2.py", "Script name with underscores/hyphens/numbers should trigger"),
        ('python "my script.py"', 'python "script.py" with double quotes should trigger'),
        ("python 'analysis.py'", "python 'script.py' with single quotes should trigger"),
        ("/usr/bin/python3 script.py", "/usr/bin/python3 should trigger"),
    ])
    def test_script_name_variations_trigger(self, command, description):
        """Script name variations should trigger hook"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", command, error_msg)

        assert "hookSpecificOutput" in output

    # Edge cases - error message variations
    def test_full_traceback_with_module_not_found(self):
        """Full Python traceback with ModuleNotFoundError should trigger"""
        error_msg = """Traceback (most recent call last):
  File "script.py", line 5, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'"""
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output
        assert "pandas" in output["hookSpecificOutput"]["additionalContext"]

    def test_import_error_with_details(self):
        """ImportError with detailed message should trigger"""
        error_msg = "ImportError: cannot import name 'DataFrame' from 'pandas' (/usr/lib/python3/site-packages/pandas/__init__.py)"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_nested_module_not_found(self):
        """Nested module import error should extract top-level module only"""
        error_msg = "ModuleNotFoundError: No module named 'sklearn.ensemble'"
        output = run_hook_with_error("Bash", "python ml_script.py", error_msg)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should suggest top-level module (pip install sklearn works)
        assert "sklearn" in context
        # Should NOT suggest submodule (pip install sklearn.ensemble doesn't exist)
        assert "sklearn.ensemble" not in context

    def test_import_error_with_from_clause_extracts_module(self):
        """ImportError with 'from pandas' should extract pandas"""
        error_msg = "ImportError: cannot import name 'DataFrame' from 'pandas' (/usr/lib/python3/site-packages/pandas/__init__.py)"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pandas" in context
        # Should show in pip install line
        assert "pip install pandas" in context

    # Edge cases - exception handling
    def test_malformed_json_input(self):
        """Hook should handle malformed JSON gracefully"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="{ invalid json }",
            capture_output=True,
            text=True
        )

        assert result.returncode == 1
        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_tool_name_field(self):
        """Hook should handle missing tool_name field gracefully"""
        input_data = {
            "tool_input": {"command": "python script.py"},
            "error": "ModuleNotFoundError: No module named 'pandas'"
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_command_field(self):
        """Hook should handle missing command field gracefully"""
        input_data = {
            "tool_name": "Bash",
            "error": "ModuleNotFoundError: No module named 'pandas'"
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert output == {}

    def test_null_error_field(self):
        """Hook should handle null error field"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"},
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

    # uv availability tests
    def test_uv_available_suggests_uv_run_with(self):
        """When uv is available, should suggest uv run --with"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=True)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "uv run --with pandas" in context
        assert "Quick fix" in context

    def test_uv_available_suggests_pep723(self):
        """When uv is available, should suggest PEP 723"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=True)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "PEP 723" in context
        assert "# /// script" in context
        assert 'dependencies = ["pandas"]' in context

    def test_uv_not_available_suggests_pip(self):
        """When uv is NOT available, should suggest pip install"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pip install pandas" in context
        assert "uv run" not in context  # Should NOT suggest uv commands

    def test_uv_not_available_recommends_venv(self):
        """When uv is NOT available, should recommend using venv"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "venv" in context

    def test_uv_not_available_mentions_uv_option(self):
        """When uv is NOT available, should mention uv as an option"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=False)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Try uv" in context or "https://docs.astral.sh/uv/" in context


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
