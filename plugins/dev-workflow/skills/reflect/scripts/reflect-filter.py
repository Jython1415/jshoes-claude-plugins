#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///

import argparse
import atexit
import glob
import json
import math
import os
import subprocess
import sys
from pathlib import Path


# Flag to distinguish normal exit from crash
_normal_exit = False


def derive_project_dir(pwd: str) -> str:
    """Derive project directory from $PWD."""
    return os.path.join(
        os.path.expanduser("~"),
        ".claude",
        "projects",
        pwd.replace("/", "-").replace("_", "-"),
    )


def find_session_jsonl(project_dir: str, nonce: str) -> str:
    """Find session JSONL file by nonce, or return most-recently-modified."""
    jsonl_files = glob.glob(os.path.join(project_dir, "*.jsonl"))

    # Try to grep for nonce in all files
    for jsonl_file in jsonl_files:
        try:
            result = subprocess.run(
                ["grep", "-q", nonce, jsonl_file],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return jsonl_file
        except Exception:
            continue

    # Fallback: most recently modified
    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {project_dir}")

    most_recent = max(jsonl_files, key=os.path.getmtime)
    return most_recent


def parse_jsonl_lines(filepath: str) -> list[dict]:
    """Parse JSONL file into list of dicts."""
    events = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    return events


def filter_events(events: list[dict]) -> list[dict]:
    """Keep only user, assistant, and system (compact_boundary) events."""
    filtered = []
    for event in events:
        event_type = event.get("type")
        if event_type == "user":
            filtered.append(event)
        elif event_type == "assistant":
            filtered.append(event)
        elif event_type == "system":
            if event.get("subtype") == "compact_boundary":
                filtered.append(event)
    return filtered


def find_last_boundary_index(events: list[dict]) -> int:
    """Find index of last compact_boundary event, or -1 if none."""
    for i in range(len(events) - 1, -1, -1):
        if (
            events[i].get("type") == "system"
            and events[i].get("subtype") == "compact_boundary"
        ):
            return i
    return -1


def segment_events(events: list[dict], full: bool) -> tuple[list[dict], str]:
    """Extract segment from last boundary to EOF, or entire list if --full."""
    if full:
        return events, "full file"

    last_boundary_idx = find_last_boundary_index(events)
    if last_boundary_idx == -1:
        return events, "full file (no boundary found)"

    start_line = last_boundary_idx
    segment = events[start_line:]
    return segment, f"line {start_line} to EOF"


def remove_thinking_blocks(content: list) -> list:
    """Remove thinking blocks from content array."""
    return [block for block in content if block.get("type") != "thinking"]


def truncate_tool_result_content(event: dict) -> dict:
    """Truncate tool_result content to 500 chars unless it contains error keywords."""
    if event.get("type") != "user":
        return event

    content = event.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return event

    new_content = []
    for block in content:
        if block.get("type") == "tool_result":
            block_content = block.get("content", "")
            # Check for error keywords
            error_keywords = ["error", "Error", "ERROR", "denied", "User has answered your questions"]
            has_error = any(kw in block_content for kw in error_keywords)

            if not has_error and len(block_content) > 500:
                block = block.copy()
                block["content"] = block_content[:500]
            new_content.append(block)
        else:
            new_content.append(block)

    event = event.copy()
    if "message" in event:
        event["message"] = event["message"].copy()
        event["message"]["content"] = new_content
    return event


def transform_for_detail_view(events: list[dict]) -> list[dict]:
    """Transform events for detail view."""
    transformed = []
    for event in events:
        event_type = event.get("type")

        if event_type == "assistant":
            event = event.copy()
            if "message" in event:
                message = event["message"].copy()
                content = message.get("content", [])
                if isinstance(content, list):
                    content = remove_thinking_blocks(content)
                    message["content"] = content
                event["message"] = message
            transformed.append(event)
        elif event_type == "user":
            event = truncate_tool_result_content(event)
            transformed.append(event)
        else:
            transformed.append(event)

    return transformed


def write_detail_view(events: list[dict], filepath: str) -> int:
    """Write detail view to file, return character count."""
    char_count = 0
    with open(filepath, "w", encoding="utf-8") as f:
        for event in events:
            line = json.dumps(event, separators=(",", ":")) + "\n"
            f.write(line)
            char_count += len(line)
    return char_count


def chunk_detail_view(
    lines: list[str], target_bytes: int = 100_000, overlap_pct: float = 0.10
) -> list[tuple[int, int]]:
    """Return list of (start_line, end_line) ranges for each chunk."""
    turn_starts = [
        i
        for i, line in enumerate(lines)
        if '"type":"assistant"' in line or '"type": "assistant"' in line
    ]

    if not turn_starts:
        return [(0, len(lines))]

    total_bytes = sum(len(line.encode("utf-8")) for line in lines)
    chunks_needed = max(1, math.ceil(total_bytes / target_bytes))

    if chunks_needed > 50:
        raise ValueError(
            f"Chunk count {chunks_needed} exceeds max (50). Transcript too large."
        )

    turns_per_chunk = math.ceil(len(turn_starts) / chunks_needed)
    overlap_turns = max(1, math.ceil(turns_per_chunk * overlap_pct))

    chunks = []
    for i in range(chunks_needed):
        start_turn_idx = max(0, i * turns_per_chunk - (overlap_turns if i > 0 else 0))
        end_turn_idx = min(len(turn_starts), (i + 1) * turns_per_chunk)

        start_line = turn_starts[start_turn_idx]
        end_line = (
            turn_starts[end_turn_idx] if end_turn_idx < len(turn_starts) else len(lines)
        )

        chunks.append((start_line, end_line))

    return chunks


def read_detail_lines(filepath: str) -> list[str]:
    """Read detail view file as list of lines."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readlines()


def condense_for_summary(event: dict) -> dict:
    """Transform event for summary view."""
    event = event.copy()
    event_type = event.get("type")

    if event_type == "user":
        if "message" in event:
            message = event["message"].copy()
            content = message.get("content", [])
            if isinstance(content, list):
                new_content = []
                for block in content:
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id", "unknown")
                        new_content.append(
                            {
                                "type": "tool_result",
                                "content": f"[tool_result for {tool_use_id[:8]}]",
                            }
                        )
                    else:
                        new_content.append(block)
                message["content"] = new_content
            event["message"] = message
    elif event_type == "assistant":
        if "message" in event:
            message = event["message"].copy()
            content = message.get("content", [])
            if isinstance(content, list):
                new_content = []
                for block in content:
                    if block.get("type") == "thinking":
                        continue
                    elif block.get("type") == "text":
                        block = block.copy()
                        text = block.get("text", "")
                        if len(text) > 100:
                            block["text"] = text[:100]
                        new_content.append(block)
                    elif block.get("type") == "tool_use":
                        new_content.append(
                            {
                                "type": "tool_use",
                                "name": block.get("name", "unknown"),
                            }
                        )
                    else:
                        new_content.append(block)
                message["content"] = new_content
            event["message"] = message

    return event


def write_summary_view(events: list[dict], filepath: str) -> int:
    """Write summary view to file, return character count."""
    char_count = 0
    with open(filepath, "w", encoding="utf-8") as f:
        for event in events:
            condensed = condense_for_summary(event)
            line = json.dumps(condensed, separators=(",", ":")) + "\n"
            f.write(line)
            char_count += len(line)
    return char_count


def extract_nonce_prefix(nonce: str) -> str:
    """Extract first 8 chars of nonce UUID (after REFLECT_SCAN_MARKER_ if present)."""
    if "REFLECT_SCAN_MARKER_" in nonce:
        nonce = nonce.split("REFLECT_SCAN_MARKER_")[-1]
    return nonce[:8] if len(nonce) >= 8 else nonce


def cleanup_reflect_files(nonce_prefix: str):
    """Cleanup handler: delete all .reflect-scan-* files with matching prefix.
    Only cleans up on abnormal exit (crash). On normal exit, files are left for
    scanners to read; main agent cleans up after scanners complete.
    """
    if _normal_exit:
        return
    pattern = f".reflect-scan-{nonce_prefix}-*.jsonl"
    for filepath in glob.glob(pattern):
        try:
            os.remove(filepath)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Filter Claude Code JSONL transcripts for /reflect skill")
    parser.add_argument("--nonce", required=True, help="Nonce string to locate transcript")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["light", "default", "heavy"],
        help="Determines scanner count in manifest output",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Skip segmentation; process entire transcript",
    )

    args = parser.parse_args()

    nonce_prefix = extract_nonce_prefix(args.nonce)
    atexit.register(cleanup_reflect_files, nonce_prefix)

    try:
        # 1. Session identification
        pwd = os.getcwd()
        project_dir = derive_project_dir(pwd)
        session_jsonl = find_session_jsonl(project_dir, args.nonce)

        # 2. Parse and filter events
        events = parse_jsonl_lines(session_jsonl)
        filtered = filter_events(events)

        # 3. Segmentation
        segment, segment_desc = segment_events(filtered, args.full)

        # 4. Detail view
        detail_events = transform_for_detail_view(segment)
        detail_file = f".reflect-scan-{nonce_prefix}-detail.jsonl"
        detail_size = write_detail_view(detail_events, detail_file)
        detail_lines = read_detail_lines(detail_file)

        # 5. Size measurement and chunking
        if detail_size < 100_000:
            chunks = None
            chunking_desc = "none"
        else:
            chunks = chunk_detail_view(detail_lines)
            chunking_desc = f"{len(chunks)} chunks with 10% overlap"

        # 6. Handle chunking
        scanner_jobs = []
        summary_file = None

        if chunks is None:
            # Single file
            scanner_jobs.append(("detail", detail_file, len(detail_lines)))
            if args.mode == "heavy":
                scanner_jobs.append(("detail", detail_file, len(detail_lines)))
        else:
            # Multiple chunks
            chunk_files = []
            for chunk_idx, (start_line, end_line) in enumerate(chunks):
                chunk_file = f".reflect-scan-{nonce_prefix}-detail-{chunk_idx}.jsonl"
                chunk_lines = detail_lines[start_line:end_line]
                with open(chunk_file, "w", encoding="utf-8") as f:
                    for line in chunk_lines:
                        f.write(line)
                chunk_files.append(chunk_file)
                scanner_jobs.append(("detail", chunk_file, len(chunk_lines)))
                if args.mode == "heavy":
                    scanner_jobs.append(("detail", chunk_file, len(chunk_lines)))

            # 7. Summary view (only if chunking)
            summary_events = [condense_for_summary(e) for e in segment]
            summary_file = f".reflect-scan-{nonce_prefix}-summary.jsonl"
            write_summary_view(summary_events, summary_file)
            summary_lines = read_detail_lines(summary_file)
            scanner_jobs.append(("high-level", summary_file, len(summary_lines)))

            # Clean up original detail file when chunked
            try:
                os.remove(detail_file)
            except Exception:
                pass

        # 8. Output manifest
        print("## Reflect Filter Report")
        print(f"- Transcript: {session_jsonl}")
        print(f"- Segment: {segment_desc}")
        print(f"- Detail size: {detail_size} chars")
        print(f"- Chunking: {chunking_desc}")
        print()
        print("## Scanner Jobs")
        for job_type, filepath, line_count in scanner_jobs:
            print(f"{job_type} {filepath} {line_count}")
        print()
        print("## Cleanup")
        print(f"rm -f .reflect-scan-{nonce_prefix}-*.jsonl")

        global _normal_exit
        _normal_exit = True
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
