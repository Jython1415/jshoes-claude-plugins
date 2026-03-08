#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "tiktoken>=0.7.0",
# ]
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

import tiktoken


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


def cap_oversized_lines(
    lines: list[str], encoding: tiktoken.Encoding, max_line_tokens: int
) -> list[str]:
    """Truncate any individual line that exceeds max_line_tokens.

    Preserves the JSON opening structure and appends a truncation marker.
    This ensures no single line can blow past the chunk token budget.
    """
    capped = []
    for line in lines:
        tokens = len(encoding.encode(line))
        if tokens <= max_line_tokens:
            capped.append(line)
        else:
            # Binary search for character position that fits token budget
            # Leave room for the truncation suffix
            suffix = '...[TRUNCATED]"}\n'
            target_tokens = max_line_tokens - 20  # headroom for suffix
            lo, hi = 0, len(line)
            while lo < hi:
                mid = (lo + hi) // 2
                if len(encoding.encode(line[:mid])) <= target_tokens:
                    lo = mid + 1
                else:
                    hi = mid
            capped.append(line[: lo - 1] + suffix)
    return capped


def count_tokens(text: str, encoding: tiktoken.Encoding) -> int:
    """Count tokens in text using tiktoken."""
    return len(encoding.encode(text))


def count_lines_tokens(lines: list[str], encoding: tiktoken.Encoding) -> int:
    """Count total tokens across a list of lines."""
    return sum(count_tokens(line, encoding) for line in lines)


def chunk_detail_view(
    lines: list[str],
    encoding: tiktoken.Encoding,
    max_tokens: int = 20_000,
    overlap_pct: float = 0.10,
) -> list[tuple[int, int]]:
    """Partition lines into token-bounded chunks, split on turn boundaries.

    Algorithm:
    1. Pre-compute per-turn token counts
    2. Split any oversized turns at line boundaries (intra-turn splitting)
    3. Derive chunk count from total tokens and an effective max that reserves
       room for overlap (max_tokens / (1 + overlap_pct))
    4. Compute even target = total / num_chunks (guaranteed <= effective max)
    5. Greedily partition turns against the even target
    6. Add token-aware overlap: walk backward from each boundary, adding turns
       until the overlap budget (remaining space up to max_tokens) is exhausted
    7. Hard cap overlap: if total chunk exceeds max_tokens, trim overlap turns
    """
    turn_starts = [
        i
        for i, line in enumerate(lines)
        if '"type":"assistant"' in line or '"type": "assistant"' in line
    ]

    if not turn_starts:
        return [(0, len(lines))]

    # 1. Pre-compute token cost per turn (turn = assistant line + following user lines)
    turn_tokens = []
    for idx in range(len(turn_starts)):
        start = turn_starts[idx]
        end = turn_starts[idx + 1] if idx + 1 < len(turn_starts) else len(lines)
        turn_tokens.append(count_lines_tokens(lines[start:end], encoding))

    # Include preamble (lines before first turn) in the first turn's cost
    if turn_starts[0] > 0:
        preamble_tokens = count_lines_tokens(lines[: turn_starts[0]], encoding)
        turn_tokens[0] += preamble_tokens

    # 2. Fix 1: Split oversized turns at line boundaries
    effective_max = max_tokens / (1 + overlap_pct)
    new_turn_starts = []
    new_turn_tokens = []

    for idx in range(len(turn_starts)):
        turn_start_line = turn_starts[idx]
        turn_end_line = turn_starts[idx + 1] if idx + 1 < len(turn_starts) else len(lines)
        turn_cost = turn_tokens[idx]

        if turn_cost <= effective_max:
            # Turn fits within effective_max; keep it as-is
            new_turn_starts.append(turn_start_line)
            new_turn_tokens.append(turn_cost)
        else:
            # Turn exceeds effective_max; split at line boundaries
            # Assistant line is at turn_start_line; subsequent lines are user events
            sub_turns = []
            sub_start = turn_start_line
            sub_tokens = 0

            for line_idx in range(turn_start_line, turn_end_line):
                line_tokens = count_tokens(lines[line_idx], encoding)

                if sub_tokens > 0 and sub_tokens + line_tokens > effective_max:
                    # Emit current sub-turn
                    sub_turns.append((sub_start, sub_tokens))
                    sub_start = line_idx
                    sub_tokens = line_tokens
                else:
                    sub_tokens += line_tokens

            # Emit final sub-turn
            if sub_tokens > 0:
                sub_turns.append((sub_start, sub_tokens))

            # Add sub-turns to the new lists
            for sub_line_start, sub_tok in sub_turns:
                new_turn_starts.append(sub_line_start)
                new_turn_tokens.append(sub_tok)

    turn_starts = new_turn_starts
    turn_tokens = new_turn_tokens

    # 3. Derive chunk count, reserving headroom for overlap
    total_tokens = sum(turn_tokens)
    effective_max = max_tokens / (1 + overlap_pct)
    num_chunks = max(1, math.ceil(total_tokens / effective_max))
    target_per_chunk = total_tokens / num_chunks

    # 4. Greedy partition: accumulate turns, split when exceeding even target
    partitions: list[tuple[int, int]] = []
    current_start = 0
    accumulated = 0

    for i, tok in enumerate(turn_tokens):
        if accumulated > 0 and accumulated + tok > target_per_chunk:
            partitions.append((current_start, i))
            current_start = i
            accumulated = 0
        accumulated += tok
    partitions.append((current_start, len(turn_tokens)))

    if len(partitions) > 200:
        raise ValueError(f"Chunk count {len(partitions)} exceeds max (200). Transcript too large.")

    # 5. Convert to line ranges with token-aware overlap
    chunks = []
    for idx, (part_start, part_end) in enumerate(partitions):
        part_tokens = sum(turn_tokens[part_start:part_end])
        # The partition's own start line — overlap must never trim past this
        partition_start_line = 0 if part_start == 0 else turn_starts[part_start]

        if idx > 0:
            # Walk backward into previous partition, bounded by token budget
            overlap_budget = max_tokens - part_tokens
            overlap_start = part_start
            overlap_used = 0
            while overlap_start > partitions[idx - 1][0]:
                prev_cost = turn_tokens[overlap_start - 1]
                if overlap_used + prev_cost > overlap_budget:
                    break
                overlap_used += prev_cost
                overlap_start -= 1
            start_line = 0 if overlap_start == 0 else turn_starts[overlap_start]
        else:
            # First chunk: include preamble
            start_line = 0

        end_line = turn_starts[part_end] if part_end < len(turn_starts) else len(lines)

        # 6. Hard cap: if chunk exceeds max_tokens, trim overlap (never past partition start)
        if start_line < partition_start_line:
            chunk_tokens = count_lines_tokens(lines[start_line:end_line], encoding)
            while chunk_tokens > max_tokens and start_line < partition_start_line:
                # Advance start_line to next turn boundary within the overlap region
                advanced = False
                for t_idx, t_start in enumerate(turn_starts):
                    if t_start > start_line:
                        start_line = t_start
                        advanced = True
                        break
                if not advanced or start_line >= partition_start_line:
                    start_line = partition_start_line
                    break
                chunk_tokens = count_lines_tokens(lines[start_line:end_line], encoding)

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


