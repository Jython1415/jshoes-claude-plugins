#!/usr/bin/env bash
# Wrapper to run hooks with graceful failure handling
# Usage: run-with-fallback.sh <fail-mode> <hook-script>
# fail-mode: "open" (advisory) or "closed" (safety-critical)
#
# Optional env var: JSHOES_HOOK_LOG_DIR — if set, appends a JSONL entry per
# invocation to $JSHOES_HOOK_LOG_DIR/{session_id}.jsonl capturing both the
# hook input and output. Logging errors are silently swallowed.

set -uo pipefail

FAIL_MODE="$1"
HOOK_SCRIPT="$2"
HOOK_NAME="$(basename "$HOOK_SCRIPT")"

# Read stdin once so it can be forwarded to the hook and logged.
INPUT=$(cat)

# _log_hook_event <output>
# Appends a JSONL entry to $JSHOES_HOOK_LOG_DIR/{session_id}.jsonl.
# No-op when JSHOES_HOOK_LOG_DIR is unset or empty. Never fails.
_log_hook_event() {
    local output="$1"
    local log_dir="${JSHOES_HOOK_LOG_DIR:-}"
    [[ -z "$log_dir" ]] && return 0
    mkdir -p "$log_dir" 2>/dev/null || return 0
    HOOK_LOG_HOOK_NAME="$HOOK_NAME" \
    HOOK_LOG_DIR="$log_dir" \
    HOOK_LOG_INPUT="$INPUT" \
    HOOK_LOG_OUTPUT="$output" \
    uv run python -c "
import json, datetime, os

hook_name  = os.environ['HOOK_LOG_HOOK_NAME']
log_dir    = os.environ['HOOK_LOG_DIR']
raw_input  = os.environ['HOOK_LOG_INPUT']
raw_output = os.environ['HOOK_LOG_OUTPUT']

try:
    input_data = json.loads(raw_input)
except Exception:
    input_data = raw_input

session_id = input_data.get('session_id', 'unknown') if isinstance(input_data, dict) else 'unknown'

try:
    output_data = json.loads(raw_output)
except Exception:
    output_data = raw_output

entry = {
    'ts':     datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'hook':   hook_name,
    'input':  input_data,
    'output': output_data,
}

with open(f'{log_dir}/{session_id}.jsonl', 'a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null || return 0
}

# Check if hook file exists
if [[ ! -f "$HOOK_SCRIPT" ]]; then
    if [[ "$FAIL_MODE" == "closed" ]]; then
        OUTPUT="{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\", \"permissionDecisionReason\": \"Safety hook not found: $HOOK_NAME. Blocking for safety. Check .claude/hooks/ directory.\"}}"
    else
        OUTPUT="{\"hookSpecificOutput\": {\"additionalContext\": \"Warning: Hook not found: $HOOK_NAME. Proceeding without validation.\"}}"
    fi
    echo "$OUTPUT"
    _log_hook_event "$OUTPUT"
    exit 0
fi

# Check if hook is executable
if [[ ! -x "$HOOK_SCRIPT" ]]; then
    chmod +x "$HOOK_SCRIPT" 2>/dev/null || true
fi

# Try to execute the hook
if OUTPUT=$(echo "$INPUT" | uv run --script "$HOOK_SCRIPT"); then
    echo "$OUTPUT"
    _log_hook_event "$OUTPUT"
    exit 0
fi

# Hook execution failed
if [[ "$FAIL_MODE" == "closed" ]]; then
    OUTPUT="{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\", \"permissionDecisionReason\": \"Safety hook execution failed: $HOOK_NAME. Blocking for safety.\"}}"
else
    OUTPUT="{\"hookSpecificOutput\": {\"additionalContext\": \"Warning: Hook execution failed: $HOOK_NAME. Check hook logs for details.\"}}"
fi
echo "$OUTPUT"
_log_hook_event "$OUTPUT"
exit 0
