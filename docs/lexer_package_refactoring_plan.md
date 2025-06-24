# Lexer Package Refactoring Implementation Plan

## Overview
Refactor the 1500+ line `state_machine_lexer.py` into a well-organized package with clear separation of concerns, improved maintainability, and better testability.

## Phase 1: Package Structure and Constants (1-2 hours)

### Step 1.1: Create Package Structure
```bash
mkdir psh/lexer
touch psh/lexer/__init__.py
```

### Step 1.2: Extract Constants (`psh/lexer/constants.py`)
**Lines to move**: ~80 lines from state_machine_lexer.py

```python
# psh/lexer/constants.py
"""Constants and character sets for the lexer."""

import string
from typing import Dict, Set
from ..token_types import TokenType

# Character sets
VARIABLE_START_CHARS = set(string.ascii_letters + '_')
VARIABLE_CHARS = set(string.ascii_letters + string.digits + '_')
SPECIAL_VARIABLES = set('?$!#@*-') | set(string.digits)

# Escape sequences
DOUBLE_QUOTE_ESCAPES = {
    '"': '"',
    '\\': '\\',
    '`': '`',
    'n': '\n',
    't': '\t',
    'r': '\r',
}

# Terminal characters
WORD_TERMINATORS = set(' \t\n|<>;&(){}\'"')
WORD_TERMINATORS_IN_BRACKETS = set(' \t\n|<>;&(){}\'"')

# Operators organized by length
OPERATORS_BY_LENGTH = {
    4: {'2>&1': TokenType.REDIRECT_DUP},
    3: {
        '<<<': TokenType.HERE_STRING,
        '2>>': TokenType.REDIRECT_ERR_APPEND,
        ';;&': TokenType.AMP_SEMICOLON,
        '<<-': TokenType.HEREDOC_STRIP,
    },
    # ... rest of operators
}

# Keywords
KEYWORDS = {
    'if', 'then', 'else', 'elif', 'fi',
    'while', 'do', 'done',
    'for', 'in',
    'case', 'esac',
    'select',
    'function',
    'break', 'continue'
}
```

### Step 1.3: Update Imports
Update `state_machine_lexer.py` to import from new constants module.

## Phase 2: Unicode Support Extraction (1-2 hours)

### Step 2.1: Create Unicode Module (`psh/lexer/unicode_support.py`)
**Lines to move**: ~120 lines from state_machine_lexer.py

```python
# psh/lexer/unicode_support.py
"""Unicode-aware character classification for shell identifiers."""

import string
import unicodedata
from typing import Optional

def is_identifier_start(char: str, posix_mode: bool = False) -> bool:
    """Check if character can start an identifier (variable name)."""
    # Move existing implementation

def is_identifier_char(char: str, posix_mode: bool = False) -> bool:
    """Check if character can be part of an identifier."""
    # Move existing implementation

def is_whitespace(char: str, posix_mode: bool = False) -> bool:
    """Check if character is whitespace."""
    # Move existing implementation

def normalize_identifier(name: str, posix_mode: bool = False, case_sensitive: bool = True) -> str:
    """Normalize an identifier name according to configuration."""
    # Move existing implementation

def validate_identifier(name: str, posix_mode: bool = False) -> bool:
    """Validate that a string is a valid identifier."""
    # Move existing implementation
```

### Step 2.2: Update Main Lexer
Remove Unicode functions from `state_machine_lexer.py` and import from new module.

## Phase 3: Token Classes Extraction (30 minutes)

### Step 3.1: Create Token Parts Module (`psh/lexer/token_parts.py`)
**Lines to move**: ~50 lines from state_machine_lexer.py

```python
# psh/lexer/token_parts.py
"""Token part classes for composite tokens."""

from dataclasses import dataclass, field
from typing import List, Optional
from ..token_types import Token
from ..lexer_position import Position

@dataclass
class TokenPart:
    """Represents a part of a composite token with metadata."""
    # Move existing implementation

@dataclass 
class RichToken(Token):
    """Enhanced token with metadata about its parts."""
    # Move existing implementation
```

## Phase 4: Helper Methods Extraction (2-3 hours)

### Step 4.1: Create Helpers Module (`psh/lexer/helpers.py`)
**Lines to move**: ~300 lines from state_machine_lexer.py

