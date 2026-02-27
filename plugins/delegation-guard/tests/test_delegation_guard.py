"""
Unit tests for delegation-guard.py hook

This test suite validates that the hook properly tracks consecutive non-Task
tool calls via offset-tracked transcript parsing and injects an advisory
reminder when the streak reaches 2.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "hooks" / "delegation-guard.py"

# Writable test state directory (redirects away from ~/.claude/hook-state/ for sandbox compat)
TEST_STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "claude-hook-test-state-delegation"

DEFAULT_SESSION_ID = "test-session-delegation-123"


def make_tool_use_line(name: str, tool_id: str = "toolu_01") -> str:
    """Return a JSONL line representing a tool_use transcript entry."""
    return json.dumps({
        "type": "tool_use",
        "id": tool_id,
        "name": name,
        "input": {},
    })


def write_transcript(lines: list[str], path: Path) -> None:
    """Write JSONL lines to a transcript file."""
    path.write_text("\n".join(lines) + "\n")


def append_transcript(lines: list[str], path: Path) -> None:
    """Append JSONL lines to an existing transcript file."""
    with path.open("a") as f:
        for line in lines:
            f.write(line + "\n")


def run_hook(
    session_id: str = DEFAULT_SESSION_ID,
    transcript_path: str = "",
    clear_state: bool = True,
) -> dict:
    """
    Helper function to run the delegation-guard hook.

    Args:
        session_id: The session ID to use in the hook input.
        transcript_path: Path to the transcript file.
        clear_state: Whether to delete the session state file before running.

    Returns:
        Parsed JSON output from the hook.
    """
    if clear_state:
        state_file = TEST_STATE_DIR / f"{session_id}-delegation.json"
        if state_file.exists():
            state_file.unlink()

    input_data = {
        "hook_event_name": "PostToolUse",
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


class TestStreakIncrement:
    """Test that streak increments on non-Task tool calls."""

    def test_single_non_task_call_increments_streak(self):
        """A single non-Task tool_use line should set streak to 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["streak"] == 1

    def test_two_non_task_calls_increment_streak(self):
        """Two non-Task tool_use lines should set streak to 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["streak"] == 2

    def test_streak_accumulates_across_calls(self):
        """Streak should accumulate correctly when transcript grows between hook calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash", "toolu_01")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)
            state = get_state()
            assert state["streak"] == 1

            # Append a new tool_use line and run again (no clear_state — simulates next call)
            append_transcript([make_tool_use_line("Read", "toolu_02")], transcript)
            run_hook(transcript_path=str(transcript), clear_state=False)

            state = get_state()
            assert state["streak"] == 2


