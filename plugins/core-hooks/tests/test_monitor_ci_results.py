"""
Unit tests for monitor-ci-results.py hook

This test suite validates that the hook properly detects git push and PR creation
commands and provides CI monitoring guidance when GitHub Actions workflows exist.

Following the testing philosophy: test behavior, not content.
- Verify that guidance is presented when expected
- Test trigger conditions (what activates the hook)
- Validate JSON output structure
- Don't assert on specific wording in guidance text
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "monitor-ci-results.py"


def run_hook(
    tool_name: str,
    command: str,
    clear_cooldown: bool = True,
    has_workflows: bool = True,
    tool_result: dict = None,
) -> dict:
    """
    Helper function to run the hook.

    Args:
        tool_name: The name of the tool being used
        command: The bash command to test
        clear_cooldown: Whether to clear cooldown state before running
        has_workflows: Whether to simulate having GitHub workflows
        tool_result: Optional tool result to include

    Returns:
        Parsed JSON output from the hook
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "session_id": "test-session-abc123"
    }

    if tool_result is not None:
        input_data["tool_result"] = tool_result

    # Clear cooldown state if requested
    if clear_cooldown:
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "monitor-ci-cooldown-test-session-abc123"
        if state_file.exists():
            state_file.unlink()

    # Create a temp directory structure to simulate workflows
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            if has_workflows:
                # Create .github/workflows with a sample workflow file
                workflows_dir = Path(tmpdir) / ".github" / "workflows"
                workflows_dir.mkdir(parents=True)
                (workflows_dir / "ci.yml").write_text("name: CI\non: push\njobs: {}")

            result = subprocess.run(
                ["uv", "run", "--script", str(HOOK_PATH)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True
            )

            if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
                raise RuntimeError(f"Hook failed: {result.stderr}")

            return json.loads(result.stdout)
        finally:
            os.chdir(original_cwd)


class TestGitPushDetection:
    """Test git push detection and CI monitoring guidance"""

    def test_git_push_with_workflows_triggers(self):
        """Git push with workflows should trigger CI monitoring guidance"""
        output = run_hook("Bash", "git push origin main", has_workflows=True)
        assert "hookSpecificOutput" in output, "Should detect git push"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0, "Should provide guidance"

    def test_git_push_without_workflows_silent(self):
        """Git push without workflows should not trigger"""
        output = run_hook("Bash", "git push origin main", has_workflows=False)
        assert output == {}, "Should not trigger without workflows"

    def test_git_push_with_flags_triggers(self):
        """Git push with various flags should trigger"""
        commands = [
            "git push",
            "git push origin main",
            "git push -u origin feature-branch",
            "git push --force origin main",
            "git push origin HEAD:refs/heads/branch",
        ]
        for cmd in commands:
            output = run_hook("Bash", cmd, has_workflows=True)
            assert "hookSpecificOutput" in output, f"Should detect: {cmd}"

    def test_git_push_case_insensitive(self):
        """Git push detection should be case-insensitive"""
        for cmd in ["GIT PUSH origin main", "Git Push origin main", "git PUSH origin main"]:
            output = run_hook("Bash", cmd, has_workflows=True)
            assert "hookSpecificOutput" in output, f"Should detect: {cmd}"

    def test_chained_git_push_triggers(self):
        """Git push in chained command should trigger"""
        output = run_hook("Bash", "git add . && git commit -m 'test' && git push", has_workflows=True)
        assert "hookSpecificOutput" in output, "Should detect git push in chain"


class TestPRCreationDetection:
    """Test PR creation detection"""

    def test_gh_pr_create_triggers(self):
        """gh pr create should trigger CI monitoring guidance"""
        output = run_hook("Bash", 'gh pr create --title "Test" --body "Description"', has_workflows=True)
        assert "hookSpecificOutput" in output, "Should detect gh pr create"
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_gh_pr_create_without_workflows_silent(self):
        """gh pr create without workflows should not trigger"""
        output = run_hook("Bash", 'gh pr create --title "Test"', has_workflows=False)
        assert output == {}, "Should not trigger without workflows"

    def test_github_api_pr_create_triggers(self):
        """curl POST to /pulls should trigger CI monitoring guidance"""
        command = '''curl -X POST -H "Authorization: token $TOKEN" \
            "https://api.github.com/repos/owner/repo/pulls" \
            -d '{"title":"Test","head":"feature","base":"main"}'
        '''
        output = run_hook("Bash", command, has_workflows=True)
        assert "hookSpecificOutput" in output, "Should detect GitHub API PR creation"

    def test_gh_pr_create_variations(self):
        """Various gh pr create forms should trigger"""
        commands = [
            'gh pr create',
            'gh pr create --title "Test"',
            'gh pr create --fill',
            'gh pr create --draft --title "WIP"',
        ]
        for cmd in commands:
            output = run_hook("Bash", cmd, has_workflows=True)
            assert "hookSpecificOutput" in output, f"Should detect: {cmd}"


class TestCooldownMechanism:
    """Test cooldown mechanism"""

    def test_cooldown_prevents_duplicate_reminders(self):
        """Reminders should be rate-limited by cooldown"""
        # First call should trigger
        output1 = run_hook("Bash", "git push origin main", clear_cooldown=True, has_workflows=True)
        assert "hookSpecificOutput" in output1, "First call should trigger"

        # Second call within cooldown should not trigger
        output2 = run_hook("Bash", "git push origin main", clear_cooldown=False, has_workflows=True)
        assert output2 == {}, "Second call should be suppressed by cooldown"

    def test_cooldown_applies_across_operations(self):
        """Cooldown should apply to both push and PR create"""
        # Trigger with git push
        output1 = run_hook("Bash", "git push origin main", clear_cooldown=True, has_workflows=True)
        assert "hookSpecificOutput" in output1

        # PR create should also be suppressed
        output2 = run_hook("Bash", 'gh pr create --title "Test"', clear_cooldown=False, has_workflows=True)
        assert output2 == {}, "PR create should be suppressed by cooldown"

    def test_cooldown_state_file_created(self):
        """Cooldown state file should be created"""
        state_dir = Path.home() / ".claude" / "hook-state"
        state_file = state_dir / "monitor-ci-cooldown-test-session-abc123"

        # Clear state first
        if state_file.exists():
            state_file.unlink()

        # Trigger hook
        run_hook("Bash", "git push origin main", clear_cooldown=False, has_workflows=True)

        # Check state file was created
        assert state_file.exists(), "State file should be created"
        assert state_file.read_text().strip(), "State file should contain timestamp"


class TestNonTriggeringCommands:
    """Test that non-relevant commands don't trigger"""

    def test_non_bash_tools_silent(self):
        """Non-Bash tools should not trigger"""
        tools = ["Read", "Write", "Edit", "Glob", "Grep", "WebFetch"]
        for tool in tools:
            output = run_hook(tool, "git push origin main", has_workflows=True)
            assert output == {}, f"{tool} should not trigger hook"

    @pytest.mark.parametrize("command,description", [
        ("git status", "git status"),
        ("git add .", "git add"),
        ("git commit -m 'test'", "git commit"),
        ("git pull origin main", "git pull"),
        ("git fetch origin", "git fetch"),
        ("git log --oneline", "git log"),
        ("git diff HEAD~1", "git diff"),
    ])
    def test_non_push_git_commands_silent(self, command, description):
        """Non-push git commands should not trigger"""
        output = run_hook("Bash", command, has_workflows=True)
        assert output == {}, f"{description} should not trigger"

    @pytest.mark.parametrize("command,description", [
        ("gh pr list", "pr list"),
        ("gh pr view 123", "pr view"),
        ("gh pr checks", "pr checks"),
        ("gh issue list", "issue list"),
        ("gh run list", "run list"),
    ])
    def test_gh_read_commands_silent(self, command, description):
        """gh CLI read commands should not trigger"""
        output = run_hook("Bash", command, has_workflows=True)
        assert output == {}, f"{description} should not trigger"

    def test_empty_command_silent(self):
        """Empty command should not trigger"""
        output = run_hook("Bash", "", has_workflows=True)
        assert output == {}, "Empty command should not trigger"


class TestErrorHandling:
    """Test behavior when command has errors"""

    def test_command_with_error_silent(self):
        """Commands that failed should not trigger"""
        output = run_hook(
            "Bash",
            "git push origin main",
            has_workflows=True,
            tool_result={"error": "fatal: could not read from remote repository"}
        )
        assert output == {}, "Failed command should not trigger CI reminder"


class TestWorkflowDetection:
    """Test GitHub workflow detection"""

    def test_triggers_with_yml_workflow(self):
        """Should trigger when .github/workflows contains .yml files"""
        output = run_hook("Bash", "git push origin main", has_workflows=True)
        assert "hookSpecificOutput" in output, "Should trigger with yml workflow"

    def test_silent_without_workflows_dir(self):
        """Should not trigger when .github/workflows doesn't exist"""
        output = run_hook("Bash", "git push origin main", has_workflows=False)
        assert output == {}, "Should not trigger without workflows directory"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_malformed_json_input_returns_empty(self):
        """Hook should handle malformed JSON gracefully"""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True
        )
        # Should exit with error code but output valid JSON
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} on malformed input"

    def test_missing_tool_name_returns_empty(self):
        """Hook should handle missing tool_name field"""
        input_data = {"tool_input": {"command": "git push origin main"}}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} when tool_name missing"

    def test_missing_command_returns_empty(self):
        """Hook should handle missing command field"""
        input_data = {"tool_name": "Bash", "tool_input": {}}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)
        assert output == {}, "Should return {} when command missing"


class TestOutputValidation:
    """Test output format validation"""

    def test_output_is_valid_json(self):
        """Hook output should always be valid JSON"""
        output = run_hook("Bash", "git push origin main", has_workflows=True)
        # Should be parseable as JSON (already done by run_hook)
        assert isinstance(output, dict)

    def test_event_name_correct_for_push(self):
        """Hook should set correct event name for push"""
        output = run_hook("Bash", "git push origin main", has_workflows=True)
        if "hookSpecificOutput" in output:
            assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"

    def test_event_name_correct_for_pr(self):
        """Hook should set correct event name for PR create"""
        output = run_hook("Bash", 'gh pr create --title "Test"', has_workflows=True)
        if "hookSpecificOutput" in output:
            assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"

    def test_push_guidance_presented(self):
        """Git push should trigger guidance presentation"""
        output = run_hook("Bash", "git push origin main", has_workflows=True)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

    def test_pr_guidance_presented(self):
        """PR creation should trigger guidance presentation"""
        output = run_hook("Bash", 'gh pr create --title "Test"', has_workflows=True)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert len(output["hookSpecificOutput"]["additionalContext"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
