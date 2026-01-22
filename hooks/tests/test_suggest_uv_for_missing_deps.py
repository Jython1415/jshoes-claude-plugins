"""
Unit tests for suggest-uv-for-missing-deps.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_suggest_uv_for_missing_deps.py  # Run this test file
  uv run pytest -v                           # Verbose output
"""
import json
import subprocess
import sys
from pathlib import Path

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "suggest-uv-for-missing-deps.py"


def run_hook_with_error(tool_name: str, command: str, error: str, use_tool_result: bool = False) -> dict:
    """Helper function to run the hook with error input and return parsed output

    Args:
        tool_name: Name of the tool (e.g., "Bash")
        command: The command that was executed
        error: The error message to include
        use_tool_result: If True, place error in tool_result.error (PostToolUse)
                        If False, place error in top-level error field (PostToolUseFailure)
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


class TestSuggestUvForMissingDeps:
    """Test suite for suggest-uv-for-missing-deps hook"""

    # PostToolUseFailure tests - ModuleNotFoundError
    def test_module_not_found_error_triggers(self):
        """ModuleNotFoundError should trigger hook"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "MISSING DEPENDENCY DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_import_error_triggers(self):
        """ImportError should trigger hook"""
        error_msg = "ImportError: cannot import name 'DataFrame' from 'pandas'"
        output = run_hook_with_error("Bash", "python analyze.py", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
        assert "MISSING DEPENDENCY DETECTED" in output["hookSpecificOutput"]["additionalContext"]

    def test_no_module_named_triggers(self):
        """'No module named' error should trigger hook"""
        error_msg = "No module named 'requests'"
        output = run_hook_with_error("Bash", "python fetch_data.py", error_msg, use_tool_result=False)

        assert "hookSpecificOutput" in output
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
    def test_python_script_execution_triggers(self):
        """python script.py should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_python3_script_execution_triggers(self):
        """python3 script.py should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python3 script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_script_with_absolute_path_triggers(self):
        """python /path/to/script.py should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python /home/user/analysis/script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_script_with_relative_path_triggers(self):
        """python ./scripts/analyze.py should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python ./scripts/analyze.py", error_msg)

        assert "hookSpecificOutput" in output

    # Exclude non-script python commands
    def test_python_module_execution_skipped(self):
        """python -m should not trigger (different use case)"""
        error_msg = "ModuleNotFoundError: No module named 'pytest'"
        output = run_hook_with_error("Bash", "python -m pytest tests/", error_msg)

        assert output == {}

    def test_python_one_liner_skipped(self):
        """python -c should not trigger (not a script file)"""
        error_msg = "ModuleNotFoundError: No module named 'json'"
        output = run_hook_with_error("Bash", "python -c 'import json'", error_msg)

        assert output == {}

    def test_python_version_check_skipped(self):
        """python --version should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'sys'"
        output = run_hook_with_error("Bash", "python --version", error_msg)

        assert output == {}

    def test_python_help_skipped(self):
        """python --help should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'argparse'"
        output = run_hook_with_error("Bash", "python --help", error_msg)

        assert output == {}

    def test_python_interactive_skipped(self):
        """python -i should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'readline'"
        output = run_hook_with_error("Bash", "python -i", error_msg)

        assert output == {}

    def test_which_python_skipped(self):
        """which python should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'os'"
        output = run_hook_with_error("Bash", "which python", error_msg)

        assert output == {}

    def test_python_in_pipeline_skipped_if_not_script(self):
        """python -c in a pipeline should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'json'"
        output = run_hook_with_error("Bash", "echo '{}' | python -c 'import json; print(json.loads(input()))'", error_msg)

        assert output == {}

    def test_python_with_flags_before_script_skipped(self):
        """python -S script.py should not trigger (intentional limitation)"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python -S script.py", error_msg)

        # This is intentional - flags before script name prevent triggering
        # to avoid complexity in pattern matching
        assert output == {}

    def test_python_with_u_flag_before_script_skipped(self):
        """python -u script.py should not trigger (intentional limitation)"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python -u script.py", error_msg)

        assert output == {}

    # Non-dependency errors should not trigger
    def test_syntax_error_no_trigger(self):
        """SyntaxError should not trigger"""
        error_msg = "SyntaxError: invalid syntax"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_name_error_no_trigger(self):
        """NameError should not trigger"""
        error_msg = "NameError: name 'foo' is not defined"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_attribute_error_no_trigger(self):
        """AttributeError should not trigger"""
        error_msg = "AttributeError: 'NoneType' object has no attribute 'foo'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_type_error_no_trigger(self):
        """TypeError should not trigger"""
        error_msg = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_value_error_no_trigger(self):
        """ValueError should not trigger"""
        error_msg = "ValueError: invalid literal for int() with base 10: 'abc'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_file_not_found_error_no_trigger(self):
        """FileNotFoundError should not trigger"""
        error_msg = "FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_keyboard_interrupt_no_trigger(self):
        """KeyboardInterrupt should not trigger"""
        error_msg = "KeyboardInterrupt"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    def test_generic_exception_no_trigger(self):
        """Generic Exception should not trigger"""
        error_msg = "Exception: Something went wrong"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert output == {}

    # Non-Bash tools should not trigger
    def test_read_tool_with_import_error(self):
        """Read tool with import error should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Read", "python script.py", error_msg)

        assert output == {}

    def test_write_tool_with_import_error(self):
        """Write tool with import error should not trigger"""
        error_msg = "ImportError: No module named 'requests'"
        output = run_hook_with_error("Write", "python script.py", error_msg)

        assert output == {}

    def test_edit_tool_with_import_error(self):
        """Edit tool with import error should not trigger"""
        error_msg = "ModuleNotFoundError: No module named 'numpy'"
        output = run_hook_with_error("Edit", "python script.py", error_msg)

        assert output == {}

    # Successful commands should not trigger
    def test_successful_python_execution(self):
        """Successful python execution should not trigger"""
        output = run_hook_success("Bash", "python script.py")

        assert output == {}

    def test_successful_python_with_output(self):
        """Successful python with output should not trigger"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "python script.py"},
            "tool_result": {"stdout": "Script completed successfully"}
        }

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        output = json.loads(result.stdout)
        assert output == {}

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
    def test_guidance_mentions_pep723(self):
        """Guidance should mention PEP 723"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "PEP 723" in context or "# /// script" in context

    def test_guidance_shows_dependencies_syntax(self):
        """Guidance should show dependencies syntax"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "dependencies" in context
        assert "# ///" in context

    def test_guidance_suggests_uv_run(self):
        """Guidance should suggest uv run --script"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "uv run" in context
        assert "--script" in context

    def test_guidance_includes_code_examples(self):
        """Guidance should include code examples"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "```" in context

    def test_guidance_explains_benefits(self):
        """Guidance should explain benefits of uv run"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Benefits:" in context or "benefit" in context.lower()

    def test_guidance_mentions_sandbox(self):
        """Guidance should mention sandbox mode"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "sandbox" in context.lower()

    def test_guidance_provides_alternative(self):
        """Guidance should provide alternative (pip install)"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Alternative" in context or "pip install" in context

    def test_guidance_includes_missing_module_in_pip_install(self):
        """Guidance should suggest pip install with the specific module"""
        error_msg = "ModuleNotFoundError: No module named 'beautifulsoup4'"
        output = run_hook_with_error("Bash", "python scrape.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pip install" in context
        assert "beautifulsoup4" in context

    def test_guidance_readable_format(self):
        """Guidance should be well-formatted and readable"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        # Should have headers
        assert "**" in context
        # Should have code blocks
        assert "```" in context
        # Should be substantial
        assert len(context) > 200

    # Edge cases - complex commands
    def test_python_with_arguments(self):
        """python script.py with arguments should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py --input data.csv --output results.json", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_with_environment_variables(self):
        """python with env vars should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "PYTHONPATH=/custom/path python script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_in_subshell(self):
        """python in subshell should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "(cd /tmp && python script.py)", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_with_redirection(self):
        """python with output redirection should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script.py > output.txt", error_msg)

        assert "hookSpecificOutput" in output

    def test_python_with_pipe(self):
        """python script in pipeline should trigger if it's script execution"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python process.py | grep 'result'", error_msg)

        assert "hookSpecificOutput" in output

    # Edge cases - script name variations
    def test_script_with_underscores(self):
        """Script name with underscores should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python data_analysis_script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_hyphens(self):
        """Script name with hyphens should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python fetch-and-process.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_numbers(self):
        """Script name with numbers should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python script123.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_dots(self):
        """Script name with dots should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python my.analysis.script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_double_quotes(self):
        """python "script.py" with double quotes should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", 'python "my script.py"', error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_single_quotes(self):
        """python 'script.py' with single quotes should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "python 'analysis.py'", error_msg)

        assert "hookSpecificOutput" in output

    def test_script_with_spaces_in_path(self):
        """Quoted path with spaces should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", 'python "~/Documents/My Scripts/test.py"', error_msg)

        assert "hookSpecificOutput" in output

    def test_absolute_python_path(self):
        """/usr/bin/python3 should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "/usr/bin/python3 script.py", error_msg)

        assert "hookSpecificOutput" in output

    def test_env_python(self):
        """/usr/bin/env python should trigger"""
        error_msg = "ModuleNotFoundError: No module named 'pandas'"
        output = run_hook_with_error("Bash", "/usr/bin/env python script.py", error_msg)

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
        """Nested module import error should trigger and extract name"""
        error_msg = "ModuleNotFoundError: No module named 'sklearn.ensemble'"
        output = run_hook_with_error("Bash", "python ml_script.py", error_msg)

        assert "hookSpecificOutput" in output
        assert "sklearn.ensemble" in output["hookSpecificOutput"]["additionalContext"]

    def test_import_error_with_from_clause_extracts_module(self):
        """ImportError with 'from pandas' should extract pandas"""
        error_msg = "ImportError: cannot import name 'DataFrame' from 'pandas' (/usr/lib/python3/site-packages/pandas/__init__.py)"
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pandas" in context
        # Should show in pip install line
        assert "pip install pandas" in context

    def test_import_error_with_from_clause_single_quotes(self):
        """ImportError with from 'module' format should extract module"""
        error_msg = "ImportError: cannot import name 'something' from 'requests'"
        output = run_hook_with_error("Bash", "python api.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "requests" in context

    def test_import_error_with_from_clause_double_quotes(self):
        """ImportError with from \"module\" format should extract module"""
        error_msg = 'ImportError: cannot import name "something" from "numpy"'
        output = run_hook_with_error("Bash", "python compute.py", error_msg)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "numpy" in context

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

    # Real-world scenarios
    def test_pandas_import_error(self):
        """Real-world pandas import error"""
        error_msg = """Traceback (most recent call last):
  File "/home/user/analysis.py", line 3, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
"""
        output = run_hook_with_error("Bash", "python analysis.py", error_msg)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "pandas" in context
        assert "uv run" in context
        assert "PEP 723" in context or "# /// script" in context

    def test_requests_import_error(self):
        """Real-world requests import error"""
        error_msg = "ModuleNotFoundError: No module named 'requests'"
        output = run_hook_with_error("Bash", "python fetch_api_data.py", error_msg)

        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "requests" in context

    def test_multiple_imports_first_fails(self):
        """When script has multiple imports and first one fails"""
        error_msg = """Traceback (most recent call last):
  File "script.py", line 1, in <module>
    import numpy as np
ModuleNotFoundError: No module named 'numpy'
"""
        output = run_hook_with_error("Bash", "python script.py", error_msg)

        assert "hookSpecificOutput" in output
        assert "numpy" in output["hookSpecificOutput"]["additionalContext"]


def main():
    """Run tests when executed as a script"""
    import pytest

    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
