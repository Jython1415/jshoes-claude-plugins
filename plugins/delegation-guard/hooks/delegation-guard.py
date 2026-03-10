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
- When subagent_count > 0 (a subagent is active): pass through silently.
  Subagents share the parent's session_id and state file; without this guard they
  would receive confusing "delegate to a subagent" messages during their own work.
- When streak == 0 and block_fired is False (i.e., at the start of a potential solo run):
  - Task/Agent tools: reset streak and re-arm block (always pass through)
  - Exempt tools (e.g. Skill, AskUserQuestion, TaskCreate, ...): neutral, no state change
  - Unblocked tools (Read, Glob, Grep, configurable): set block_fired=True, increment
    streak to 1, fire advisory (never hard-blocked)
  - All other tools: hard-stop with permissionDecision: "deny"
- After the block fires (block_fired=True), all tool calls (normal and unblocked) increment
  streak. Escalating advisory messages fire at Fibonacci numbers >= 2 (2, 3, 5, 8, 13, 21, ...).
  At Fibonacci thresholds >= 5 (5, 8, 13, ...), normal tools are re-blocked (permissionDecision:
  "deny"); unblocked tools receive advisory-only messages at all thresholds.
  Unblocked tools also fire a distinct advisory at streak=1 (only possible on their first call).
- A Task or Agent call resets streak to 0 and re-arms the block (block_fired=False).
  ("Agent" is the name used by Claude Code v2.1.63+; "Task" is the legacy name.)

Behavior (SubagentStart):
- Increments subagent_count. While count > 0, PreToolUse passes through silently.

Behavior (SubagentStop):
- Decrements subagent_count (minimum 0).
- When count returns to 0, the main session's delegation guard resumes.
  The hard block re-arms naturally: the Agent call that spawned the subagent already
  reset streak=0 and block_fired=False, so the next main-session solo call will be blocked.

Known trade-off:
- While ANY subagent is active (count > 0), the main session's guard is ALSO suppressed.
  If the main session launches a background subagent and continues solo work during that
  window, the guard will not fire. This is considered semantically acceptable — the
  session IS delegating during that window.
- SubagentStop is not guaranteed to fire if a subagent process crashes (e.g. OOM, signal).
  If that happens, subagent_count remains elevated for the rest of the session and the
  guard is permanently suppressed. This is an accepted known limitation — no recovery
  mechanism is implemented. The Claude Code docs state hooks are "deterministic" but do
  not explicitly cover process-level crashes.

State management:
- State files stored in: ~/.claude/hook-state/{session_id}-delegation.json
- Override location: CLAUDE_HOOK_STATE_DIR environment variable
- State fields: streak (int), block_fired (bool), subagent_count (int)
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
    "ToolSearch",
}

# Tools that are never hard-blocked on first call; instead fire advisory at streak=1
UNBLOCKED_TOOLS = {"Read", "Glob", "Grep"}


