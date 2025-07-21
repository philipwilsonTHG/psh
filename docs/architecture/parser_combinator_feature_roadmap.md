# Parser Combinator Feature Roadmap

## Overview

This document outlines the missing features in the parser combinator implementation and provides a prioritized roadmap for future development. Features are prioritized based on their importance for shell compatibility, educational value, and implementation complexity.

**Last Updated**: December 2024  
**Recent Progress**: 
- ✅ Function definitions fully implemented (all three syntax forms)
- ✅ Control structure handling fixed (proper nesting support)
- ✅ Expansion AST nodes implemented (Phase 2 complete)
- ✅ Word AST creation with full parser parity

## Feature Categories

### 🔴 Critical Features (Shell Compatibility)

These features are essential for basic shell script compatibility.

#### 1. Function Definitions ✅ COMPLETED
**Status**: Fully implemented  
**Complexity**: Medium  
**Educational Value**: High

```bash
greet() { echo "Hello $1"; }
function greet { echo "Hello"; }
function greet() { echo "Hello"; }  # Bash style with parens
```

**Completed Features**:
- All three syntax forms supported
- Proper function body parsing with nested structures
- Function name validation
- Integration with control structures

#### 2. Command Substitution
**Status**: AST nodes created, lexer support added  
**Complexity**: High  
**Educational Value**: Very High

```bash
echo "Today is $(date)"
files=`ls *.txt`
```

**Completed**:
- ✅ CommandSubstitution AST node
- ✅ Lexer tokens: COMMAND_SUB, COMMAND_SUB_BACKTICK
- ✅ Word AST integration

**Remaining**:
- Parser implementation for nested command parsing
- Integration with shell execution
- Proper quote handling

#### 3. Here Documents
**Status**: Not implemented  
**Complexity**: High  
**Educational Value**: Medium

```bash
cat <<EOF
Line 1
Line 2
EOF
```

**Implementation challenges**:
- Multi-line token collection
- Delimiter tracking
- Variable expansion control

#### 4. Variable/Parameter Expansion ✅ PARSER COMPLETE
**Status**: Parser fully implemented, executor pending  
**Complexity**: Very High  
**Educational Value**: High

```bash
${var:-default}
${var:=default}
${var:?error}
${var:+alternate}
${#var}
${var#pattern}
${var%pattern}
${var/search/replace}
```

**Completed**:
- ✅ ParameterExpansion AST node with operator/word fields
- ✅ PARAM_EXPANSION token type
- ✅ Full lexer support for all forms
- ✅ Parser support in both implementations
- ✅ WordBuilder handles all expansion types

**Remaining**:
- Executor implementation for actual expansion evaluation

### 🟡 Important Features (Common Usage)

These features are commonly used in shell scripts and interactive shells.

#### 5. Arithmetic Expansion
**Status**: Not implemented  
**Complexity**: Medium  
**Educational Value**: High

```bash
echo $((2 + 2))
i=$((i + 1))
```

#### 6. Process Substitution
**Status**: AST node exists, parser not implemented  
**Complexity**: Medium  
**Educational Value**: Medium

```bash
diff <(sort file1) <(sort file2)
>(command)
```

#### 7. Advanced Redirections
**Status**: Basic redirections only  
**Complexity**: Medium  
**Educational Value**: Medium

```bash
exec 3< file
command <&3
command 2>&1
command &> file
```

#### 8. Arrays
**Status**: Not implemented  
**Complexity**: High  
**Educational Value**: Medium

```bash
arr=(one two three)
echo ${arr[0]}
echo ${arr[@]}
```

### 🟢 Nice-to-Have Features (Advanced Usage)

These features enhance shell capabilities but are less commonly used.

#### 9. Brace Expansion
**Status**: Not implemented  
**Complexity**: Medium  
**Educational Value**: Low

```bash
echo {a,b,c}
echo file{1..10}.txt
```

#### 10. Select Loops
**Status**: Not implemented  
**Complexity**: Low  
**Educational Value**: Low

```bash
select opt in "Option 1" "Option 2"; do
    echo "You selected $opt"
done
```

#### 11. Compound Commands
**Status**: Not implemented  
**Complexity**: Low  
**Educational Value**: Medium

```bash
{ echo a; echo b; } > file
(cd /tmp && ls)
```

#### 12. Job Control
**Status**: Not implemented  
**Complexity**: Very High  
**Educational Value**: Low

```bash
command &
fg %1
jobs
```

## Implementation Roadmap

### Phase 1: Foundation (Q1)
**Goal**: Complete core shell features for basic script compatibility

1. **Week 1-2**: Function Definitions
   - Implement all three syntax forms
   - Add comprehensive tests
   - Update documentation

2. **Week 3-4**: Command Substitution
   - Design recursive parsing approach
   - Implement $() syntax
   - Add backtick support
   - Integration tests

3. **Week 5-6**: Here Documents
   - Design token collection strategy
   - Implement delimiter parsing
   - Handle variable expansion
   - Test with real scripts

4. **Week 7-8**: Basic Parameter Expansion
   - Implement ${var} forms
   - Add default/alternate values
   - String manipulation basics

### Phase 2: Enhanced Features (Q2)
**Goal**: Add commonly used shell features

1. **Week 1-2**: Arithmetic Expansion
   - Expression parser
   - Operator precedence
   - Variable references

2. **Week 3-4**: Process Substitution
   - Parser implementation
   - Named pipe integration
   - Error handling

