#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import fcntl
import glob
import json
import os
import sys
from pathlib import Path

def main():
    """SubagentStart hook for reflect-scanner agents.

    Reads JSON input from stdin, checks if this is a reflect-scanner agent spawn,
    and if so, pops a chunk file path from the queue file and injects its content
    as additionalContext.
    """
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        # If input is malformed, output empty JSON and exit
        print("{}", file=sys.stdout)
        print(f"Hook input parse error: {e}", file=sys.stderr)
        return

    # Check if this is a reflect-scanner agent
    agent_type = input_data.get("agent_type", "")
    if agent_type != "reflect-scanner":
        # Not our agent type, pass through
        print("{}", file=sys.stdout)
        return

    # Get the working directory
    cwd = input_data.get("cwd", os.getcwd())

    # Find queue file
    queue_pattern = os.path.join(cwd, ".reflect-scan-*-queue.txt")
    queue_files = glob.glob(queue_pattern)
    if not queue_files:
        # No queue file found
        print("{}", file=sys.stdout)
        return

    queue_file = queue_files[0]

    try:
        # Open queue file with exclusive lock
        with open(queue_file, "r+") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                # Lock timeout or error, try with blocking for a short time
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except Exception as e:
                    print("{}", file=sys.stdout)
                    print(f"Queue lock acquisition failed: {e}", file=sys.stderr)
                    return

            # Read all lines
            lines = f.readlines()

            if not lines:
                # Queue is empty
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                print("{}", file=sys.stdout)
                return

            # Pop first line (chunk file path)
            chunk_path = lines[0].strip()
            remaining_lines = lines[1:]

            # Write remaining lines back
            f.seek(0)
            f.truncate()
            f.writelines(remaining_lines)

            # Release lock
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    except FileNotFoundError:
        # Queue file doesn't exist
        print("{}", file=sys.stdout)
        return
    except Exception as e:
        # Any other error
        print("{}", file=sys.stdout)
        print(f"Queue file error: {e}", file=sys.stderr)
        return

    # Read chunk file
    try:
        with open(chunk_path, "r", encoding="utf-8") as f:
            chunk_content = f.read()
    except FileNotFoundError:
        print("{}", file=sys.stdout)
        print(f"Chunk file not found: {chunk_path}", file=sys.stderr)
        return
    except Exception as e:
        print("{}", file=sys.stdout)
        print(f"Chunk file read error: {e}", file=sys.stderr)
        return

    # Construct additionalContext with structured markers and trailing prompt
    context = f"""## Transcript Chunk

The following is your assigned transcript chunk in JSONL format. Each line
is a JSON object representing one conversation event (user message, assistant
response, or system event). Analyze this data using the 4 checklists defined
in your instructions above.

---

{chunk_content}
---

## Your Task

You have received the complete transcript chunk above. Now apply all 4
checklists to this data:

1. **User Corrections** — Where did the user redirect, correct, or disagree?
2. **Execution Failures** — Which tool calls failed, errored, or needed retries?
3. **Approach Pivots** — Where did the strategy change significantly?
4. **Codifiable Patterns** — What patterns were used repeatedly?

Report each finding using the structured format from your instructions.
If fewer than 2 findings survive, report "Clean session — nothing to persist"
with approximate message and tool call counts."""

    # Output hook response
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": context
        }
    }
    print(json.dumps(output), file=sys.stdout)

if __name__ == "__main__":
    main()
