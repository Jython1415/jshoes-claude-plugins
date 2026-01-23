# Test Improvement Implementation Plan

## Executive Summary

All 11 test files were reviewed by Sonnet subagents. The test files demonstrate **excellent code quality and comprehensive coverage**, but **nearly all violate the "test behavior, not content" philosophy** documented in CLAUDE.md.

### Overall Statistics
- **Total test files**: 11
- **Total test functions**: 312
- **Files with philosophy violations**: 10 out of 11
- **Critical bug found**: 1 (auto-unsandbox-pbcopy hook)
- **Estimated refactoring effort**: ~12-15 hours

---

## Priority 1: Critical Bug Fix

### 1. Fix auto-unsandbox-pbcopy Hook Implementation

**File**: `.claude/hooks/auto-unsandbox-pbcopy.py`

**Problem**: Hook uses substring matching (`"pbcopy" in command`) which incorrectly triggers on:
- `echo "pbcopy is a tool"` ✗
- `cat pbcopy.txt` ✗
- `echo $pbcopy_cmd` ✗
- `mypbcopy_script.sh` ✗

**Solution**: Use word boundary matching
```python
# BEFORE
if "pbcopy" in command:

# AFTER
import re
if re.search(r'\bpbcopy\b', command):
```

**Associated Test Changes**: `.claude/hooks/tests/test_auto_unsandbox_pbcopy.py`
- Convert false-positive trigger tests (lines 149-198) to non-trigger tests
- Verify word boundary behavior works correctly

---

## Priority 2: Remove Content-Testing Violations

### Files Ranked by Severity (Most violations → Least)

#### 2.1 test_detect_heredoc_errors.py (11 violations) ⚠️ HIGHEST

**Lines to Remove/Refactor**:
- Lines 89, 96, 104, 121, 140, 304: Remove `HEREDOC_ERROR in context` assertions
- Lines 227-263: **REMOVE** entire `test_guidance_content_includes_key_phrases` function
- Lines 264-272: **REMOVE** entire `test_guidance_shows_practical_examples` function
- Lines 274-280: **REMOVE** entire `test_error_message_included_in_context` function
- Lines 404-411: **REMOVE** entire `test_workaround_count` function
- Lines 413-423: **REMOVE** entire `test_guidance_format_readable` function

**Replacement Pattern**:
```python
# Replace all content checks with:
assert "hookSpecificOutput" in output
assert "additionalContext" in output["hookSpecificOutput"]
assert len(output["hookSpecificOutput"]["additionalContext"]) > 0
```

---

#### 2.2 test_gpg_signing_helper.py (9 violations)

**Lines to Remove/Refactor**:
- Lines 116-118, 126: Remove `--no-gpg-sign` content checks
- Lines 134-135: Remove sandbox mention checks
- Lines 142-144: Remove emphasis text checks
- Lines 380-381, 394-396, 429-431: Remove flag content checks
- Lines 120-127: **REMOVE** entire `test_guidance_includes_no_gpg_sign_flag` function
- Lines 129-135: **REMOVE** entire `test_guidance_mentions_sandbox_mode` function
- Lines 137-144: **REMOVE** entire `test_guidance_emphasizes_importance` function
- Lines 465-472: **REMOVE** entire `test_additional_context_includes_command_example` function

**Keep** (Good structural test):
- Lines 474-480: `test_no_decision_field_in_output` ✓

---

#### 2.3 test_gh_fallback_helper.py (Worst philosophy adherence: 3/10)

**Lines to Remove/Refactor**:
- Lines 105-106: Remove "GH CLI NOT FOUND" and "GITHUB_TOKEN DETECTED" checks
- Lines 296-343: **REFACTOR** large parametrized test - remove curl, jq, api.github.com content checks
- Lines 469-470: Remove header format checks

**Strategy**: Test that different scenarios (token vs no token) produce different guidance, but don't check specific content.

---

#### 2.4 test_detect_cd_pattern.py (5 violations)

**Lines to Remove/Refactor**:
- Lines 62-63: Remove "GLOBAL CD DETECTED" check
- Lines 70-74: **REMOVE** entire `test_guidance_includes_target_dir` function
- Lines 76-81: **REMOVE** entire `test_guidance_includes_subshell_alternative` function
- Line 68, 74, 80-81: Refactor content assertions

---

#### 2.5 test_suggest_uv_for_missing_deps.py (Multiple violations)

**Lines to Remove/Refactor**:
- Lines 398-404: **REMOVE** `test_uv_available_suggests_uv_run_with` function
- Lines 406-414: **REMOVE** `test_uv_available_suggests_pep723` function
- Lines 416-439: **REMOVE** similar content-checking tests for pip, venv, URLs
- Lines 106-328: **KEEP** but add comment explaining module extraction tests verify behavior

**Replacement**:
```python
def test_uv_available_provides_guidance(self):
    output = run_hook_with_error("Bash", "python script.py", error_msg, uv_available=True)
    assert "hookSpecificOutput" in output
    assert len(output["hookSpecificOutput"]["additionalContext"]) > 100

def test_uv_availability_affects_guidance(self):
    with_uv = run_hook_with_error(..., uv_available=True)
    without_uv = run_hook_with_error(..., uv_available=False)
    assert with_uv["hookSpecificOutput"]["additionalContext"] != \
           without_uv["hookSpecificOutput"]["additionalContext"]
```

