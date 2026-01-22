#!/usr/bin/env python3
# /// script
# dependencies = ["pytest>=7.0.0"]
# ///
"""
Test runner for all hook tests

Run all hook tests:
  uv run --script hooks/tests/run_tests.py

Run specific test file:
  uv run --script hooks/tests/test_detect_cd_pattern.py

Run with pytest directly:
  cd hooks/tests && uv run pytest -v
"""
import sys
import pytest
from pathlib import Path


def main():
    """Run all tests in the tests directory"""
    tests_dir = Path(__file__).parent

    print("Running all hook tests...\n")

    # Run pytest on the tests directory with verbose output
    args = [
        str(tests_dir),
        "-v",
        "--tb=short",
        "--color=yes"
    ]

    # Add any additional args passed to this script
    args.extend(sys.argv[1:])

    exit_code = pytest.main(args)

    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
