"""
Unit tests for reflect-scanner-inject.py SubagentStart hook

This hook is responsible for injecting transcript chunks into reflect-scanner
subagent initialization. It manages a queue file, pops chunks from it, and
injects their content as additionalContext for the agent.
"""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "reflect-scanner-inject.py"


def run_hook(stdin_data: str, cwd: str | None = None) -> dict:
    """Run the hook directly via uv run --script and return parsed output.

    Args:
        stdin_data: JSON string to pass to the hook
        cwd: Optional working directory to set for the hook subprocess

    Returns:
        Parsed JSON output from the hook
    """
    input_obj = json.loads(stdin_data)
    if cwd is not None:
        input_obj["cwd"] = cwd

    result = subprocess.run(
        ["uv", "run", "--script", str(HOOK_PATH)],
        input=json.dumps(input_obj),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    assert result.returncode == 0, f"Hook failed: {result.stderr}"
    return json.loads(result.stdout)


class TestReflectScannerInject:
    """Tests for the reflect-scanner-inject SubagentStart hook."""

    def test_non_reflect_scanner_agent_type(self):
        """Input with agent_type != 'reflect-scanner' should output {}."""
        input_data = {
            "agent_type": "some-other-agent",
            "cwd": "/tmp",
        }
        output = run_hook(json.dumps(input_data))
        assert output == {}, "Non-reflect-scanner agents should pass through"

    def test_no_agent_type_field(self):
        """Input without agent_type field should output {}."""
        input_data = {
            "cwd": "/tmp",
        }
        output = run_hook(json.dumps(input_data))
        assert output == {}, "Missing agent_type should pass through"

    def test_no_queue_file(self, tmp_path):
        """No queue file in cwd should output {}."""
        cwd = str(tmp_path)
        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)
        assert output == {}, "Missing queue file should result in empty output"

    def test_empty_queue_file(self, tmp_path):
        """Queue file that exists but is empty should output {}."""
        cwd = str(tmp_path)
        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text("")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)
        assert output == {}, "Empty queue file should result in empty output"

    def test_basic_injection(self, tmp_path):
        """Queue file with one entry and chunk file should inject content."""
        cwd = str(tmp_path)

        # Create chunk file
        chunk_file = tmp_path / "chunk-001.jsonl"
        chunk_content = '{"event": "message", "role": "user"}\n{"event": "message", "role": "assistant"}\n'
        chunk_file.write_text(chunk_content)

        # Create queue file pointing to chunk
        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text(str(chunk_file) + "\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)

        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
        assert "additionalContext" in output["hookSpecificOutput"]

        context = output["hookSpecificOutput"]["additionalContext"]
        # Check for structured markers
        assert "## Transcript Chunk" in context
        assert "## Your Task" in context
        assert chunk_content in context
        assert "---" in context
        assert "User Corrections" in context
        assert "Execution Failures" in context
        assert "Approach Pivots" in context
        assert "Codifiable Patterns" in context

    def test_missing_chunk_file(self, tmp_path):
        """Queue file pointing to nonexistent chunk file should output {}."""
        cwd = str(tmp_path)

        nonexistent_chunk = str(tmp_path / "nonexistent-chunk.jsonl")
        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text(nonexistent_chunk + "\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)
        assert output == {}, "Missing chunk file should result in empty output"

    def test_queue_consumption(self, tmp_path):
        """After hook runs, the consumed entry should be removed from queue file."""
        cwd = str(tmp_path)

        # Create two chunk files
        chunk1 = tmp_path / "chunk-001.jsonl"
        chunk1.write_text('{"event": "message", "role": "user"}\n')

        chunk2 = tmp_path / "chunk-002.jsonl"
        chunk2.write_text('{"event": "message", "role": "assistant"}\n')

        # Create queue file with both chunks
        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text(f"{str(chunk1)}\n{str(chunk2)}\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }

        # First invocation should consume chunk1
        output1 = run_hook(json.dumps(input_data), cwd=cwd)
        assert "hookSpecificOutput" in output1
        context1 = output1["hookSpecificOutput"]["additionalContext"]
        assert '{"event": "message", "role": "user"}' in context1

        # Queue file should now only have chunk2
        remaining_queue = queue_file.read_text()
        assert str(chunk2) in remaining_queue
        assert str(chunk1) not in remaining_queue

        # Second invocation should consume chunk2
        output2 = run_hook(json.dumps(input_data), cwd=cwd)
        assert "hookSpecificOutput" in output2
        context2 = output2["hookSpecificOutput"]["additionalContext"]
        assert '{"event": "message", "role": "assistant"}' in context2

        # Queue file should now be empty
        remaining_queue = queue_file.read_text()
        assert remaining_queue == ""

        # Third invocation should return empty
        output3 = run_hook(json.dumps(input_data), cwd=cwd)
        assert output3 == {}

    def test_concurrent_queue_pops(self, tmp_path):
        """Concurrent invocations should each get unique chunks from queue."""
        cwd = str(tmp_path)

        # Create 5 chunk files
        chunk_files = []
        for i in range(1, 6):
            chunk_file = tmp_path / f"chunk-{i:03d}.jsonl"
            chunk_file.write_text(f'{{"chunk_id": {i}}}\n')
            chunk_files.append(chunk_file)

        # Create queue file with all 5 chunks
        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text("\n".join(str(f) for f in chunk_files) + "\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }

        # Run 5 concurrent invocations
        results = []
        def invoke_hook():
            return run_hook(json.dumps(input_data), cwd=cwd)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(invoke_hook) for _ in range(5)]
            results = [f.result() for f in as_completed(futures)]

        # Verify we got 5 successful injections
        successful_injections = [r for r in results if "hookSpecificOutput" in r]
        assert len(successful_injections) == 5, "All concurrent invocations should succeed"

        # Extract chunk IDs from contexts
        chunk_ids = []
        for output in successful_injections:
            context = output["hookSpecificOutput"]["additionalContext"]
            # Parse the chunk_id from the context
            for i in range(1, 6):
                if f'{{"chunk_id": {i}}}' in context:
                    chunk_ids.append(i)
                    break

        # Verify all 5 chunks were consumed (no duplicates)
        assert len(chunk_ids) == 5, "Should have received 5 unique chunks"
        assert sorted(chunk_ids) == [1, 2, 3, 4, 5], "All chunks should be unique and accounted for"

        # Queue file should be empty
        remaining_queue = queue_file.read_text()
        assert remaining_queue.strip() == "", "Queue file should be empty after all chunks consumed"

    def test_output_has_valid_json_structure(self, tmp_path):
        """Hook output should be valid JSON with correct structure."""
        cwd = str(tmp_path)

        chunk_file = tmp_path / "chunk.jsonl"
        chunk_file.write_text('{"test": "data"}\n')

        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text(str(chunk_file) + "\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)

        assert isinstance(output, dict)
        assert "hookSpecificOutput" in output
        assert isinstance(output["hookSpecificOutput"], dict)
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_chunk_content_preserved(self, tmp_path):
        """Hook should preserve chunk content exactly as-is."""
        cwd = str(tmp_path)

        # Create chunk with special characters and newlines
        special_content = '''{"event": "message", "text": "Hello\\nWorld"}
{"event": "tool_call", "args": {"key": "value with spaces"}}
{"event": "error", "message": "Error: Connection timeout"}
'''
        chunk_file = tmp_path / "chunk.jsonl"
        chunk_file.write_text(special_content)

        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        queue_file.write_text(str(chunk_file) + "\n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)

        context = output["hookSpecificOutput"]["additionalContext"]
        assert special_content in context, "Chunk content should be preserved exactly"

    def test_queue_file_with_whitespace(self, tmp_path):
        """Queue file entries should handle leading/trailing whitespace."""
        cwd = str(tmp_path)

        chunk_file = tmp_path / "chunk.jsonl"
        chunk_file.write_text('{"test": "data"}\n')

        queue_file = tmp_path / ".reflect-scan-test-queue.txt"
        # Entry with leading/trailing whitespace
        queue_file.write_text(f"  {str(chunk_file)}  \n")

        input_data = {
            "agent_type": "reflect-scanner",
            "cwd": cwd,
        }
        output = run_hook(json.dumps(input_data), cwd=cwd)

        # Should still work despite whitespace
        assert "hookSpecificOutput" in output

    def test_cwd_defaults_to_getcwd(self):
        """If cwd not provided, should use current working directory."""
        input_data = {
            "agent_type": "reflect-scanner",
        }
        # Since there's no queue file in the current directory, should return {}
        output = run_hook(json.dumps(input_data))
        assert output == {}

    def test_malformed_json_input(self):
        """Malformed JSON input should output {}."""
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input="not valid json",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output == {}, "Malformed JSON should result in empty output"


def main():
    """Run tests when executed as a script"""
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
