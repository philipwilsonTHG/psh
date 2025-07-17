# Enhanced Lexer Testing Strategy

## Current Status and Issue

We've successfully implemented Phase 1-4 of the lexer-parser interface improvements:

✅ **Phase 1**: Enhanced Token Infrastructure  
✅ **Phase 2**: Syntax Validation in Lexer  
✅ **Phase 3**: Lexer-Parser Contract  
✅ **Phase 4**: Integration and Migration  

However, there's a critical gap: **the parser hasn't been updated to fully utilize the enhanced tokens**. We have the infrastructure but need proper integration testing.

## Testing Strategy

### 1. **Compatibility Testing First**

Before adding enhanced features to the parser, we need to ensure our enhanced lexer can work with the existing parser through the compatibility layer.

```python
# Test: Enhanced lexer → Legacy tokens → Existing parser
def test_enhanced_lexer_legacy_parser_compatibility():
    """Test that enhanced lexer can feed existing parser via compatibility layer."""
    from psh.lexer.enhanced_integration import enhanced_tokenize
    from psh.parser import parse
    
    command = "echo hello | grep world"
    
    # Get enhanced lexer output
    contract = enhanced_tokenize(command, enable_enhancements=True)
    
    # Extract legacy tokens
    from psh.lexer.parser_contract import extract_legacy_tokens
    legacy_tokens = extract_legacy_tokens(contract)
    
    # Parse with existing parser
    ast = parse(legacy_tokens)
    
    # Should succeed and produce correct AST
    assert ast is not None
    # Add more specific AST validation
```

### 2. **Enhanced Parser Integration Testing**

Test the new enhanced parser with enhanced tokens:

```python
# Test: Enhanced lexer → Enhanced tokens → Enhanced parser
def test_enhanced_lexer_enhanced_parser():
    """Test full enhanced pipeline."""
    from psh.lexer.enhanced_integration import enhanced_tokenize
    from psh.parser.enhanced_integration import create_enhanced_parser
    
    command = "VAR=value echo $VAR"
    
    # Get enhanced contract
    contract = enhanced_tokenize(command, enable_enhancements=True)
    
    # Create enhanced parser
    parser = create_enhanced_parser(contract)
    
    # Parse with enhanced features
    ast = parser.parse()
    
    # Validate enhanced features are recognized
    # - Assignment should be detected in lexer
    # - Variables should have proper metadata
    assert ast is not None
```

### 3. **Feature-by-Feature Testing**

Test each enhanced feature individually:

#### Assignment Recognition
```python
def test_assignment_recognition():
    """Test that assignments are properly recognized and handled."""
    from psh.lexer.enhanced_integration import enhanced_tokenize
    
    test_cases = [
        "VAR=value",
        "arr[0]=element", 
        "VAR+=append",
        "count*=2"
    ]
    
    for command in test_cases:
        contract = enhanced_tokenize(command)
        
        # Check that assignment tokens are created
        assignment_tokens = [
            token for token in contract.tokens 
            if hasattr(token, 'assignment_info')
        ]
        assert len(assignment_tokens) > 0
```

#### Context Tracking
```python
def test_context_tracking():
    """Test that token contexts are properly tracked."""
    command = "if [[ -f file ]]; then echo hello; fi"
    
    contract = enhanced_tokenize(command)
    
    # Find tokens in test context
    test_tokens = [
        token for token in contract.tokens
        if hasattr(token.metadata, 'contexts') and 
           'test_expression' in [str(c) for c in token.metadata.contexts]
    ]
    
    assert len(test_tokens) > 0
```

#### Validation
```python
def test_syntax_validation():
    """Test that syntax errors are caught in lexer phase."""
    error_cases = [
        "echo 'unclosed quote",
        "echo $(unclosed substitution",
        "echo $((unclosed arithmetic"
    ]
    
    for command in error_cases:
        contract = enhanced_tokenize(command)
        
        # Should have validation errors
        assert contract.validation_result is not None
        assert len(contract.validation_result.errors) > 0
```

### 4. **Performance Testing**

Ensure enhanced features don't significantly impact performance:

```python
def test_performance_impact():
    """Test that enhanced lexer performance is acceptable."""
    import time
    
    command = "for i in {1..100}; do echo $i; done"
    iterations = 100
    
    # Test base lexer
    from psh.lexer import tokenize
    start = time.time()
    for _ in range(iterations):
        tokenize(command)
    base_time = time.time() - start
    
    # Test enhanced lexer
    from psh.lexer.enhanced_integration import enhanced_tokenize
    start = time.time()
    for _ in range(iterations):
        enhanced_tokenize(command, enable_enhancements=True)
    enhanced_time = time.time() - start
    
    # Should not be more than 2x slower
    overhead = enhanced_time / base_time
    assert overhead < 2.0, f"Enhanced lexer too slow: {overhead:.2f}x overhead"
```

## Step-by-Step Testing Plan

### Phase 1: Basic Compatibility (Week 1)

1. **Test Enhanced Lexer → Legacy Parser**
   ```bash
   python -m pytest tests/integration/lexer/test_enhanced_compatibility.py::TestEnhancedLexerCompatibility::test_basic_tokenization_compatibility -v
   ```

2. **Test Feature Flags**
   ```bash
   python -m pytest tests/integration/lexer/test_enhanced_compatibility.py::TestEnhancedLexerCompatibility::test_feature_flag_integration -v
   ```

