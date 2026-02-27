#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""
stop-momentum: Enforce execution momentum via an ack token handshake.

Event: Stop

Purpose: Prevents Claude from stopping prematurely by requiring deliberate
acknowledgment before allowing a session stop. On each Stop event, the hook
checks whether the last assistant message contains the expected ack token. If
not, it blocks the stop and asks Claude to confirm with a newly generated token.

Behavior:
- If stop_hook_active is True → allow immediately (prevents infinite loops)
- If last assistant message contains the current ack token → allow, delete state
- Otherwise → block with guidance and a new ack token

Ack token handshake:
1. Hook generates token "ACK-XXXX" and writes it to a per-session state file
2. Hook blocks the stop with a message that includes the token
3. Claude must include the exact token string in its next response
4. On the next Stop event, hook reads the token from state, finds it in the
   assistant message, and allows the stop

State management:
- State files stored in: ~/.claude/hook-state/stop-ack-{session_id}
- Override location: CLAUDE_HOOK_STATE_DIR environment variable

Custom guidance:
- If .claude/momentum-guide.md exists in the project's cwd, its contents are
  used as the guidance block instead of the built-in default message.
"""
import json
import os
import random
import string
import sys
from pathlib import Path

# State directory location
_state_dir_env = os.environ.get("CLAUDE_HOOK_STATE_DIR")
STATE_DIR = Path(_state_dir_env) if _state_dir_env else Path.home() / ".claude" / "hook-state"

DEFAULT_GUIDANCE = """EXECUTION MOMENTUM CHECK: Before stopping, consider:
- Have you completed what the user actually asked for, or just a sub-task within a larger request?
- If you have a question, status update, or finding to share, prefer /consult over stopping — it gives the user a structured way to respond without treating this as a session boundary.
- If this is a genuine session end (user's request fully fulfilled, or an explicit checkpoint they asked for), you may stop deliberately."""


def generate_token() -> str:
    """Generate a random ack token."""
    return "ACK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def get_state_file(session_id: str) -> Path:
    """Return the path to the state file for this session."""
    return STATE_DIR / f"stop-ack-{session_id}"


def read_token(session_id: str) -> str | None:
    """Read the current ack token from state file. Returns None if not found."""
    try:
        state_file = get_state_file(session_id)
        if state_file.exists():
            return state_file.read_text().strip()
        return None
    except Exception:
        return None


def write_token(session_id: str, token: str) -> None:
    """Write the ack token to the state file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    get_state_file(session_id).write_text(token)


def delete_state(session_id: str) -> None:
    """Delete the state file for this session."""
    try:
        state_file = get_state_file(session_id)
        if state_file.exists():
            state_file.unlink()
    except Exception:
        pass


def load_custom_guidance(cwd: str) -> str | None:
    """Load custom guidance from .claude/momentum-guide.md in the project cwd."""
    try:
        guide_path = Path(cwd) / ".claude" / "momentum-guide.md"
        if guide_path.exists():
            return guide_path.read_text().strip()
        return None
    except Exception:
        return None


def build_block_message(guidance: str, token: str) -> str:
    """Assemble the full block message with guidance and token instruction."""
    return (
        f"{guidance}\n\n"
        f"To confirm this is a deliberate stop, include {token} in your next response."
    )


def main():
    try:
        input_data = json.load(sys.stdin)

        # Step 1: If stop_hook_active is True, allow to prevent infinite loops
        if input_data.get("stop_hook_active", False):
            print("{}")
            sys.exit(0)

        session_id = input_data.get("session_id", "")
        last_message = input_data.get("last_assistant_message", "")
        cwd = input_data.get("cwd", "")

        # Step 2: Check for existing ack token in state
        existing_token = read_token(session_id)

        # Step 3: If token exists and is found in last message → allow
        if existing_token and existing_token in last_message:
            delete_state(session_id)
            print("{}")
            sys.exit(0)

        # Step 4: Block — generate new token, write state, build message
        new_token = generate_token()
        write_token(session_id, new_token)

        # Load custom or default guidance
        custom_guidance = load_custom_guidance(cwd)
        guidance = custom_guidance if custom_guidance is not None else DEFAULT_GUIDANCE

        message = build_block_message(guidance, new_token)

        output = {
            "decision": "block",
            "reason": message,
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        print(f"Error in stop-momentum hook: {e}", file=sys.stderr)
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