```python
# psh/lexer/helpers.py
"""Helper methods for lexer operations."""

from typing import List, Optional, Tuple
from ..token_types import TokenType
from .token_parts import TokenPart
from .constants import OPERATORS_BY_LENGTH

class LexerHelpers:
    """Mixin class providing helper methods for the lexer."""
    
    def read_balanced_parens(self) -> str:
        """Read content until balanced parentheses."""
        # Move existing implementation
    
    def read_balanced_double_parens(self) -> str:
        """Read content until balanced double parentheses."""
        # Move existing implementation
    
    def read_until_char(self, target: str, escape: bool = False) -> str:
        """Read until a specific character is found."""
        # Move existing implementation
    
    def handle_escape_sequence(self, quote_context: Optional[str] = None) -> str:
        """Handle escape sequences based on context."""
        # Move existing implementation
    
    def _check_for_operator(self) -> Optional[Tuple[str, TokenType]]:
        """Check if current position starts an operator."""
        # Move existing implementation
    
    def _is_operator_enabled(self, op: str, token_type: TokenType) -> bool:
        """Check if an operator is enabled in the current configuration."""
        # Move existing implementation
    
    def _build_token_value(self, parts: List[TokenPart]) -> str:
        """Build complete token value from parts."""
        # Move existing implementation
    
    def _get_word_terminators(self) -> set:
        """Get the set of word terminator characters based on configuration."""
        # Move existing implementation
    
    def _is_word_terminator_char(self, char: str) -> bool:
        """Check if a character terminates a word."""
        # Move existing implementation
    
    def _is_word_terminator(self, char: str) -> bool:
        """Check if character terminates a word in current context."""
        # Move existing implementation
```

## Phase 5: State Handlers Extraction (2-3 hours)

### Step 5.1: Create State Handlers Module (`psh/lexer/state_handlers.py`)
**Lines to move**: ~500 lines from state_machine_lexer.py

```python
# psh/lexer/state_handlers.py
"""State handler methods for the lexer state machine."""

from typing import List, Optional
from ..lexer_position import LexerState
from .token_parts import TokenPart
from .unicode_support import is_whitespace, is_identifier_start

class StateHandlers:
    """Mixin class providing state handler methods for the lexer."""
    
    def handle_normal_state(self) -> None:
        """Handle tokenization in normal state."""
        # Move existing implementation
    
    def handle_word_state(self) -> None:
        """Handle reading a word, which may contain embedded variables."""
        # Move existing implementation
    
    def handle_double_quote_state(self) -> None:
        """Handle reading inside double quotes with variable expansion."""
        # Move existing implementation
    
    def handle_single_quote_state(self) -> None:
        """Handle reading inside single quotes (no expansion)."""
        # Move existing implementation
    
    def handle_variable_state(self) -> None:
        """Handle reading a simple variable name with Unicode support."""
        # Move existing implementation
    
    def handle_brace_var_state(self) -> None:
        """Handle reading ${...} variable."""
        # Move existing implementation
    
    def handle_command_sub_state(self) -> None:
        """Handle reading $(...) command substitution."""
        # Move existing implementation
    
    def handle_arithmetic_state(self) -> None:
        """Handle reading $((...)) arithmetic expansion."""
        # Move existing implementation
    
    def handle_backtick_state(self) -> None:
        """Handle reading `...` backtick substitution."""
        # Move existing implementation
    
    def handle_comment_state(self) -> None:
        """Handle reading a comment."""
        # Move existing implementation
    
    def handle_process_substitution(self) -> None:
        """Handle <(...) or >(...) process substitution."""
        # Move existing implementation
```

## Phase 6: Core Lexer Refinement (1-2 hours)

### Step 6.1: Create Core Module (`psh/lexer/core.py`)
**Lines remaining**: ~400 lines

```python
# psh/lexer/core.py
"""Core lexer implementation."""

from typing import List, Optional
from ..token_types import Token, TokenType
from ..lexer_position import LexerConfig, LexerState, PositionTracker, LexerErrorHandler
from .constants import KEYWORDS
from .helpers import LexerHelpers
from .state_handlers import StateHandlers
from .token_parts import TokenPart, RichToken

class StateMachineLexer(LexerHelpers, StateHandlers):
    """State machine-based lexer for shell tokenization."""
    
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        # Core initialization only
        
    def tokenize(self) -> List[Token]:
        """Main tokenization method."""
        # Main tokenization loop
        
    # Core methods that coordinate with helpers and state handlers
    def emit_token(self, token_type: TokenType, value: str, ...) -> None:
        """Emit a token with current parts."""
        
    def parse_variable_or_expansion(self, quote_context: Optional[str] = None) -> TokenPart:
        """Parse a variable or expansion starting after the $."""
        
    def read_variable_name(self) -> str:
        """Read a simple variable name (after $) with Unicode support."""
```

## Phase 7: Package API and Testing (1-2 hours)

### Step 7.1: Create Package Init (`psh/lexer/__init__.py`)
```python
# psh/lexer/__init__.py
"""Advanced lexer package with Unicode support."""

from .core import StateMachineLexer
from .token_parts import TokenPart, RichToken
from .unicode_support import (
    is_identifier_start,
    is_identifier_char, 
    is_whitespace,
    normalize_identifier,
    validate_identifier
)

# Maintain backward compatibility
def tokenize(input_string: str) -> List[Token]:
    """Drop-in replacement for the existing tokenize function."""
    # Move implementation from state_machine_lexer.py

__all__ = [
    'StateMachineLexer',
    'TokenPart', 
    'RichToken',
    'tokenize',
    'is_identifier_start',
    'is_identifier_char',
    'is_whitespace',
    'normalize_identifier', 
    'validate_identifier'
]
```

