"""
Unit tests for haiku-enforce.py hook (PreToolUse)

Behavioral model:
- Agent tool calls: hook outputs updatedInput with model: "haiku",
  permissionDecision: "allow", and additionalContext.
- Non-Agent tool calls: hook outputs {} (silent pass-through).
- Malformed input: hook outputs {} gracefully.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "haiku-enforce.py"


def run_hook(tool_name: str, tool_input: dict | None = None) -> dict:
    """Run the haiku-enforce hook and return parsed JSON output."""
    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input or {},
        "session_id": "test-session-haiku-123",
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
# Agent tool override
# ---------------------------------------------------------------------------

class TestAgentOverride:
    """Agent tool calls must have model overridden to haiku."""

    def test_agent_call_returns_updated_input(self):
        """Agent call must include updatedInput with model: haiku."""
        output = run_hook("Agent")
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("updatedInput", {}).get("model") == "haiku"

    def test_agent_call_allows_execution(self):
        """Agent call must include permissionDecision: allow."""
        output = run_hook("Agent")
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("permissionDecision") == "allow"

    def test_agent_call_includes_additional_context(self):
        """Agent call must include additionalContext informing Claude."""
        output = run_hook("Agent")
        hook_out = output["hookSpecificOutput"]
        assert isinstance(hook_out.get("additionalContext"), str)
        assert len(hook_out["additionalContext"]) > 0

    def test_agent_call_includes_hook_event_name(self):
        """Output must include hookEventName: PreToolUse."""
        output = run_hook("Agent")
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"

    def test_agent_call_includes_permission_reason(self):
        """Output must include a non-empty permissionDecisionReason."""
        output = run_hook("Agent")
        hook_out = output["hookSpecificOutput"]
        assert isinstance(hook_out.get("permissionDecisionReason"), str)
        assert len(hook_out["permissionDecisionReason"]) > 0

    def test_agent_call_with_existing_model_overrides(self):
        """Agent call with an existing model value must still override to haiku."""
        output = run_hook("Agent", tool_input={"model": "opus", "prompt": "test"})
        hook_out = output["hookSpecificOutput"]
        assert hook_out["updatedInput"]["model"] == "haiku"

    def test_agent_call_with_haiku_model_still_outputs(self):
        """Agent call already set to haiku still gets the override (idempotent)."""
        output = run_hook("Agent", tool_input={"model": "haiku", "prompt": "test"})
        hook_out = output["hookSpecificOutput"]
        assert hook_out["updatedInput"]["model"] == "haiku"

    def test_updated_input_only_contains_model(self):
        """updatedInput must only contain the model field (merge, don't replace)."""
        output = run_hook("Agent", tool_input={"prompt": "test", "description": "test"})
        hook_out = output["hookSpecificOutput"]
        assert hook_out["updatedInput"] == {"model": "haiku"}


# ---------------------------------------------------------------------------
# Non-Agent tools (defensive — matcher should prevent these)
# ---------------------------------------------------------------------------

class TestNonAgentTools:
    """Non-Agent tool calls must pass through silently."""

    def test_bash_is_silent(self):
        output = run_hook("Bash")
        assert output == {}

    def test_read_is_silent(self):
        output = run_hook("Read")
        assert output == {}

    def test_write_is_silent(self):
        output = run_hook("Write")
        assert output == {}

    def test_empty_tool_name_is_silent(self):
        output = run_hook("")
        assert output == {}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Hook must handle bad inputs gracefully."""

    def test_malformed_json_returns_empty(self):
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}

    def test_missing_tool_name_returns_empty(self):
        input_data = {"session_id": "test-minimal"}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        assert output == {}


# ---------------------------------------------------------------------------
# Output format validation
# ---------------------------------------------------------------------------

class TestOutputFormat:
    """Validate the complete JSON output structure."""

    def test_agent_output_is_valid_json(self):
        """Output must be valid JSON."""
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {},
            "session_id": "test-format",
        }
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, dict)

    def test_agent_output_has_all_required_fields(self):
        """Agent output must have all required hookSpecificOutput fields."""
        output = run_hook("Agent")
        hook_out = output["hookSpecificOutput"]
        required_fields = {"hookEventName", "permissionDecision", "permissionDecisionReason", "updatedInput", "additionalContext"}
        assert required_fields.issubset(set(hook_out.keys()))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