class TestStreakReset:
    """Test that streak resets to 0 on Task tool calls."""

    def test_task_call_resets_streak(self):
        """A Task tool_use line should reset the streak to 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            # Two non-Task calls followed by a Task call
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
                make_tool_use_line("Task", "toolu_03"),
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["streak"] == 0

    def test_task_call_increments_task_count(self):
        """A Task tool_use line should increment task_calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Task", "toolu_01")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["task_calls"] == 1

    def test_task_resets_streak_then_increments(self):
        """Task call resets streak; subsequent non-Task calls count from 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            # One non-Task, then Task (reset), then one more non-Task
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Task", "toolu_02"),
                make_tool_use_line("Grep", "toolu_03"),
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["streak"] == 1
            assert state["task_calls"] == 1


class TestAdvisoryFiring:
    """Test that advisory fires at streak >= 2 and not below."""

    def test_advisory_fires_at_streak_2(self):
        """Advisory should fire when streak reaches 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert "hookSpecificOutput" in output, "Advisory should fire at streak 2"
            hook_output = output["hookSpecificOutput"]
            assert hook_output.get("hookEventName") == "PostToolUse"
            assert "additionalContext" in hook_output

    def test_advisory_fires_exactly_once_per_run(self):
        """Advisory fires at streak=2 but NOT again at streak=3 without a Task call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"

            # First call: 2 non-Task lines → advisory fires
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
            ], transcript)
            output_first = run_hook(transcript_path=str(transcript), clear_state=True)
            assert "hookSpecificOutput" in output_first, "Advisory should fire at streak 2"

            # Second call: 1 more non-Task line → advisory should NOT fire again
            append_transcript([make_tool_use_line("Grep", "toolu_03")], transcript)
            output_second = run_hook(transcript_path=str(transcript), clear_state=False)
            assert output_second == {}, "Advisory should not fire again after already fired"

    def test_advisory_fires_again_after_task_reset(self):
        """Advisory fires again after a Task call resets the streak and advisory_fired."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"

            # First run: advisory fires at streak=2
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
            ], transcript)
            output_first = run_hook(transcript_path=str(transcript), clear_state=True)
            assert "hookSpecificOutput" in output_first

            # Task call resets streak and advisory_fired
            append_transcript([make_tool_use_line("Task", "toolu_03")], transcript)
            run_hook(transcript_path=str(transcript), clear_state=False)
            state_after_task = get_state()
            assert state_after_task["streak"] == 0
            assert state_after_task["advisory_fired"] == False

            # Advisory fires again after streak reaches 2 again
            append_transcript([
                make_tool_use_line("Grep", "toolu_04"),
                make_tool_use_line("Edit", "toolu_05"),
            ], transcript)
            output_third = run_hook(transcript_path=str(transcript), clear_state=False)
            assert "hookSpecificOutput" in output_third, "Advisory should fire again after Task reset"

    def test_no_advisory_at_streak_1(self):
        """Advisory should NOT fire when streak is 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert output == {}, f"Expected empty output at streak 1, got: {output}"

    def test_no_advisory_when_task_resets_before_threshold(self):
        """No advisory when Task resets streak before it hits 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Task", "toolu_02"),  # resets to 0
                make_tool_use_line("Grep", "toolu_03"),  # streak = 1
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert output == {}, f"Expected empty output after Task reset, got: {output}"


class TestExemptTools:
    """Test that exempt tools (Skill) do not affect streak counting."""

    def test_skill_does_not_increment_streak(self):
        """Skill tool calls should not increment the streak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Skill", "toolu_01"),
                make_tool_use_line("Skill", "toolu_02"),
                make_tool_use_line("Skill", "toolu_03"),
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state["streak"] == 0, "Skill calls should not increment streak"

    def test_skill_does_not_reset_streak(self):
        """Skill tool calls should not reset an existing streak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),  # streak = 1
                make_tool_use_line("Skill", "toolu_02"),  # neutral — streak stays 1
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state["streak"] == 1, "Skill should not reset streak"

    def test_skill_between_non_task_calls_does_not_interrupt_streak(self):
        """Skill call between non-Task calls should not break streak accumulation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),   # streak = 1
                make_tool_use_line("Skill", "toolu_02"),  # neutral
                make_tool_use_line("Read", "toolu_03"),   # streak = 2 → advisory fires
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert "hookSpecificOutput" in output, (
                "Advisory should fire at streak 2 even with Skill call in between"
            )

    def test_ask_user_question_is_neutral(self):
        """AskUserQuestion should not increment or reset the streak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),          # streak = 1
                make_tool_use_line("AskUserQuestion", "toolu_02"),  # neutral
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state["streak"] == 1, "AskUserQuestion should not affect streak"

    def test_task_create_is_neutral(self):
        """TaskCreate should not increment or reset the streak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),      # streak = 1
                make_tool_use_line("TaskCreate", "toolu_02"),  # neutral
            ], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state["streak"] == 1, "TaskCreate should not affect streak"

    def test_mixing_new_exempt_tools_with_non_exempt_preserves_streak_behavior(self):
        """Mixing new exempt tools among non-exempt calls should not change streak accumulation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),       # streak = 1
                make_tool_use_line("TaskList", "toolu_02"),   # neutral
                make_tool_use_line("TaskUpdate", "toolu_03"), # neutral
                make_tool_use_line("EnterPlanMode", "toolu_04"),  # neutral
                make_tool_use_line("Read", "toolu_05"),       # streak = 2 → advisory fires
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert "hookSpecificOutput" in output, (
                "Advisory should fire at streak 2 with exempt tools interspersed"
            )
            state = get_state()
            assert state["streak"] == 2, (
                "Exempt orchestration tools should not count toward or reset streak"
            )


