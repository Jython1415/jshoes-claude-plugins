"""
Unit tests for prefer-gh-for-own-repos.py hook

This test suite uses mocking to test gh availability and cooldown scenarios.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "prefer-gh-for-own-repos.py"

# Target owner from the hook
TARGET_OWNER = "Jython1415"

# Writable test state directory (redirects away from ~/.claude/hook-state/ for sandbox compat)
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state"


def run_hook(
    tool_name: str,
    tool_input: dict,
    gh_available: bool = True,
    clear_cooldown: bool = True
) -> dict:
    """
    Helper function to run the hook with mocked gh availability.

    Args:
        tool_name: The tool name (e.g., "WebFetch" or "Bash")
        tool_input: The tool input dict (e.g., {"url": "..."} or {"command": "..."})
        gh_available: Whether to mock gh as available
        clear_cooldown: Whether to clear cooldown state before running

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": "test-session-abc123"
    }

    # Create a temporary directory for mock tools
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clear cooldown state if requested
        if clear_cooldown:
            state_file = TEST_STATE_DIR / "prefer-gh-cooldown-test-session-abc123"
            if state_file.exists():
                state_file.unlink()

        # Create a mock 'which' command that controls gh availability
        which_path = Path(tmpdir) / "which"
        which_script = "#!/bin/sh\n"
        which_script += "# Mock which script that controls gh availability\n"
        which_script += "case \"$1\" in\n"

        # Handle gh
        if gh_available:
            which_script += f"  gh) echo '{tmpdir}/gh'; exit 0 ;;\n"
        else:
            which_script += "  gh) exit 1 ;;\n"

        # For other commands, use the real which
        which_script += "  *) /usr/bin/which \"$1\" 2>/dev/null || exit 1 ;;\n"
        which_script += "esac\n"
        which_path.write_text(which_script)
        which_path.chmod(0o755)

        # Create mock gh if available
        if gh_available:
            gh_path = Path(tmpdir) / "gh"
            gh_path.write_text("#!/bin/sh\necho 'mock gh'\nexit 0\n")
            gh_path.chmod(0o755)

        # Modify PATH based on gh_available to control whether real gh is accessible
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)

        if gh_available:
            # When gh is available, prepend our mock to PATH
            env['PATH'] = f"{tmpdir}:{env.get('PATH', '')}"
        else:
            # When gh should be unavailable, filter PATH to exclude directories containing gh
            # but keep essential tools like uv, python
            import shutil
            minimal_path_parts = [tmpdir]

            # Find and include the directory containing uv
            uv_path = shutil.which('uv')
            if uv_path:
                uv_dir = os.path.dirname(uv_path)
                minimal_path_parts.append(uv_dir)

            # Add other essential paths but check they don't contain gh
            for path_part in env.get('PATH', '').split(':'):
                if not path_part or path_part in minimal_path_parts:
                    continue
                # Check if this directory contains gh
                potential_gh = os.path.join(path_part, 'gh')
                if not os.path.exists(potential_gh) and not os.path.islink(potential_gh):
                    # Safe to include - no gh here
                    minimal_path_parts.append(path_part)

            env['PATH'] = ':'.join(minimal_path_parts)

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