---

#### 2.6 test_prefer_modern_tools.py (Lines 433-458)

**Lines to Remove/Refactor**:
- Lines 433-438: **REMOVE** `test_find_suggestion_mentions_fd_syntax`
- Lines 440-458: **REMOVE** similar tests for "rg", "ripgrep", "faster", "gitignore"

**Replacement**:
```python
def test_find_suggestion_provides_guidance(self):
    output = run_hook("Bash", 'find . -name "*.py"', fd_available=True)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert len(context) > 50  # Has substantial guidance
```

---

#### 2.7 test_gh_authorship_attribution.py (Philosophy: 4/10)

**Lines to Remove/Refactor**:
- Lines 72-73, 151: Remove "AUTHORSHIP ATTRIBUTION REMINDER", "Co-authored-by" checks
- Lines 296-343: **REFACTOR** parametrized test - validate behavior (cooldown works) not content

---

#### 2.8 test_prefer_gh_for_own_repos.py (Philosophy: 6/10)

**Lines to Remove/Refactor**:
- Lines 119-120: Remove "gh" and TARGET_OWNER content checks
- Lines 358-401: **REFACTOR** tests validating suggestion content

---

#### 2.9 test_gh_web_fallback.py (Philosophy: 7/10) ✓ Best adherence

**Lines to Remove/Refactor**:
- Lines 147, 400-412: Remove "GitHub API", "REST", "jq", "curl" checks
- Minimal changes needed - mostly compliant

---

#### 2.10 test_normalize_line_endings.py (Philosophy: Good) ✓

**Lines to Refactor** (optional, low priority):
- Line 176: Consider changing `assert reason == "Normalized line endings"` to `assert len(reason) > 0`

**Note**: This file is already mostly compliant. Changes are optional.

---

## Priority 3: Create Shared Test Utilities

### 3.1 Create conftest.py

**File**: `.claude/hooks/tests/conftest.py`

**Purpose**: Reduce code duplication across all test files

**Contents**:
```python
"""Shared pytest configuration and utilities for hook tests."""
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

def assert_hook_triggered_with_guidance(output: dict) -> None:
    """Assert hook triggered and provided guidance.

    This is the standard assertion for testing that a hook activated
    without checking specific guidance content.
    """
    assert "hookSpecificOutput" in output
    assert "additionalContext" in output["hookSpecificOutput"]
    assert len(output["hookSpecificOutput"]["additionalContext"]) > 0

def assert_hook_silent(output: dict) -> None:
    """Assert hook did not trigger."""
    assert output == {}

def assert_valid_json_output(output: dict, expected_event: str) -> None:
    """Assert output has valid JSON structure for given event type."""
    assert isinstance(output, dict)
    if output:  # If hook triggered
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"].get("hookEvent") == expected_event
```

**Benefits**:
- Enforces philosophy adherence by providing standard assertion helpers
- Reduces duplication of ~50 lines per test file
- Makes tests more readable

### 3.2 Update All Test Files

After creating `conftest.py`, update all test files to:
1. Import shared utilities: `from conftest import assert_hook_triggered_with_guidance, assert_hook_silent`
2. Replace duplicate assertions with helper functions
3. Remove redundant `main()` boilerplate if desired (pytest finds tests automatically)

---

## Priority 4: Add Missing Test Coverage

### 4.1 Add Hook Deactivation Tests

**Files**: All test files

**Missing Coverage**: None of the test files verify hook behavior when:
- Hook is disabled in settings
- Insufficient permissions granted

**New Tests to Add**:
```python
def test_hook_respects_disabled_setting(self):
    """Hook should not trigger when disabled in settings."""
    # Mock settings.json with hook disabled
    # Verify hook stays silent even with triggering input

def test_hook_respects_permission_restrictions(self):
    """Hook should handle missing permissions gracefully."""
    # Test hook behavior with minimal permissions
```

### 4.2 Add Edge Cases

**Files**: test_prefer_modern_tools.py, test_suggest_uv_for_missing_deps.py

**Missing Tests**:
- Extremely long commands (performance/edge case)
- Commands with unusual characters (newlines, null bytes)
- Multiple missing modules in single error
- Concurrent/parallel execution safety

---

## Implementation Strategy

### Phase 1: Critical (Do First) - 2-3 hours
1. ✅ Fix auto-unsandbox-pbcopy hook word boundary bug
2. ✅ Update test_auto_unsandbox_pbcopy.py tests
3. ✅ Run tests to verify bug fix works

### Phase 2: High Priority - 6-8 hours
4. ✅ Refactor test_detect_heredoc_errors.py (most violations)
5. ✅ Refactor test_gpg_signing_helper.py
6. ✅ Refactor test_gh_fallback_helper.py
7. ✅ Refactor test_detect_cd_pattern.py
8. ✅ Run tests after each file to ensure no breakage

