# Parser Refactoring Plan

## Overview
The current parser.py file is 1806 lines with 85 method definitions, making it quite large and difficult to maintain. I propose refactoring it into a well-organized parser package with logical separation of concerns.

## Current Issues
1. **Monolithic structure**: All parsing logic is in a single large file
2. **Mixed concerns**: Statement parsing, command parsing, control structures, tests, arithmetic, and redirections are all in one class
3. **Duplicate code**: Many similar patterns for parsing control structures (`_parse_*_neutral` methods)
4. **Complex dependencies**: Everything depends on the main Parser class

## Proposed Structure

### New Directory: `psh/parser/`
Create a parser package with the following modules:

```
psh/parser/
├── __init__.py              # Public API exports
├── base.py                  # Base parser class (move from parser_base.py)
├── helpers.py              # Parser helpers (move from parser_helpers.py)
├── main.py                 # Main Parser class with top-level parsing
├── statements.py           # Statement parsing (if, while, for, case, etc.)
├── commands.py             # Command and pipeline parsing
├── control_structures.py   # Control structure parsing logic
├── tests.py               # Test expression parsing ([[ ]] constructs)
├── arithmetic.py          # Arithmetic expression parsing
├── redirections.py        # Redirection parsing
├── arrays.py              # Array assignment and initialization parsing
├── functions.py           # Function definition parsing
└── utils.py               # Utility functions and heredoc handling
```

## Refactoring Steps

### Step 1: Create Parser Package
1. Create `psh/parser/` directory
2. Move existing files:
   - `parser_base.py` → `parser/base.py`
   - `parser_helpers.py` → `parser/helpers.py`
3. Update imports throughout the codebase

### Step 2: Extract Main Parser
Create `parser/main.py` with:
- Top-level parsing logic (`parse()`, `_parse_top_level_item()`)
- Statement list parsing
- Basic token management delegation

### Step 3: Extract Statement Parser
Create `parser/statements.py` with:
- `parse_statement()`
- `parse_and_or_list()`
- `parse_command_list()` methods
- Statement-level coordination

### Step 4: Extract Command Parser
Create `parser/commands.py` with:
- `parse_command()`
- `parse_pipeline()`
- `parse_composite_argument()`
- Command argument handling

### Step 5: Extract Control Structure Parser
Create `parser/control_structures.py` with:
- All control structure parsing (if, while, for, case, select)
- Both neutral and context-specific variants
- Common patterns extracted to base methods

### Step 6: Extract Specialized Parsers
Create specialized modules:
- `tests.py`: Enhanced test parsing (`[[...]]`)
- `arithmetic.py`: Arithmetic command parsing (`((...))`) 
- `redirections.py`: All redirection parsing
- `arrays.py`: Array assignment parsing
- `functions.py`: Function definition parsing

### Step 7: Create Clean API
In `parser/__init__.py`:
```python
from .main import Parser
from .helpers import ParseError, TokenGroups
from .base import BaseParser

# Public API
__all__ = ['parse', 'parse_with_heredocs', 'Parser', 'ParseError', 'TokenGroups']

def parse(tokens):
    """Parse tokens into AST."""
    return Parser(tokens).parse()

def parse_with_heredocs(tokens, heredoc_map):
    """Parse tokens with heredoc content."""
    parser = Parser(tokens)
    return parser.parse_with_heredocs(heredoc_map)
```

## Benefits

1. **Improved maintainability**: Each module has a focused responsibility
2. **Better testability**: Individual parsers can be tested in isolation
3. **Easier navigation**: Developers can find specific parsing logic quickly
4. **Reduced complexity**: Each file is smaller and more focused
5. **Better reusability**: Parsers can be composed and reused
6. **Cleaner dependencies**: Clear separation between different parsing concerns

## Migration Strategy

1. Create new package structure without removing old files
2. Gradually move functionality to new modules
3. Update imports one at a time
4. Run tests after each change
5. Remove old files only after complete migration
6. Update documentation and imports across codebase

## Additional Improvements

1. **Extract common patterns**: Create base classes for similar control structures
2. **Improve error handling**: Centralize error message generation
3. **Add parser context**: Use context objects to manage parser state
4. **Type hints**: Ensure all methods have proper type annotations
5. **Documentation**: Add docstrings to all public methods

This refactoring will make the parser more maintainable, testable, and easier to extend with new features.

## Implementation Details

### Method Distribution by Module

Based on analysis of the current parser.py (1806 lines, 85 methods):

**main.py** (~300 lines):
- `parse()`, `_parse_top_level_item()`, `_simplify_result()`
- Top-level orchestration logic

**statements.py** (~400 lines):
- `parse_statement()`, `parse_and_or_list()`, `parse_command_list()`
- Statement coordination and list management

**commands.py** (~300 lines):
- `parse_command()`, `parse_pipeline()`, `parse_composite_argument()`
- Command argument parsing and pipeline handling

**control_structures.py** (~500 lines):
- All if/while/for/case/select parsing methods
- Neutral parsing variants
- Loop control (break/continue)

**tests.py** (~200 lines):
- `parse_enhanced_test_statement()`, `parse_test_expression()`
- Test operator handling and expression parsing

**arithmetic.py** (~150 lines):
- `parse_arithmetic_command()`, arithmetic expression parsing
- C-style for loop arithmetic sections

**redirections.py** (~200 lines):
- `parse_redirects()`, `parse_redirect()`, all redirect variants
- Heredoc and here-string handling

**arrays.py** (~150 lines):
- Array assignment parsing
- Array initialization and element assignment

**functions.py** (~100 lines):
- Function definition parsing
- Function detection logic

Each module will be self-contained with clear interfaces and minimal cross-dependencies.