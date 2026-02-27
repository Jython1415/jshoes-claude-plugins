#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
delegation-guard: Track consecutive non-Task tool calls and inject a delegation advisory.

Event: PostToolUse (no matcher — fires on all tools)

Purpose: Encourages the main session agent to delegate implementation, research,
and multi-step analysis work to subagents via the Task tool. Fires an advisory
reminder when Claude makes 3 or more consecutive tool calls without spawning a
subagent, matching the '3 consecutive non-spawn tool calls = delegate' rule.

Mechanism — offset-tracked transcript parsing:
Each PostToolUse call reads the transcript from the last recorded byte offset,
parses only the new JSONL lines, and counts tool_use entries. Lines where the
tool name is "Task" reset the streak; all other tool_use lines increment it.

Behavior:
- If streak >= 3: inject an additionalContext advisory
- Otherwise: output {}

State management:
- State files stored in: ~/.claude/hook-state/{session_id}-delegation.json
- Override location: CLAUDE_HOOK_STATE_DIR environment variable
- State fields: offset (int, bytes), streak (int), task_calls (int)
"""
import json
import os
import sys
from pathlib import Path

# State directory location
_state_dir_env = os.environ.get("CLAUDE_HOOK_STATE_DIR")
STATE_DIR = Path(_state_dir_env) if _state_dir_env else Path.home() / ".claude" / "hook-state"

# Delegation threshold (number of consecutive non-Task calls before advisory fires)
DELEGATION_THRESHOLD = 3


def get_state_file(session_id: str) -> Path:
    """Return the path to the state file for this session."""
    return STATE_DIR / f"{session_id}-delegation.json"


def read_state(session_id: str) -> dict:
    """Read delegation state for this session. Returns default state if not found or corrupt."""
    default = {"offset": 0, "streak": 0, "task_calls": 0}
    try:
        state_file = get_state_file(session_id)
        if not state_file.exists():
            return default
        data = json.loads(state_file.read_text())
        # Validate expected fields are present and are ints
        if not all(isinstance(data.get(k), int) for k in ("offset", "streak", "task_calls")):
            return default
        return data
    except Exception:
        return default


def write_state(session_id: str, state: dict) -> None:
    """Write delegation state for this session."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        get_state_file(session_id).write_text(json.dumps(state))
    except Exception as e:
        print(f"Warning: Could not write delegation state: {e}", file=sys.stderr)


def parse_new_transcript_lines(transcript_path: str, offset: int) -> tuple[list[dict], int]:
    """
    Read transcript from offset to end, parse JSONL lines.

    Returns a tuple of (parsed_lines, new_offset). Lines that fail JSON parsing
    are skipped. new_offset is the byte position after the last byte read.
    """
    parsed = []
    new_offset = offset
    try:
        path = Path(transcript_path)
        if not path.exists():
            return parsed, new_offset

        with path.open("rb") as f:
            f.seek(offset)
            raw = f.read()
            new_offset = offset + len(raw)

        if not raw:
            return parsed, new_offset

        # Decode and split into lines
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                parsed.append(obj)
            except json.JSONDecodeError:
                # Skip unparseable lines (partial writes, etc.)
                continue
    except Exception as e:
        print(f"Warning: Could not read transcript: {e}", file=sys.stderr)

    return parsed, new_offset


def compute_streak(lines: list[dict], initial_streak: int) -> tuple[int, int]:
    """
    Compute the new streak and task_call count from new transcript lines.

    Processes tool_use entries in order. Task calls reset the streak to 0;
    non-Task calls increment it. The initial_streak is the streak before
    seeing any of the new lines.

    Returns (new_streak, new_task_calls).
    """
    streak = initial_streak
    task_calls = 0
    for line in lines:
        if not isinstance(line, dict):
            continue
        if line.get("type") == "tool_use":
            name = line.get("name", "")
            if name == "Task":
                streak = 0
                task_calls += 1
            else:
                streak += 1
    return streak, task_calls


def build_advisory(streak: int) -> str:
    """Build the delegation advisory message."""
    return (
        f"Delegation check: {streak} consecutive tool calls without using Task. "
        f"Consider whether this work should be delegated to a subagent to preserve "
        f"main context. Use the Task tool to spawn a subagent for implementation, "
        f"research, or multi-step analysis work."
    )


def main():
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "")
        transcript_path = input_data.get("transcript_path", "")

        # Load current state
        state = read_state(session_id)
        offset = state["offset"]
        streak = state["streak"]
        task_calls = state["task_calls"]

        # Read and parse new transcript content
        new_lines, new_offset = parse_new_transcript_lines(transcript_path, offset)

        # Compute updated streak from new lines
        new_streak, new_task_count = compute_streak(new_lines, streak)
        new_task_calls = task_calls + new_task_count

        # Persist updated state
        write_state(session_id, {
            "offset": new_offset,
            "streak": new_streak,
            "task_calls": new_task_calls,
        })

        # Emit advisory if threshold reached
        if new_streak >= DELEGATION_THRESHOLD:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": build_advisory(new_streak),
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
