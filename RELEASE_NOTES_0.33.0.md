# PSH Release Notes - Version 0.33.0

**Release Date**: 2025-01-06

## Overview

This release adds bash-compatible history expansion and fixes a critical bug with for loop variable persistence. It also updates documentation by removing outdated TODO entries for issues that were already resolved.

## New Features

### History Expansion
- Implemented complete bash-compatible history expansion as a preprocessor step
- Supported patterns:
  - `!!` - Execute previous command
  - `!n` - Execute command number n from history
  - `!-n` - Execute n commands back
  - `!string` - Execute most recent command starting with string
  - `!?string?` - Execute most recent command containing string
- History expansion respects quotes and parameter expansion contexts
- Expanded commands are displayed before execution in interactive mode
- Comprehensive error messages for failed expansions

## Bug Fixes

### For Loop Variable Persistence
- **Fixed**: Loop variables now correctly persist after the loop with their last iteration value
- **Previous behavior**: Variables were incorrectly restored to pre-loop values or removed
- **New behavior**: Matches bash - variables retain their last iteration value
- This fix applies to both traditional `for` loops and ensures consistency with C-style loops
- Updated tests to expect correct bash behavior

## Documentation Updates

### TODO.md Cleanup
- Removed "Variable Assignment with Spaces" entry - feature was already working correctly
- Removed "Builtin I/O Redirection" entry - feature was already working correctly  
- Updated test count from 730+ to 749 passing tests
- These features were incorrectly listed as problems but testing confirmed they work properly

## Technical Details

### History Expansion Implementation
- Added `psh/history_expansion.py` module with `HistoryExpander` class
- Integration points:
  - Shell initialization creates history expander instance
  - Source processor performs expansion before tokenization
  - Character-by-character parsing for context awareness
- Properly handles:
  - Single and double quotes (no expansion inside)
  - Parameter expansions `${...}` (no expansion inside)
  - `!=` operator preservation in arithmetic contexts

### For Loop Fix
- Modified `executor/control_flow.py` to remove variable restoration code
- Updated test expectations in `test_for_loops.py`:
  - `test_for_variable_persistence` (was `test_for_variable_scoping`)
  - `test_for_variable_persists_when_new` (was `test_for_variable_does_not_leak`)
- Also updated `test_local_builtin.py` to expect correct behavior with local variables

## Test Suite Status
- **Total tests**: 749 (up from 730+ in v0.32.0)
- **All tests passing**: 100% pass rate maintained
- Added comprehensive test suite for history expansion
- Updated for loop tests to validate correct bash behavior

## Breaking Changes
None - all changes maintain backward compatibility while fixing incorrect behaviors.

## Known Limitations
- History expansion patterns like `!$` (last word) and `:p` (print only) are not yet implemented
- History expansion cannot be disabled with `set +H` (not yet configurable)

## Upgrade Notes
Users relying on the incorrect for loop behavior (variables being restored) will need to update their scripts. The new behavior matches bash and is more intuitive - loop variables persist with their final value.