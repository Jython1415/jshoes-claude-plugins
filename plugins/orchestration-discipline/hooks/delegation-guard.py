#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
delegation-guard: Block the first solo tool call after delegation, then escalate advisories.

Event: PreToolUse (all tools)

Purpose: Encourages the main session agent to delegate implementation, research,
and multi-step analysis work to subagents via the Task/Agent tool.

Behavior:
- Subagent contexts (transcript_path contains "/subagents/") are skipped entirely.
  Subagents share the parent's session_id and state file; without this guard they
  would receive confusing "delegate to a subagent" messages during their own work.
- When streak == 0 and block_fired is False (i.e., at the start of a potential solo run):
  Block the incoming non-Task/Agent tool call with permissionDecision: "deny". The blocked
  call does NOT increment the streak — only executed calls count.
- After the block fires (block_fired=True), subsequent non-Task/Agent calls increment streak.
  Escalating advisory messages fire at streak 2, 4, 8, 16, ... (powers of 2 >= 2).
- A Task or Agent call resets streak to 0 and re-arms the block (block_fired=False).
  ("Agent" is the name used by Claude Code v2.1.63+; "Task" is the legacy name.)
- Exempt tools (e.g. Skill, AskUserQuestion, TaskCreate, ...) are neutral — they neither
  increment streak nor reset it.

State management:
- State files stored in: ~/.claude/hook-state/{session_id}-delegation.json
- Override location: CLAUDE_HOOK_STATE_DIR environment variable
- State fields: streak (int), block_fired (bool)
"""
import json
import os
import sys
from pathlib import Path

# State directory location
_state_dir_env = os.environ.get("CLAUDE_HOOK_STATE_DIR")
STATE_DIR = Path(_state_dir_env) if _state_dir_env else Path.home() / ".claude" / "hook-state"

# Tools that don't affect streak counting (neither increment nor reset)
EXEMPT_TOOLS = {
    "Skill",
    "AskUserQuestion",
    "TaskCreate",
    "TaskUpdate",
    "TaskGet",
    "TaskList",
    "EnterPlanMode",
    "ExitPlanMode",
}


def get_state_file(session_id: str) -> Path:
    """Return the path to the state file for this session."""
    return STATE_DIR / f"{session_id}-delegation.json"


def read_state(session_id: str) -> dict:
    """Read delegation state for this session. Returns default state if not found or corrupt."""
    default = {"streak": 0, "block_fired": False}
    try:
        state_file = get_state_file(session_id)
        if not state_file.exists():
            return default
        data = json.loads(state_file.read_text())
        if not isinstance(data.get("streak"), int):
            return default
        if not isinstance(data.get("block_fired"), bool):
            data["block_fired"] = False
        return {"streak": data["streak"], "block_fired": data["block_fired"]}
    except Exception:
        return default


def write_state(session_id: str, state: dict) -> None:
    """Write delegation state for this session."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        get_state_file(session_id).write_text(json.dumps(state))
    except Exception as e:
        print(f"Warning: Could not write delegation state: {e}", file=sys.stderr)


def is_backoff_point(streak: int) -> bool:
    """Return True if streak is a power of 2 >= 2 (i.e., 2, 4, 8, 16, ...)."""
    return streak >= 2 and (streak & (streak - 1)) == 0


def build_block_message() -> str:
    """Build the one-time hard-stop block message for streak=0."""
    return (
        "Delegation check: you are about to make a solo tool call. "
        "This is a one-time hard stop — delegate to a Task subagent instead. "
        "After this, reminders will be advisory-only (non-blocking). "
        "Use the Task tool to spawn a subagent, then synthesize what it returns."
    )


def build_advisory_message(streak: int) -> str:
    """Build an escalating advisory message for the given streak level."""
    if streak <= 2:
        tone = (
            f"Delegation reminder [streak={streak}]: you have made {streak} consecutive "
            f"solo tool calls. Consider delegating this work to a Task subagent."
        )
    elif streak <= 4:
        tone = (
            f"Delegation advisory [streak={streak}]: {streak} consecutive solo tool calls. "
            f"Main session context is non-renewable — push reads, research, and implementation "
            f"to subagents. Use the Task tool."
        )
    elif streak <= 8:
        tone = (
            f"Delegation warning [streak={streak}]: {streak} consecutive solo tool calls. "
            f"Main session capacity is depleting. This work belongs in a subagent. "
            f"Spawn a Task now and synthesize the result."
        )
    else:
        tone = (
            f"DELEGATION CRITICAL [streak={streak}]: {streak} consecutive solo tool calls. "
            f"You are consuming irreplaceable main session context. Stop and delegate immediately. "
            f"Use the Task tool to spawn a subagent for any further work."
        )
    return tone


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "")
        tool_name = input_data.get("tool_name", "")
        transcript_path = input_data.get("transcript_path", "")

        # Subagent transcripts are stored at .../subagents/agent-{id}.jsonl
        # Skip the delegation guard entirely in subagent contexts
        if "/subagents/" in transcript_path:
            print("{}")
            sys.exit(0)

        # Unknown/missing tool name — pass through silently
        if not tool_name:
            print("{}")
            sys.exit(0)

        state = read_state(session_id)
        streak = state["streak"]
        block_fired = state["block_fired"]

        if tool_name in ("Task", "Agent"):
            # Delegation occurred — reset streak and re-arm the block
            write_state(session_id, {"streak": 0, "block_fired": False})
            print("{}")
            sys.exit(0)

        if tool_name in EXEMPT_TOOLS:
            # Neutral — no state change
            print("{}")
            sys.exit(0)

        # Non-Task/Agent, non-exempt tool call
        if streak == 0 and not block_fired:
            # First solo call after a Task or session start: hard stop
            # Blocked call does NOT increment streak — only executed calls count
            write_state(session_id, {"streak": 0, "block_fired": True})
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": build_block_message(),
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Block already fired — this call executes; increment streak
        new_streak = streak + 1
        write_state(session_id, {"streak": new_streak, "block_fired": block_fired})

        if is_backoff_point(new_streak):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": build_advisory_message(new_streak),
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        print("{}")
        sys.exit(0)

    except Exception as e:
        print(f"Error in delegation-guard hook: {e}", file=sys.stderr)
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
