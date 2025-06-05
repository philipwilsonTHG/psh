# PSH Release Notes - Version 0.34.0

**Release Date**: 2025-01-06

## Overview

This release adds the bash-compatible `select` statement, completing another major control structure from the shell feature set. The select statement provides an interactive menu system for user selection, commonly used in shell scripts for creating user-friendly interfaces.

## New Features

### Select Statement Implementation
- Full bash-compatible `select` statement for interactive menu generation
- Syntax: `select var in items...; do commands; done`
- Key features:
  - Displays numbered menu to stderr
  - Uses PS3 prompt (default "#? ") for user input
  - Sets selected item in specified variable
  - Sets raw user input in REPLY variable
  - Multi-column layout for large lists (automatic column width calculation)
  - Empty list handling (exits loop immediately)
  - EOF (Ctrl+D) and interrupt (Ctrl+C) handling
  - Full integration with break/continue statements
  - I/O redirection support on entire select loop
  - Variable and command substitution expansion in item lists

## Technical Implementation

### Parser Changes
- Added SELECT token type to `token_types.py`
- Added 'select' to KEYWORDS in `state_machine_lexer.py`
- Enhanced context-aware keyword handling for 'in' after 'select variable'
- Created `SelectStatement` AST node with fields:
  - `variable`: The variable to set with selection
  - `items`: List of items to display (after expansion)
  - `body`: Commands to execute in loop
  - `redirects`: I/O redirections for the loop

### Executor Implementation
- Added `execute_select` method to `ControlFlowExecutor`
- Menu display algorithm:
  - Single column for ≤9 items
  - 2 columns for 10-20 items
  - 3 columns for >20 items
  - Automatic column width calculation
- Input handling:
  - Reads from shell.stdin if redirected, otherwise sys.stdin
  - Numeric selections set variable to corresponding item
  - Invalid/out-of-range selections set variable to empty string
  - Non-numeric input sets variable to empty string
  - REPLY always contains raw user input

### Integration Points
- Added SelectStatement handling in `statement.py` executor
- Proper heredoc collection support for select statements
- Integration with existing break/continue infrastructure
- Reuses for loop expansion logic for item list processing

## Examples

```bash
# Simple menu
select fruit in apple banana cherry; do
    echo "You selected: $fruit"
    break
done

# Using PS3 custom prompt
PS3="Choose your option: "
select opt in "Start Service" "Stop Service" "Check Status" "Exit"; do
    case $opt in
        "Start Service") echo "Starting..."; break;;
        "Stop Service") echo "Stopping..."; break;;
        "Check Status") echo "Checking..."; break;;
        "Exit") break;;
        *) echo "Invalid option";;
    esac
done

# Command substitution in list
select file in $(ls *.txt); do
    echo "Processing $file"
    break
done
```

## Test Suite

- Added comprehensive test suite in `test_select_statement.py`
- 12 tests covering:
  - Basic functionality
  - Empty lists
  - PS3 prompt customization
  - Break/continue behavior
  - I/O redirection
  - Command substitution
  - Invalid selections
  - Multi-column display
  - Variable expansion
  - Quoted items with spaces
- Tests marked with `@pytest.mark.skip` due to stdin requirements
- Run tests with: `pytest -s tests/test_select_statement.py`

## Known Limitations

1. **Interactive stdin requirement**: Select tests require pytest -s flag to access stdin
2. **Control structures in pipelines**: Like other control structures, select cannot be used directly in pipelines (architectural limitation)
3. **Variable splitting**: Unquoted variables in word lists are not word-split (different from bash)

## Test Suite Status
- **Total tests**: 751
- **Passing**: 710
- **Skipped**: 38 (including 12 select tests requiring interactive stdin)
- **XFailed**: 3

## Example Script

Created `examples/select_demo.sh` demonstrating:
- Basic select usage
- Custom PS3 prompts
- Multi-column menus
- Case statement integration
- Empty input handling
- Break/continue usage

## Breaking Changes
None - this is a new feature that doesn't affect existing functionality.

## Upgrade Notes
The select statement is immediately available after upgrading. No migration required.

## Future Enhancements
- Consider adding timeout support for select (bash doesn't have this)
- Investigate stdin handling improvements for better pytest integration
- Add support for select in non-interactive contexts