"""
Unit tests for delegation-guard.py hook (PreToolUse)

Behavioral model:
- Subagent contexts (subagent_count > 0 in state, set by SubagentStart/Stop events): hook passes through silently,
  no state changes. Subagents share the parent's session_id/state file; the guard does not
  apply to them.
- First solo call (streak==0, block_fired==False): BLOCK via permissionDecision: "deny".
  Blocked call does NOT increment streak.
- After block fires (block_fired=True): subsequent non-Task/Agent calls increment streak.
  Escalating advisory fires at streak 2, 4, 8, 16, ... (powers of 2 >= 2).
- Task or Agent call: resets streak to 0 and re-arms block (block_fired=False).
  ("Agent" is the name used by Claude Code v2.1.63+; "Task" is the legacy name.)
- Exempt tools (Skill, AskUserQuestion, TaskCreate, etc.): neutral, no state change.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "delegation-guard.py"

# Writable test state directory (redirects away from ~/.claude/hook-state/ for sandbox compat)
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state-delegation"

DEFAULT_SESSION_ID = "test-session-delegation-123"


def run_hook(
    tool_name: str,
    session_id: str = DEFAULT_SESSION_ID,
    clear_state: bool = True,
    transcript_path: str = "",
) -> dict:
    """Run the delegation-guard hook and return parsed JSON output."""
    if clear_state:
        state_file = TEST_STATE_DIR / f"{session_id}-delegation.json"
        if state_file.exists():
            state_file.unlink()

    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {},
        "session_id": session_id,
        "transcript_path": transcript_path,
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


def get_state(session_id: str = DEFAULT_SESSION_ID) -> dict | None:
    """Read the current delegation state from the test state directory."""
    state_file = TEST_STATE_DIR / f"{session_id}-delegation.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return None


def run_event(
    event_name: str,
    session_id: str = DEFAULT_SESSION_ID,
    clear_state: bool = False,
) -> dict:
    """Run the delegation-guard hook with a lifecycle event (SubagentStart/SubagentStop)."""
    if clear_state:
        state_file = TEST_STATE_DIR / f"{session_id}-delegation.json"
        if state_file.exists():
            state_file.unlink()

    input_data = {
        "hook_event_name": event_name,
        "session_id": session_id,
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


# ---------------------------------------------------------------------------
# Block behavior (streak=0 → permissionDecision: deny)
# ---------------------------------------------------------------------------

class TestBlockBehavior:
    """First solo tool call blocks; blocked call does not increment streak."""

    def test_first_non_task_call_blocks(self):
        """First non-Task call (streak=0, block_fired=False) must block."""
        output = run_hook("Bash", clear_state=True)
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("permissionDecision") == "deny"
        assert "permissionDecisionReason" in hook_out

    def test_block_does_not_increment_streak(self):
        """Streak must stay 0 after the block fires."""
        run_hook("Bash", clear_state=True)
        state = get_state()
        assert state["streak"] == 0

    def test_block_sets_block_fired(self):
        """block_fired must be True after the block fires."""
        run_hook("Bash", clear_state=True)
        state = get_state()
        assert state["block_fired"] is True

    def test_block_fires_only_once_per_run(self):
        """After block fires, subsequent non-Task calls must NOT block again."""
        run_hook("Bash", clear_state=True)          # block fires
        output = run_hook("Bash", clear_state=False) # block already fired
        hook_out = output.get("hookSpecificOutput", {})
        assert hook_out.get("permissionDecision") != "deny", (
            "Block must not fire twice in the same run"
        )

    def test_block_message_mentions_advisory_only_future(self):
        """Block message must inform Claude that future reminders are advisory-only."""
        output = run_hook("Bash", clear_state=True)
        reason = output["hookSpecificOutput"]["permissionDecisionReason"]
        assert isinstance(reason, str) and len(reason) > 0


# ---------------------------------------------------------------------------
# Streak counting (only executed calls increment)
# ---------------------------------------------------------------------------

class TestStreakCounting:
    """Streak counts only calls that execute (after the block has fired)."""

    def test_first_executed_call_sets_streak_to_1(self):
        """Non-Task call after the block should set streak to 1."""
        run_hook("Bash", clear_state=True)          # block fires; streak stays 0
        run_hook("Bash", clear_state=False)          # executes; streak → 1
        state = get_state()
        assert state["streak"] == 1

    def test_streak_accumulates_across_calls(self):
        """Streak should accumulate correctly across multiple executed calls."""
        run_hook("Bash", clear_state=True)   # block fires; streak=0
        run_hook("Bash", clear_state=False)  # streak → 1
        run_hook("Read", clear_state=False)  # streak → 2
        run_hook("Grep", clear_state=False)  # streak → 3
        state = get_state()
        assert state["streak"] == 3

    def test_task_call_resets_streak_to_zero(self):
        """Task call must reset streak to 0."""
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Bash", clear_state=False)  # streak → 1
        run_hook("Task", clear_state=False)  # reset
        state = get_state()
        assert state["streak"] == 0

    def test_task_call_resets_block_fired(self):
        """Task call must re-arm the block (block_fired=False)."""
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Task", clear_state=False)  # reset
        state = get_state()
        assert state["block_fired"] is False

    def test_block_re_arms_after_task_reset(self):
        """After a Task reset, the next solo call must block again."""
        run_hook("Bash", clear_state=True)   # first block
        run_hook("Task", clear_state=False)  # reset
        output = run_hook("Bash", clear_state=False)  # should block again
        assert output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# ---------------------------------------------------------------------------
# Escalating advisories (streak 2, 4, 8, 16)
# ---------------------------------------------------------------------------

class TestEscalatingAdvisories:
    """Advisory fires at streak 2, 4, 8, 16 (powers of 2 >= 2); silent at all others."""

    def _reach_streak(self, n: int) -> dict:
        """Advance to the given streak level and return the output from the final call."""
        run_hook("Bash", clear_state=True)   # block fires; streak=0
        output = {}
        for _ in range(n):
            output = run_hook("Bash", clear_state=False)
        return output

    def test_advisory_fires_at_streak_2(self):
        """Advisory must fire when streak reaches 2."""
        output = self._reach_streak(2)
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert "additionalContext" in hook_out
        assert hook_out.get("permissionDecision") != "deny"

    def test_advisory_fires_at_streak_4(self):
        """Advisory must fire when streak reaches 4."""
        output = self._reach_streak(4)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_advisory_fires_at_streak_8(self):
        """Advisory must fire when streak reaches 8."""
        output = self._reach_streak(8)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_advisory_fires_at_streak_16(self):
        """Advisory must fire when streak reaches 16."""
        output = self._reach_streak(16)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_silent_at_streak_1(self):
        """First executed call (streak=1) must be silent."""
        run_hook("Bash", clear_state=True)          # block fires
        output = run_hook("Bash", clear_state=False) # streak → 1
        assert output == {}, f"Expected silent at streak=1, got: {output}"

    def test_silent_at_streak_3(self):
        """Streak=3 is not a power of 2, must be silent."""
        output = self._reach_streak(3)
        assert output == {}, f"Expected silent at streak=3, got: {output}"

    def test_silent_at_streak_5(self):
        """Streak=5 is not a power of 2, must be silent."""
        output = self._reach_streak(5)
        assert output == {}, f"Expected silent at streak=5, got: {output}"

    def test_silent_at_streak_6(self):
        """Streak=6 is not a power of 2, must be silent."""
        output = self._reach_streak(6)
        assert output == {}, f"Expected silent at streak=6, got: {output}"

    def test_advisory_fires_again_after_task_reset(self):
        """After a Task reset, advisory schedule restarts from the beginning."""
        # First run: advance past streak=2
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Bash", clear_state=False)  # streak=1
        run_hook("Bash", clear_state=False)  # streak=2 → advisory
        # Reset via Task
        run_hook("Task", clear_state=False)
        # Second run: advisory must fire again at streak=2
        run_hook("Bash", clear_state=False)  # block fires again (re-armed)
        run_hook("Bash", clear_state=False)  # streak=1
        output = run_hook("Bash", clear_state=False)  # streak=2 → advisory again
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]


# ---------------------------------------------------------------------------
# Exempt tools
# ---------------------------------------------------------------------------

class TestExemptTools:
    """Exempt tools are neutral: they don't increment or reset streak."""

    def test_exempt_tools_do_not_trigger_block(self):
        """Exempt tools must not trigger the block, even with streak=0."""
        for tool in ("Skill", "AskUserQuestion", "TaskCreate", "TaskUpdate",
                     "TaskGet", "TaskList", "EnterPlanMode", "ExitPlanMode"):
            output = run_hook(tool, clear_state=True)
            assert output == {}, f"Exempt tool {tool} should not trigger block"

    def test_exempt_tools_do_not_increment_streak(self):
        """Exempt tools must not increment the streak after block fires."""
        run_hook("Bash", clear_state=True)          # block fires
        run_hook("Skill", clear_state=False)         # neutral
        run_hook("AskUserQuestion", clear_state=False)  # neutral
        state = get_state()
        assert state["streak"] == 0, "Exempt tools should not increment streak"

    def test_exempt_tools_do_not_reset_streak(self):
        """Exempt tools must not reset a non-zero streak."""
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Bash", clear_state=False)  # streak → 1
        run_hook("Skill", clear_state=False) # neutral
        state = get_state()
        assert state["streak"] == 1, "Exempt tool should not reset streak"

    def test_exempt_tool_does_not_re_arm_block(self):
        """Exempt tool after block fires must not reset block_fired."""
        run_hook("Bash", clear_state=True)   # block fires; block_fired=True
        run_hook("Skill", clear_state=False) # neutral
        state = get_state()
        assert state["block_fired"] is True, "Exempt tool should not re-arm block"


