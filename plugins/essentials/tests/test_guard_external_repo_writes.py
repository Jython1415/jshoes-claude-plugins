"""
Unit tests for guard-external-repo-writes.py hook

This test suite validates that the hook properly detects and blocks write commands
to external repositories (repos the user doesn't own).
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
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "guard-external-repo-writes.py"


def run_hook(
    tool_name: str,
    command: str,
    username: str = "testuser",
) -> dict:
    """
    Helper function to run the hook with a mocked username.

    Sets up a temporary HOME directory with a cached username to avoid
    requiring actual GitHub API calls.
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command}
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create the hook-state directory and cache file
        hook_state_dir = Path(tmpdir) / ".claude" / "hook-state"
        hook_state_dir.mkdir(parents=True, exist_ok=True)

        cache_file = hook_state_dir / "gh-username-cache"
        cache_file.write_text(f"{time.time()}:{username}")

        # Set up environment with custom HOME
        env = os.environ.copy()
        env["HOME"] = tmpdir

        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )

        if result.returncode not in [0, 1]:
            raise RuntimeError(f"Hook failed: {result.stderr}")

        return json.loads(result.stdout)


class TestGuardExternalRepoWrites:
    """Test suite for guard-external-repo-writes hook"""

    def test_no_block_for_non_bash_tool(self):
        """Non-Bash tools should not be blocked"""
        output = run_hook("Write", "gh issue create -R external/repo")
        assert output == {}

    def test_no_block_for_read_only_command(self):
        """Read-only gh commands should not be blocked"""
        output = run_hook(
            "Bash",
            "gh issue view -R external/repo",
        )
        assert output == {}

    def test_no_block_for_local_repo(self):
        """Commands without --repo flag (local repo) should not be blocked"""
        output = run_hook(
            "Bash",
            "gh issue create --title 'test'",
        )
        assert output == {}

    def test_no_block_for_owned_repo(self):
        """Commands targeting user's own repo should not be blocked"""
        output = run_hook(
            "Bash",
            "gh issue create -R testuser/myrepo --title 'test'",
            username="testuser",
        )
        assert output == {}

    def test_no_block_for_owned_repo_case_insensitive(self):
        """Repo ownership comparison should be case-insensitive"""
        output = run_hook(
            "Bash",
            "gh issue create -R TESTUSER/myrepo --title 'test'",
            username="testuser",
        )
        assert output == {}

    def test_blocks_external_repo_with_long_form_flag(self):
        """Writing to external repo with --repo flag should be blocked"""
        output = run_hook(
            "Bash",
            "gh issue create --repo external/repo --title 'test'",
            username="testuser",
        )
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_blocks_external_repo_with_short_form_flag(self):
        """Writing to external repo with -R flag should be blocked"""
        output = run_hook(
            "Bash",
            "gh issue create -R external/repo --title 'test'",
            username="testuser",
        )
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_block_reason_field_present(self):
        """Blocked output should include permissionDecisionReason"""
        output = run_hook(
            "Bash",
            "gh issue create -R external/repo --title 'test'",
            username="testuser",
        )
        hook_output = output["hookSpecificOutput"]
        assert "permissionDecisionReason" in hook_output
        assert len(hook_output["permissionDecisionReason"]) > 0

    def test_block_reason_includes_repo_info(self):
        """Block reason should mention the external repo name"""
        output = run_hook(
            "Bash",
            "gh issue create -R external/repo --title 'test'",
            username="testuser",
        )
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert "external" in reason.lower()

    def test_block_output_has_hook_event_name(self):
        """Blocked output should include hookEventName"""
        output = run_hook(
            "Bash",
            "gh issue create -R external/repo --title 'test'",
            username="testuser",
        )
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_blocks_multiple_write_actions(self):
        """Various write actions should all be blocked for external repos"""
        commands = [
            "gh issue create -R external/repo --title 'test'",
            "gh issue comment -R external/repo -b 'test'",
            "gh issue close -R external/repo",
            "gh pr create -R external/repo --title 'test'",
            "gh pr comment -R external/repo -b 'test'",
            "gh pr review -R external/repo --approve",
        ]
        for cmd in commands:
            output = run_hook(
                "Bash",
                cmd,
                username="testuser",
            )
            assert output["hookSpecificOutput"]["permissionDecision"] == "deny", (
                f"Command '{cmd}' should have been blocked"
            )

    def test_no_block_for_non_write_subcommand(self):
        """Non-write subcommands should not be blocked even with --repo"""
        output = run_hook(
            "Bash",
            "gh issue list -R external/repo",
            username="testuser",
        )
        assert output == {}

    def test_json_output_valid_for_all_cases(self):
        """All hook outputs should be valid JSON dicts"""
        test_cases = [
            ("Bash", "gh issue create -R external/repo --title 'test'"),
            ("Bash", "gh issue view -R external/repo"),
            ("Bash", "gh issue create --title 'test'"),
            ("Write", "gh issue create -R external/repo"),
        ]
        for tool_name, command in test_cases:
            output = run_hook(
                tool_name,
                command,
                username="testuser",
            )
            assert isinstance(output, dict), f"Output should be valid JSON dict for: {command}"

    def test_no_block_for_empty_command(self):
        """Empty command should not be blocked"""
        output = run_hook(
            "Bash",
            "",
        )
        assert output == {}

    def test_blocks_external_repo_with_owner_name_with_dash(self):
        """Repo owners with dashes should be correctly parsed and blocked"""
        output = run_hook(
            "Bash",
            "gh issue create -R my-external-org/repo --title 'test'",
            username="testuser",
        )
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def main():
    """Run tests when executed as a script"""
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
