"""
Unit tests for ensure-tmpdir.py hook

This test suite validates that the hook creates TMPDIR when missing and is
otherwise silent. The hook runs on SessionStart — it receives session metadata
but only acts on the TMPDIR environment variable.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_PATH = Path(__file__).parent.parent / "ensure-tmpdir.py"


def run_hook(env: dict | None = None) -> dict:
    """Helper function to run the hook with SessionStart-shaped input and return parsed output.

    Invokes the hook using the current Python interpreter directly (not via
    uv) because the hook has no external dependencies. This avoids the issue
    where uv itself tries to create temp files inside TMPDIR — which would
    fail when the test intentionally points TMPDIR at a missing path.

    Args:
        env: Optional environment overrides. Pass None to use the current
             process environment. Pass a dict to override specific variables.
             To unset a variable, set its value to None in the dict.
    """
    input_data = {
        "session_id": "test-session",
        "source": "startup"
    }

    # Build the environment for the subprocess
    base_env = os.environ.copy()
    if env is not None:
        for key, value in env.items():
            if value is None:
                base_env.pop(key, None)
            else:
                base_env[key] = value

    # Use sys.executable (current Python) directly — the hook has no
    # external deps, so uv is not required here.
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=base_env
    )

    if result.returncode not in [0, 1]:  # 0 = success, 1 = expected error with {}
        raise RuntimeError(f"Hook failed: {result.stderr}")

    return json.loads(result.stdout)


class TestEnsureTmpdir:
    """Test suite for ensure-tmpdir hook"""

    def test_creates_missing_tmpdir(self):
        """Hook should create TMPDIR when it is set but the directory is missing"""
        with tempfile.TemporaryDirectory() as parent:
            missing_dir = os.path.join(parent, "tmpdir-that-does-not-exist")
            assert not os.path.isdir(missing_dir), "Pre-condition: directory should not exist"

            output = run_hook(env={"TMPDIR": missing_dir})

            assert output == {}, "Hook should return empty JSON"
            assert os.path.isdir(missing_dir), "Hook should have created the missing directory"

    def test_silent_when_tmpdir_exists(self):
        """Hook should return {} silently when TMPDIR already exists"""
        with tempfile.TemporaryDirectory() as existing_dir:
            output = run_hook(env={"TMPDIR": existing_dir})
            assert output == {}, "Hook should return empty JSON when TMPDIR exists"

    def test_silent_when_tmpdir_not_set(self):
        """Hook should return {} silently when TMPDIR is not set"""
        output = run_hook(env={"TMPDIR": None})
        assert output == {}, "Hook should return empty JSON when TMPDIR is unset"

    def test_json_output_is_valid(self):
        """Hook output should always be valid JSON"""
        output = run_hook(env={"TMPDIR": None})
        assert isinstance(output, dict), "Output should be a valid JSON dict"

    def test_malformed_input_returns_empty_json(self):
        """Hook should return {} gracefully on malformed input"""
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not valid json {{{",
            capture_output=True,
            text=True
        )
        assert result.returncode in [0, 1], "Hook should not crash on malformed input"
        assert result.stdout.strip() == "{}", "Hook should output {} on malformed input"

    def test_creates_nested_tmpdir(self):
        """Hook should create deeply nested TMPDIR paths"""
        with tempfile.TemporaryDirectory() as parent:
            nested_dir = os.path.join(parent, "a", "b", "c")
            assert not os.path.isdir(nested_dir)

            output = run_hook(env={"TMPDIR": nested_dir})

            assert output == {}, "Hook should return empty JSON"
            assert os.path.isdir(nested_dir), "Hook should create nested directories"

    def test_works_via_uv_with_missing_tmpdir(self):
        """Hook must work through uv run --script even when TMPDIR is missing.

        This is the critical integration test: the hook is invoked via
        run-with-fallback.sh which calls uv run --script. If the PEP 723
        header includes `dependencies = [...]`, uv tries to write temp files
        to TMPDIR during startup — failing before the hook code runs. The
        hook avoids this by using requires-python instead of dependencies.
        """
        with tempfile.TemporaryDirectory() as parent:
            missing_dir = os.path.join(parent, "uv-integration-test")
            assert not os.path.isdir(missing_dir)

            base_env = os.environ.copy()
            base_env["TMPDIR"] = missing_dir

            result = subprocess.run(
                ["uv", "run", "--script", str(HOOK_PATH)],
                input=json.dumps({"session_id": "test", "source": "startup"}),
                capture_output=True,
                text=True,
                env=base_env,
            )

            assert result.returncode == 0, f"uv run --script failed: {result.stderr}"
            assert json.loads(result.stdout) == {}
            assert os.path.isdir(missing_dir), "Hook should have created TMPDIR via uv"


def main():
    """Run tests when executed as a script"""
    import pytest

    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
