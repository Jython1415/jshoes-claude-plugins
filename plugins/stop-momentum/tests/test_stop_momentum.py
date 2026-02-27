"""
Unit tests for stop-momentum.py hook

This test suite validates that the hook properly enforces execution momentum
via an ack token handshake on Stop events.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "stop-momentum.py"

# Writable test state directory (redirects away from ~/.claude/hook-state/ for sandbox compat)
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state"

DEFAULT_SESSION_ID = "test-session-stop-123"


def run_hook(
    session_id: str = DEFAULT_SESSION_ID,
    stop_hook_active: bool = False,
    last_assistant_message: str = "",
    cwd: str = "",
    clear_state: bool = True,
) -> dict:
    """
    Helper function to run the stop-momentum hook.

    Args:
        session_id: The session ID to use in the hook input.
        stop_hook_active: Whether stop_hook_active is True in the input.
        last_assistant_message: The last assistant message to include.
        cwd: The working directory to pass to the hook.
        clear_state: Whether to delete the session state file before running.

    Returns:
        Parsed JSON output from the hook.
    """
    if clear_state:
        state_file = TEST_STATE_DIR / f"stop-ack-{session_id}"
        if state_file.exists():
            state_file.unlink()

    input_data = {
        "hook_event_name": "Stop",
        "session_id": session_id,
        "stop_hook_active": stop_hook_active,
        "last_assistant_message": last_assistant_message,
        "cwd": cwd,
    }

    env = os.environ.copy()
    env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
    TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode not in [0, 1]:
        raise RuntimeError(f"Hook failed unexpectedly: {result.stderr}")

    return json.loads(result.stdout)


def get_state_token(session_id: str = DEFAULT_SESSION_ID) -> str | None:
    """Read the current ack token from the test state directory."""
    state_file = TEST_STATE_DIR / f"stop-ack-{session_id}"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


class TestStopHookActive:
    """Test that stop_hook_active=True is always allowed."""

    def test_stop_hook_active_returns_empty(self):
        """When stop_hook_active is True, hook should return {} without writing state."""
        output = run_hook(stop_hook_active=True, clear_state=True)
        assert output == {}, "stop_hook_active=True should return {}"

    def test_stop_hook_active_does_not_write_state(self):
        """When stop_hook_active is True, no state file should be written."""
        run_hook(stop_hook_active=True, clear_state=True)
        token = get_state_token()
        assert token is None, "stop_hook_active=True should not write state"


class TestNoExistingState:
    """Test behavior when there is no existing state file."""

    def test_no_state_no_ack_returns_block(self):
        """No state file and no ack in message should return a block decision."""
        output = run_hook(last_assistant_message="I have finished the task.", clear_state=True)
        assert output.get("decision") == "block", "Should block without existing ack"
        assert "reason" in output, "Block response should include reason"
        assert len(output["reason"]) > 0, "Reason should not be empty"

    def test_no_state_writes_ack_token_to_state(self):
        """After blocking, the new ack token should be written to state."""
        run_hook(clear_state=True)
        token = get_state_token()
        assert token is not None, "State file should be created after block"
        assert token.startswith("ACK-"), "Token should start with 'ACK-'"
        assert len(token) == 8, "Token should be 8 chars: 'ACK-' + 4 chars"

    def test_no_state_token_appears_in_reason(self):
        """The generated ack token should appear in the block reason."""
        output = run_hook(clear_state=True)
        token = get_state_token()
        assert token is not None
        assert token in output["reason"], "Generated token should appear in block reason"


class TestValidAck:
    """Test that a valid ack token in the last message allows the stop."""

    def test_valid_ack_returns_empty(self):
        """When last_assistant_message contains the current token, return {}."""
        # First, trigger a block to create a state file
        run_hook(clear_state=True)
        token = get_state_token()
        assert token is not None

        # Now run again with the token in the message
        output = run_hook(
            last_assistant_message=f"Task complete. {token}",
            clear_state=False,
        )
        assert output == {}, "Valid ack in message should allow stop"

    def test_valid_ack_deletes_state_file(self):
        """After a valid ack, the state file should be deleted."""
        # Create state by blocking first
        run_hook(clear_state=True)
        token = get_state_token()
        assert token is not None

        # Provide valid ack
        run_hook(
            last_assistant_message=f"Done. {token}",
            clear_state=False,
        )

        # State file should be gone
        remaining = get_state_token()
        assert remaining is None, "State file should be deleted after valid ack"

    def test_token_only_in_message_is_enough(self):
        """Token appearing anywhere in the message is sufficient."""
        run_hook(clear_state=True)
        token = get_state_token()

        output = run_hook(
            last_assistant_message=token,
            clear_state=False,
        )
        assert output == {}, "Token alone in message should allow stop"


class TestInvalidAck:
    """Test that wrong or missing ack token causes another block."""

    def test_wrong_token_returns_block(self):
        """State file exists but message has wrong token — should block again."""
        run_hook(clear_state=True)
        old_token = get_state_token()
        assert old_token is not None

        output = run_hook(
            last_assistant_message="Task complete. ACK-WRONG",
            clear_state=False,
        )
        assert output.get("decision") == "block", "Wrong token should block"

    def test_wrong_token_generates_new_token(self):
        """After a failed ack, a new token should be written to state."""
        run_hook(clear_state=True)
        old_token = get_state_token()
        assert old_token is not None

        run_hook(
            last_assistant_message="I'm done. ACK-WRONG",
            clear_state=False,
        )
        new_token = get_state_token()
        assert new_token is not None, "New token should be written after wrong ack"
        assert new_token.startswith("ACK-"), "New token should have correct prefix"

    def test_no_ack_in_message_blocks(self):
        """State file exists but no token in message — should block."""
        run_hook(clear_state=True)
        assert get_state_token() is not None

        output = run_hook(
            last_assistant_message="All done, stopping now.",
            clear_state=False,
        )
        assert output.get("decision") == "block", "Missing token should block"


class TestCustomGuidance:
    """Test custom momentum-guide.md integration."""

    def test_custom_guide_used_when_present(self):
        """Block reason should use custom guide content when .claude/momentum-guide.md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            guide_dir = Path(tmpdir) / ".claude"
            guide_dir.mkdir()
            guide_path = guide_dir / "momentum-guide.md"
            custom_text = "PROJECT CUSTOM STOP GUIDANCE: Please verify all acceptance criteria."
            guide_path.write_text(custom_text)

            output = run_hook(cwd=tmpdir, clear_state=True)
            assert output.get("decision") == "block"
            assert custom_text in output["reason"], "Custom guide content should appear in reason"

    def test_default_guidance_used_when_no_guide(self):
        """Block reason should use default guidance when no momentum-guide.md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = run_hook(cwd=tmpdir, clear_state=True)
            assert output.get("decision") == "block"
            assert "EXECUTION MOMENTUM CHECK" in output["reason"], (
                "Default guidance should appear when no custom guide"
            )

    def test_custom_guide_token_appended_correctly(self):
        """Token instruction should be appended after custom guide content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            guide_dir = Path(tmpdir) / ".claude"
            guide_dir.mkdir()
            (guide_dir / "momentum-guide.md").write_text("Custom guidance here.")

            output = run_hook(cwd=tmpdir, clear_state=True)
            token = get_state_token()
            assert token is not None
            assert token in output["reason"], "Token should appear in reason"
            assert "Custom guidance here." in output["reason"], "Custom text should also be present"