def load_project_config() -> dict:
    """Load per-project delegation-guard config from .claude/delegation-guard.json.

    Returns a dict with optional 'exempt_tools' and 'unblocked_tools' keys (lists of strings).
    Returns empty dict on file not found, invalid JSON, or missing keys.
    """
    config_path = Path.cwd() / ".claude" / "delegation-guard.json"
    try:
        with open(config_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def get_state_file(session_id: str) -> Path:
    """Return the path to the state file for this session."""
    return STATE_DIR / f"{session_id}-delegation.json"


def read_state(session_id: str) -> dict:
    """Read delegation state for this session. Returns default state if not found or corrupt."""
    default = {"streak": 0, "block_fired": False, "subagent_count": 0}
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
        return {
            "streak": data["streak"],
            "block_fired": data["block_fired"],
            "subagent_count": max(0, data["subagent_count"]),
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
    """Return True if streak is a Fibonacci number >= 2 (i.e., 2, 3, 5, 8, 13, 21, ...)."""
    if streak < 2:
        return False
    a, b = 1, 2
    while b < streak:
        a, b = b, a + b
    return b == streak


DELEGATION_EXAMPLES = (
    "Common tasks that SHOULD be delegated: "
    "codebase exploration (Read/Glob/Grep chains), "
    "implementation work (Edit/Write chains), "
    "git workflows (status/diff/log/commit sequences), "
    "running and debugging tests, "
    "and online research (WebSearch/WebFetch)."
)


def build_block_message() -> str:
    """Build the one-time hard-stop block message for streak=0."""
    return (
        "Delegation check: this tool call was blocked. "
        "If this task requires more than 1 tool call, delegate it to an Agent subagent. "
        f"{DELEGATION_EXAMPLES} "
        "This is a one-time block — if this call is genuinely a quick one-off, "
        "retry it and the block won't fire again. "
        "Re-blocking will occur at higher streaks (5, 8, 13, ...)."
    )


def build_streak1_message() -> str:
    """Build the distinct advisory for unblocked tools at streak=1."""
    return (
        "Delegation reminder [streak=1]: this call was allowed through without blocking. "
        "Before continuing solo, consider whether this is part of a larger task that "
        "should be an Agent subagent. "
        f"{DELEGATION_EXAMPLES} "
        "If this work genuinely cannot be delegated, continue, but re-blocking "
        "will occur at the next threshold."
    )


def build_advisory_message(streak: int) -> str:
    """Build an escalating advisory message for the given streak level."""
    if streak <= 2:
        label = "reminder"
    elif streak <= 3:
        label = "advisory"
    elif streak <= 5:
        label = "warning"
    else:
        label = "CRITICAL"

    return (
        f"Delegation {label} [streak={streak}]: You have made {streak} consecutive "
        f"solo tool calls. This work should be delegated to an Agent subagent — "
        f"stop and launch one now. {DELEGATION_EXAMPLES} "
        f"If this work genuinely cannot be delegated, continue, but "
        f"re-blocking will occur at the next threshold."
    )


def build_reblock_message(streak: int) -> str:
    """Build the re-blocking message for Fibonacci thresholds >= 5."""
    return (
        f"Re-blocked at streak {streak}. You have made {streak} consecutive solo calls "
        f"without delegating. Launch an Agent subagent for the remaining work. "
        f"{DELEGATION_EXAMPLES} "
        f"Retry this call only if it is a genuine one-off that cannot be delegated."
    )


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "")
        hook_event_name = input_data.get("hook_event_name", "")

        # SubagentStart: increment the reference counter
        if hook_event_name == "SubagentStart":
            state = read_state(session_id)
            state["subagent_count"] = state["subagent_count"] + 1
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

        if tool_name in ("Task", "Agent"):
            # Delegation occurred — reset streak and re-arm the block
            # subagent_count is managed by SubagentStart/Stop, not by Tool calls
            write_state(session_id, {"streak": 0, "block_fired": False, "subagent_count": subagent_count})
            print("{}")
            sys.exit(0)

        # Merge project config exempt_tools and unblocked_tools with defaults
        config = load_project_config()
        extra_exempt = set(config.get("exempt_tools", []))
        exempt = EXEMPT_TOOLS | extra_exempt
        if tool_name in exempt:
            # Neutral — no state change
            print("{}")
            sys.exit(0)

        # A subagent is active — pass through silently; do not modify state
        if subagent_count > 0:
            print("{}")
            sys.exit(0)

        # Merge unblocked_tools defaults with project config
        extra_unblocked = set(config.get("unblocked_tools", []))
        unblocked = UNBLOCKED_TOOLS | extra_unblocked

        # Non-Task/Agent, non-exempt tool call
        if streak == 0 and not block_fired:
            # First solo call after a Task or session start
            if tool_name in unblocked:
                # Unblocked tools: never hard-blocked, but fire advisory at streak=1
                new_streak = 1
                write_state(session_id, {"streak": new_streak, "block_fired": True, "subagent_count": subagent_count})
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": build_streak1_message(),
                    }
                }
                print(json.dumps(output))
                sys.exit(0)
            else:
                # Normal tools: hard stop
                # Blocked call does NOT increment streak — only executed calls count
                write_state(session_id, {"streak": 0, "block_fired": True, "subagent_count": subagent_count})
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
        write_state(session_id, {"streak": new_streak, "block_fired": block_fired, "subagent_count": subagent_count})

        if is_backoff_point(new_streak):
            # At Fibonacci thresholds >= 5, re-block (unless tool is in unblocked set)
            if new_streak >= 5 and tool_name not in unblocked:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": build_reblock_message(new_streak),
                    }
                }
                print(json.dumps(output))
                sys.exit(0)
            else:
                # Fibonacci < 5 or unblocked tool: advisory-only
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