def cleanup_reflect_files(nonce_prefix: str, base_dir: str):
    """Cleanup handler: delete all .reflect-scan-* files with matching prefix.
    Only cleans up on abnormal exit (crash). On normal exit, files are left for
    scanners to read; main agent cleans up after scanners complete.
    """
    if _normal_exit:
        return
    pattern = os.path.join(base_dir, f".reflect-scan-{nonce_prefix}-*.jsonl")
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
    pwd = os.getcwd()
    atexit.register(cleanup_reflect_files, nonce_prefix, pwd)

    try:
        # 1. Session identification
        project_dir = derive_project_dir(pwd)
        session_jsonl = find_session_jsonl(project_dir, args.nonce)

        # 2. Parse and filter events
        events = parse_jsonl_lines(session_jsonl)
        filtered = filter_events(events)

        # 3. Segmentation
        segment, segment_desc = segment_events(filtered, args.full)

        # 4. Detail view
        detail_events = transform_for_detail_view(segment)
        detail_file = os.path.join(pwd, f".reflect-scan-{nonce_prefix}-detail.jsonl")
        detail_size = write_detail_view(detail_events, detail_file)
        detail_lines = read_detail_lines(detail_file)

        # 5. Size measurement and chunking
        encoding = tiktoken.get_encoding("cl100k_base")
        max_chunk_tokens = 80_000
        overlap_pct = 0.10
        max_line_tokens = int(max_chunk_tokens / (1 + overlap_pct))  # effective_max
        detail_lines = cap_oversized_lines(detail_lines, encoding, max_line_tokens)
        detail_tokens = count_lines_tokens(detail_lines, encoding)

        if detail_tokens < max_chunk_tokens * 0.9:
            chunks = None
            chunking_desc = "none"
        else:
            chunks = chunk_detail_view(detail_lines, encoding, max_tokens=max_chunk_tokens, overlap_pct=overlap_pct)
            chunking_desc = f"{len(chunks)} chunks with {int(overlap_pct*100)}% overlap"

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
                chunk_file = os.path.join(pwd, f".reflect-scan-{nonce_prefix}-detail-{chunk_idx}.jsonl")
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
            summary_file = os.path.join(pwd, f".reflect-scan-{nonce_prefix}-summary.jsonl")
            write_summary_view(summary_events, summary_file)
            summary_lines = read_detail_lines(summary_file)
            summary_lines = cap_oversized_lines(summary_lines, encoding, max_line_tokens)
            summary_tokens = count_lines_tokens(summary_lines, encoding)

            if summary_tokens < max_chunk_tokens * 0.9:
                scanner_jobs.append(("high-level", summary_file, len(summary_lines)))
            else:
                # Chunk the summary too
                summary_chunks = chunk_detail_view(summary_lines, encoding, max_tokens=max_chunk_tokens, overlap_pct=overlap_pct)
                for sc_idx, (sc_start, sc_end) in enumerate(summary_chunks):
                    sc_file = os.path.join(pwd, f".reflect-scan-{nonce_prefix}-summary-{sc_idx}.jsonl")
                    sc_lines = summary_lines[sc_start:sc_end]
                    with open(sc_file, "w", encoding="utf-8") as f:
                        for line in sc_lines:
                            f.write(line)
                    scanner_jobs.append(("high-level", sc_file, len(sc_lines)))
                try:
                    os.remove(summary_file)
                except Exception:
                    pass

            # Clean up original detail file when chunked
            try:
                os.remove(detail_file)
            except Exception:
                pass

        # 8. Output manifest
        print("## Reflect Filter Report")
        print(f"- Transcript: {session_jsonl}")
        print(f"- Segment: {segment_desc}")
        print(f"- Detail size: {detail_size} chars ({detail_tokens} tokens)")
        print(f"- Chunking: {chunking_desc}")
        print()
        print("## Scanner Jobs")
        for job_type, filepath, line_count in scanner_jobs:
            print(f"{job_type} {filepath} {line_count}")
        print()
        print("## Cleanup")
        print(f"rm -f {os.path.join(pwd, f'.reflect-scan-{nonce_prefix}-*.jsonl')}")

        global _normal_exit
        _normal_exit = True
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
