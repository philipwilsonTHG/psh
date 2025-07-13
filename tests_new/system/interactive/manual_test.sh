#!/bin/bash
# Manual test script for PSH interactive features

echo "PSH Interactive Feature Test Script"
echo "=================================="
echo

# Function to pause and wait for user
pause() {
    echo
    echo "Press Enter to continue..."
    read
}

# Start PSH
echo "Starting PSH..."
python -m psh --norc << 'TESTSCRIPT'

echo "=== Test 1: Arrow Key Navigation ==="
echo "Type: hello world"
echo "Press left arrow 5 times"
echo "Type: brave "
echo "Press Enter"
echo "Expected: hello brave world"
pause

echo "=== Test 2: History Navigation ==="
echo "Commands will be executed:"
echo one
echo two  
echo three
echo "Now press up arrow - should see 'echo three'"
echo "Press up again - should see 'echo two'"
pause

echo "=== Test 3: Control Keys ==="
echo "Type: test line"
echo "Press Ctrl-A - cursor should go to beginning"
echo "Press Ctrl-E - cursor should go to end"
echo "Press Ctrl-U - line should be cleared"
pause

echo "=== Test 4: Tab Completion ==="
touch test_file.txt
echo "Type: echo test_f"
echo "Press Tab - should complete to test_file.txt"
rm test_file.txt
pause

echo "All tests complete!"
exit

TESTSCRIPT
