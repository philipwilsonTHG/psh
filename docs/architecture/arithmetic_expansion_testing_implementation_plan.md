# Arithmetic Expansion Testing Implementation Plan

## Executive Summary

This implementation plan focuses on completing arithmetic expansion testing for the parser combinator, building upon existing test infrastructure. The goal is to ensure comprehensive coverage of all arithmetic features while avoiding duplication with existing tests.

## Current Testing Landscape

### Existing Test Coverage
1. **Parser Tests** (`test_parser_combinator_arithmetic_expansion.py`)
   - ✅ 43 tests for parsing arithmetic syntax
   - ✅ AST construction verification
   - ✅ Word AST integration

2. **Evaluation Tests** (`test_arithmetic_comprehensive.py`)
   - ✅ Basic arithmetic operations
   - ✅ Variable expansion
   - ✅ Operator precedence
   - ✅ Assignment operations
   - ✅ Increment/decrement
   - ✅ Ternary and comma operators
   - ✅ Error handling (division by zero)

3. **Expansion Tests** (`test_arithmetic_expansion.py`)
   - ✅ Basic expansion functionality
   - ✅ Integration with shell

### Identified Gaps

Based on analysis, the following areas need additional testing:

1. **Advanced Number Formats**
   - Base notation (2#, 8#, 16#)
   - Large number handling
   - Overflow/underflow behavior

2. **Complex Variable Integration**
   - Special variables ($#, $?, $$)
   - Array element arithmetic
   - Positional parameters in expressions

3. **Edge Cases**
   - Whitespace handling variations
   - Complex nested expressions
   - Mixed expansion types

4. **Bash Compatibility**
   - Specific bash behaviors
   - POSIX compliance verification
   - Cross-shell compatibility

5. **Performance Testing**
   - Large expression evaluation
   - Recursive depth limits
   - Memory usage patterns

## Implementation Plan

### Phase 1: Enhanced Number Format Testing (Days 1-2)

#### Objective
Ensure all number formats are correctly parsed and evaluated.

#### Test File: `test_arithmetic_number_formats.py`

```python
"""Test arithmetic expansion with various number formats."""

class TestArithmeticNumberFormats:
    
    def test_base_notation(self, shell):
        """Test base#number notation."""
        # Binary
        assert shell.evaluate("echo $((2#1010))") == "10\n"
        assert shell.evaluate("echo $((2#11111111))") == "255\n"
        
        # Octal
        assert shell.evaluate("echo $((8#77))") == "63\n"
        assert shell.evaluate("echo $((8#377))") == "255\n"
        
        # Hexadecimal
        assert shell.evaluate("echo $((16#FF))") == "255\n"
        assert shell.evaluate("echo $((16#CAFE))") == "51966\n"
        
        # Arbitrary bases (2-36)
        assert shell.evaluate("echo $((36#Z))") == "35\n"
        assert shell.evaluate("echo $((36#10))") == "36\n"
    
    def test_large_numbers(self, shell):
        """Test 32/64-bit integer limits."""
        # 32-bit limits
        assert shell.evaluate("echo $((2147483647))") == "2147483647\n"
        assert shell.evaluate("echo $((-2147483648))") == "-2147483648\n"
        
        # Overflow behavior
        result = shell.evaluate("echo $((2147483647 + 1))")
        # Document actual behavior (wrap or error)
    
    def test_mixed_formats(self, shell):
        """Test mixing different number formats."""
        assert shell.evaluate("echo $((0x10 + 010))") == "24\n"
        assert shell.evaluate("echo $((16#10 + 8#10))") == "24\n"
```

### Phase 2: Special Variable Testing (Days 2-3)

#### Objective
Verify arithmetic with all special shell variables.

#### Test File: `test_arithmetic_special_variables.py`

```python
"""Test arithmetic with special variables and parameters."""

class TestArithmeticSpecialVariables:
    
    def test_positional_parameters(self, shell):
        """Test arithmetic with $1, $2, etc."""
        shell.run_command("set -- 10 20 30")
        assert shell.evaluate("echo $(($1 + $2))") == "30\n"
        assert shell.evaluate("echo $(($1 * $3))") == "300\n"
    
    def test_special_parameters(self, shell):
        """Test $#, $?, $$, etc."""
        shell.run_command("set -- a b c")
        assert shell.evaluate("echo $(($# * 10))") == "30\n"
        
        # Exit status
        shell.run_command("true")
        assert shell.evaluate("echo $(($? + 5))") == "5\n"
        
        shell.run_command("false")
        assert shell.evaluate("echo $(($? + 5))") == "6\n"
    
    def test_array_arithmetic(self, shell):
        """Test arithmetic with array elements."""
        shell.run_command("arr=(5 10 15 20)")
        assert shell.evaluate("echo $((${arr[0]} + ${arr[1]}))") == "15\n"
        assert shell.evaluate("echo $((${arr[2]} * 2))") == "30\n"
        
        # Array indices from arithmetic
        shell.run_command("i=2")
        assert shell.evaluate("echo $((${arr[$((i-1))]} + 5))") == "15\n"
```

### Phase 3: Complex Integration Testing (Days 3-4)

#### Objective
Test arithmetic expansion in complex shell contexts.

#### Test File: `test_arithmetic_integration.py`

```python
"""Test arithmetic expansion integration with shell features."""

class TestArithmeticIntegration:
    
    def test_nested_expansions(self, shell):
        """Test arithmetic within other expansions."""
        # In parameter expansion
        shell.run_command("str='hello world'")
        assert shell.evaluate("echo ${str:$((2+1)):$((2*2))}") == "lo w\n"
        
        # In array indices
        shell.run_command("arr=(a b c d e)")
        shell.run_command("i=2")
        assert shell.evaluate("echo ${arr[$((i*2))]}") == "e\n"
    
    def test_command_substitution_arithmetic(self, shell):
        """Test arithmetic with command substitution."""
        shell.run_command("get_num() { echo 42; }")
        assert shell.evaluate("echo $(($(get_num) / 2))") == "21\n"
        
        # Nested arithmetic in command substitution
        assert shell.evaluate("echo $(echo $((5 + 3)))") == "8\n"
    
    def test_arithmetic_in_control_structures(self, shell):
        """Test arithmetic in if, while, for."""
        # In if conditions
        result = shell.evaluate("""
        if (( 5 > 3 )); then
            echo "true"
        fi
        """)
        assert "true" in result
        
        # In for loops
        result = shell.evaluate("""
        for ((i=0; i<3; i++)); do
            echo $i
        done
        """)
        assert result == "0\n1\n2\n"
```

### Phase 4: Error Handling and Edge Cases (Days 4-5)

#### Objective
Ensure robust error handling and edge case coverage.

#### Test File: `test_arithmetic_edge_cases.py`

```python
"""Test arithmetic expansion edge cases and error handling."""

class TestArithmeticEdgeCases:
    
    def test_syntax_errors(self, shell):
        """Test various syntax error conditions."""
        # Missing operands
        assert "error" in shell.evaluate("echo $((5 +))").lower()
        assert "error" in shell.evaluate("echo $((* 5))").lower()
        
        # Invalid operators
        assert "error" in shell.evaluate("echo $((5 ** ))").lower()
    
    def test_whitespace_variations(self, shell):
        """Test different whitespace patterns."""
        # No spaces
        assert shell.evaluate("echo $((5+3*2))") == "11\n"
        
        # Excessive spaces
        assert shell.evaluate("echo $((  5  +  3  *  2  ))") == "11\n"
        
        # Newlines
        assert shell.evaluate("echo $((5 +\n3))") == "8\n"
    
    def test_recursive_depth(self, shell):
        """Test deeply nested expressions."""
        # Build a deeply nested expression
        expr = "1"
        for i in range(50):
            expr = f"({expr} + 1)"
        
        result = shell.evaluate(f"echo $(({expr}))")
        assert result == "51\n"
```

### Phase 5: Bash Compatibility Testing (Days 5-6)

#### Objective
Ensure PSH matches bash behavior exactly.

#### Test File: `test_arithmetic_bash_compatibility.py`

```python
"""Test arithmetic expansion bash compatibility."""

class TestArithmeticBashCompatibility:
    
    def test_bash_specific_features(self, shell, bash_shell):
        """Compare PSH and bash arithmetic results."""
        test_cases = [
            # Negative modulo
            "echo $((-7 % 3))",
            # Right shift with negative
            "echo $((-1 >> 1))",
            # Base notation edge cases
            "echo $((36#zz))",
            # Overflow behavior
            "echo $((9999999999999999999))",
        ]
        
        for expr in test_cases:
            psh_result = shell.evaluate(expr)
            bash_result = bash_shell.evaluate(expr)
            assert psh_result == bash_result, f"Mismatch for {expr}"
    
    def test_posix_compliance(self, shell):
        """Test POSIX-mandated arithmetic behavior."""
        # POSIX requires specific behaviors
        # Document and test them
        pass
```

## Testing Infrastructure

### Helper Functions

```python
# tests/helpers/arithmetic_helpers.py

def compare_with_bash(shell, expression):
    """Compare PSH arithmetic result with bash."""
    psh_result = shell.evaluate(f"echo $(({expression}))")
    bash_result = subprocess.run(
        ['bash', '-c', f"echo $(({expression}))"],
        capture_output=True, text=True
    ).stdout
    return psh_result == bash_result

def test_arithmetic_limits(shell):
    """Test system-specific integer limits."""
    import sys
    max_int = sys.maxsize
    min_int = -sys.maxsize - 1
    # Test behavior at limits
```

## Validation Strategy

### 1. Unit Testing
- Test each arithmetic feature in isolation
- Verify correct tokenization, parsing, and evaluation
- Check error conditions

### 2. Integration Testing
- Test arithmetic with other shell features
- Verify behavior in realistic scripts
- Check performance characteristics

### 3. Compatibility Testing
- Compare results with bash
- Verify POSIX compliance
- Document any intentional differences

### 4. Regression Testing
- Ensure existing tests continue to pass
- Add tests for any bugs found
- Maintain test suite health

## Success Metrics

1. **Coverage**: 100% of arithmetic operators and features tested
2. **Compatibility**: 95%+ bash compatibility for common cases
3. **Performance**: Evaluation time < 10ms for typical expressions
4. **Reliability**: No crashes or panics on any input
5. **Documentation**: All behaviors clearly documented

## Timeline

- **Days 1-2**: Number format testing
- **Days 2-3**: Special variable testing  
- **Days 3-4**: Complex integration testing
- **Days 4-5**: Edge cases and error handling
- **Days 5-6**: Bash compatibility verification
- **Day 7**: Documentation and cleanup

Total: 7 days for complete implementation

## Deliverables

1. **Test Files**: 5 new comprehensive test modules
2. **Documentation**: Updated feature docs and test results
3. **Bug Fixes**: Any issues discovered during testing
4. **Compatibility Report**: Detailed bash comparison results
5. **Performance Report**: Benchmarks and optimization opportunities

## Risks and Mitigations

### Risk 1: Undocumented Bash Behaviors
**Mitigation**: Extensive bash testing and documentation of differences

### Risk 2: Platform-Specific Integer Behavior  
**Mitigation**: Test on multiple platforms, document variations

### Risk 3: Performance Issues with Complex Expressions
**Mitigation**: Set reasonable limits, optimize critical paths

## Conclusion

This implementation plan provides a systematic approach to completing arithmetic expansion testing. By focusing on gaps in existing coverage and ensuring bash compatibility, we can deliver a robust and reliable arithmetic expansion feature that meets user expectations.