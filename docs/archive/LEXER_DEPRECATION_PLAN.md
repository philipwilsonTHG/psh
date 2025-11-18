# Detailed PSH Lexer-Parser Deprecation Plan

## Overview

This plan outlines the systematic removal of legacy lexer compatibility code and simplification of the PSH lexer-parser architecture. The enhanced lexer-parser integration is functionally complete with 99.7% test pass rate (2221/2226 tests).

## Current Architecture Assessment

### ✅ **Components Ready for Deprecation**
- **StateMachineLexer**: Already deprecated and removed
- **Enhanced Parser Integration**: 74/74 tests passing, fully functional
- **Shell Integration**: Working with enhanced features
- **Core Functionality**: 2221 tests passing

### ❌ **Remaining Issues (5 test failures)**
- Enhanced lexer compatibility tests with token count mismatches
- Validation result expectations in compatibility tests  
- Error handling differences between enhanced and legacy paths

### 📁 **Current Code Structure**
```
psh/
├── lexer/
│   ├── modular_lexer.py          # Primary lexer (keep)
│   ├── enhanced_integration.py   # Enhanced features (keep)
│   ├── feature_flags.py          # Gradual rollout (deprecate)
│   ├── parser_contract.py        # Contract system (simplify)
│   └── ...
├── parser/
│   ├── enhanced_base.py          # Enhanced parser (promote to default)
│   ├── enhanced_integration_manager.py  # Integration (simplify)
│   └── ...
└── compatibility/               # Compatibility layer (remove)
```

---

## Phase 1: Pre-Deprecation Cleanup (2-3 days)

### Day 1: Fix Remaining Test Failures

**Goal**: Achieve 100% test pass rate for enhanced features

#### 1.1 Fix Token Count Mismatches
```bash
# Target: tests/integration/lexer/test_enhanced_compatibility.py
```

**Issues**: Enhanced lexer producing different token counts than base lexer
- **Root Cause**: Enhanced lexer may include additional metadata tokens or handle whitespace differently
- **Solution**: Normalize token streams in compatibility adapter

**Implementation**:
```python
# File: psh/lexer/compatibility_adapter.py (to be removed later)
class CompatibilityAdapter:
    def normalize_token_stream(self, tokens: List[EnhancedToken]) -> List[Token]:
        """Normalize enhanced tokens to match legacy expectations."""
        # Filter out metadata-only tokens
        # Merge adjacent whitespace tokens
        # Convert enhanced tokens to basic tokens
```

#### 1.2 Fix Validation Result Issues
**Issues**: `validation_result` is None in some enhanced lexer contracts
- **Root Cause**: Fallback lexer paths not setting validation results
- **Solution**: Ensure all lexer paths set proper validation results

#### 1.3 Fix Error Handling Differences
**Issues**: Enhanced error handling behaves differently than legacy
- **Root Cause**: Enhanced error recovery vs legacy error propagation
- **Solution**: Align error handling behaviors for compatibility

### Day 2: Documentation and Migration Prep

#### 2.1 Create Migration Guide
```markdown
# File: LEXER_DEPRECATION_MIGRATION.md

## Migration from Legacy to Enhanced Lexer

### Breaking Changes
- Feature flags system removed
- Compatibility adapters removed
- Single lexer implementation (ModularLexer)

### Code Updates Required
[Detailed migration instructions]
```

#### 2.2 Add Deprecation Warnings
```python
# File: psh/lexer/feature_flags.py
import warnings

def apply_feature_profile(profile: str):
    warnings.warn(
        "Feature flags are deprecated. Enhanced lexer is now the default.",
        DeprecationWarning,
        stacklevel=2
    )
```

#### 2.3 Version Planning
```python
# File: psh/version.py
__version__ = "0.60.0"  # Next version: Enhanced lexer becomes default
```

---

## Phase 2: Compatibility Code Removal (3-4 days)

### Day 1: Remove Feature Flag System

#### 2.1 Remove Feature Flag Files
```bash
# Files to remove:
rm psh/lexer/feature_flags.py
rm psh/builtins/lexer_control.py
```

#### 2.2 Update Enhanced Integration
```python
# File: psh/lexer/enhanced_integration.py (simplified)
# Remove feature flag dependencies
# Remove conditional enhancement logic
# Make enhanced features always available
```

#### 2.3 Remove Feature Flag Tests
```bash
rm tests/integration/lexer/test_enhanced_compatibility.py
# Remove feature flag related tests from other files
```

