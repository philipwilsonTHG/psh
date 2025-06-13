# Brace Expansion Phase 2: Sequence Expansion

## Overview

This document outlines the implementation plan for Phase 2 of brace expansion, adding support for sequence expansion patterns like `{1..10}`, `{a..z}`, and `{1..20..2}`.

## Sequence Expansion Syntax

### Numeric Sequences
- Basic: `{start..end}` (e.g., `{1..5}` → `1 2 3 4 5`)
- With increment: `{start..end..increment}` (e.g., `{1..10..2}` → `1 3 5 7 9`)
- Reverse: `{10..1}` → `10 9 8 7 6 5 4 3 2 1`
- Negative: `{-3..3}` → `-3 -2 -1 0 1 2 3`
- Zero-padded: `{01..10}` → `01 02 03 04 05 06 07 08 09 10`

### Character Sequences
- Basic: `{a..z}` → `a b c d ... z`
- Reverse: `{z..a}` → `z y x ... a`
- With increment: `{a..z..3}` → `a d g j m p s v y`
- Cross-case: `{A..z}` includes all ASCII characters from A to z

### Increment Behavior
- Increment is optional (defaults to 1)
- Direction is auto-determined from start/end
- Sign of increment is ignored
- Increment of 0 treated as 1

## Implementation Plan

### 1. Enhance `_expand_one_brace()` method
Currently returns `[text]` for sequences. Need to:
- Detect sequence pattern with regex
- Parse start, end, and optional increment
- Call appropriate expansion method

### 2. Add `_expand_sequence()` method
```python
def _expand_sequence(self, content: str) -> List[str]:
    """Expand sequence like 1..10 or a..z."""
    # Parse content for start..end[..increment]
    # Determine if numeric or character sequence
    # Generate appropriate sequence
    # Handle zero-padding for numeric sequences
```

### 3. Add helper methods
- `_parse_sequence()`: Extract start, end, increment from content
- `_expand_numeric_sequence()`: Handle numeric sequences with padding
- `_expand_char_sequence()`: Handle character sequences
- `_determine_padding()`: Calculate zero-padding width

### 4. Validation
- Ensure start and end are same type (both numeric or both single chars)
- Reject invalid patterns (mixed types, non-ASCII, floats)
- Handle edge cases gracefully

## Test Strategy

### Numeric Sequence Tests
```python
def test_numeric_sequence_expansion():
    assert expand("{1..5}") == "1 2 3 4 5"
    assert expand("{5..1}") == "5 4 3 2 1"
    assert expand("{0..20..5}") == "0 5 10 15 20"
    assert expand("{01..10}") == "01 02 03 04 05 06 07 08 09 10"
    assert expand("{-5..5}") == "-5 -4 -3 -2 -1 0 1 2 3 4 5"
```

### Character Sequence Tests
```python
def test_char_sequence_expansion():
    assert expand("{a..e}") == "a b c d e"
    assert expand("{e..a}") == "e d c b a"
    assert expand("{a..z..5}") == "a f k p u z"
    assert expand("{A..C}") == "A B C"
```

### Invalid Sequence Tests
```python
def test_invalid_sequences():
    assert expand("{1..a}") == "{1..a}"  # Mixed types
    assert expand("{1.5..5.5}") == "{1.5..5.5}"  # Floats
    assert expand("{@..G}") == "{@..G}"  # Invalid start char
```

### Integration Tests
```python
def test_sequence_with_prefix_suffix():
    assert expand("file{1..3}.txt") == "file1.txt file2.txt file3.txt"
    assert expand("test_{a..c}_end") == "test_a_end test_b_end test_c_end"
```

## Edge Cases to Handle

1. **Zero padding edge cases**:
   - `{-05..05}` should pad appropriately
   - `{1..010}` should use 3-digit padding
   
2. **ASCII boundary cases**:
   - `{X..c}` crosses case boundary
   - Should include non-letter ASCII chars
   
3. **Memory limits**:
   - `{1..1000000}` could exceed limits
   - Apply same MAX_EXPANSION_ITEMS check

4. **Nested sequences**:
   - `{{1..3},{a..c}}` should work
   - Order matters for expansion

## Implementation Order

1. Start with numeric sequences (most common use case)
2. Add character sequences
3. Add increment support for both
4. Add zero-padding support
5. Comprehensive testing and edge case handling

## Backward Compatibility

- Phase 1 functionality must remain intact
- All existing tests must continue to pass
- Sequence expansion happens at same stage as list expansion