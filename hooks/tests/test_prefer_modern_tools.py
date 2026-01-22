"""
Unit tests for prefer-modern-tools.py hook

Run with:
  uv run pytest                              # Run all tests
  uv run pytest hooks/tests/test_prefer_modern_tools.py  # Run this test file
  uv run pytest -v                           # Verbose output

This test suite uses mocking to test tool availability scenarios regardless of
what tools are actually installed on the system. All tests should pass on any
system configuration.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "prefer-modern-tools.py"


def run_hook(tool_name: str, command: str, fd_available: bool = True, rg_available: bool = True) -> dict:
    """
    Helper function to run the hook with mocked tool availability.

    Args:
        tool_name: The tool name (e.g., "Bash")
        command: The command string
        fd_available: Whether to mock fd as available
        rg_available: Whether to mock rg as available

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    # Create a temporary directory for mock tools and a mock 'which' command
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock 'which' command that only succeeds for available tools
        which_path = Path(tmpdir) / "which"
        which_script = "#!/bin/sh\n"
        which_script += "# Mock which script that controls fd and rg availability\n"
        which_script += "case \"$1\" in\n"

        # Handle fd
        if fd_available:
            which_script += f"  fd) echo '{tmpdir}/fd'; exit 0 ;;\n"
        else:
            which_script += "  fd) exit 1 ;;\n"

        # Handle rg
        if rg_available:
            which_script += f"  rg) echo '{tmpdir}/rg'; exit 0 ;;\n"
        else:
            which_script += "  rg) exit 1 ;;\n"

        # For other commands, use the real which (avoid calling ourselves)
        which_script += "  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\n"
        which_script += "esac\n"
        which_path.write_text(which_script)
        which_path.chmod(0o755)

        # Create mock fd if available
        if fd_available:
            fd_path = Path(tmpdir) / "fd"
            fd_path.write_text("#!/bin/sh\necho 'mock fd'\nexit 0\n")
            fd_path.chmod(0o755)

        # Create mock rg if available
        if rg_available:
            rg_path = Path(tmpdir) / "rg"
            rg_path.write_text("#!/bin/sh\necho 'mock rg'\nexit 0\n")
            rg_path.chmod(0o755)

        # Modify PATH to include our mock directory at the beginning
        # This ensures our mock 'which' is found first
        env = os.environ.copy()
        env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
            raise RuntimeError(f"Hook failed: {result.stderr}")

        return json.loads(result.stdout)