### Day 2: Simplify Lexer Architecture

#### 2.1 Promote Enhanced Lexer to Default
```python
# File: psh/lexer/__init__.py (simplified)
from .modular_lexer import ModularLexer

def tokenize(input_string: str, strict: bool = True) -> LexerOutput:
    """Tokenize using enhanced lexer (now the only implementation)."""
    # Remove compatibility checks
    # Remove feature flag logic
    # Always use enhanced tokenization
```

#### 2.2 Remove Contract Complexity
```python
# File: psh/lexer/parser_contract.py (simplified)
# Remove compatibility adapters
# Remove legacy token conversion
# Simplify contract interface
```

#### 2.3 Clean Up Enhanced Integration
```python
# File: psh/lexer/enhanced_integration.py (simplified)
# Remove fallback logic
# Remove compatibility mode
# Simplify integration manager
```

### Day 3: Simplify Parser Architecture

#### 2.1 Promote Enhanced Parser to Default
```python
# File: psh/parser/__init__.py (simplified)
from .enhanced_base import EnhancedContextBaseParser as ContextBaseParser
from .enhanced_integration_manager import create_parser

def parse(tokens, config=None):
    """Parse tokens using enhanced parser (now the only implementation)."""
    # Remove token type checking
    # Remove compatibility fallbacks
    # Always use enhanced parsing
```

#### 2.2 Rename Enhanced Components
```bash
# Rename enhanced components to be the default:
mv psh/parser/enhanced_base.py psh/parser/base_context.py
mv psh/parser/enhanced_integration_manager.py psh/parser/integration_manager.py
```

#### 2.3 Remove Parser Compatibility
```python
# Remove dual parser paths
# Remove enhanced vs basic token handling
# Simplify parser factory
```

### Day 4: Update Shell Integration

#### 2.1 Simplify Shell Parser Integration
```python
# File: psh/shell_enhanced_parser.py -> psh/shell_parser.py
# Remove enhanced vs basic detection
# Remove compatibility modes
# Always use enhanced features
```

#### 2.2 Update Shell State
```python
# File: psh/core/state.py
# Remove enhanced parser options (now always on)
# Simplify parser configuration
```

#### 2.3 Remove Shell Compatibility Code
```python
# Remove dual parsing paths from shell
# Remove lexer manager compatibility checks
# Simplify shell initialization
```

---

## Phase 3: API Simplification (2 days)

### Day 1: Unify Token Classes

#### 3.1 Merge Token Classes
```python
# File: psh/token_types.py (unified)
@dataclass
class Token:
    """Unified token class with metadata (formerly EnhancedToken)."""
    type: TokenType
    value: str
    position: int
    end_position: int
    quote_type: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    metadata: TokenMetadata = field(default_factory=TokenMetadata)
    parts: List[TokenPart] = field(default_factory=list)

# Remove EnhancedToken class (functionality merged into Token)
```

#### 3.2 Update All Imports
```bash
# Update all files that import token classes
find psh/ -name "*.py" -exec sed -i '' 's/EnhancedToken/Token/g' {} \;
find tests/ -name "*.py" -exec sed -i '' 's/EnhancedToken/Token/g' {} \;
```

#### 3.3 Simplify Token Handling
```python
# Remove token conversion utilities
# Remove enhanced vs basic token checking
# Unify token processing
```

### Day 2: Clean Up Imports and Dependencies

#### 3.2 Update Import Statements
```python
# File: psh/lexer/__init__.py (final)
"""Advanced lexer package for PSH shell tokenization."""

from .modular_lexer import ModularLexer
from .position import Position, LexerState, LexerConfig
from .token_parts import TokenPart, RichToken
# Remove enhanced imports (now standard)
```

#### 3.3 Remove Compatibility Modules
```bash
# Remove compatibility directories and files
rm -rf psh/compatibility/
rm psh/lexer/compatibility_adapter.py
rm psh/parser/migration.py
```

#### 3.4 Update Public API
```python
# File: psh/parser/__init__.py (final)
__all__ = [
    'parse', 'parse_with_heredocs', 'Parser', 'ParseError',
    'ContextBaseParser', 'ParserContext', 'ParserConfig',
    # Remove enhanced-specific exports (now standard)
]
```

---

## Phase 4: Testing and Validation (2 days)

### Day 1: Test Suite Updates