class TestAdvisoryContent:
    """Test that advisory output has the correct structure when triggered."""

    def test_advisory_is_non_empty_string(self):
        """Advisory additionalContext should be a non-empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
                make_tool_use_line("Grep", "toolu_03"),
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            advisory = output["hookSpecificOutput"]["additionalContext"]
            assert isinstance(advisory, str) and len(advisory) > 0

    def test_advisory_is_string_not_structured_data(self):
        """Advisory should be a plain string, not a dict or list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
                make_tool_use_line("Grep", "toolu_03"),
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            advisory = output["hookSpecificOutput"]["additionalContext"]
            assert isinstance(advisory, str)


class TestOffsetTracking:
    """Test that offset tracking correctly reads only new content."""

    def test_offset_advances_after_read(self):
        """State offset should advance after reading transcript content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            assert state["offset"] > 0, "Offset should advance after reading content"

    def test_new_lines_only_counted_once(self):
        """Lines read in a previous call should not be re-counted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"

            # First call: write 2 lines — advisory fires at streak=2
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
            ], transcript)
            run_hook(transcript_path=str(transcript), clear_state=True)
            state_after_first = get_state()
            assert state_after_first["streak"] == 2

            # Second call: append 1 more line (don't clear state)
            append_transcript([make_tool_use_line("Grep", "toolu_03")], transcript)
            run_hook(transcript_path=str(transcript), clear_state=False)
            state_after_second = get_state()

            # Streak should be 3 (2 + 1), not 5 (re-reading all 3 lines from start)
            assert state_after_second["streak"] == 3, (
                f"Expected streak 3, got {state_after_second['streak']}. "
                "Previous lines should not be re-counted."
            )

    def test_empty_transcript_keeps_streak_unchanged(self):
        """If no new content, streak should remain at its previous value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)
            state_after_first = get_state()
            assert state_after_first["streak"] == 1

            # Run again with no new content (offset is at end of file)
            run_hook(transcript_path=str(transcript), clear_state=False)
            state_after_second = get_state()

            assert state_after_second["streak"] == 1, (
                "Streak should not change when there is no new transcript content"
            )


class TestStateFilePersistence:
    """Test that state persists correctly across calls."""

    def test_state_file_created_on_first_call(self):
        """State file should be created on first hook call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None, "State file should be created"

    def test_state_has_correct_fields(self):
        """State file should contain offset, streak, task_calls, and advisory_fired fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert "offset" in state
            assert "streak" in state
            assert "task_calls" in state
            assert "advisory_fired" in state
            assert isinstance(state["offset"], int)
            assert isinstance(state["streak"], int)
            assert isinstance(state["task_calls"], int)
            assert isinstance(state["advisory_fired"], bool)

    def test_state_persists_between_calls(self):
        """Streak state should accumulate correctly across multiple hook calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"

            # First call: streak = 1, no advisory
            write_transcript([make_tool_use_line("Bash", "toolu_01")], transcript)
            run_hook(transcript_path=str(transcript), clear_state=True)
            assert get_state()["streak"] == 1

            # Second call: streak = 2, advisory fires
            append_transcript([make_tool_use_line("Read", "toolu_02")], transcript)
            output = run_hook(transcript_path=str(transcript), clear_state=False)
            assert get_state()["streak"] == 2
            assert "hookSpecificOutput" in output, "Advisory should fire at streak 2"
            assert get_state()["advisory_fired"] == True

            # Third call: streak = 3, advisory already fired — no repeat
            append_transcript([make_tool_use_line("Grep", "toolu_03")], transcript)
            output_third = run_hook(transcript_path=str(transcript), clear_state=False)
            assert get_state()["streak"] == 3
            assert output_third == {}, "Advisory should not fire again at streak 3"


