# Release Notes for v0.28.4

## Overview

Version 0.28.4 is a critical bug fix release that resolves a regression introduced during the Phase 7 refactoring where command substitution would fail in certain contexts.

## Bug Fix

### Fixed Command Substitution Method Call

**Issue**: Command substitution in for loops and string expansions would fail with:
```
AttributeError: 'Shell' object has no attribute '_execute_command_substitution'
```

**Example of failing code**:
```bash
for file in $(find . -type f -print | sort); do
    echo $file
done
```

**Root Cause**: During the refactoring to a component-based architecture, the `_execute_command_substitution` method was moved to the expansion manager, but some references weren't updated.

**Fix**: Updated `VariableExpander.expand_string_variables()` to use the correct API:
- Changed `self.shell._execute_command_substitution(cmd_sub)` 
- To `self.shell.expansion_manager.command_sub.execute(cmd_sub)`

## Testing

- Added 4 regression tests to prevent future breakage
- All 612 tests now pass (up from 608 in v0.28.3)
- Verified the original failing example now works correctly

## Files Changed

- `psh/expansion/variable.py` - Fixed method calls on lines 114 and 162
- `tests/test_expansion_regression.py` - New regression test suite

## Upgrade Notes

This is a bug fix release with no breaking changes. Users experiencing command substitution errors should upgrade immediately.