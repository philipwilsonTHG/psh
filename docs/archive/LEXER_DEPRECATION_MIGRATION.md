# PSH Lexer Deprecation Migration Guide

## Overview

This guide helps developers migrate from the legacy lexer-parser system to the enhanced unified architecture introduced in PSH v0.60.0.

## Background

PSH v0.60.0 represents a major architectural simplification where:
- Enhanced lexer becomes the default and only lexer implementation
- Feature flag system is removed
- Compatibility layers are eliminated
- Unified token system replaces dual token classes

## What's Changing

### ✅ Components Being Promoted to Default
- `EnhancedModularLexer` → `ModularLexer` (default)
- `EnhancedToken` → `Token` (unified class)
- `EnhancedContextBaseParser` → `ContextBaseParser` (default)
- Enhanced features (metadata, validation, context tracking) → Standard features

### ❌ Components Being Removed
- Feature flag system (`psh.lexer.feature_flags`)
- Lexer control builtin (`lexer` command)
- Compatibility adapters (`CompatibilityAdapter`)
- Dual token conversion utilities
- Legacy fallback paths

### 🔄 Components Being Simplified
- `LexerParserContract` (simplified interface)
- `EnhancedIntegrationManager` → `IntegrationManager`
- Parser factory methods (unified API)

## Migration Steps

### 1. Update Imports

#### Before (v0.59.x and earlier):
```python
from psh.token_types import Token, EnhancedToken
from psh.lexer import ModularLexer, EnhancedModularLexer
from psh.lexer.feature_flags import apply_feature_profile, is_feature_enabled
from psh.lexer.enhanced_integration import enhanced_tokenize
from psh.parser.enhanced_base import EnhancedContextBaseParser
```

#### After (v0.60.0+):
```python
from psh.token_types import Token  # EnhancedToken is now just Token
from psh.lexer import ModularLexer  # Enhanced is now the default
from psh.lexer.enhanced_integration import enhanced_tokenize  # Still available
from psh.parser.base_context import ContextBaseParser  # Renamed from enhanced
```

### 2. Update Token Handling

#### Before:
```python
def process_tokens(tokens):
    for token in tokens:
        if isinstance(token, EnhancedToken):
            # Use enhanced features
            contexts = token.metadata.contexts
            semantic_type = token.metadata.semantic_type
        else:
            # Basic token handling
            process_basic_token(token)
```

#### After:
```python
def process_tokens(tokens):
    for token in tokens:
        # All tokens now have metadata
        contexts = token.metadata.contexts
        semantic_type = token.metadata.semantic_type
```

### 3. Update Lexer Usage

#### Before:
```python
# Feature flag configuration
apply_feature_profile("full")
if is_feature_enabled("enhanced_tokens"):
    lexer = EnhancedModularLexer(input_string)
    contract = lexer.tokenize_with_validation()
else:
    lexer = ModularLexer(input_string)
    tokens = lexer.tokenize()
```

#### After:
```python
# Simplified - enhanced features are always available
lexer = ModularLexer(input_string)
contract = lexer.tokenize_with_validation()
```

### 4. Update Parser Usage

#### Before:
```python
# Conditional parser creation
if use_enhanced_features:
    parser = EnhancedContextBaseParser(ctx, enhanced_config)
else:
    parser = ContextBaseParser(ctx)
```

#### After:
```python
# Unified parser - enhanced features are standard
parser = ContextBaseParser(ctx, config)
```

### 5. Remove Feature Flag Code

#### Before:
```python
from psh.lexer.feature_flags import apply_feature_profile

def setup_lexer():
    apply_feature_profile("standard")
    if is_feature_enabled("assignment_recognition"):
        # Enable assignment detection
        pass
```

#### After:
```python
# Feature flags are removed - all features are standard
def setup_lexer():
    # Assignment recognition is always enabled
    pass
```

### 6. Update Shell Integration

#### Before:
```python
from psh.shell_enhanced_lexer import install_enhanced_lexer_integration
from psh.shell_enhanced_parser import install_enhanced_parser_integration

shell = Shell()
install_enhanced_lexer_integration(shell)
install_enhanced_parser_integration(shell)
```

#### After:
```python
# Enhanced features are built-in
shell = Shell()  # Enhanced features included by default
```

## API Changes

### Removed Functions

