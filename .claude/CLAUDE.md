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
