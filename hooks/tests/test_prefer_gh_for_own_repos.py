"""
Unit tests for prefer-gh-for-own-repos.py hook

Run with:
  uv run pytest                                          # Run all tests
  uv run pytest hooks/tests/test_prefer_gh_for_own_repos.py  # Run this test file
  uv run pytest -v                                       # Verbose output

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
HOOK_PATH = Path(__file__).parent.parent / "prefer-gh-for-own-repos.py"

# Target owner from the hook
TARGET_OWNER = "Jython1415"


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
        "tool_input": tool_input
    }

    # Create a temporary directory for mock tools
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clear cooldown state if requested
        if clear_cooldown:
            state_dir = Path.home() / ".claude" / "hook-state"
            state_file = state_dir / "prefer-gh-cooldown"
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

        # Modify PATH to include our mock directory
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


class TestPreferGhForOwnRepos:
    """Test suite for prefer-gh-for-own-repos hook"""

    # ========== WebFetch with Jython1415 repos ==========

    def test_webfetch_github_issue_url(self):
        """WebFetch accessing Jython1415 issue should suggest gh when gh available"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/my-repo/issues/10"},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "gh" in output["hookSpecificOutput"]["additionalContext"]
        assert TARGET_OWNER in output["hookSpecificOutput"]["additionalContext"]

    def test_webfetch_github_pr_url(self):
        """WebFetch accessing Jython1415 PR should suggest gh when gh available"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/my-repo/pull/5"},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "gh" in output["hookSpecificOutput"]["additionalContext"]

    def test_webfetch_api_github_url(self):
        """WebFetch accessing GitHub API for Jython1415 repo should suggest gh when gh available"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "gh" in output["hookSpecificOutput"]["additionalContext"]

    def test_webfetch_github_url_gh_unavailable(self):
        """WebFetch accessing Jython1415 repo should NOT suggest when gh unavailable"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/my-repo/issues/10"},
            gh_available=False
        )
        assert output == {}, "Should return {} when gh not available"

    def test_webfetch_different_owner(self):
        """WebFetch accessing different owner's repo should NOT suggest gh"""
        output = run_hook(
            "WebFetch",
            {"url": "https://github.com/torvalds/linux/issues/1"},
            gh_available=True
        )
        assert output == {}, "Should not trigger for different owner"

    def test_webfetch_non_github_url(self):
        """WebFetch accessing non-GitHub URL should NOT trigger"""
        output = run_hook(
            "WebFetch",
            {"url": "https://stackoverflow.com/questions/12345"},
            gh_available=True
        )
        assert output == {}, "Should not trigger for non-GitHub URLs"

    # ========== Bash with curl commands ==========

    def test_bash_curl_github_api(self):
        """Bash curl accessing Jython1415 GitHub API should suggest gh when gh available"""
        output = run_hook(
            "Bash",
            {"command": f'curl -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"'},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "gh" in output["hookSpecificOutput"]["additionalContext"]

    def test_bash_curl_github_url(self):
        """Bash curl accessing Jython1415 GitHub should suggest gh when gh available"""
        output = run_hook(
            "Bash",
            {"command": f'curl "https://github.com/{TARGET_OWNER}/my-repo/issues/10"'},
            gh_available=True
        )
        assert "hookSpecificOutput" in output, "Should return hook output"
        assert "gh" in output["hookSpecificOutput"]["additionalContext"]

    def test_bash_curl_different_owner(self):
        """Bash curl accessing different owner's repo should NOT trigger"""
        output = run_hook(
            "Bash",
            {"command": 'curl "https://api.github.com/repos/torvalds/linux/issues/1"'},
            gh_available=True
        )
        assert output == {}, "Should not trigger for different owner"

    def test_bash_curl_gh_unavailable(self):
        """Bash curl accessing Jython1415 repo should NOT suggest when gh unavailable"""
        output = run_hook(
            "Bash",
            {"command": f'curl "https://api.github.com/repos/{TARGET_OWNER}/my-repo/issues/10"'},
            gh_available=False
        )
        assert output == {}, "Should return {} when gh not available"

    def test_bash_without_curl(self):
        """Bash command without curl should NOT trigger"""
        output = run_hook(
            "Bash",
            {"command": "git status"},
            gh_available=True
        )
        assert output == {}, "Should not trigger for non-curl commands"

    def test_bash_curl_non_github(self):
        """Bash curl to non-GitHub URL should NOT trigger"""
        output = run_hook(
            "Bash",
            {"command": 'curl "https://api.example.com/data"'},
            gh_available=True
        )
        assert output == {}, "Should not trigger for non-GitHub URLs"

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
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "prefer-gh-cooldown"
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
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "prefer-gh-cooldown"
        state_dir.mkdir(parents=True, exist_ok=True)
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

    def test_non_webfetch_non_bash_tool(self):
        """Non-WebFetch, non-Bash tools should NOT trigger"""
        output = run_hook(
            "Read",
            {"file_path": "/some/path"},
            gh_available=True
        )
        assert output == {}, "Read tool should not trigger"

    def test_edit_tool(self):
        """Edit tool should NOT trigger"""
        output = run_hook(
            "Edit",
            {"file_path": "/some/path", "old_string": "a", "new_string": "b"},
            gh_available=True
        )
        assert output == {}, "Edit tool should not trigger"

    def test_glob_tool(self):
        """Glob tool should NOT trigger"""
        output = run_hook(
            "Glob",
            {"pattern": "*.py"},
            gh_available=True
        )
        assert output == {}, "Glob tool should not trigger"

    # ========== Edge cases ==========

    def test_empty_url(self):
        """WebFetch with empty URL should NOT trigger"""
        output = run_hook(
            "WebFetch",
            {"url": ""},
            gh_available=True
        )
        assert output == {}, "Empty URL should not trigger"

    def test_missing_url_field(self):
        """WebFetch with missing URL field should NOT trigger"""
        output = run_hook(
            "WebFetch",
            {},
            gh_available=True
        )
        assert output == {}, "Missing URL should not trigger"

    def test_empty_command(self):
        """Bash with empty command should NOT trigger"""
        output = run_hook(
            "Bash",
            {"command": ""},
            gh_available=True
        )
        assert output == {}, "Empty command should not trigger"

    def test_missing_command_field(self):
        """Bash with missing command field should NOT trigger"""
        output = run_hook(
            "Bash",
            {},
            gh_available=True
        )
        assert output == {}, "Missing command should not trigger"

    def test_malformed_url(self):
        """WebFetch with malformed URL should NOT crash"""
        output = run_hook(
            "WebFetch",
            {"url": "not-a-url"},
            gh_available=True
        )
        assert isinstance(output, dict), "Should return valid JSON even with malformed URL"

    # ========== URL pattern variations ==========

    def test_github_url_with_different_paths(self):
        """Various GitHub URL paths for Jython1415 should trigger when gh available"""
        test_urls = [
            f"https://github.com/{TARGET_OWNER}/repo/issues/10",
            f"https://github.com/{TARGET_OWNER}/repo/pull/5",
            f"https://github.com/{TARGET_OWNER}/repo/blob/main/file.py",
            f"https://github.com/{TARGET_OWNER}/repo",
            f"https://api.github.com/repos/{TARGET_OWNER}/repo/issues",
            f"https://api.github.com/repos/{TARGET_OWNER}/repo/pulls/5",
            f"https://raw.githubusercontent.com/{TARGET_OWNER}/repo/main/README.md",
        ]
        for url in test_urls:
            output = run_hook("WebFetch", {"url": url}, gh_available=True)
            assert "hookSpecificOutput" in output, f"Should trigger for: {url}"

    def test_curl_with_quotes_variations(self):
        """Curl commands with various quote styles should be detected"""
        test_commands = [
            f'curl "https://api.github.com/repos/{TARGET_OWNER}/repo/issues"',
            f"curl 'https://api.github.com/repos/{TARGET_OWNER}/repo/issues'",
            f'curl https://api.github.com/repos/{TARGET_OWNER}/repo/issues',
        ]
        for cmd in test_commands:
            output = run_hook("Bash", {"command": cmd}, gh_available=True)
            assert "hookSpecificOutput" in output, f"Should detect URL in: {cmd}"

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

    # ========== Suggestion content validation ==========

    def test_suggestion_mentions_gh_commands(self):
        """Suggestion should mention gh commands"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "gh issue" in context or "gh pr" in context, "Should mention gh commands"

    def test_suggestion_mentions_owner(self):
        """Suggestion should mention the target owner"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        assert TARGET_OWNER in context, "Should mention target owner"

    def test_suggestion_provides_examples(self):
        """Suggestion should provide example commands"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should contain code blocks or example syntax
        assert "```" in context or "gh " in context, "Should provide examples"

    def test_suggestion_allows_intentional_api_use(self):
        """Suggestion should acknowledge that API use might be intentional"""
        output = run_hook(
            "WebFetch",
            {"url": f"https://github.com/{TARGET_OWNER}/repo/issues/1"},
            gh_available=True
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should mention that API use can be intentional
        assert "intentional" in context.lower() or "continue" in context.lower(), \
            "Should acknowledge intentional API use"

    # ========== Real-world scenarios ==========

    def test_scenario_webfetch_issue_details(self):
        """Real scenario: WebFetch fetching issue details"""
        output = run_hook(
            "WebFetch",
            {
                "url": f"https://api.github.com/repos/{TARGET_OWNER}/claude-code-config/issues/10",
                "prompt": "Extract the issue details"
            },
            gh_available=True
        )
        assert "hookSpecificOutput" in output
        assert "gh issue view" in output["hookSpecificOutput"]["additionalContext"]

    def test_scenario_curl_create_pr(self):
        """Real scenario: curl creating a PR"""
        cmd = f'''curl -X POST \\
            -H "Authorization: token $GITHUB_TOKEN" \\
            "https://api.github.com/repos/{TARGET_OWNER}/my-repo/pulls" \\
            -d '{{"title":"New feature","head":"feature-branch","base":"main"}}'
        '''
        output = run_hook("Bash", {"command": cmd}, gh_available=True)
        assert "hookSpecificOutput" in output
        assert "gh pr create" in output["hookSpecificOutput"]["additionalContext"]

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