# ---------------------------------------------------------------------------
# Task / Agent call behavior
# ---------------------------------------------------------------------------

class TestTaskCall:
    """Task and Agent calls reset the delegation state and re-arm the block."""

    def test_task_call_is_silent(self):
        """Task call must return empty output (no advisory or block)."""
        run_hook("Bash", clear_state=True)  # set up some state
        output = run_hook("Task", clear_state=False)
        assert output == {}, f"Task call should be silent, got: {output}"

    def test_agent_call_is_silent(self):
        """Agent call must return empty output (no advisory or block)."""
        run_hook("Bash", clear_state=True)  # set up some state
        output = run_hook("Agent", clear_state=False)
        assert output == {}, f"Agent call should be silent, got: {output}"

    def test_task_call_with_fresh_state_is_silent(self):
        """Task call on fresh session must be silent."""
        output = run_hook("Task", clear_state=True)
        assert output == {}

    def test_agent_call_with_fresh_state_is_silent(self):
        """Agent call on fresh session must be silent."""
        output = run_hook("Agent", clear_state=True)
        assert output == {}

    def test_multiple_task_calls_keep_streak_at_zero(self):
        """Multiple consecutive Task calls must keep streak at 0."""
        run_hook("Task", clear_state=True)
        run_hook("Task", clear_state=False)
        run_hook("Task", clear_state=False)
        state = get_state()
        assert state["streak"] == 0
        assert state["block_fired"] is False

    def test_multiple_agent_calls_keep_streak_at_zero(self):
        """Multiple consecutive Agent calls must keep streak at 0."""
        run_hook("Agent", clear_state=True)
        run_hook("Agent", clear_state=False)
        run_hook("Agent", clear_state=False)
        state = get_state()
        assert state["streak"] == 0
        assert state["block_fired"] is False