class TestGracefulErrorHandling:
    """Test that the hook handles errors gracefully."""

    def test_malformed_json_input_returns_empty(self):
        """Hook should return {} on malformed JSON input."""
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
        assert output == {}, "Malformed JSON should return {}"

    def test_missing_transcript_path_returns_empty(self):
        """Hook should return {} when transcript_path is missing."""
        output = run_hook(transcript_path="", clear_state=True)
        assert output == {}, f"Missing transcript path should return {{}}, got: {output}"

    def test_nonexistent_transcript_returns_empty(self):
        """Hook should return {} when transcript file does not exist."""
        output = run_hook(
            transcript_path="/tmp/nonexistent-transcript-xyz.jsonl",
            clear_state=True,
        )
        assert output == {}, f"Nonexistent transcript should return {{}}, got: {output}"

    def test_corrupt_state_file_handled_gracefully(self):
        """Hook should recover from a corrupt state file."""
        TEST_STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = TEST_STATE_DIR / f"{DEFAULT_SESSION_ID}-delegation.json"
        state_file.write_text("this is not json {{{{")

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            # Should not crash — corrupt state should be reset to defaults
            output = run_hook(
                transcript_path=str(transcript),
                clear_state=False,  # Don't clear — we want to test the corrupt file
            )
            assert isinstance(output, dict), "Hook should return a dict even with corrupt state"

    def test_missing_fields_handled_gracefully(self):
        """Hook should handle missing optional fields without crashing."""
        env = os.environ.copy()
        env["CLAUDE_HOOK_STATE_DIR"] = str(TEST_STATE_DIR)
        input_data = {"session_id": "minimal-session-delegation"}
        result = subprocess.run(
            ["uv", "run", "--script", str(HOOK_PATH)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
        )
        output = json.loads(result.stdout)
        assert isinstance(output, dict), "Output should be a dict"

    def test_transcript_with_non_jsonl_lines_handled(self):
        """Hook should skip non-JSONL lines in the transcript gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            # Mix valid and invalid lines
            transcript.write_text(
                "not json\n"
                + make_tool_use_line("Bash") + "\n"
                + "also not json\n"
                + make_tool_use_line("Read") + "\n"
            )

            run_hook(transcript_path=str(transcript), clear_state=True)

            state = get_state()
            assert state is not None
            # Only 2 valid tool_use lines should be counted
            assert state["streak"] == 2


class TestOutputFormat:
    """Test output format correctness."""

    def test_no_advisory_output_is_empty_dict(self):
        """When no advisory fires, output must be exactly {}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([make_tool_use_line("Bash")], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)
            assert output == {}

    def test_advisory_output_has_correct_structure(self):
        """Advisory output must have hookSpecificOutput with hookEventName and additionalContext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "transcript.jsonl"
            write_transcript([
                make_tool_use_line("Bash", "toolu_01"),
                make_tool_use_line("Read", "toolu_02"),
                make_tool_use_line("Grep", "toolu_03"),
            ], transcript)

            output = run_hook(transcript_path=str(transcript), clear_state=True)

            assert "hookSpecificOutput" in output
            hook_output = output["hookSpecificOutput"]
            assert "hookEventName" in hook_output
            assert hook_output["hookEventName"] == "PostToolUse"
            assert "additionalContext" in hook_output
            assert isinstance(hook_output["additionalContext"], str)
            assert len(hook_output["additionalContext"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