```python
# These functions are no longer available:
apply_feature_profile()
is_feature_enabled()
enable_enhanced_features()
create_compatible_lexer()
adapt_tokens()
LexerParserCompatibility.tokenize_compatible()
```

### Renamed Classes

```python
# Old name → New name
EnhancedToken → Token
EnhancedModularLexer → ModularLexer (enhanced features built-in)
EnhancedContextBaseParser → ContextBaseParser
```

### Simplified Interfaces

```python
# tokenize() now always returns LexerOutput with validation
def tokenize(input_string: str, strict: bool = True) -> LexerOutput:
    """Tokenize using enhanced lexer (now the only implementation)."""
    
# parse() now always supports enhanced tokens
def parse(tokens, config=None):
    """Parse tokens into AST (enhanced features standard)."""
```

## Compatibility Layer

### Temporary Compatibility (v0.60.0 only)

For the v0.60.0 release, we provide limited backward compatibility:

```python
# Deprecated but still works in v0.60.0
from psh.token_types import EnhancedToken
# EnhancedToken is an alias for Token with deprecation warning

from psh.lexer.feature_flags import apply_feature_profile
# apply_feature_profile issues deprecation warning but does nothing
```

### Breaking Changes in v0.61.0

Starting with v0.61.0, these compatibility shims will be removed:
- `EnhancedToken` alias
- `feature_flags` module
- Compatibility adapter functions

## Testing Updates

### Test Fixtures

#### Before:
```python
@pytest.fixture
def enhanced_lexer():
    return EnhancedModularLexer("test input")

@pytest.fixture 
def basic_lexer():
    return ModularLexer("test input")
```

#### After:
```python
@pytest.fixture
def lexer():
    return ModularLexer("test input")  # Always enhanced
```

### Test Cases

#### Before:
```python
def test_enhanced_vs_basic():
    enhanced_tokens = enhanced_lexer.tokenize()
    basic_tokens = basic_lexer.tokenize()
    # Compare behaviors
```

#### After:
```python
def test_tokenization():
    tokens = lexer.tokenize()
    # Test unified behavior
```

## Performance Considerations

### Expected Changes
- **Startup**: ~10% faster (no compatibility layer overhead)
- **Memory**: ~5% reduction (single token class, no dual paths)
- **Tokenization**: ~5% faster (optimized single path)

### Monitoring
```python
# Monitor performance impact
import time
start = time.time()
tokens = lexer.tokenize()
duration = time.time() - start
```

## Troubleshooting

### Common Migration Issues

#### 1. Import Errors
```
ImportError: cannot import name 'EnhancedToken' from 'psh.token_types'
```
**Solution**: Replace `EnhancedToken` with `Token`

#### 2. Feature Flag Errors
```
ImportError: No module named 'psh.lexer.feature_flags'
```
**Solution**: Remove feature flag code - features are always enabled

#### 3. Compatibility Adapter Errors
```
ImportError: cannot import name 'CompatibilityAdapter'
```
**Solution**: Remove compatibility code - not needed anymore

#### 4. Parser Creation Errors
```
TypeError: EnhancedContextBaseParser() missing required arguments
```
**Solution**: Use `ContextBaseParser` instead

### Debug Mode

Enable debug mode to see migration issues:
```bash
export PSH_DEBUG=migration
python -m psh
```

## Benefits After Migration

### For Users
- **Faster startup** - No compatibility layer overhead
- **Better error messages** - Enhanced error detection is standard
- **Consistent behavior** - Single implementation path

### For Developers  
- **Simpler API** - Unified interface without conditionals
- **Easier testing** - Single code path to test
- **Better maintainability** - Less code complexity

### For Contributors
- **Cleaner codebase** - 30% reduction in lexer/parser complexity
- **Easier onboarding** - Single architecture to learn
- **Future-proof** - Enhanced features are the foundation for future development

## Support

### Getting Help
- **Documentation**: Updated architecture docs in ARCHITECTURE.md
- **Issues**: Report migration problems at https://github.com/anthropics/psh/issues
- **Examples**: See `examples/` directory for updated usage patterns

### Timeline
- **v0.60.0** (Current): Enhanced lexer promoted, compatibility layer available
- **v0.61.0** (Future): Compatibility layer removed, breaking changes finalized

This migration represents a major step forward in PSH's architecture, providing a cleaner, faster, and more maintainable codebase while preserving all the enhanced functionality that makes PSH a powerful educational shell.