#!/usr/bin/env psh
# Demonstration of parser limitations in PSH
# See TODO.md "Parser Limitations" section

echo "=== Parser Limitations Demo ==="
echo

echo "1. Composite Argument Quote Handling"
echo "   Problem: Parser loses quote information when creating composite arguments"
echo "   Example: file'*'.txt may incorrectly expand wildcards"
echo

# Create test files for demonstration
echo "Creating test files..."
touch file1.txt file2.txt file_star.txt "file*.txt"

echo "Test files created:"
ls -1 file*.txt
echo

echo "Now testing composite argument quote handling:"
echo

# This should NOT expand the * wildcard because it's quoted
echo "Command: ls file'*'.txt"
echo "Expected: Should only match file*.txt (literal asterisk)"
echo "Actual result:"
ls file'*'.txt 2>/dev/null || echo "Error: No such file (wildcard expanded incorrectly)"
echo

# Compare with bash behavior
echo "For comparison, in bash this would work correctly:"
echo "bash -c \"ls file'*'.txt\" (would find file*.txt)"
echo

echo "2. Another composite quote example:"
echo "Command: echo prefix'quoted'suffix"
echo "Expected: prefixquotedsuffix"
echo "Actual:"
echo prefix'quoted'suffix
echo

echo "3. Mixed quoting in composite arguments:"
echo "Command: echo \"double\"'single'unquoted"
echo "Expected: doublesinglunquoted"
echo "Actual:"
echo "double"'single'unquoted
echo

# Cleanup
rm -f file1.txt file2.txt file_star.txt "file*.txt"