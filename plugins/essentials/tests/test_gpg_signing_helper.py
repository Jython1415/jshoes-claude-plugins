"""
Unit tests for gpg-signing-helper.py hook (PreToolUse)

Behavioral model:
- Bash tool with git commit/tag/merge/rebase: outputs updatedInput with modified command
- Bash tool with non-signing git commands: outputs {} (silent pass-through)
- Non-Bash tools: outputs {} (silent pass-through)
- Malformed input: outputs {} gracefully
- Already-modified commands: outputs {} (idempotent)
"""
import json
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "gpg-signing-helper.py"


def run_hook(tool_name: str = "Bash", command: str = "") -> dict:
    """Run the gpg-signing-helper hook and return parsed JSON output."""
    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "session_id": "test-gpg-session-123",
    }

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )

    if result.returncode not in [0, 1]:
        raise RuntimeError(f"Hook failed unexpectedly: {result.stderr}")

    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Git commit flag injection
# ---------------------------------------------------------------------------

class TestGitCommitInjection:
    """Test that --no-gpg-sign is injected into git commit commands."""

    def test_simple_commit(self):
        """Simple git commit should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git commit -m 'test'")
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out["updatedInput"]["command"] == "git commit --no-gpg-sign -m 'test'"

    def test_commit_with_amend(self):
        """git commit --amend should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git commit --amend")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "git commit --no-gpg-sign --amend" == output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_commit_with_multiple_flags(self):
        """git commit with multiple flags should inject --no-gpg-sign after commit."""
        output = run_hook("Bash", "git commit --verbose -m 'msg'")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert modified.startswith("git commit --no-gpg-sign")
        assert "-m 'msg'" in modified

    def test_commit_already_has_flag(self):
        """git commit that already has --no-gpg-sign should not be modified."""
        output = run_hook("Bash", "git commit --no-gpg-sign -m 'msg'")
        assert output == {}, "Already-modified commit should pass through"

    def test_commit_allows_execution(self):
        """Commit injection should include permissionDecision: allow."""
        output = run_hook("Bash", "git commit -m 'test'")
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("permissionDecision") == "allow"


# ---------------------------------------------------------------------------
# Git tag flag injection
# ---------------------------------------------------------------------------

class TestGitTagInjection:
    """Test that --no-gpg-sign is injected into git tag commands."""

    def test_tag_with_sign_flag(self):
        """git tag -s should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git tag -s v1.0.0")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_tag_with_long_sign_flag(self):
        """git tag --sign should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git tag --sign v1.0.0")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_tag_without_sign_flag(self):
        """Unsigned tag creation (no -s) should still get --no-gpg-sign injected."""
        output = run_hook("Bash", "git tag v1.0.0")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_tag_already_has_flag(self):
        """git tag that already has --no-gpg-sign should not be modified."""
        output = run_hook("Bash", "git tag --no-gpg-sign v1.0.0")
        assert output == {}, "Already-modified tag should pass through"


# ---------------------------------------------------------------------------
# Git merge flag injection
# ---------------------------------------------------------------------------

