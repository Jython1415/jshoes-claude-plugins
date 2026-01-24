Use `uv run` or `uv run --script` over `python` when running Python files, unless specified otherwise

For temporary Python scripts: use `create_file` to write the script, `uv run` to execute it, then clean up with `rm`
- Example: `create_file(_temp_script.py)` → `uv run _temp_script.py` → `rm _temp_script.py`
- Works in sandbox mode (unlike heredoc which creates files in `/tmp/`)
- For temporary Python scripts, use inline dependencies (PEP 723) and run with `uv`

When creating temporary files, DO NOT put them in /tmp/claude/. Put them in the project directory.

Use emojis only when directed to do so

If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially. For example, when reading 3 files, run 3 tool calls in parallel to read all 3 files into context at the same time. Maximize use of parallel tool calls where possible to increase speed and efficiency. However, if some tool calls depend on previous calls to inform dependent values like the parameters, do NOT call these tools in parallel and instead call them sequentially. Never use placeholders or guess missing parameters in tool calls.

If a task will take more than 5–8 tool calls, then prefer to hand it off to a subagent and have it report back to you. You are the orchestrator. Use subagents in a "call stack" style.

If you create any temporary new files, scripts, or helper files for iteration, clean up these files by removing them at the end of the task.

Take ownership over the tasks in the repositories and projects you manage, responding in ways that lessen the user's mental overhead.

## Testing Philosophy for Hooks

When writing tests for hooks in this repository:

### Test Behavior, Not Content

**DO**:
- Verify that guidance is presented when expected
- Test trigger conditions (what activates the hook)
- Validate JSON output structure
- Check that hook activates/deactivates correctly

**DON'T**:
- Validate specific strings or phrases in guidance text
- Check for particular examples in output
- Assert on exact wording or formatting
- Test content that may evolve over time

### Rationale

Guidance messages should be improvable without breaking tests. Tests should validate that hooks work correctly, not freeze the specific content of their messages.

### Examples

❌ **Bad Test** (brittle, tests content):
```python
def test_guidance_includes_examples():
    output = run_hook("Bash", 'git commit -m "Test"')
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "Co-authored-by" in context  # Breaks if wording changes
    assert "claude.ai/code" in context  # Brittle
```

✅ **Good Test** (robust, tests behavior):
```python
def test_guidance_presented_for_commit():
    output = run_hook("Bash", 'git commit -m "Test"')
    assert "hookSpecificOutput" in output  # Hook triggered
    assert "additionalContext" in output["hookSpecificOutput"]  # Guidance exists
    assert len(output["hookSpecificOutput"]["additionalContext"]) > 0  # Non-empty
```

### Test Categories

1. **Trigger Tests**: Verify hook activates on correct inputs
2. **Non-Trigger Tests**: Verify hook stays silent on incorrect inputs
3. **Structure Tests**: Validate JSON format and required fields
4. **Edge Case Tests**: Handle malformed input, missing fields, etc.

This philosophy applies to all hooks in `.claude/hooks/`.