### Phase 3: Medium Priority - 3-4 hours
9. ✅ Refactor test_suggest_uv_for_missing_deps.py
10. ✅ Refactor test_prefer_modern_tools.py
11. ✅ Refactor test_gh_authorship_attribution.py
12. ✅ Refactor test_prefer_gh_for_own_repos.py
13. ✅ Refactor test_gh_web_fallback.py
14. ✅ Run full test suite

### Phase 4: Shared Utilities - 1 hour
15. ✅ Create conftest.py with shared utilities
16. ✅ Update all test files to use shared utilities
17. ✅ Run full test suite to verify

### Phase 5: Final Touches - 1 hour
18. ✅ Optionally refactor test_normalize_line_endings.py
19. ✅ Run full test suite
20. ✅ Update documentation if needed

---

## Handoff to Haiku Subagents

Each Haiku subagent will receive:
- Specific test file(s) to refactor
- Line numbers to remove/change
- Replacement code patterns
- Instructions to run tests after changes

### Agent Assignments

**Agent 1 (Critical)**:
- Fix `.claude/hooks/auto-unsandbox-pbcopy.py`
- Update `.claude/hooks/tests/test_auto_unsandbox_pbcopy.py`
- Run: `uv run pytest .claude/hooks/tests/test_auto_unsandbox_pbcopy.py -v`

**Agent 2 (High Priority)**:
- Refactor `.claude/hooks/tests/test_detect_heredoc_errors.py`
- Run: `uv run pytest .claude/hooks/tests/test_detect_heredoc_errors.py -v`

**Agent 3 (High Priority)**:
- Refactor `.claude/hooks/tests/test_gpg_signing_helper.py`
- Run: `uv run pytest .claude/hooks/tests/test_gpg_signing_helper.py -v`

**Agent 4 (High Priority)**:
- Refactor `.claude/hooks/tests/test_gh_fallback_helper.py`
- Refactor `.claude/hooks/tests/test_detect_cd_pattern.py`
- Run: `uv run pytest .claude/hooks/tests/test_gh_fallback_helper.py test_detect_cd_pattern.py -v`

**Agent 5 (Medium Priority)**:
- Refactor `.claude/hooks/tests/test_suggest_uv_for_missing_deps.py`
- Refactor `.claude/hooks/tests/test_prefer_modern_tools.py`
- Run: `uv run pytest .claude/hooks/tests/test_suggest_uv_for_missing_deps.py test_prefer_modern_tools.py -v`

**Agent 6 (Medium Priority)**:
- Refactor `.claude/hooks/tests/test_gh_authorship_attribution.py`
- Refactor `.claude/hooks/tests/test_prefer_gh_for_own_repos.py`
- Refactor `.claude/hooks/tests/test_gh_web_fallback.py`
- Run: `uv run pytest .claude/hooks/tests/test_gh_*.py -v`

**Agent 7 (Utilities)**:
- Create `.claude/hooks/tests/conftest.py`
- Update all test files to use shared utilities
- Run: `uv run pytest .claude/hooks/tests/ -v`

**Agent 8 (Final)**:
- Optionally refactor `.claude/hooks/tests/test_normalize_line_endings.py`
- Run full test suite: `uv run pytest .claude/hooks/tests/ -v`
- Verify all tests pass

---

## Success Criteria

### All Changes Must:
1. ✅ Remove content-checking assertions
2. ✅ Replace with behavior-checking assertions
3. ✅ Maintain or improve test coverage
4. ✅ Pass all existing tests (or fix legitimately broken ones)
5. ✅ Follow the testing philosophy in CLAUDE.md

### Final Verification:
```bash
# All tests should pass
uv run pytest .claude/hooks/tests/ -v

# No tests should check guidance content
grep -r "assert.*in context" .claude/hooks/tests/*.py | grep -v "hookSpecificOutput"
# Should return minimal/no results

# Verify philosophy compliance
grep -r "HEREDOC_ERROR\|Co-authored-by\|--no-gpg-sign" .claude/hooks/tests/*.py
# Should return no assertion lines
```

---

## Documentation Updates

After implementation, update:
1. `.claude/hooks/README.md` - Document testing philosophy adherence
2. `pyproject.toml` - No changes needed (already configured correctly)
3. This plan file - Mark as completed

---

## Estimated Timeline

- **Phase 1 (Critical)**: 2-3 hours
- **Phase 2 (High Priority)**: 6-8 hours
- **Phase 3 (Medium Priority)**: 3-4 hours
- **Phase 4 (Utilities)**: 1 hour
- **Phase 5 (Final)**: 1 hour

**Total**: 13-17 hours with thorough testing

Using Haiku subagents in parallel, this can be completed in **4-6 hours wall-clock time**.

---

## Notes for Implementation

- Each subagent should verify tests pass before completing
- If a test legitimately fails after refactoring, investigate whether the original test was catching a real bug
- Preserve all non-content behavioral tests (they're valuable!)
- Keep test organization and structure (it's excellent)
- Only change what's necessary for philosophy compliance
