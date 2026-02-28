"""
Unit tests for log-event.py observer hook

This hook is used for PermissionRequest and Notification events. It is a
no-op observer that outputs {} so run-with-fallback.sh can log the full
event input to JSONL.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "log-event.py"
WRAPPER_PATH = Path(__file__).parent.parent / "hooks" / "run-with-fallback.sh"


def run_hook(stdin_data: str = "{}") -> dict:
    """Run the hook directly via uv run --script and return parsed output."""
    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=stdin_data,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Hook failed: {result.stderr}"
    return json.loads(result.stdout)


def run_via_wrapper(stdin_data: str = "{}", env: dict | None = None) -> dict:
    """Run the hook through run-with-fallback.sh and return parsed output."""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        [str(WRAPPER_PATH), "open", str(HOOK_PATH)],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=merged_env,
    )
    assert result.returncode == 0
    return json.loads(result.stdout.strip().splitlines()[0])


class TestLogEvent:
    """Tests for the log-event observer hook."""

    def test_returns_empty_dict(self):
        """Hook should return {} for any input."""
        output = run_hook('{"session_id": "abc", "hook_event_name": "PermissionRequest"}')
        assert output == {}, "Observer hook must return {}"

    def test_returns_empty_dict_for_notification_input(self):
        """Hook should return {} for Notification-shaped input."""
        output = run_hook(
            '{"session_id": "abc", "hook_event_name": "Notification", '
            '"message": "Claude needs permission", "notification_type": "permission_prompt"}'
        )
        assert output == {}

    def test_returns_empty_dict_for_empty_input(self):
        """Hook should return {} even for minimal input."""
        output = run_hook("{}")
        assert output == {}

    def test_output_is_valid_json(self):
        """Hook output must be valid JSON."""
        output = run_hook("{}")
        assert isinstance(output, dict)

    def test_no_permission_decision_returned(self):
        """Observer hook must not return any permission decision."""
        output = run_hook('{"session_id": "abc", "hook_event_name": "PermissionRequest"}')
        assert "hookSpecificOutput" not in output, "Observer should not return hookSpecificOutput"

    def test_runs_through_wrapper(self):
        """Hook must execute successfully through run-with-fallback.sh."""
        output = run_via_wrapper(
            '{"session_id": "test-session", "hook_event_name": "PermissionRequest"}'
        )
        assert output == {}

    def test_logs_permission_request_when_log_dir_set(self, tmp_path):
        """PermissionRequest input should appear in JSONL log when JSHOES_HOOK_LOG_DIR is set."""
        log_dir = tmp_path / "hook-logs"
        stdin_data = json.dumps(
            {
                "session_id": "perm-session",
                "hook_event_name": "PermissionRequest",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
                "permission_suggestions": [],
            }
        )
        run_via_wrapper(stdin_data, env={"JSHOES_HOOK_LOG_DIR": str(log_dir)})

        log_file = log_dir / "perm-session.jsonl"
        assert log_file.exists(), "Log file should be created for the session"

        entry = json.loads(log_file.read_text().strip())
        assert entry["hook"] == "log-event.py"
        assert entry["input"]["tool_name"] == "Bash"
        assert entry["output"] == {}

    def test_logs_notification_when_log_dir_set(self, tmp_path):
        """Notification input should appear in JSONL log when JSHOES_HOOK_LOG_DIR is set."""
        log_dir = tmp_path / "hook-logs"
        stdin_data = json.dumps(
            {
                "session_id": "notif-session",
                "hook_event_name": "Notification",
                "message": "Claude needs permission",
                "notification_type": "permission_prompt",
            }
        )
        run_via_wrapper(stdin_data, env={"JSHOES_HOOK_LOG_DIR": str(log_dir)})

        log_file = log_dir / "notif-session.jsonl"
        assert log_file.exists()

        entry = json.loads(log_file.read_text().strip())
        assert entry["input"]["notification_type"] == "permission_prompt"
        assert entry["output"] == {}


def main():
    """Run tests when executed as a script"""
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