class TestGracefulErrorHandling:
    """Test that the hook handles errors gracefully."""

    def test_malformed_json_input_returns_empty(self):
        """Hook should return {} on malformed JSON input."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json at all",
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        assert output == {}, "Malformed JSON should return {}"

    def test_missing_fields_handled_gracefully(self):
        """Hook should handle missing optional fields without crashing."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        input_data = {"session_id": "minimal-session"}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        # Should either block or allow — just not crash
        assert isinstance(output, dict), "Output should be a dict"


class TestOutputFormat:
    """Test output format correctness."""

    def test_allow_output_is_empty_dict(self):
        """Allow output must be exactly {}."""
        run_hook(clear_state=True)
        token = get_state_token()
        output = run_hook(last_assistant_message=token, clear_state=False)
        assert output == {}

    def test_block_output_has_decision_and_reason(self):
        """Block output must have 'decision' and 'reason' keys."""
        output = run_hook(clear_state=True)
        assert "decision" in output
        assert output["decision"] == "block"
        assert "reason" in output
        assert isinstance(output["reason"], str)

    def test_token_format(self):
        """Generated tokens should match ACK-XXXX format."""
        run_hook(clear_state=True)
        token = get_state_token()
        assert token is not None
        assert len(token) == 8
        assert token[:4] == "ACK-"
        # Remaining 4 chars should be uppercase letters/digits
        suffix = token[4:]
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        assert all(c in valid_chars for c in suffix), f"Token suffix '{suffix}' has invalid chars"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
