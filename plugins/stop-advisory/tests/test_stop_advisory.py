"""
Unit tests for stop-advisory.py hook

This test suite validates that the hook properly implements stop advisory guidance
with optional enforcement via an ack token handshake on Stop events.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "stop-advisory.py"

# Writable test state directory (redirects away from ~/.claude/hook-state/ for sandbox compat)
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state"

DEFAULT_SESSION_ID = "test-session-stop-123"


def run_hook(
    session_id: str = DEFAULT_SESSION_ID,
    stop_hook_active: bool = False,
    last_assistant_message: str = "",
    cwd: str = "",
    clear_state: bool = True,
    env_guidance: str | None = None,
) -> dict:
    """
    Helper function to run the stop-advisory hook.

    Args:
        session_id: The session ID to use in the hook input.
        stop_hook_active: Whether stop_hook_active is True in the input.
        last_assistant_message: The last assistant message to include.
        cwd: The working directory to pass to the hook.
        clear_state: Whether to delete the session state file before running.
        env_guidance: If provided, sets STOP_HOOK_GUIDANCE environment variable.

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
    if env_guidance is not None:
        env["STOP_HOOK_GUIDANCE"] = env_guidance
    else:
        # Remove from env if it was set
        env.pop("STOP_HOOK_GUIDANCE", None)

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


class TestNoGuidanceConfigured:
    """Test behavior when no guidance is configured."""

    def test_no_guidance_configured_allows_stop(self):
        """When no guidance is configured (no env var, no file), hook returns {} (no-op)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # tmpdir has no .claude/stop-guidance.md and no env var
            output = run_hook(cwd=tmpdir, clear_state=True, env_guidance=None)
            assert output == {}, "No guidance should result in no-op (empty dict)"

    def test_no_guidance_does_not_write_state(self):
        """When no guidance, hook should not write state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_hook(cwd=tmpdir, clear_state=True, env_guidance=None)
            token = get_state_token()
            assert token is None, "No guidance should not create state"


