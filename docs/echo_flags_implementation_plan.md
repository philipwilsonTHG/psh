# Implementation Plan: echo -n and echo -e flags

## Overview

This document outlines the plan to implement the `-n` (suppress newline) and `-e` (interpret escapes) flags for the echo builtin in PSH.

## Current State

The echo builtin currently:
- Supports `-e` flag for basic escape sequences
- Always adds a newline at the end
- Handles the fork/pipeline issue by writing directly to fd 1 in child processes
- Does not support `-n` flag
- Does not support all escape sequences that bash does

## Implementation Goals

1. Add `-n` flag to suppress trailing newline
2. Enhance `-e` flag to support all bash escape sequences
3. Support combining flags (`echo -ne`, `echo -en`)
4. Maintain compatibility with existing tests
5. Fix the I/O redirection issue (use os.write instead of print)

## Detailed Implementation Plan

### Phase 1: Fix I/O Redirection Issue

**Problem**: Current implementation uses `print()` which doesn't respect file descriptor redirections properly.

**Solution**: 
- Replace `print()` with `os.write()` to the appropriate file descriptor
- Use `shell.stdout.fileno()` when available, fallback to fd 1

### Phase 2: Implement Flag Parsing

**Current**: Only checks for `-e` as the first argument

**New Approach**:
1. Parse all flags at the beginning of arguments
2. Support combined flags: `-ne`, `-en`, `-n -e`, etc.
3. Stop flag parsing at first non-flag argument
4. Handle `--` as explicit end of flags

**Flag Parsing Logic**:
```python
suppress_newline = False
interpret_escapes = False
arg_index = 1

while arg_index < len(args):
    arg = args[arg_index]
    if arg == '--':
        arg_index += 1
        break
    elif arg.startswith('-') and len(arg) > 1:
        for flag in arg[1:]:
            if flag == 'n':
                suppress_newline = True
            elif flag == 'e':
                interpret_escapes = True
            elif flag == 'E':
                interpret_escapes = False
            else:
                # Unknown flag - bash echo ignores it
                break
        arg_index += 1
    else:
        break
```

### Phase 3: Enhance Escape Sequence Support

**Current escape sequences**: \n, \t, \r, \b, \f, \a, \v, \\, \nnn (octal)

**Missing escape sequences**:
- `\c` - Suppress further output
- `\e` or `\E` - Escape character (ASCII 27)
- `\xhh` - Hex character
- `\uhhhh` - Unicode character (4 hex digits)
- `\Uhhhhhhhh` - Unicode character (8 hex digits)

**Implementation approach**:
1. Process `\c` first (it terminates output)
2. Use regex for hex and unicode sequences
3. Handle edge cases (invalid sequences, truncated sequences)

### Phase 4: Update Tests

**New test cases needed**:
1. Test `-n` flag alone
2. Test `-e` flag with all escape sequences
3. Test combined flags (`-ne`, `-en`)
4. Test with redirections
5. Test in pipelines
6. Test edge cases (no args, only flags, invalid escapes)

**Test file**: Create `test_echo_flags.py` with comprehensive coverage

### Phase 5: Documentation Updates

1. Update help text in EchoBuiltin
2. Update README.md if needed
3. Add to release notes

## Implementation Steps

1. **Create feature branch**: `feature/echo-flags`

2. **Implement core changes**:
   - Refactor echo to use os.write()
   - Add comprehensive flag parsing
   - Implement all escape sequences
   - Handle \c termination

3. **Add tests**:
   - Create test_echo_flags.py
   - Add comparison tests
   - Ensure backward compatibility

4. **Update documentation**:
   - Update builtin help
   - Update version.py with release notes

5. **Test and review**:
   - Run full test suite
   - Test manually in interactive shell
   - Check bash compatibility

## Code Structure

```python
class EchoBuiltin(Builtin):
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse flags
        suppress_newline, interpret_escapes, start_idx = self._parse_flags(args)
        
        # Get output text
        output = ' '.join(args[start_idx:]) if len(args) > start_idx else ''
        
        # Process escape sequences if needed
        if interpret_escapes:
            output, terminate = self._process_escapes(output)
            if terminate:
                suppress_newline = True
        
        # Write output
        self._write_output(output, suppress_newline, shell)
        return 0
    
    def _parse_flags(self, args: List[str]) -> Tuple[bool, bool, int]:
        """Parse echo flags and return (suppress_newline, interpret_escapes, start_index)."""
        # Implementation here
        
    def _process_escapes(self, text: str) -> Tuple[str, bool]:
        """Process escape sequences. Returns (processed_text, terminate_output)."""
        # Implementation here
        
    def _write_output(self, text: str, suppress_newline: bool, shell: 'Shell'):
        """Write output to appropriate file descriptor."""
        # Implementation here
```

## Testing Strategy

### Unit Tests
```python
def test_echo_n_flag():
    """Test -n flag suppresses newline."""
    
def test_echo_e_flag():
    """Test -e flag interprets escapes."""
    
def test_echo_combined_flags():
    """Test -ne and -en combinations."""
    
def test_echo_escape_sequences():
    """Test all escape sequences with -e."""
    
def test_echo_with_redirections():
    """Test echo with output redirections."""
    
def test_echo_in_pipeline():
    """Test echo in pipelines."""
```

### Comparison Tests
- Add to test_basic_commands.py
- Compare with bash behavior
- Edge cases and error conditions

## Success Criteria

1. All existing tests pass
2. New tests for -n and -e pass
3. Comparison tests show bash compatibility
4. I/O redirections work correctly
5. Pipelines work correctly
6. No performance regression

## Estimated Timeline

- Phase 1 (I/O fix): 1 hour
- Phase 2 (Flag parsing): 1 hour
- Phase 3 (Escape sequences): 2 hours
- Phase 4 (Tests): 2 hours
- Phase 5 (Documentation): 30 minutes

Total: ~6.5 hours of implementation time