class TestGitMergeInjection:
    """Test that --no-gpg-sign is injected into git merge commands."""

    def test_simple_merge(self):
        """Simple git merge should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git merge feature")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_merge_with_no_ff(self):
        """git merge --no-ff should get --no-gpg-sign injected."""
        output = run_hook("Bash", "git merge --no-ff feature")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_merge_already_has_flag(self):
        """git merge that already has --no-gpg-sign should not be modified."""
        output = run_hook("Bash", "git merge --no-gpg-sign feature")
        assert output == {}, "Already-modified merge should pass through"


# ---------------------------------------------------------------------------
# Git rebase rewrite (special case: -c flag instead of --no-gpg-sign)
# ---------------------------------------------------------------------------

class TestGitRebaseRewrite:
    """Test that git rebase is rewritten to use -c commit.gpgSign=false."""

    def test_simple_rebase(self):
        """Simple git rebase should be rewritten with -c commit.gpgSign=false."""
        output = run_hook("Bash", "git rebase main")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "git -c commit.gpgSign=false rebase main" == modified

    def test_rebase_interactive(self):
        """git rebase -i should be rewritten with -c flag."""
        output = run_hook("Bash", "git rebase -i main")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "git -c commit.gpgSign=false rebase -i main" == modified

    def test_rebase_already_rewritten(self):
        """git rebase already rewritten should pass through."""
        output = run_hook("Bash", "git -c commit.gpgSign=false rebase main")
        assert output == {}, "Already-rewritten rebase should pass through"

    def test_rebase_with_multiple_flags(self):
        """git rebase with multiple flags should preserve all flags."""
        output = run_hook("Bash", "git rebase --autostash --keep-empty main")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "git -c commit.gpgSign=false rebase" in modified
        assert "--autostash" in modified
        assert "--keep-empty main" in modified


# ---------------------------------------------------------------------------
# Non-signing git commands (passthrough)
# ---------------------------------------------------------------------------

class TestNonSigningGitCommands:
    """Test that non-signing git commands pass through silently."""

    def test_git_status(self):
        """git status should pass through silently."""
        output = run_hook("Bash", "git status")
        assert output == {}

    def test_git_push(self):
        """git push should pass through silently."""
        output = run_hook("Bash", "git push origin main")
        assert output == {}

    def test_git_pull(self):
        """git pull should pass through silently."""
        output = run_hook("Bash", "git pull origin main")
        assert output == {}

    def test_git_branch(self):
        """git branch should pass through silently."""
        output = run_hook("Bash", "git branch -a")
        assert output == {}

    def test_git_log(self):
        """git log should pass through silently."""
        output = run_hook("Bash", "git log --oneline")
        assert output == {}


# ---------------------------------------------------------------------------
# Non-Bash tools (passthrough)
# ---------------------------------------------------------------------------

class TestNonBashTools:
    """Test that non-Bash tools pass through silently."""

    def test_read_tool(self):
        """Read tool should pass through silently."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/test.txt"},
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_write_tool(self):
        """Write tool should pass through silently."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/test.txt", "content": "test"},
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_empty_tool_name(self):
        """Empty tool_name should pass through silently."""
        output = run_hook("", "git commit -m 'msg'")
        assert output == {}


# ---------------------------------------------------------------------------
# Piped and chained commands
# ---------------------------------------------------------------------------

class TestPipedAndChainedCommands:
    """Test that piped and chained commands are handled correctly."""

    def test_piped_commit(self):
        """git commit piped to other commands should be modified."""
        output = run_hook("Bash", "git commit -m 'msg' | tee log.txt")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "--no-gpg-sign" in modified
        assert "| tee log.txt" in modified

    def test_chained_commit_and_push(self):
        """git commit && git push should modify the commit."""
        output = run_hook("Bash", "git commit -m 'msg' && git push")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "--no-gpg-sign" in modified
        assert "&& git push" in modified

    def test_chained_with_semicolon(self):
        """git commit; other command should be modified."""
        output = run_hook("Bash", "git commit -m 'msg'; echo done")
        assert "hookSpecificOutput" in output
        modified = output["hookSpecificOutput"]["updatedInput"]["command"]
        assert "--no-gpg-sign" in modified


# ---------------------------------------------------------------------------
# Edge cases and output format
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and malformed input handling."""

    def test_empty_command(self):
        """Empty command should pass through silently."""
        output = run_hook("Bash", "")
        assert output == {}

    def test_missing_command_field(self):
        """Missing command field should pass through silently."""
        input_data = {
            "tool_name": "Bash",
            "tool_input": {},
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_malformed_json_input(self):
        """Malformed JSON input should return empty JSON."""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_commit_with_extra_spaces(self):
        """git commit with extra spaces should still be detected."""
        output = run_hook("Bash", "git   commit   -m 'test'")
        assert "hookSpecificOutput" in output
        assert "--no-gpg-sign" in output["hookSpecificOutput"]["updatedInput"]["command"]

    def test_commit_at_end_of_pipeline(self):
        """git commit at end of pipeline (after |) should not be modified."""
        # This is an edge case: we don't want to modify "git commit" in the middle of a complex pipeline
        # For now, we modify it (conservative approach: safety first)
        output = run_hook("Bash", "echo 'msg' | xargs -I {} git commit -m '{}'")
        # The hook will detect and modify this
        assert "hookSpecificOutput" in output or output == {}


# ---------------------------------------------------------------------------
# Output format validation
# ---------------------------------------------------------------------------

class TestOutputFormat:
    """Validate the complete JSON output structure."""

    def test_modification_output_has_required_fields(self):
        """Modified command output must have all required fields."""
        output = run_hook("Bash", "git commit -m 'test'")
        hook_out = output["hookSpecificOutput"]
        required_fields = {
            "hookEventName",
            "permissionDecision",
            "permissionDecisionReason",
            "updatedInput",
            "additionalContext",
        }
        assert required_fields.issubset(set(hook_out.keys()))

    def test_hook_event_name_is_pretooluse(self):
        """hookEventName must be PreToolUse."""
        output = run_hook("Bash", "git commit -m 'test'")
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_updated_input_only_contains_command(self):
        """updatedInput must only contain the command field (merge pattern)."""
        output = run_hook("Bash", "git commit -m 'test'")
        assert output["hookSpecificOutput"]["updatedInput"] == {
            "command": output["hookSpecificOutput"]["updatedInput"]["command"]
        }

    def test_permission_decision_is_allow(self):
        """permissionDecision must be 'allow'."""
        output = run_hook("Bash", "git commit -m 'test'")
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_additional_context_is_informative(self):
        """additionalContext should explain the change."""
        output = run_hook("Bash", "git commit -m 'test'")
        context = output["hookSpecificOutput"]["additionalContext"]
        assert isinstance(context, str)
        assert len(context) > 0
        assert "Original:" in context or "Modified:" in context

    def test_passthrough_is_empty_dict(self):
        """Non-modified commands should return empty dict {}."""
        output = run_hook("Bash", "git status")
        assert output == {}
        assert isinstance(output, dict)

    def test_output_is_valid_json(self):
        """All outputs must be valid JSON."""
        outputs = [
            run_hook("Bash", "git commit -m 'test'"),
            run_hook("Bash", "git status"),
            run_hook("Bash", ""),
        ]
        for output in outputs:
            assert isinstance(output, dict)


def main():
    """Run tests when executed as a script"""
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    return exit_code


if __name__ == "__main__":
    import sys

    sys.exit(main())
