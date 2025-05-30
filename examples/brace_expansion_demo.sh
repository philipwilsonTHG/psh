#!/usr/bin/env psh

# Brace Expansion Demo - Showcasing complete implementation

echo "=== List Expansion (Phase 1) ==="
echo "Simple list: {red,green,blue}"
echo {red,green,blue}
echo

echo "With prefix/suffix: file{1,2,3}.txt"
echo file{1,2,3}.txt
echo

echo "Nested lists: {a,b{1,2}}"
echo {a,b{1,2}}
echo

echo "=== Sequence Expansion (Phase 2) ==="
echo "Numeric sequence: {1..10}"
echo {1..10}
echo

echo "Reverse sequence: {10..1}"
echo {10..1}
echo

echo "Character sequence: {a..f}"
echo {a..f}
echo

echo "With increment: {0..20..5}"
echo {0..20..5}
echo

echo "Zero-padded: {01..10}"
echo {01..10}
echo

echo "Cross-zero padding: {-03..03}"
echo {-03..03}
echo

echo "=== Combined Expansions ==="
echo "List with sequences: {{1..3},{a..c}}"
echo {{1..3},{a..c}}
echo

echo "Multiple expansions: {A,B}{1..3}"
echo {A,B}{1..3}
echo

echo "=== Practical Examples ==="
echo "Create backup files: cp important.conf{,.bak}"
echo "Would execute: cp important.conf important.conf.bak"
echo

echo "Create test files: touch test_{001..005}.dat"
echo "Would create: test_001.dat test_002.dat test_003.dat test_004.dat test_005.dat"
echo

echo "Generate URLs: curl https://example.com/page{1..5}.html"
echo "Would fetch 5 pages"
echo