class TestEnvVarGuidance:
    """Test STOP_HOOK_GUIDANCE environment variable configuration."""

    def test_env_var_guidance_used(self):
        """Guidance from STOP_HOOK_GUIDANCE env var should appear in block reason."""
        env_text = "CUSTOM STOP GUIDANCE: Please verify your work before stopping."
        output = run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance=env_text,
        )
        assert output.get("decision") == "block"
        assert env_text in output["reason"]

    def test_env_var_overrides_file(self):
        """STOP_HOOK_GUIDANCE env var should take priority over .claude/stop-guidance.md file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file
            guide_dir = Path(tmpdir) / ".claude"
            guide_dir.mkdir()
            file_text = "FILE GUIDANCE: This is from the file."
            (guide_dir / "stop-guidance.md").write_text(file_text)

            # But set env var with different text
            env_text = "ENV GUIDANCE: This is from the env var."
            output = run_hook(
                cwd=tmpdir,
                clear_state=True,
                env_guidance=env_text,
            )

            assert output.get("decision") == "block"
            # Env var text should be in reason
            assert env_text in output["reason"]
            # File text should NOT be in reason
            assert file_text not in output["reason"]


class TestFileGuidance:
    """Test .claude/stop-guidance.md file configuration."""

    def test_file_guidance_used(self):
        """Guidance from .claude/stop-guidance.md file should appear in block reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            guide_dir = Path(tmpdir) / ".claude"
            guide_dir.mkdir()
            custom_text = "PROJECT CUSTOM STOP GUIDANCE: Please verify all acceptance criteria."
            (guide_dir / "stop-guidance.md").write_text(custom_text)

            output = run_hook(cwd=tmpdir, clear_state=True, env_guidance=None)
            assert output.get("decision") == "block"
            assert custom_text in output["reason"]

    def test_file_guidance_token_appended(self):
        """Token instruction should be appended after file guidance content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            guide_dir = Path(tmpdir) / ".claude"
            guide_dir.mkdir()
            (guide_dir / "stop-guidance.md").write_text("Custom guidance here.")

            output = run_hook(cwd=tmpdir, clear_state=True, env_guidance=None)
            token = get_state_token()
            assert token is not None
            assert token in output["reason"]
            assert "Custom guidance here." in output["reason"]


class TestAckTokenHandshake:
    """Test the ack token handshake mechanism when guidance is configured."""

    def test_block_creates_ack_token(self):
        """When blocking (guidance configured), hook should create ack token in state."""
        output = run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        assert output.get("decision") == "block"
        token = get_state_token()
        assert token is not None
        assert token.startswith("ACK-")
        assert len(token) == 8

    def test_token_in_block_reason(self):
        """Generated ack token should appear in block reason."""
        output = run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()
        assert token is not None
        assert token in output["reason"]

    def test_valid_ack_allows_stop(self):
        """When last_assistant_message contains the ack token, allow stop."""
        # First call creates token and state
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()
        assert token is not None

        # Second call with token in message should allow
        output = run_hook(
            last_assistant_message=f"Task complete. {token}",
            clear_state=False,
            env_guidance="Some guidance",
        )
        assert output == {}

    def test_valid_ack_deletes_state(self):
        """After valid ack, state file should be deleted."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()

        run_hook(
            last_assistant_message=f"Done. {token}",
            clear_state=False,
            env_guidance="Some guidance",
        )
        remaining = get_state_token()
        assert remaining is None

    def test_token_alone_in_message_sufficient(self):
        """Token appearing alone in message is sufficient for ack."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()

        output = run_hook(
            last_assistant_message=token,
            clear_state=False,
            env_guidance="Some guidance",
        )
        assert output == {}

    def test_wrong_token_blocks_again(self):
        """Wrong or missing token should block again."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )

        output = run_hook(
            last_assistant_message="Task complete. ACK-WRONG",
            clear_state=False,
            env_guidance="Some guidance",
        )
        assert output.get("decision") == "block"

    def test_no_token_in_message_blocks(self):
        """No token in message should block again."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )

        output = run_hook(
            last_assistant_message="All done, stopping now.",
            clear_state=False,
            env_guidance="Some guidance",
        )
        assert output.get("decision") == "block"

    def test_wrong_token_generates_new_token(self):
        """After wrong ack, a new token should be written."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        old_token = get_state_token()

        run_hook(
            last_assistant_message="I'm done. ACK-WRONG",
            clear_state=False,
            env_guidance="Some guidance",
        )
        new_token = get_state_token()
        assert new_token is not None
        assert new_token.startswith("ACK-")
        # Most likely different (could theoretically be same but very unlikely)
        # Just verify it's valid


class TestOutputFormat:
    """Test output format correctness."""

    def test_allow_output_is_empty_dict(self):
        """Allow output must be exactly {}."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()
        output = run_hook(
            last_assistant_message=token,
            clear_state=False,
            env_guidance="Some guidance",
        )
        assert output == {}

    def test_block_output_has_decision_and_reason(self):
        """Block output must have 'decision' and 'reason' keys."""
        output = run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        assert "decision" in output
        assert output["decision"] == "block"
        assert "reason" in output
        assert isinstance(output["reason"], str)

    def test_token_format(self):
        """Generated tokens should match ACK-XXXX format."""
        run_hook(
            cwd="/tmp",
            clear_state=True,
            env_guidance="Some guidance",
        )
        token = get_state_token()
        assert token is not None
        assert len(token) == 8
        assert token[:4] == "ACK-"
        suffix = token[4:]
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert all(c in valid_chars for c in suffix)


class TestGracefulErrorHandling:
    """Test that the hook handles errors gracefully."""

    def test_malformed_json_input_returns_empty(self):
        """Hook should return {} on malformed JSON input."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        env.pop("STOP_HOOK_GUIDANCE", None)
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json at all",
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_fields_handled_gracefully(self):
        """Hook should handle missing optional fields without crashing."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        env.pop("STOP_HOOK_GUIDANCE", None)
        input_data = {"session_id": "minimal-session"}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        # No guidance configured, so should be no-op
        assert output == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
