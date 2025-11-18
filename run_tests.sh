#!/bin/bash
# Simple shell script wrapper for PSH test runner
# For full options, use: python run_tests.py --help

set -e

echo "PSH Test Runner"
echo "==============="
echo ""

# Check if user wants all tests with -s
if [[ "$1" == "-s" ]] || [[ "$1" == "--all-nocapture" ]]; then
    echo "Running ALL tests with capture disabled..."
    python -m pytest tests/ -s "${@:2}"
    exit $?
fi

# Check if user wants subshells only
if [[ "$1" == "--subshells-only" ]]; then
    echo "Running subshell tests only..."
    python -m pytest tests/integration/subshells/ -s "${@:2}"
    exit $?
fi

# Smart mode (default)
echo "Running tests in smart mode (recommended)..."
echo ""
python run_tests.py "$@"