3. **Week 5-6**: Advanced Redirections
   - File descriptor manipulation
   - Duplication operators
   - Here strings

4. **Week 7-8**: Arrays
   - Array literals
   - Subscript parsing
   - Array expansion

### Phase 3: Advanced Features (Q3)
**Goal**: Complete shell feature set

1. **Month 1**: Remaining Expansions
   - Brace expansion
   - Tilde expansion
   - Advanced parameter expansion

2. **Month 2**: Additional Control Structures
   - Select loops
   - Compound commands
   - Coproc support

3. **Month 3**: Interactive Features
   - Job control basics
   - Alias support
   - History expansion

### Phase 4: Parser Enhancements (Q4)
**Goal**: Improve parser performance and capabilities

1. **Memoization**: Cache parse results
2. **Error Recovery**: Continue after errors
3. **Incremental Parsing**: Efficient updates
4. **Streaming Support**: Large file handling

## Implementation Guidelines

### For Each Feature

1. **Design Phase**
   - Study shell behavior
   - Design AST nodes
   - Plan parser approach
   - Consider edge cases

2. **Implementation**
   - Add lexer support if needed
   - Implement parser combinators
   - Add error handling
   - Update grammar

3. **Testing**
   - Unit tests for parser
   - Integration tests
   - Comparison with bash
   - Error case tests

4. **Documentation**
   - Update architecture docs
   - Add usage examples
   - Document limitations
   - Update feature matrix

### Code Structure

```python
# For each major feature, create dedicated methods:
def _build_command_substitution(self) -> Parser[CommandSubstitution]:
    """Parser for command substitution $() and ``."""
    
def _build_arithmetic_expansion(self) -> Parser[ArithmeticExpansion]:
    """Parser for arithmetic expansion $(())."""
    
def _build_here_document(self) -> Parser[HereDocument]:
    """Parser for here documents << and <<-."""
```

### Testing Strategy

```python
# Comprehensive test file for each feature
tests/unit/parser/test_parser_combinator_functions.py
tests/unit/parser/test_parser_combinator_substitutions.py
tests/unit/parser/test_parser_combinator_expansions.py
```

## Success Metrics

### Phase 1 Completion
- [ ] 90% of basic shell scripts parse correctly
- [ ] All POSIX required features implemented
- [ ] Comprehensive test coverage

### Phase 2 Completion
- [ ] 95% of common shell scripts parse correctly
- [ ] Bash compatibility for common features
- [ ] Performance comparable to recursive descent

### Phase 3 Completion
- [ ] 99% of shell scripts parse correctly
- [ ] Full bash feature parity
- [ ] Interactive shell ready

### Phase 4 Completion
- [ ] Sub-second parsing for large scripts
- [ ] IDE-ready incremental parsing
- [ ] Production-quality error recovery

## Resource Requirements

### Development Time
- **Phase 1**: 2 months (1 developer)
- **Phase 2**: 2 months (1 developer)
- **Phase 3**: 3 months (1-2 developers)
- **Phase 4**: 1 month (1 developer)

### Skills Needed
- Functional programming expertise
- Shell scripting knowledge
- Parser theory understanding
- Testing methodology

## Recommended Next Steps (December 2024)

Based on recent progress and current state, here are the recommended priorities:

### 1. **Implement Expansion Evaluation in Executor** (HIGH PRIORITY)
Since we've completed the parser support for expansions, the logical next step is to implement the actual evaluation:
- Start with simple variable expansion ($var)
- Add parameter expansion operators (${var:-default}, etc.)
- Implement pattern matching (${var#pattern}, ${var%pattern})
- Add length operator ${#var}
- This will make many integration tests pass

### 2. **Complete Command Substitution Parser** (HIGH PRIORITY)
We have the AST nodes and lexer support, now need the parser:
- Implement recursive parsing for $(command) syntax
- Handle backtick syntax `command`
- Ensure proper nesting support
- This is critical for real-world shell scripts

### 3. **Add Here Document Support** (MEDIUM PRIORITY)
Essential for many scripts but complex to implement:
- Design multi-line token collection
- Implement delimiter tracking
- Handle variable expansion in here docs
- Support <<- for tab stripping

### 4. **Arithmetic Expansion** (MEDIUM PRIORITY)
Common in scripts and builds on expansion framework:
- ArithmeticExpansion AST node already exists
- Add $((expression)) parsing
- Integrate with expression evaluator
- Support variable references in expressions

### 5. **Improve Error Handling** (LOW PRIORITY)
Current parser is permissive, but better errors help users:
- Add recovery mechanisms
- Provide better error messages
- Implement partial parsing for IDEs

## Why This Order?

1. **Expansion Evaluation** enables many existing tests to pass and provides immediate value
2. **Command Substitution** is the most commonly used feature still missing
3. **Here Documents** complete the core I/O redirection features
4. **Arithmetic Expansion** rounds out the expansion types
5. **Error Handling** improves user experience once features work

## Implementation Tips

- Use the existing Word AST infrastructure for all expansions
- Maintain backward compatibility with string-based parsing
- Add comprehensive tests for each feature
- Update documentation as you go
- Consider parser performance impacts

## Conclusion

This roadmap provides a structured approach to completing the parser combinator implementation. By following this plan, the parser will evolve from an educational example to a production-ready shell parser while maintaining its clean, functional design.

The recent completion of expansion AST nodes and parser improvements has set a solid foundation. The next phase should focus on making these expansions actually work through executor implementation.