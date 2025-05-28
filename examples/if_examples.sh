#!/usr/bin/env psh

# Examples of if/then/else/fi control structures in psh

echo "=== Basic if statement examples ==="

# Simple if with true condition
if true; then echo "This will be printed"; fi

# Simple if with false condition  
if false; then echo "This will NOT be printed"; fi

echo ""
echo "=== if/else examples ==="

# If/else with string comparison
if [ "hello" = "hello" ]; then echo "Strings match!"; else echo "Strings don't match"; fi

if [ "hello" = "world" ]; then echo "Strings match!"; else echo "Strings don't match"; fi

echo ""
echo "=== Using test command ==="

# Test if file exists
if test -f "/etc/passwd"; then echo "/etc/passwd exists"; else echo "/etc/passwd does not exist"; fi

# Test if directory exists
if [ -d "/tmp" ]; then echo "/tmp directory exists"; fi

# Test string length
if [ -z "" ]; then echo "Empty string detected"; fi

if [ -n "hello" ]; then echo "Non-empty string detected"; fi

echo ""
echo "=== Numeric comparisons ==="

# Numeric equality
if [ 5 -eq 5 ]; then echo "5 equals 5"; fi

# Numeric inequality  
if [ 5 -ne 3 ]; then echo "5 does not equal 3"; fi

# Less than
if [ 3 -lt 5 ]; then echo "3 is less than 5"; fi

# Greater than
if [ 5 -gt 3 ]; then echo "5 is greater than 3"; fi

echo ""
echo "=== Using command exit status ==="

# Test based on command success/failure
if echo "test command"; then echo "echo command succeeded (exit code 0)"; fi

# Use exit status of external commands
if true && echo "chained success"; then echo "Both commands succeeded"; fi

echo ""
echo "=== Complex conditions with && and || ==="

# If statement with complex condition
if echo "testing" && true; then echo "Complex condition with && succeeded"; fi

if false || true; then echo "Complex condition with || succeeded"; fi

echo ""
echo "All if/then/else/fi examples completed!"