class TestStreakCountingWithAgent:
    """Agent tool resets streak and re-arms block, same as Task."""

    def test_agent_call_resets_streak_to_zero(self):
        """Agent call must reset streak to 0."""
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Bash", clear_state=False)  # streak → 1
        run_hook("Agent", clear_state=False)  # reset
        state = get_state()
        assert state["streak"] == 0

    def test_agent_call_resets_block_fired(self):
        """Agent call must re-arm the block (block_fired=False)."""
        run_hook("Bash", clear_state=True)    # block fires
        run_hook("Agent", clear_state=False)  # reset
        state = get_state()
        assert state["block_fired"] is False

    def test_block_re_arms_after_agent_reset(self):
        """After an Agent reset, the next solo call must block again."""
        run_hook("Bash", clear_state=True)    # first block
        run_hook("Agent", clear_state=False)  # reset
        output = run_hook("Bash", clear_state=False)  # should block again
        assert output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# ---------------------------------------------------------------------------
# Subagent counter (SubagentStart/Stop reference counter)
# ---------------------------------------------------------------------------

class TestSubagentCounter:
    """SubagentStart/Stop events manage the reference counter; PreToolUse is silent when count > 0."""

    def test_subagent_start_increments_count(self):
        """SubagentStart must increment subagent_count in state."""
        run_hook("Bash", clear_state=True)  # set up some state (block fires)
        run_event("SubagentStart")
        state = get_state()
        assert state["subagent_count"] == 1

    def test_subagent_stop_decrements_count(self):
        """SubagentStop must decrement subagent_count in state."""
        run_hook("Bash", clear_state=True)  # fresh state
        run_event("SubagentStart")
        run_event("SubagentStop")
        state = get_state()
        assert state["subagent_count"] == 0

    def test_subagent_stop_floor_at_zero(self):
        """SubagentStop on a zero count must not go negative."""
        run_hook("Bash", clear_state=True)
        run_event("SubagentStop")  # count was already 0
        state = get_state()
        assert state["subagent_count"] == 0

    def test_pretooluse_silent_when_subagent_active(self):
        """PreToolUse must pass through silently when subagent_count > 0."""
        run_hook("Bash", clear_state=True)   # block fires, block_fired=True
        run_event("SubagentStart")           # subagent_count -> 1
        # Next Bash call should be silent (not block again)
        output = run_hook("Bash", clear_state=False)
        assert output == {}, f"Expected silent while subagent active, got: {output}"

    def test_pretooluse_does_not_modify_state_when_subagent_active(self):
        """PreToolUse must not modify streak or block_fired when subagent is active."""
        run_hook("Bash", clear_state=True)   # block fires, block_fired=True, streak=0
        run_event("SubagentStart")           # subagent_count -> 1
        state_before = get_state()
        run_hook("Bash", clear_state=False)  # should be a no-op
        state_after = get_state()
        assert state_before["streak"] == state_after["streak"]
        assert state_before["block_fired"] == state_after["block_fired"]

    def test_block_resumes_after_subagent_stops(self):
        """After SubagentStop returns count to 0, PreToolUse block must resume."""
        run_hook("Bash", clear_state=True)   # block fires, re-arms
        run_hook("Agent", clear_state=False) # reset: streak=0, block_fired=False
        run_event("SubagentStart")           # subagent_count -> 1
        run_hook("Bash", clear_state=False)  # silent (subagent active)
        run_event("SubagentStop")            # subagent_count -> 0
        output = run_hook("Bash", clear_state=False)  # should block again
        assert output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", (
            "Block must re-arm after subagent_count returns to 0"
        )

    def test_multiple_subagents_handled_correctly(self):
        """Multiple concurrent SubagentStart calls require matching SubagentStops to resume."""
        run_hook("Bash", clear_state=True)   # block fires
        run_hook("Agent", clear_state=False) # reset
        run_event("SubagentStart")           # count -> 1
        run_event("SubagentStart")           # count -> 2
        run_hook("Bash", clear_state=False)  # silent
        run_event("SubagentStop")            # count -> 1 (still active)
        output = run_hook("Bash", clear_state=False)  # still silent
        assert output == {}, "Guard must remain suppressed until all subagents complete"
        run_event("SubagentStop")            # count -> 0
        output = run_hook("Bash", clear_state=False)  # should block now
        assert output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def test_subagent_events_are_silent(self):
        """SubagentStart and SubagentStop must return {} (no blocks or advisories)."""
        run_hook("Bash", clear_state=True)
        output_start = run_event("SubagentStart")
        output_stop = run_event("SubagentStop")
        assert output_start == {}, f"SubagentStart must be silent, got: {output_start}"
        assert output_stop == {}, f"SubagentStop must be silent, got: {output_stop}"

    def test_task_reset_preserves_subagent_count(self):
        """Task/Agent reset must not zero out subagent_count."""
        run_hook("Bash", clear_state=True)
        run_event("SubagentStart")           # count -> 1
        run_hook("Agent", clear_state=False) # reset streak/block_fired
        state = get_state()
        assert state["subagent_count"] == 1, "Task/Agent reset must preserve subagent_count"


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

