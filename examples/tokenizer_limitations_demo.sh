#!/usr/bin/env psh
# Demonstration of tokenizer quote handling issues in PSH
# See TODO.md "Tokenizer Issues" section

echo "=== Tokenizer Quote Handling Issues Demo ==="
echo

echo "Problem: Quotes within words included in token value"
echo "Example: a'b'c tokenizes as a'b'c instead of abc"
echo "Impact: Incorrect output for concatenated quoted strings"
echo

echo "1. Basic quote concatenation issue:"
echo "Command: echo a'b'c"
echo "Expected: abc"
echo "Actual:"
echo a'b'c
echo

echo "2. Mixed quote types:"
echo "Command: echo prefix'middle'\"end\""
echo "Expected: prefixmiddleend"
echo "Actual:"
echo prefix'middle'"end"
echo

echo "3. Multiple quoted segments:"
echo "Command: echo 'first''second''third'"
echo "Expected: firstsecondthird"
echo "Actual:"
echo 'first''second''third'
echo

echo "4. Quotes with variables:"
echo "Command: var=test; echo pre'$var'post"
echo "Expected: pretestpost"
echo "Actual:"
var=test
echo pre'$var'post
echo

echo "5. Empty quotes in concatenation:"
echo "Command: echo a''b"
echo "Expected: ab"
echo "Actual:"
echo a''b
echo

echo "6. Nested quote handling:"
echo "Command: echo outer'inner\"nested\"inner'outer"
echo "Expected: outerinner\"nested\"innerouter"
echo "Actual:"
echo outer'inner"nested"inner'outer
echo

echo
echo "Note: These examples show how the tokenizer preserves quote characters"
echo "in the final output instead of properly processing concatenated quoted strings."