#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
delegation-guard: Block the first solo tool call after delegation, then escalate advisories.

Event: PreToolUse (all tools), SubagentStart, SubagentStop

Purpose: Encourages the main session agent to delegate implementation, research,
and multi-step analysis work to subagents via the Task/Agent tool.

Behavior (PreToolUse):
- When subagent_grace is True (window between Agent/Task call and SubagentStart): pass through
  silently. This covers the race where SubagentStart fires after the subagent's first tool call.
- When subagent_count > 0 (a subagent is active): pass through silently.
  Subagents share the parent's session_id and state file; without this guard they
  would receive confusing "delegate to a subagent" messages during their own work.
- When streak == 0 and block_fired is False (i.e., at the start of a potential solo run):
  Block the incoming non-Task/Agent tool call with permissionDecision: "deny". The blocked
  call does NOT increment the streak — only executed calls count.
- After the block fires (block_fired=True), subsequent non-Task/Agent calls increment streak.
  Escalating advisory messages fire at streak 2, 4, 8, 16, ... (powers of 2 >= 2).
- A Task or Agent call resets streak to 0 and re-arms the block (block_fired=False), and
  sets subagent_grace=True to cover the SubagentStart race.
  ("Agent" is the name used by Claude Code v2.1.63+; "Task" is the legacy name.)
- Exempt tools (e.g. Skill, AskUserQuestion, TaskCreate, ...) are neutral — they neither
  increment streak nor reset it, and do not consume subagent_grace.

Behavior (SubagentStart):
- Increments subagent_count and clears subagent_grace. While count > 0, PreToolUse passes
  through silently. Clearing grace here prevents it from being double-consumed if SubagentStart
  fires before the subagent's first PreToolUse (the normal case).

Behavior (SubagentStop):
- Decrements subagent_count (minimum 0).
- When count returns to 0, the main session's delegation guard resumes.
  The hard block re-arms naturally: the Agent call that spawned the subagent already
  reset streak=0 and block_fired=False, so the next main-session solo call will be blocked.

Known trade-off:
- While ANY subagent is active (count > 0) or subagent_grace is True, the main session's
  guard is ALSO suppressed. If the main session launches a background subagent and continues
  solo work during that window, the guard will not fire. This is considered semantically
  acceptable — the session IS delegating during that window.
- subagent_grace gives one free PreToolUse pass after Agent/Task. If the main session (not
  the subagent) makes the next tool call, it consumes the grace and the block fires on the
  call after that. This is an acceptable trade-off — the session just delegated, so one
  additional free call is semantically reasonable.
- SubagentStop is not guaranteed to fire if a subagent process crashes (e.g. OOM, signal).
  If that happens, subagent_count remains elevated for the rest of the session and the
  guard is permanently suppressed. This is an accepted known limitation — no recovery
  mechanism is implemented. The Claude Code docs state hooks are "deterministic" but do
  not explicitly cover process-level crashes.

State management:
- State files stored in: ~/.claude/hook-state/{session_id}-delegation.json
- Override location: CLAUDE_HOOK_STATE_DIR environment variable
- State fields: streak (int), block_fired (bool), subagent_count (int), subagent_grace (bool)
- /clear generates a new session_id → state resets automatically (old file orphaned but harmless)
- /compact preserves session_id → state persists correctly through compaction
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
    default = {"streak": 0, "block_fired": False, "subagent_count": 0, "subagent_grace": False}
    try:
        state_file = get_state_file(session_id)
        if not state_file.exists():
            return default
        data = json.loads(state_file.read_text())
        if not isinstance(data.get("streak"), int):
            return default
        if not isinstance(data.get("block_fired"), bool):
            data["block_fired"] = False
        if not isinstance(data.get("subagent_count"), int):
            data["subagent_count"] = 0
        if not isinstance(data.get("subagent_grace"), bool):
            data["subagent_grace"] = False
        return {
            "streak": data["streak"],
            "block_fired": data["block_fired"],
            "subagent_count": max(0, data["subagent_count"]),
            "subagent_grace": data["subagent_grace"],
        }
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
        hook_event_name = input_data.get("hook_event_name", "")

        # SubagentStart: increment the reference counter and clear the grace window
        if hook_event_name == "SubagentStart":
            state = read_state(session_id)
            state["subagent_count"] = state["subagent_count"] + 1
            state["subagent_grace"] = False
            write_state(session_id, state)
            print("{}")
            sys.exit(0)

        # SubagentStop: decrement the reference counter (floor at 0)
        if hook_event_name == "SubagentStop":
            state = read_state(session_id)
            state["subagent_count"] = max(0, state["subagent_count"] - 1)
            write_state(session_id, state)
            print("{}")
            sys.exit(0)

        # PreToolUse handling below
        tool_name = input_data.get("tool_name", "")

        # Unknown/missing tool name — pass through silently
        if not tool_name:
            print("{}")
            sys.exit(0)

        state = read_state(session_id)
        streak = state["streak"]
        block_fired = state["block_fired"]
        subagent_count = state["subagent_count"]
        subagent_grace = state["subagent_grace"]

        if tool_name in ("Task", "Agent"):
            # Delegation occurred — reset streak, re-arm the block, and open the grace window.
            # Grace covers the race where SubagentStart fires after the subagent's first PreToolUse.
            # subagent_count is managed by SubagentStart/Stop, not by Tool calls.
            write_state(session_id, {"streak": 0, "block_fired": False, "subagent_count": subagent_count, "subagent_grace": True})
            print("{}")
            sys.exit(0)

        if tool_name in EXEMPT_TOOLS:
            # Neutral — no state change, and does not consume subagent_grace
            print("{}")
            sys.exit(0)

        # Grace window is open (between Agent/Task call and SubagentStart firing).
        # Pass through silently and consume the grace — one free pass for the
        # subagent's first tool call. If SubagentStart fires first it also clears
        # grace, so whichever comes first claims it.
        if subagent_grace:
            write_state(session_id, {"streak": streak, "block_fired": block_fired, "subagent_count": subagent_count, "subagent_grace": False})
            print("{}")
            sys.exit(0)

        # A subagent is active — pass through silently; do not modify state
        if subagent_count > 0:
            print("{}")
            sys.exit(0)

        # Non-Task/Agent, non-exempt tool call
        if streak == 0 and not block_fired:
            # First solo call after a Task or session start: hard stop
            # Blocked call does NOT increment streak — only executed calls count
            write_state(session_id, {"streak": 0, "block_fired": True, "subagent_count": subagent_count, "subagent_grace": False})
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
        write_state(session_id, {"streak": new_streak, "block_fired": block_fired, "subagent_count": subagent_count, "subagent_grace": False})

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