class TestOutputFormat:
    """Validate JSON output structure."""

    def test_silent_output_is_empty_dict(self):
        """Silent output must be exactly {}."""
        run_hook("Bash", clear_state=True)          # block fires
        output = run_hook("Bash", clear_state=False) # streak=1, silent
        assert output == {}

    def test_block_output_structure(self):
        """Block output must have hookSpecificOutput with permissionDecision: deny."""
        output = run_hook("Bash", clear_state=True)
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"
        assert hook_out.get("permissionDecision") == "deny"
        assert isinstance(hook_out.get("permissionDecisionReason"), str)
        assert len(hook_out["permissionDecisionReason"]) > 0

    def test_advisory_output_structure(self):
        """Advisory output must have hookSpecificOutput with additionalContext."""
        run_hook("Bash", clear_state=True)   # block
        run_hook("Bash", clear_state=False)  # streak=1
        output = run_hook("Bash", clear_state=False)  # streak=2 → advisory
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert hook_out.get("hookEventName") == "PreToolUse"
        assert isinstance(hook_out.get("additionalContext"), str)
        assert len(hook_out["additionalContext"]) > 0
        assert "permissionDecision" not in hook_out


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------

class TestStateFile:
    """State file is created, has the correct schema, and persists correctly."""

    def test_state_file_created_on_first_call(self):
        """State file must be created on first hook call."""
        run_hook("Bash", clear_state=True)
        state = get_state()
        assert state is not None

    def test_state_has_correct_fields(self):
        """State file must contain streak (int), block_fired (bool), and subagent_count (int)."""
        run_hook("Bash", clear_state=True)
        state = get_state()
        assert isinstance(state["streak"], int)
        assert isinstance(state["block_fired"], bool)
        assert isinstance(state["subagent_count"], int)

    def test_state_does_not_contain_legacy_fields(self):
        """State must not contain deprecated fields (offset, task_calls, advisory_fired)."""
        run_hook("Bash", clear_state=True)
        state = get_state()
        assert "offset" not in state
        assert "task_calls" not in state
        assert "advisory_fired" not in state


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestGracefulErrorHandling:
    """Hook must handle bad inputs without crashing."""

    def test_malformed_json_returns_empty(self):
        """Hook must return {} on malformed JSON input."""
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
        assert output == {}

    def test_missing_session_id_handled(self):
        """Hook must handle a missing session_id without crashing."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        input_data = {"tool_name": "Bash", "tool_input": {}}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )
        assert json.loads(result.stdout) is not None

    def test_missing_tool_name_returns_empty(self):
        """Hook must pass through silently when tool_name is missing or empty."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        input_data = {"session_id": "test-minimal"}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        assert output == {}, "Missing tool_name should return {} (not a block)"

    def test_corrupt_state_file_recovered(self):
        """Hook must recover from a corrupt state file."""
        TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = TEST_STATE_DIR / f"{DEFAULT_SESSION_ID}-delegation.json"
        state_file.write_text("this is not json {{{{")
        output = run_hook("Bash", clear_state=False)
        assert isinstance(output, dict)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