### Step 7.2: Update Import References
Update all files that import from `state_machine_lexer.py`:

```python
# Before
from psh.state_machine_lexer import tokenize, StateMachineLexer

# After  
from psh.lexer import tokenize, StateMachineLexer
```

### Step 7.3: Create Module Tests
Create individual test files for each module:
- `tests/test_lexer_unicode.py` 
- `tests/test_lexer_constants.py`
- `tests/test_lexer_helpers.py`
- `tests/test_lexer_state_handlers.py`

## Phase 8: Validation and Cleanup (1 hour)

### Step 8.1: Run Full Test Suite
```bash
pytest tests/ -v
```

### Step 8.2: Update Documentation
- Update `ARCHITECTURE.llm` to reflect package structure
- Update import examples in documentation
- Add package overview to docstrings

### Step 8.3: Remove Original File
```bash
git rm psh/state_machine_lexer.py
```

## Migration Strategy

### Option 1: Big Bang (4-6 hours total)
- Complete all phases in one session
- Single large commit with all changes
- Higher risk but faster completion

### Option 2: Incremental (2-3 sessions)
- **Session 1**: Phases 1-3 (Constants, Unicode, Token Parts)
- **Session 2**: Phases 4-5 (Helpers, State Handlers) 
- **Session 3**: Phases 6-8 (Core, API, Validation)
- Multiple commits, easier to review and debug

### Option 3: Gradual with Compatibility (3-4 sessions)
- Keep `state_machine_lexer.py` temporarily with imports from package
- Remove original file only after full validation
- Safest approach

## Risk Mitigation

1. **Backup**: Create branch before starting refactoring
2. **Testing**: Run tests after each phase
3. **Import Validation**: Verify all imports work correctly
4. **Performance**: Benchmark before/after to ensure no regression
5. **Rollback Plan**: Keep original file until package is fully validated

## Success Criteria

- [ ] All existing tests pass
- [ ] Import statements work correctly
- [ ] No performance regression
- [ ] Code is more maintainable (smaller, focused modules)
- [ ] Better test coverage possible with granular modules
- [ ] Documentation updated

## Implementation Status

**Session 1**: Phases 1-3 (Constants, Unicode, Token Parts) - ✅ Complete
**Session 2**: Phases 4-5 (Helpers, State Handlers) - ✅ Complete  
**Session 3**: Phases 6-8 (Core, API, Validation) - ✅ Complete

### Session 2 Results (COMPLETED)

✅ **Phases 4-5 Successfully Completed**

**Massive File Reduction:**
- Main lexer: 1504 → 460 lines (**69% reduction**)
- Extracted: 32 methods into focused modules
- Package total: 1132 lines across 6 well-organized modules

**Files Created:**
- `helpers.py` (388 lines) - Helper methods and utilities
- `state_handlers.py` (475 lines) - State machine handlers

**Architecture Benefits:**
- **Separation of concerns**: Each module has focused responsibility
- **Better testability**: Modules can be tested in isolation  
- **Improved maintainability**: Easier to find and modify specific functionality
- **Enhanced reusability**: Helper functions available throughout package
- **Future extensibility**: Easy to add new state handlers or utilities

**Test Results:**
- All 15 tokenizer tests: ✅ PASSED
- All 18 Unicode tests: ✅ PASSED
- Full shell functionality: ✅ WORKING
- Perfect backward compatibility maintained

### Session 3 Results (COMPLETED)

🎉 **ALL PHASES SUCCESSFULLY COMPLETED**

**Final Package Structure:**
```
psh/lexer/
├── __init__.py              (79 lines)   - Clean public API
├── constants.py             (74 lines)   - Character sets & operators  
├── unicode_support.py       (126 lines)  - Unicode functions
├── token_parts.py           (37 lines)   - Token classes
├── helpers.py               (388 lines)  - Helper methods & utilities
├── state_handlers.py        (475 lines)  - State machine handlers
└── core.py                  (408 lines)  - Core lexer implementation
```

**Outstanding Results:**
- **Total reduction**: 1504 → 15 lines (**99% reduction** in main file!)
- **Well-organized package**: 1587 lines across 7 focused modules
- **Perfect API**: Both new package interface and backward compatibility
- **Complete test coverage**: All existing tests pass + new package tests

**Final Test Results:**
- ✅ **15 tokenizer tests**: All passing
- ✅ **18 Unicode tests**: All passing  
- ✅ **9 package structure tests**: All passing (NEW)
- ✅ **Full shell functionality**: Working perfectly
- ✅ **Backward compatibility**: 100% maintained

**Architecture Achievements:**
- **Crystal clear separation**: Each module has single, focused responsibility
- **Enhanced maintainability**: Easy to locate and modify specific functionality
- **Superior testability**: Granular testing of individual components
- **Improved reusability**: Helper functions accessible throughout codebase
- **Future extensibility**: Simple to add new features without complexity
- **Clean public API**: Professional package interface with proper exports
- **Perfect compatibility**: All existing code continues to work unchanged