3. **Test Error Handling**
   ```bash
   python -m pytest tests/integration/lexer/test_enhanced_compatibility.py::TestEnhancedLexerCompatibility::test_error_handling_compatibility -v
   ```

### Phase 2: Enhanced Parser Integration (Week 2)

1. **Create Enhanced Parser Tests**
   ```python
   # tests/integration/parser/test_enhanced_integration.py
   def test_enhanced_parser_with_enhanced_tokens():
       """Test that enhanced parser can consume enhanced tokens."""
       pass
   
   def test_enhanced_parser_context_validation():
       """Test context-aware parsing."""
       pass
   
   def test_enhanced_parser_semantic_validation():
       """Test semantic type validation."""
       pass
   ```

2. **Test Full Pipeline**
   ```python
   def test_full_enhanced_pipeline():
       """Test complete enhanced lexer → enhanced parser pipeline."""
       from psh.parser.enhanced_integration import parse_with_enhanced_lexer
       
       command = "VAR=value echo $VAR | grep pattern"
       ast = parse_with_enhanced_lexer(command, use_enhanced_features=True)
       
       # Should parse successfully with enhanced features
       assert ast is not None
   ```

### Phase 3: Real-World Testing (Week 3)

1. **Test Against Existing Shell Scripts**
   ```bash
   # Run enhanced lexer against existing test scripts
   for script in tests/scripts/*.sh; do
       python -m psh --enhanced-lexer --validate "$script"
   done
   ```

2. **Test Integration with Shell Execution**
   ```python
   def test_enhanced_lexer_in_shell():
       """Test enhanced lexer integration with shell execution."""
       from psh.shell_enhanced_lexer import create_enhanced_shell
       
       shell = create_enhanced_shell()
       
       # Test various commands
       commands = [
           "VAR=test echo $VAR",
           "if [[ -f /etc/passwd ]]; then echo exists; fi",
           "for i in {1..5}; do echo $i; done"
       ]
       
       for cmd in commands:
           result = shell.run_command(cmd)
           assert result == 0  # Should execute successfully
   ```

### Phase 4: Error Cases and Edge Cases (Week 4)

1. **Test Error Recovery**
   ```python
   def test_error_recovery():
       """Test that parser can recover from lexer errors."""
       error_commands = [
           "echo 'partial quote && echo fixed",
           "echo $(incomplete && echo complete"
       ]
       
       for cmd in error_commands:
           # Should not crash, may produce partial AST
           try:
               ast = parse_with_enhanced_lexer(cmd)
               # Some parsing should be possible
           except Exception as e:
               # Error should be informative
               assert "lexer" in str(e).lower() or "quote" in str(e).lower()
   ```

2. **Test Complex Cases**
   ```python
   def test_complex_shell_constructs():
       """Test enhanced lexer with complex shell constructs."""
       complex_commands = [
           "function test() { local VAR=value; echo $VAR; }",
           "case $VAR in pattern) echo match ;; esac",
           "{ echo group; } | while read line; do echo $line; done"
       ]
       
       for cmd in complex_commands:
           contract = enhanced_tokenize(cmd)
           # Should handle complex constructs without critical errors
           assert contract.should_attempt_parsing()
   ```

## Implementation Approach

### Step 1: Fix Import Issues

First, we need to address the missing import issue in the enhanced lexer:

```python
# psh/lexer/quote_validator.py - Fix import
from ..lexer.token_parts import TokenPart  # Adjust path as needed
```

### Step 2: Create Minimal Enhanced Parser

Create a minimal enhanced parser that can consume enhanced tokens but falls back gracefully:

```python
# tests/test_enhanced_lexer_integration.py
def test_minimal_enhanced_parser():
    """Test minimal enhanced parser integration."""
    from psh.lexer.enhanced_integration import enhanced_tokenize
    from psh.parser.enhanced_integration import create_enhanced_parser
    
    # Simple command that should work
    command = "echo hello"
    
    # Get enhanced contract
    contract = enhanced_tokenize(command, enable_enhancements=True)
    assert isinstance(contract, psh.lexer.parser_contract.LexerParserContract)
    
    # Create parser in compatibility mode
    parser = create_enhanced_parser(contract, 
                                   config=EnhancedParserConfig(use_enhanced_tokens=False))
    
    # Should be able to parse
    ast = parser.parse()
    assert ast is not None
```

### Step 3: Gradual Enhancement

Once basic compatibility works, gradually enable enhanced features:

1. **Week 1**: Basic compatibility - enhanced lexer feeds existing parser
2. **Week 2**: Enhanced parser consumes enhanced tokens in compatibility mode  
3. **Week 3**: Enable context validation and semantic validation
4. **Week 4**: Full feature integration and optimization

## Success Metrics

1. **Compatibility**: 100% of existing tests pass with enhanced lexer in compatibility mode
2. **Enhanced Features**: New features (assignment detection, context tracking, validation) work correctly
3. **Performance**: Enhanced lexer adds no more than 50% overhead in compatibility mode, 100% overhead in full mode
4. **Error Handling**: Enhanced validation catches 90% more syntax errors than current lexer
5. **Integration**: Enhanced parser correctly utilizes enhanced token metadata

## Risk Mitigation

1. **Compatibility Issues**: Always maintain fallback to base lexer
2. **Performance Impact**: Use feature flags to disable expensive features
3. **Parser Complexity**: Start with minimal enhanced parser, add features incrementally
4. **Test Coverage**: Comprehensive test suite covering all integration paths

This strategy ensures we can properly test and validate the enhanced lexer-parser integration while maintaining backward compatibility and system stability.