#### 4.1 Remove Compatibility Tests
```bash
# Remove tests that are no longer relevant
rm tests/integration/lexer/test_enhanced_compatibility.py
rm tests/integration/parser/test_enhanced_parser_integration.py
# Remove feature flag tests
```

#### 4.2 Update Remaining Tests
```python
# Update tests to use unified API
# Remove enhanced vs basic test variants
# Simplify test setup and teardown
```

#### 4.3 Add Regression Tests
```python
# File: tests/regression/test_lexer_deprecation.py
# Ensure deprecation didn't break functionality
# Test edge cases that were previously handled by compatibility code
```

### Day 2: Full System Validation

#### 4.1 Run Full Test Suite
```bash
python -m pytest tests/ -v
# Target: 100% pass rate (or document acceptable failures)
```

#### 4.2 Performance Validation
```bash
python -m pytest tests/performance/ -v
# Ensure no performance regression
```

#### 4.3 Integration Testing
```bash
# Test real-world shell usage
# Test complex command parsing
# Test error handling edge cases
```

---

## Phase 5: Documentation and Release (1 day)

### 5.1 Update Documentation

#### Update Architecture Documentation
```markdown
# File: ARCHITECTURE.md (updated)
## Lexer Architecture (Simplified)
- Single lexer implementation (ModularLexer)
- Enhanced features are standard
- Unified token system with metadata
```

#### Update User Guide
```markdown
# File: docs/user_guide/lexer.md
## PSH Lexer
The PSH lexer provides advanced tokenization with:
- Unicode support
- Enhanced error detection
- Rich token metadata
```

### 5.2 Create Release Notes
```markdown
# File: RELEASE_NOTES_v0.60.0.md
## PSH v0.60.0 - Enhanced Lexer Promotion

### Major Changes
- Enhanced lexer is now the default and only lexer implementation
- Feature flag system removed
- Simplified API with unified token classes
- Improved performance and reliability

### Breaking Changes
[List of breaking changes and migration instructions]

### Migration Guide
[Link to migration guide]
```

### 5.3 Version Update
```python
# File: psh/version.py
__version__ = "0.60.0"
__version_info__ = (0, 60, 0)

# Update version history
VERSION_HISTORY = [
    # ...
    ("0.60.0", "Enhanced lexer promotion - simplified architecture"),
]
```

---

## Implementation Timeline

| Phase | Duration | Description | Deliverables |
|-------|----------|-------------|--------------|
| **Phase 1** | 2-3 days | Pre-deprecation cleanup | 100% test pass rate, migration docs |
| **Phase 2** | 3-4 days | Remove compatibility code | Simplified architecture |
| **Phase 3** | 2 days | API unification | Clean, unified API |
| **Phase 4** | 2 days | Testing and validation | Validated system |
| **Phase 5** | 1 day | Documentation and release | v0.60.0 release |

**Total Duration**: 10-12 days

---

## Risk Mitigation

### Backup Strategy
```bash
# Create backup branch before starting
git checkout -b backup-before-deprecation
git checkout main
```

### Rollback Plan
- Keep backup branch with compatibility code
- Document known issues for quick fixes
- Prepare patch release process if needed

### Testing Strategy
- Run tests after each phase
- Test with real shell scripts
- Performance monitoring
- User acceptance testing

### Communication Plan
- Announce deprecation timeline
- Provide migration support
- Update documentation proactively
- Monitor for user issues

---

## Success Metrics

### Technical Metrics
- [ ] 100% test pass rate (2226/2226 tests)
- [ ] No performance regression (<5% slower)
- [ ] Memory usage stable or improved
- [ ] API surface reduced by 30%

### Code Quality Metrics
- [ ] 30% reduction in lexer/parser codebase size
- [ ] Elimination of feature flag complexity
- [ ] Single code path for tokenization
- [ ] Simplified test suite

### User Experience Metrics
- [ ] Maintained backward compatibility for public API
- [ ] Improved error messages
- [ ] Faster startup time
- [ ] Reduced learning curve for contributors

---

## Post-Deprecation Benefits

1. **Simplified Architecture**: Single lexer implementation, cleaner codebase
2. **Better Performance**: No compatibility overhead, optimized paths
3. **Enhanced Features Standard**: All users get advanced features
4. **Easier Maintenance**: Single code path to maintain and debug
5. **Future Development**: Easier to add new features without compatibility concerns

This deprecation plan provides a systematic approach to removing legacy code while maintaining system stability and user experience. The enhanced parser integration work is essentially complete, making this the right time to simplify the architecture.