class TestPreferGhForOwnRepos:
    """Test suite for prefer-gh-for-own-repos hook"""

    # ========== WebFetch with Jython1415 repos ==========

    @pytest.mark.parametrize(
        "description,url",
        [
            ("GitHub issue URL", f"https://github.com/{TARGET_OWNER}/my-repo/issues/10"),
            ("GitHub PR URL", f"https://github.com/{TARGET_OWNER}/my-repo/pull/5"),
            ("GitHub API URL", f"https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"),
        ]
    )
    def test_webfetch_positive(self, description, url):
        """WebFetch accessing Jython1415 repos should suggest gh when gh available"""
        output = run_hook("WebFetch", {"url": url}, gh_available=True)
        assert "hookSpecificOutput" in output, f"Should return hook output for {description}"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance content"

    @pytest.mark.parametrize(
        "description,url",
        [
            ("gh unavailable", f"https://github.com/{TARGET_OWNER}/my-repo/issues/10"),
            ("different owner", "https://github.com/torvalds/linux/issues/1"),
            ("non-GitHub URL", "https://stackoverflow.com/questions/12345"),
        ]
    )
    def test_webfetch_negative(self, description, url):
        """WebFetch should NOT trigger for unavailable gh, different owners, or non-GitHub URLs"""
        gh_avail = description != "gh unavailable"
        output = run_hook("WebFetch", {"url": url}, gh_available=gh_avail)
        assert output == {}, f"Should not trigger for {description}"

    # ========== Bash with curl commands ==========

    @pytest.mark.parametrize(
        "description,command",
        [
            ("GitHub API URL", f'curl -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"'),
            ("GitHub URL", f'curl "https://github.com/{TARGET_OWNER}/my-repo/issues/10"'),
        ]
    )
    def test_bash_curl_positive(self, description, command):
        """Bash curl accessing Jython1415 repos should suggest gh when gh available"""
        output = run_hook("Bash", {"command": command}, gh_available=True)
        assert "hookSpecificOutput" in output, f"Should return hook output for {description}"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance content"

    @pytest.mark.parametrize(
        "description,command,gh_avail",
        [
            ("different owner", 'curl "https://api.github.com/repos/torvalds/linux/issues/1"', True),
            ("gh unavailable", f'curl "https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"', False),
            ("without curl", "git status", True),
            ("non-GitHub URL", 'curl "https://api.example.com/data"', True),
        ]
    )
    def test_bash_curl_negative(self, description, command, gh_avail):
        """Bash curl should NOT trigger for different owners, unavailable gh, non-curl, or non-GitHub URLs"""
        output = run_hook("Bash", {"command": command}, gh_available=gh_avail)
        assert output == {}, f"Should not trigger for {description}"

    # ========== Cooldown mechanism tests ==========

    def test_cooldown_prevents_duplicate_suggestion(self):
        """Second suggestion within cooldown period should not trigger"""
        # First call - should suggest
        output1 = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo1/issues/1"},
            gh_available=True,
            clear_cooldown=True
        )
        assert "hookSpecificOutput" in output1, "First call should suggest"

        # Second call immediately after - should NOT suggest (within cooldown)
        output2 = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo2/issues/2"},
            gh_available=True,
            clear_cooldown=False  # Don't clear cooldown
        )
        assert output2 == {}, "Second call within cooldown should not suggest"

    def test_cooldown_expires_after_period(self):
        """Suggestion should resume after cooldown period expires"""
        # First call - should suggest
        output1 = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo1/issues/1"},
            gh_available=True,
            clear_cooldown=True
        )
        assert "hookSpecificOutput" in output1, "First call should suggest"

        # Manually modify the cooldown file to simulate expired cooldown
        state_dir = TEST_STATE_DIR
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "prefer-gh-cooldown-test-session-abc123"
        old_time = time.time() - 65  # 65 seconds ago (beyond 60 second cooldown)
        state_file.write_text(str(old_time))

        # Second call after cooldown expires - should suggest again
        output2 = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo2/issues/2"},
            gh_available=True,
            clear_cooldown=False  # Don't clear cooldown
        )
        assert "hookSpecificOutput" in output2, "Should suggest again after cooldown expires"

    def test_corrupted_cooldown_file(self):
        """Hook should handle corrupted cooldown file gracefully"""
        # Create a corrupted cooldown file
        state_dir = TEST_STATE_DIR
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "prefer-gh-cooldown-test-session-abc123"
        state_file.write_text("not-a-number-corrupted-data")

        # Hook should still work and suggest (cooldown check fails gracefully)
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True,
            clear_cooldown=False  # Don't clear, let it deal with corruption
        )
        # Should still suggest since cooldown check fails on corrupted data
        assert "hookSpecificOutput" in output, "Should suggest even with corrupted state file"

    # ========== Other tool types ==========

    @pytest.mark.parametrize(
        "tool_name,tool_input",
        [
            ("Read", {"file_path": "/some/path"}),
            ("Edit", {"file_path": "/some/path", "old_string": "a", "new_string": "b"}),
            ("Glob", {"pattern": "*.py"}),
        ]
    )
    def test_non_triggering_tools(self, tool_name, tool_input):
        """Non-WebFetch, non-Bash tools should NOT trigger"""
        output = run_hook(tool_name, tool_input, gh_available=True)
        assert output == {}, f"{tool_name} tool should not trigger"

    # ========== Edge cases ==========

    @pytest.mark.parametrize(
        "tool_name,tool_input,description",
        [
            ("WebFetch", {"url": ""}, "empty URL"),
            ("WebFetch", {}, "missing URL field"),
            ("Bash", {"command": ""}, "empty command"),
            ("Bash", {}, "missing command field"),
        ]
    )
    def test_empty_and_missing_fields(self, tool_name, tool_input, description):
        """Empty and missing fields should NOT trigger"""
        output = run_hook(tool_name, tool_input, gh_available=True)
        assert output == {}, f"{description} should not trigger"

    def test_malformed_url(self):
        """WebFetch with malformed URL should NOT crash"""
        output = run_hook(
            "WebFetch",
            {"url": "not-a-url"},
            gh_available=True
        )
        assert isinstance(output, dict), "Should return valid JSON even with malformed URL"

    # ========== URL pattern variations ==========

    @pytest.mark.parametrize(
        "url",
        [
            f"https://github.com/{TARGET_OWNER}/repo/issues/10",
            f"https://github.com/{TARGET_OWNER}/repo/pull/5",
            f"https://github.com/{TARGET_OWNER}/repo/blob/main/file.py",
            f"https://github.com/{TARGET_OWNER}/repo",
            f"https://api.github.com/repos/{TARGET_OWNER}/repo/issues",
            f"https://api.github.com/repos/{TARGET_OWNER}/repo/pulls/5",
            f"https://raw.githubusercontent.com/{TARGET_OWNER}/repo/main/README.md",
        ]
    )
    def test_github_url_with_different_paths(self, url):
        """Various GitHub URL paths for Jython1415 should trigger when gh available"""
        output = run_hook("WebFetch", {"url": url}, gh_available=True)
        assert "hookSpecificOutput" in output, f"Should trigger for: {url}"

    @pytest.mark.parametrize(
        "command",
        [
            f'curl "https://api.github.com/repos/{TARGET_OWNER}/repo/issues"',
            f"curl 'https://api.github.com/repos/{TARGET_OWNER}/repo/issues'",
            f'curl https://api.github.com/repos/{TARGET_OWNER}/repo/issues',
        ]
    )
    def test_curl_with_quotes_variations(self, command):
        """Curl commands with various quote styles should be detected"""
        output = run_hook("Bash", {"command": command}, gh_available=True)
        assert "hookSpecificOutput" in output, f"Should detect URL in: {command}"

    def test_curl_complex_command(self):
        """Complex curl command with headers and data should still trigger"""
        cmd = f'''curl -X POST -H "Authorization: token $GITHUB_TOKEN" \\
            -H "Accept: application/vnd.github.v3+json" \\
            "https://api.github.com/repos/{TARGET_OWNER}/repo/issues" \\
            -d '{{"title":"Test"}}'
        '''
        output = run_hook("Bash", {"command": cmd}, gh_available=True)
        assert "hookSpecificOutput" in output, "Should trigger for complex curl"

    # ========== Output format validation ==========

    def test_json_output_valid(self):
        """All hook outputs should be valid JSON"""
        test_cases = [
            ("WebFetch", {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"}, True),
            ("WebFetch", {"url": "https://github.com/other/repo/issues/1"}, True),
            ("Bash", {"command": f'curl "https://api.github.com/repos/{TARGET_OWNER}/repo"'}, True),
            ("Bash", {"command": "git status"}, True),
            ("WebFetch", {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"}, False),
            ("Read", {"file_path": "/path"}, True),
        ]
        for tool_name, tool_input, gh_avail in test_cases:
            output = run_hook(tool_name, tool_input, gh_available=gh_avail)
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {tool_name}"

    def test_hook_event_name_correct(self):
        """Hook output should include correct event name"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_additional_context_present(self):
        """additionalContext should be present and non-empty"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_no_decision_field(self):
        """Hook should not include decision field (only additionalContext)"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        assert "decision" not in output.get("hookSpecificOutput", {})

    # ========== Output format validation ==========

    # ========== Real-world scenarios ==========

    def test_scenario_webfetch_issue_details(self):
        """Real scenario: WebFetch fetching issue details"""
        output = run_hook(
            "WebFetch",
            {
                "url": f"https://api.github.com/repos/{TARGET_OWNER}/jshoes-claude-plugins/issues/10",
                "prompt": "Extract the issue details"
            },
            gh_available=True
        )
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_scenario_curl_create_pr(self):
        """Real scenario: curl creating a PR"""
        cmd = f'''curl -X POST \\
            -H "Authorization: token $GITHUB_TOKEN" \\
            "https://api.github.com/repos/{TARGET_OWNER}/my-repo/pulls" \\
            -d '{{"title":"New feature","head":"feature-branch","base":"main"}}'
        '''
        output = run_hook("Bash", {"command": cmd}, gh_available=True)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_scenario_after_multiple_uses_cooldown(self):
        """Real scenario: Multiple API calls in sequence trigger cooldown"""
        # First call
        output1 = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True,
            clear_cooldown=True
        )
        assert "hookSpecificOutput" in output1

        # Subsequent calls within cooldown don't trigger
        for i in range(2, 5):
            output = run_hook(
                "WebFetch",
                {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/{i}"},
                gh_available=True,
                clear_cooldown=False
            )
            assert output == {}, f"Call {i} should be suppressed by cooldown"

    # ========== Case sensitivity ==========

    def test_owner_name_case_sensitive(self):
        """Owner name matching should be case sensitive"""
        # Lowercase should NOT trigger
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER.lower()}/repo/issues/1"},
            gh_available=True
        )
        assert output == {}, "Lowercase owner name should not trigger"

        # Correct case should trigger
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Correct case should trigger"


def main():
    """Run tests when executed as a script"""
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