class TestPreferModernTools:
    """Test suite for prefer-modern-tools hook"""

    # ========== Basic find detection tests ==========

    def test_find_basic_usage(self):
        """Basic find command should trigger fd suggestion when fd is available"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]
        assert "find" in output["hookSpecificOutput"]["additionalContext"].lower()

    def test_find_basic_usage_fd_unavailable(self):
        """Basic find command should NOT trigger when fd is unavailable"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=False)
        assert output == {}, "Should return {} when fd not available"

    def test_find_at_command_start(self):
        """find at the start of command should trigger suggestion when fd is available"""
        output = run_hook("Bash", "find /path/to/dir -type f", fd_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_find_at_command_start_fd_unavailable(self):
        """find at the start of command should NOT trigger when fd is unavailable"""
        output = run_hook("Bash", "find /path/to/dir -type f", fd_available=False)
        assert output == {}, "Should return {} when fd not available"

    def test_find_with_pipe(self):
        """find command piped to other commands should trigger when fd is available"""
        output = run_hook("Bash", 'find . -name "*.txt" | xargs cat', fd_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_find_with_pipe_fd_unavailable(self):
        """find command piped to other commands should NOT trigger when fd is unavailable"""
        output = run_hook("Bash", 'find . -name "*.txt" | xargs cat', fd_available=False)
        assert output == {}, "Should return {} when fd not available"

    def test_find_complex_pattern(self):
        """Complex find command with multiple options should trigger when fd is available"""
        output = run_hook("Bash", "find /var/log -type f -name '*.log' -mtime +7 -delete", fd_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_find_with_exec(self):
        """find with -exec should trigger suggestion when fd is available"""
        output = run_hook("Bash", "find . -name '*.pyc' -exec rm {} \\;", fd_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    # ========== Basic grep detection tests ==========

    def test_grep_basic_usage(self):
        """Basic grep command should trigger rg suggestion when rg is available"""
        output = run_hook("Bash", 'grep -r "pattern" .', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]
        assert "grep" in output["hookSpecificOutput"]["additionalContext"].lower()

    def test_grep_basic_usage_rg_unavailable(self):
        """Basic grep command should NOT trigger when rg is unavailable"""
        output = run_hook("Bash", 'grep -r "pattern" .', rg_available=False)
        assert output == {}, "Should return {} when rg not available"

    def test_grep_at_command_start(self):
        """grep at the start of command should trigger suggestion when rg is available"""
        output = run_hook("Bash", 'grep "error" /var/log/syslog', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_at_command_start_rg_unavailable(self):
        """grep at the start of command should NOT trigger when rg is unavailable"""
        output = run_hook("Bash", 'grep "error" /var/log/syslog', rg_available=False)
        assert output == {}, "Should return {} when rg not available"

    def test_grep_with_options(self):
        """grep with various options should trigger when rg is available"""
        output = run_hook("Bash", 'grep -rn "TODO" src/', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_piped_input(self):
        """grep receiving piped input should trigger when rg is available"""
        output = run_hook("Bash", 'cat file.txt | grep "pattern"', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_case_insensitive(self):
        """grep -i should trigger suggestion when rg is available"""
        output = run_hook("Bash", 'grep -i "error" logs/*.log', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    # ========== Commands that should NOT trigger ==========

    def test_no_find_or_grep(self):
        """Commands without find or grep should return {}"""
        output = run_hook("Bash", "ls -la /tmp")
        assert output == {}, "Commands without find/grep should not trigger"

    def test_git_command(self):
        """git commands should return {}"""
        output = run_hook("Bash", "git status")
        assert output == {}, "git commands should not trigger"

    def test_npm_command(self):
        """npm commands should return {}"""
        output = run_hook("Bash", "npm install")
        assert output == {}, "npm commands should not trigger"

    def test_already_using_rg(self):
        """Commands already using rg should not suggest rg again"""
        output = run_hook("Bash", 'rg "pattern" .', rg_available=True)
        assert output == {}, "Commands using rg should not trigger grep suggestion"

    def test_already_using_fd(self):
        """Commands already using fd should not trigger"""
        output = run_hook("Bash", 'fd "*.py"', fd_available=True)
        assert output == {}, "Commands using fd should not trigger"

    def test_non_bash_tool(self):
        """Non-Bash tools should return {}"""
        output = run_hook("Read", 'find . -name "*.py"')
        assert output == {}, "Non-Bash tools should not trigger"

    def test_non_bash_tool_read(self):
        """Read tool should not trigger even with grep-like content"""
        output = run_hook("Read", "/path/to/grep-file.txt")
        assert output == {}, "Read tool should not trigger"

    def test_non_bash_tool_edit(self):
        """Edit tool should not trigger"""
        output = run_hook("Edit", 'grep "pattern"')
        assert output == {}, "Edit tool should not trigger"

    def test_empty_command(self):
        """Empty command should return {}"""
        output = run_hook("Bash", "")
        assert output == {}, "Empty command should not trigger"

    # ========== Edge cases - find/grep in strings should NOT trigger ==========

    def test_find_in_double_quoted_string(self):
        """
        LIMITATION: find inside double-quoted string WILL trigger if it has spaces around it.
        Hook uses simple substring matching and doesn't parse shell quotes.
        """
        output = run_hook("Bash", 'echo "use find to search"', fd_available=True)
        # The pattern ' find ' (with spaces) matches "use find to", so it triggers
        assert "hookSpecificOutput" in output, "Hook triggers even with find in quotes (limitation)"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_find_in_single_quoted_string(self):
        """find inside single-quoted string should not trigger"""
        output = run_hook("Bash", "echo 'find . -name test'", fd_available=True)
        assert output == {}, "find in string literal should not trigger"

    def test_grep_in_double_quoted_string(self):
        """grep inside double-quoted string should not trigger"""
        output = run_hook("Bash", 'echo "grep searches for patterns"', rg_available=True)
        assert output == {}, "grep in string literal should not trigger"

    def test_grep_in_single_quoted_string(self):
        """grep inside single-quoted string should not trigger (when no spaces around it)"""
        output = run_hook("Bash", "echo 'grep'", rg_available=True)
        assert output == {}, "grep without surrounding spaces should not trigger"

    def test_git_commit_with_find(self):
        """find in git commit message should not trigger"""
        output = run_hook("Bash", 'git commit -m "find and fix bug"', fd_available=True)
        assert output == {}, "find in commit message should not trigger"

    def test_git_commit_with_grep(self):
        """grep in git commit message should not trigger"""
        output = run_hook("Bash", 'git commit -m "grep through logs"', rg_available=True)
        assert output == {}, "grep in commit message should not trigger"

    # ========== Edge cases - find/grep as part of words should NOT trigger ==========

    def test_find_as_part_of_word(self):
        """find as part of a larger word should not trigger"""
        test_cases = [
            "pathfinder /tmp",
            "finder app.py",
            "findings.txt",
            "refind-boot",
            "unfind something"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, fd_available=True)
            assert output == {}, f"'{cmd}' should not trigger (find is part of word)"

    def test_grep_as_part_of_word(self):
        """grep as part of a larger word should not trigger"""
        test_cases = [
            "postgres database",
            "egrep-tool",
            "grepcode.com",
            "mgrep utility",
            "agrep fuzzy"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, rg_available=True)
            assert output == {}, f"'{cmd}' should not trigger (grep is part of word)"

    # ========== Edge cases - find/grep in filenames should NOT trigger ==========

    def test_find_in_filename(self):
        """find in filename should not trigger"""
        test_cases = [
            "cat find.txt",
            "./find-script.sh",
            "python3 my-find-tool.py",
            "ls -la findings",
            "rm -f old_find.log"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, fd_available=True)
            assert output == {}, f"'{cmd}' should not trigger (find in filename)"

    def test_grep_in_filename(self):
        """grep in filename should not trigger"""
        test_cases = [
            "cat grep.txt",
            "./grep-helper.sh",
            "python3 advanced-grep.py",
            "ls -la grep_results",
            "rm -f grep_output.log"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, rg_available=True)
            assert output == {}, f"'{cmd}' should not trigger (grep in filename)"

    def test_hook_limitation_quotes_not_parsed(self):
        """
        LIMITATION: Hook doesn't parse shell quotes, so ' grep ' pattern in quoted
        strings will still trigger suggestion. This is a known limitation of simple
        substring matching.
        """
        # This WILL trigger because hook uses simple substring matching
        output = run_hook("Bash", "echo 'use grep command here'", rg_available=True)
        # Document actual behavior: it triggers even though grep is in quotes
        assert "hookSpecificOutput" in output, "Hook triggers even with grep in quotes (limitation)"

    # ========== Multiple suggestions ==========

    def test_both_find_and_grep_both_available(self):
        """Command with both find and grep should suggest both alternatives when both tools available"""
        output = run_hook("Bash", 'find . -name "*.py" | xargs grep "TODO"', fd_available=True, rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" in context, "Should suggest fd"
        assert "rg" in context, "Should suggest rg"
        assert "find" in context.lower(), "Should mention find"
        assert "grep" in context.lower(), "Should mention grep"

    def test_both_find_and_grep_only_fd_available(self):
        """Command with both find and grep should only suggest fd when only fd is available"""
        output = run_hook("Bash", 'find . -name "*.py" | xargs grep "TODO"', fd_available=True, rg_available=False)
        assert "hookSpecificOutput" in output, "Should return hook output"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" in context, "Should suggest fd"
        assert "rg" not in context, "Should NOT suggest rg when unavailable"

    def test_both_find_and_grep_only_rg_available(self):
        """Command with both find and grep should only suggest rg when only rg is available"""
        output = run_hook("Bash", 'find . -name "*.py" | xargs grep "TODO"', fd_available=False, rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" not in context, "Should NOT suggest fd when unavailable"
        assert "rg" in context, "Should suggest rg"

    def test_both_find_and_grep_neither_available(self):
        """Command with both find and grep should return {} when neither tool is available"""
        output = run_hook("Bash", 'find . -name "*.py" | xargs grep "TODO"', fd_available=False, rg_available=False)
        assert output == {}, "Should return {} when neither tool is available"

    def test_grep_and_find_in_sequence(self):
        """Sequential find and grep commands should trigger appropriate suggestions"""
        output = run_hook("Bash", 'grep "class" *.py && find . -name "*.pyc" -delete', fd_available=True, rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "rg" in context, "Should suggest rg for grep"
        assert "fd" in context, "Should suggest fd for find"

    def test_grep_and_find_in_sequence_only_rg(self):
        """Sequential grep and find should only suggest rg when only rg is available"""
        output = run_hook("Bash", 'grep "class" *.py && find . -name "*.pyc" -delete', fd_available=False, rg_available=True)
        assert "hookSpecificOutput" in output, "Should return hook output"
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "rg" in context, "Should suggest rg for grep"
        assert "fd" not in context, "Should NOT suggest fd when unavailable"

    # ========== Edge cases - environment variables ==========

    def test_find_in_env_var_name(self):
        """Environment variables with find in name should not trigger"""
        test_cases = [
            "echo $FINDPATH",
            "export FIND_DIR=/tmp",
            "${FIND_ROOT}/bin/app",
            "$FINDER_APP"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, fd_available=True)
            assert output == {}, f"'{cmd}' should not trigger (env var, not find command)"

    def test_grep_in_env_var_name(self):
        """Environment variables with grep in name should not trigger"""
        test_cases = [
            "echo $GREP_COLORS",
            "export GREP_OPTIONS='--color=auto'",
            "${GREP_PATH}/bin",
            "$GREPPY_VAR"
        ]
        for cmd in test_cases:
            output = run_hook("Bash", cmd, rg_available=True)
            assert output == {}, f"'{cmd}' should not trigger (env var, not grep command)"

    # ========== Commands with rg present should not suggest grep alternative ==========

    def test_grep_with_rg_in_command(self):
        """If rg is present in command, don't suggest it for grep"""
        output = run_hook("Bash", 'grep "test" file.txt && rg "pattern" .', rg_available=True)
        # Per the hook logic: if "rg " appears in the command, it won't suggest rg for grep
        assert output == {}, "Should not suggest rg if already in command"

    # ========== Output format validation ==========

    def test_json_output_valid_for_all_cases(self):
        """All hook outputs should be valid JSON"""
        test_commands = [
            ('find . -name "*.py"', True, False),
            ('grep "pattern" file.txt', False, True),
            ('find . | xargs grep "test"', True, True),
            ("ls -la", False, False),
            ('rg "pattern"', False, True),
            ('fd "*.py"', True, False),
            ("", False, False)
        ]
        for cmd, fd_avail, rg_avail in test_commands:
            output = run_hook("Bash", cmd, fd_available=fd_avail, rg_available=rg_avail)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {cmd}"

    def test_hook_event_name_correct_for_find(self):
        """Hook output should include correct event name for find when fd is available"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_hook_event_name_correct_for_grep(self):
        """Hook output should include correct event name for grep when rg is available"""
        output = run_hook("Bash", 'grep "pattern" file.txt', rg_available=True)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_additional_context_present_for_find(self):
        """additionalContext should be present and non-empty for find when fd is available"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_additional_context_present_for_grep(self):
        """additionalContext should be present and non-empty for grep when rg is available"""
        output = run_hook("Bash", 'grep "pattern" file.txt', rg_available=True)
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_no_decision_field(self):
        """Hook should not include decision field (only additionalContext)"""
        output = run_hook("Bash", 'grep "pattern" .', rg_available=True)
        assert "decision" not in output.get("hookSpecificOutput", {})

    # ========== Tool availability scenarios ==========

    def test_find_without_fd_installed(self):
        """When fd is not available, find commands should return {}"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=False)
        assert output == {}, "Should return {} when fd not available"

    def test_grep_without_rg_installed(self):
        """When rg is not available, grep commands should return {}"""
        output = run_hook("Bash", 'grep "pattern" file.txt', rg_available=False)
        assert output == {}, "Should return {} when rg not available"

    def test_find_with_fd_installed(self):
        """When fd is available, find commands should return suggestions"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        assert "hookSpecificOutput" in output, "Should return suggestions when fd is available"
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_with_rg_installed(self):
        """When rg is available, grep commands should return suggestions"""
        output = run_hook("Bash", 'grep "pattern" file.txt', rg_available=True)
        assert "hookSpecificOutput" in output, "Should return suggestions when rg is available"
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    # ========== Suggestion content validation ==========

    def test_find_suggestion_mentions_fd_syntax(self):
        """find suggestion should mention fd syntax examples when fd is available"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" in context.lower()
        assert "faster" in context.lower() or "simpler" in context.lower()

    def test_grep_suggestion_mentions_rg_benefits(self):
        """grep suggestion should mention rg benefits when rg is available"""
        output = run_hook("Bash", 'grep -r "pattern" .', rg_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "rg" in context.lower() or "ripgrep" in context.lower()
        assert "faster" in context.lower()

    def test_find_suggestion_mentions_gitignore(self):
        """find suggestion should mention .gitignore behavior when fd is available"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "gitignore" in context.lower()

    def test_grep_suggestion_mentions_gitignore(self):
        """grep suggestion should mention .gitignore behavior when rg is available"""
        output = run_hook("Bash", 'grep -r "pattern" .', rg_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "gitignore" in context.lower()

    # ========== Complex real-world scenarios ==========

    def test_find_in_complex_script(self):
        """
        LIMITATION: find in command substitution $(find ...) will NOT trigger.
        Hook looks for ' find ' (with spaces) but $(find has no space before find.
        """
        cmd = 'for file in $(find /var/log -name "*.log" -mtime +30); do rm "$file"; done'
        output = run_hook("Bash", cmd, fd_available=True)
        # Pattern ' find ' doesn't match '$(find' (no space before find)
        assert output == {}, "find in $(find ...) doesn't match ' find ' pattern"

    def test_find_in_complex_script_with_spaces(self):
        """Complex script with spaced find command should trigger when fd is available"""
        cmd = 'for file in $( find /var/log -name "*.log" -mtime +30); do rm "$file"; done'
        output = run_hook("Bash", cmd, fd_available=True)
        # Now there's a space: '$( find /var' contains ' find '
        assert "hookSpecificOutput" in output
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_in_complex_pipeline(self):
        """Complex pipeline with grep should trigger when rg is available"""
        cmd = 'cat *.log | grep ERROR | sort | uniq -c | sort -rn | head -10'
        output = run_hook("Bash", cmd, rg_available=True)
        assert "hookSpecificOutput" in output
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_in_complex_pipeline_rg_unavailable(self):
        """Complex pipeline with grep should NOT trigger when rg is unavailable"""
        cmd = 'cat *.log | grep ERROR | sort | uniq -c | sort -rn | head -10'
        output = run_hook("Bash", cmd, rg_available=False)
        assert output == {}, "Should return {} when rg not available"

    def test_nested_find_with_grep_both_available(self):
        """Nested command with both find and grep should suggest both when both tools available"""
        cmd = 'find src/ -type f -name "*.py" -exec grep -l "import pandas" {} \\;'
        output = run_hook("Bash", cmd, fd_available=True, rg_available=True)
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" in context, "Should suggest fd when available"
        assert "rg" in context, "Should suggest rg when available"

    def test_nested_find_with_grep_only_fd(self):
        """Nested command with both find and grep should only suggest fd when only fd available"""
        cmd = 'find src/ -type f -name "*.py" -exec grep -l "import pandas" {} \\;'
        output = run_hook("Bash", cmd, fd_available=True, rg_available=False)
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" in context, "Should suggest fd when available"
        assert "rg" not in context, "Should NOT suggest rg when unavailable"

    def test_nested_find_with_grep_only_rg(self):
        """Nested command with both find and grep should only suggest rg when only rg available"""
        cmd = 'find src/ -type f -name "*.py" -exec grep -l "import pandas" {} \\;'
        output = run_hook("Bash", cmd, fd_available=False, rg_available=True)
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "fd" not in context, "Should NOT suggest fd when unavailable"
        assert "rg" in context, "Should suggest rg when available"

    def test_nested_find_with_grep_neither_available(self):
        """Nested command with both find and grep should return {} when neither tool available"""
        cmd = 'find src/ -type f -name "*.py" -exec grep -l "import pandas" {} \\;'
        output = run_hook("Bash", cmd, fd_available=False, rg_available=False)
        assert output == {}, "Should return {} when neither tool is available"

    # ========== Edge cases - spacing variations ==========

    def test_find_with_multiple_spaces(self):
        """find with extra spaces should still trigger when fd is available"""
        output = run_hook("Bash", "find  .  -name  '*.py'", fd_available=True)
        assert "hookSpecificOutput" in output
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_find_at_end_of_command(self):
        """find at the end of command should trigger when fd is available"""
        output = run_hook("Bash", "cd /tmp && find .", fd_available=True)
        assert "hookSpecificOutput" in output
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

    def test_grep_at_end_of_command(self):
        """grep at the end of command should trigger when rg is available"""
        output = run_hook("Bash", 'cd /var/log && grep "error"', rg_available=True)
        assert "hookSpecificOutput" in output
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    # ========== Tool availability combinations ==========

    def test_both_tools_available(self):
        """Test scenario where both fd and rg are available"""
        # find should suggest fd
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True, rg_available=True)
        assert "hookSpecificOutput" in output
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

        # grep should suggest rg
        output = run_hook("Bash", 'grep "pattern" .', fd_available=True, rg_available=True)
        assert "hookSpecificOutput" in output
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    def test_neither_tool_available(self):
        """Test scenario where neither fd nor rg are available"""
        # find should return {}
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=False, rg_available=False)
        assert output == {}

        # grep should return {}
        output = run_hook("Bash", 'grep "pattern" .', fd_available=False, rg_available=False)
        assert output == {}

    def test_only_fd_available_not_rg(self):
        """Test scenario where only fd is available, not rg"""
        # find should suggest fd
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True, rg_available=False)
        assert "hookSpecificOutput" in output
        assert "fd" in output["hookSpecificOutput"]["additionalContext"]

        # grep should return {}
        output = run_hook("Bash", 'grep "pattern" .', fd_available=True, rg_available=False)
        assert output == {}

    def test_only_rg_available_not_fd(self):
        """Test scenario where only rg is available, not fd"""
        # find should return {}
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=False, rg_available=True)
        assert output == {}

        # grep should suggest rg
        output = run_hook("Bash", 'grep "pattern" .', fd_available=False, rg_available=True)
        assert "hookSpecificOutput" in output
        assert "rg" in output["hookSpecificOutput"]["additionalContext"]

    # ========== Suggestion format validation ==========

    def test_suggestion_format_matches_expected_structure(self):
        """Verify suggestion format matches expected markdown structure"""
        output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should contain markdown formatting
        assert "**" in context or "#" in context, "Should use markdown formatting"
        assert "fd" in context, "Should mention fd"

    # ========== Error handling ==========

    def test_missing_tool_input_field(self):
        """Missing tool_input field should return {}"""
        input_data = {
            "tool_name": "Bash"
            # Missing tool_input
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Missing tool_input should return {}"

    def test_missing_command_field(self):
        """Missing command field should return {}"""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {}
            # Missing command
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Missing command should return {}"


def main():
    """Run tests when executed as a script"""
    # Run pytest on this file
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
