# Parser Combinator Feature Parity Implementation Plan

## Executive Summary

This plan outlines the systematic approach to achieve complete feature parity between the parser combinator implementation and the hand-coded recursive descent parser in PSH. The parser combinator currently handles ~85% of shell syntax with 142+ passing tests. This plan details the implementation of the remaining 15% to achieve 100% compatibility.

## Current State Analysis

### Parser Combinator Strengths
- ✅ **Core shell syntax** (pipes, redirections, simple commands)
- ✅ **Control structures** (if, while, for, case, until)
- ✅ **Functions** (definition and invocation)
- ✅ **Expansions** (parameter, command, arithmetic, pathname)
- ✅ **Here documents** (innovative two-pass architecture)
- ✅ **Job control basics** (background commands with &)

### Missing Features (Gap Analysis)
1. **Process Substitution** - `<(cmd)` and `>(cmd)`
2. **Compound Commands** - `(subshell)` and `{ group; }`
3. **Arithmetic Commands** - `((expression))` statements
4. **Enhanced Test Expressions** - `[[ conditional ]]`
5. **Array Literals** - `arr=(a b c)` syntax
6. **Advanced I/O Redirection** - FD manipulation (`exec 3<`, `2>&1`)
7. **Select Loops** - `select var in list`

## Implementation Phases

### Phase 1: Process Substitution (Weeks 1-3) ✅ **COMPLETED**

#### Objective
Implement full process substitution support to enable advanced I/O patterns.

#### Status: ✅ COMPLETED
- **Implementation Date**: January 2025
- **Test Coverage**: 26 comprehensive tests
- **Integration**: Fully integrated with existing ProcessSubstitution AST node
- **Compatibility**: Full feature parity with recursive descent parser

#### Technical Design
```python
# New parser combinator functions needed:
def process_substitution_parser() -> Parser[ProcessSubstitution]:
    """Parse <(command) or >(command) syntax."""
    return alt(
        seq(
            literal('<'),
            literal('('),
            lazy(lambda: complete_command_parser),
            literal(')')
        ).map(lambda x: ProcessSubstitution('input', x[2])),
        seq(
            literal('>'),
            literal('('),
            lazy(lambda: complete_command_parser),
            literal(')')
        ).map(lambda x: ProcessSubstitution('output', x[2]))
    )
```

#### Implementation Tasks ✅ COMPLETED
1. **✅ Parser implementation**
   - Added `PROCESS_SUB_IN` and `PROCESS_SUB_OUT` token parsers
   - Integrated into expansion combinator chain (`word_like` parser)
   - Implemented command extraction from token values
   
2. **✅ AST integration**
   - Integrated with existing `ProcessSubstitution` AST node
   - Added to `_build_word_from_token` method for Word AST creation
   - Embedded as ExpansionPart within Word nodes

3. **✅ Testing and validation**
   - Created comprehensive test suite (26 tests)
   - Tested nested process substitutions and complex scenarios
   - Validated with real-world examples including pipes, redirections, conditionals

#### Implementation Details
**Files Modified:**
- `psh/parser/implementations/parser_combinator_example.py`:
  - Added ProcessSubstitution import
  - Added token parsers and parsing logic
  - Enhanced Word AST building
  
**Tests Created:**
- `tests/unit/parser/test_process_substitution_combinator.py` (11 basic tests)
- `tests/unit/parser/test_process_substitution_edge_cases.py` (15 edge case tests)

#### Test Cases
```bash
# Basic process substitution
diff <(sort file1) <(sort file2)
comm -12 <(sort file1) <(sort file2)

# Output process substitution
command | tee >(grep ERROR > errors.log) >(grep WARN > warnings.log)

# Nested usage
paste <(cut -f1 <(sort data)) <(cut -f2 <(sort data))
```

### Phase 2: Compound Commands (Weeks 4-7) ✅ **COMPLETED**

#### Objective
Add support for subshells and brace groups for proper command grouping.

#### Status: ✅ COMPLETED
- **Implementation Date**: January 2025 
- **Test Coverage**: 27 comprehensive compound command tests + 46 integration tests
- **Integration**: Fully integrated with existing SubshellGroup and BraceGroup AST nodes
- **Compatibility**: Full feature parity with recursive descent parser

#### Technical Design
```python
# Implemented using the between combinator for elegant delimiter handling
def _build_subshell_group(self) -> Parser[SubshellGroup]:
    """Build parser for subshell group (...) syntax."""
    return between(
        self.lparen,
        self.rparen,
        lazy(lambda: self.statement_list)
    ).map(lambda statements: SubshellGroup(statements=statements))

def _build_brace_group(self) -> Parser[BraceGroup]:
    """Build parser for brace group {...} syntax."""
    return between(
        self.lbrace,
        self.rbrace,
        lazy(lambda: self.statement_list)
    ).map(lambda statements: BraceGroup(statements=statements))
```

#### Implementation Tasks ✅ COMPLETED
1. **✅ Subshell implementation**
   - Added `LPAREN` and `RPAREN` token parsers  
   - Integrated into control structure parsing chain
   - Supports variable scoping and environment isolation

2. **✅ Brace group implementation**
   - Added `LBRACE` and `RBRACE` token parsers
   - Proper semicolon/newline handling within braces
   - Maintains current shell execution context

3. **✅ Integration and edge cases**
   - Complex and-or list integration: `(echo test) && { echo success; }`
   - Nested compound commands: `( { (echo nested); } )`
   - Pipeline integration: `echo start | (cat; echo middle) | echo end`
   - Proper AST structure without unnecessary Pipeline wrapping

4. **✅ Comprehensive testing**
   - 27 compound command tests (10 basic + 17 edge cases)
   - All 46 integration tests passing
   - Complex scenarios including control structures, functions, redirections

#### Implementation Details
**Files Modified:**
- `psh/parser/implementations/parser_combinator_example.py`:
  - Added compound command token parsers
  - Implemented `_build_subshell_group()` and `_build_brace_group()` methods
  - Enhanced control structure parsing chain
  - Fixed parser ordering for complex integration scenarios
  - Modified pipeline builder to avoid over-wrapping control structures

**Tests Created:**
- `tests/unit/parser/test_compound_commands_combinator.py` (10 basic tests)
- `tests/unit/parser/test_compound_commands_edge_cases.py` (17 edge case tests)
- Updated integration tests to reflect new capabilities

#### Test Cases ✅ ALL PASSING
```bash
# Subshells
(echo hello)                                    # Simple subshell
(cd /tmp && ls) && echo "back in $PWD"          # Variable scoping
(export VAR=value; echo $VAR); echo ${VAR:-unset}  # Environment isolation

# Brace groups  
{ echo hello; }                                 # Simple brace group
{ echo "header"; cat data; echo "footer"; } > output.txt  # I/O redirection
{ read x; read y; echo $((x + y)); } < numbers.txt       # Input redirection

# Complex integration
(echo test) && { echo success; }               # And-or lists
echo start | (cat; echo middle) | echo end    # Pipeline integration
( { (echo nested); } )                        # Deep nesting
{ (cd dir1 && tar cf -) | (cd dir2 && tar xf -); } 2>errors.log  # Complex nesting

# With control structures
(if true; then echo hi; fi)                   # Control structures in subshells
{ for i in 1 2 3; do echo $i; done; }        # Control structures in brace groups

# With functions
(foo() { echo hello; }; foo)                  # Function definitions in subshells
```

### Phase 3: Arithmetic Commands (Weeks 8-9) ✅ **COMPLETED**

#### Objective
Implement arithmetic command syntax for mathematical operations.

#### Status: ✅ COMPLETED
- **Implementation Date**: January 2025
- **Test Coverage**: 35 comprehensive tests (10 basic + 16 edge cases + 9 integration tests)
- **Integration**: Fully integrated with existing ArithmeticEvaluation AST node
- **Compatibility**: Full feature parity with recursive descent parser

#### Technical Design
```python
def _build_arithmetic_command(self) -> Parser[ArithmeticEvaluation]:
    """Build parser for arithmetic command ((expression)) syntax."""
    def parse_arithmetic_command(tokens: List[Token], pos: int) -> ParseResult[ArithmeticEvaluation]:
        # Check for opening ((
        if pos >= len(tokens) or tokens[pos].type.name != 'DOUBLE_LPAREN':
            return ParseResult(success=False, error=f"Expected '((', got {token.type.name}", position=pos)
        
        pos += 1  # Skip ((
        
        # Collect arithmetic expression until ))
        expr_tokens = []
        paren_depth = 0
        
        while pos < len(tokens):
            token = tokens[pos]
            if token.type.name == 'DOUBLE_RPAREN' and paren_depth == 0:
                break
            # Handle nested parentheses...
            expr_tokens.append(token)
            pos += 1
        
        # Build expression with variable preservation
        expression_parts = []
        for token in expr_tokens:
            if token.type.name == 'VARIABLE':
                expression_parts.append(f'${token.value}')
            else:
                expression_parts.append(token.value)
        
        expression = ' '.join(expression_parts)
        expression = re.sub(r'\s+', ' ', expression).strip()
        
        return ParseResult(
            success=True,
            value=ArithmeticEvaluation(expression=expression, redirects=[], background=False),
            position=pos
        )
```

#### Implementation Tasks ✅ COMPLETED
1. **✅ Parser implementation**
   - Added `DOUBLE_LPAREN` and `DOUBLE_RPAREN` token parsers
   - Integrated into control structure parsing chain
   - Handles complex expressions with proper parentheses tracking
   - Preserves variable syntax (`$var`) when tokenized as separate VARIABLE tokens
   
2. **✅ AST integration**
   - Integrated with existing `ArithmeticEvaluation` AST node
   - Added to control structure parsing chain via `or_else` composition
   - Fixed pipeline and and-or list unwrapping to prevent unnecessary wrapping
   
3. **✅ Comprehensive testing**
   - Created 35 tests covering basic usage through complex scenarios
   - Edge cases: empty expressions, complex operators, special variables
   - Integration tests: arithmetic in control structures, logical operators, sequences

#### Implementation Details
**Files Modified:**
- `psh/parser/implementations/parser_combinator_example.py`:
  - Added ArithmeticEvaluation import
  - Added arithmetic command token parsers (DOUBLE_LPAREN, DOUBLE_RPAREN)
  - Implemented `_build_arithmetic_command()` method
  - Enhanced control structure parsing chain
  - Fixed unwrapping logic to prevent unnecessary Pipeline/AndOrList wrapping

**Tests Created:**
- `tests/unit/parser/test_arithmetic_commands_combinator.py` (10 basic tests)
- `tests/unit/parser/test_arithmetic_commands_edge_cases.py` (16 edge case tests)
- `tests/unit/parser/test_arithmetic_commands_integration.py` (9 integration tests)
- Updated integration tests to reflect new arithmetic command support

#### Test Cases ✅ ALL PASSING
```bash
# Basic arithmetic commands
((x = 5 + 3))                          # Simple assignment
((++x))                                 # Increment operations
((total += value))                      # Compound assignment
((a *= 2, b += 3, c--))                # Multiple operations

# In control structures
if ((x > 10)); then echo large; fi     # If conditions
while ((count < 100)); do ((count++)); done  # While loops
for i in 1 2 3; do ((sum += i)); done  # For loop bodies

# Complex expressions
((x * y + z / 2 - 1))                  # Mathematical operations
(($# + $?))                            # Special variables
((x & 0xFF | y << 2))                  # Bitwise operations
((x > 0 ? x : -x))                     # Ternary operator
```

#### Key Achievements
- **Full arithmetic command syntax support** - All `((expression))` constructs now parse correctly
- **Seamless integration** - Works naturally within control structures and shell constructs
- **Proper exit status semantics** - Returns 0 for true expressions, 1 for false
- **Variable handling** - Correctly preserves `$` syntax for variables when appropriate
- **Expression preservation** - Maintains original arithmetic expression structure
- **Error handling** - Graceful handling of malformed expressions and syntax errors

#### Test Cases
```bash
# Basic arithmetic commands
((x = 5 + 3))
((count++))
((total += value))

# In control structures
if ((x > 10)); then echo "large"; fi
while ((i < 100)); do ((i += 2)); done

# Complex expressions
((result = (x * y) / (z - 1) % 10))
```

### Phase 4: Enhanced Test Expressions (Weeks 10-13)

#### Objective
Implement `[[ ]]` conditional expressions with pattern matching.

#### Technical Design
```python
def conditional_expression_parser() -> Parser[ConditionalExpression]:
    """Parse [[ expression ]] syntax."""
    return seq(
        literal('['),
        literal('['),
        whitespace,
        test_expression_parser,
        whitespace,
        literal(']'),
        literal(']')
    ).map(lambda x: ConditionalExpression(x[3]))

def test_expression_parser() -> Parser[TestExpression]:
    """Parse test expressions with operators."""
    # Complex parser supporting:
    # - Binary operators: ==, !=, <, >, -eq, -ne, -lt, -gt
    # - Pattern matching: ==, !=, =~
    # - File tests: -f, -d, -e, -r, -w, -x
    # - Logical operators: &&, ||, !
    # - Parentheses for grouping
```

#### Implementation Tasks
1. **Week 10**: Basic expression parsing
   - Binary comparison operators
   - Unary file test operators
   - String comparisons

2. **Week 11**: Pattern matching
   - Glob pattern support (`==`, `!=`)
   - Regex support (`=~`)
   - Quote handling rules

3. **Week 12**: Logical operators
   - AND/OR/NOT operations
   - Parentheses for grouping
   - Operator precedence

4. **Week 13**: Testing and refinement
   - Edge case handling
   - Error messages
   - Performance optimization

#### Test Cases
```bash
# String comparisons
[[ $str == "hello" ]]
[[ $file == *.txt ]]
[[ $path =~ ^/home/[^/]+/Documents ]]

# Numeric comparisons
[[ $x -gt 10 ]]
[[ $count -eq 0 ]]

# File tests
[[ -f $file && -r $file ]]
[[ -d $dir || -L $dir ]]

# Complex expressions
[[ ($a -gt 5 && $b -lt 10) || ($c == "yes" && -f $file) ]]
```

### Phase 5: Array Support Completion (Weeks 14-16)

#### Objective
Complete array literal syntax and array expansion support.

#### Technical Design
```python
def array_literal_parser() -> Parser[ArrayLiteral]:
    """Parse array=(element1 element2) syntax."""
    return seq(
        identifier,
        literal('='),
        literal('('),
        many(word_parser, sep=whitespace),
        literal(')')
    ).map(lambda x: ArrayLiteral(x[0], x[3]))

def array_subscript_parser() -> Parser[ArraySubscript]:
    """Parse ${array[index]} syntax."""
    # Integration with parameter expansion parser
```

#### Implementation Tasks
1. **Week 14**: Array literal parsing
   - Assignment syntax `arr=(a b c)`
   - Empty array support
   - Quote handling in elements

2. **Week 15**: Array expansion
   - Index access `${arr[5]}`
   - All elements `${arr[@]}`, `${arr[*]}`
   - Array length `${#arr[@]}`

3. **Week 16**: Advanced array features
   - Associative arrays (if supported)
   - Array slicing
   - Testing and validation

#### Test Cases
```bash
# Array literals
colors=(red green blue)
empty=()
mixed=("hello world" 42 $var)

# Array access
echo ${colors[0]}
echo ${colors[@]}
echo ${#colors[@]}

# Array manipulation
arr[5]="fifth"
arr+=(new elements)
unset arr[2]
```

### Phase 6: Advanced I/O and Select (Weeks 17-18)

#### Objective
Complete remaining I/O features and select loop support.

#### Technical Design
```python
def exec_redirect_parser() -> Parser[ExecRedirect]:
    """Parse exec fd< file syntax."""
    # Handle exec with redirections
    
def fd_redirect_parser() -> Parser[FdRedirect]:
    """Parse fd>&fd syntax."""
    # File descriptor duplication

def select_loop_parser() -> Parser[SelectLoop]:
    """Parse select var in list syntax."""
    # Interactive menu loop
```

#### Implementation Tasks
1. **Week 17**: Advanced I/O
   - `exec` with redirections
   - FD duplication (`2>&1`)
   - FD closing (`3>&-`)

2. **Week 18**: Select loop
   - Basic select syntax
   - Menu generation
   - User interaction handling

## Testing Strategy

### Unit Testing
Each phase includes comprehensive unit tests:
- **Parser tests**: Verify correct AST generation
- **Integration tests**: Test with shell execution
- **Error tests**: Invalid syntax handling
- **Edge cases**: Unusual but valid constructs

### Conformance Testing
- Compare AST output with recursive descent parser
- Validate behavior matches bash/POSIX
- Performance benchmarking against hand-coded parser

### Regression Testing
- Ensure existing features remain functional
- Run full test suite after each phase
- Monitor parser performance metrics

## Quality Assurance

### Code Review Process
1. **Design review** before implementation
2. **Code review** for each PR
3. **Test review** for comprehensive coverage
4. **Documentation review** for clarity

### Documentation Requirements
- **Parser combinator guide** updates
- **Feature documentation** for each addition
- **Migration guide** for parser switching
- **Performance analysis** reports

## Risk Management

### Technical Risks
1. **Parser ambiguity**: Some constructs may be ambiguous
   - *Mitigation*: Study bash parser behavior
   - *Mitigation*: Add disambiguation rules

2. **Performance degradation**: Complex features may slow parsing
   - *Mitigation*: Profile and optimize hot paths
   - *Mitigation*: Consider memoization

3. **Integration complexity**: AST changes may affect execution
   - *Mitigation*: Extensive integration testing
   - *Mitigation*: Phased rollout

### Schedule Risks
1. **Underestimated complexity**: Features may take longer
   - *Mitigation*: Buffer time in schedule
   - *Mitigation*: Prioritize high-impact features

2. **Discovered requirements**: New edge cases found
   - *Mitigation*: Allocate research time
   - *Mitigation*: Regular bash comparison

## Success Metrics

### Functional Metrics
- **Feature coverage**: 100% parity with recursive descent
- **Test pass rate**: All existing tests plus new tests passing
- **Bash compatibility**: 95%+ compatibility on real scripts

### Performance Metrics
- **Parse time**: Within 2x of hand-coded parser
- **Memory usage**: Comparable memory footprint
- **Scalability**: Handle large scripts efficiently

### Quality Metrics
- **Code coverage**: 90%+ test coverage
- **Documentation**: Complete for all features
- **Error handling**: Clear messages for all errors

## Timeline Summary

| Phase | Feature | Duration | Priority | Status |
|-------|---------|----------|----------|---------|
| 1 | Process Substitution | 3 weeks | HIGH | ✅ **COMPLETED** |
| 2 | Compound Commands | 4 weeks | HIGH | ✅ **COMPLETED** |
| 3 | Arithmetic Commands | 2 weeks | MEDIUM | ✅ **COMPLETED** |
| 4 | Enhanced Test Expressions | 4 weeks | MEDIUM | 🔲 Pending |
| 5 | Array Support | 3 weeks | MEDIUM | 🔲 Pending |
| 6 | Advanced I/O & Select | 2 weeks | LOW | 🔲 Pending |

**Progress**: 3/6 phases completed (50%)  
**Remaining Duration**: 9 weeks (2.25 months)

## Conclusion

This implementation plan provides a systematic approach to achieving parser combinator feature parity. By focusing on high-impact features first and maintaining rigorous testing standards, we can deliver a fully-featured functional parser that serves both educational and production purposes. The modular approach allows for incremental delivery and validation, reducing risk while maintaining momentum.

The successful completion of this plan will demonstrate that parser combinators can handle the full complexity of shell syntax while maintaining the elegance and composability that makes them valuable as educational tools. This achievement would position PSH's parser combinator as a reference implementation for functional parsing of complex, real-world languages.

## Implementation Completion Notes

### Phase 1 Completion (January 2025)

**Phase 1: Process Substitution** has been successfully completed, marking the first major milestone in achieving parser combinator feature parity. The implementation demonstrates that:

1. **Parser combinators can elegantly handle complex shell syntax** like process substitution
2. **Full integration is possible** with existing AST infrastructure and execution systems
3. **Comprehensive testing ensures reliability** with 26 tests covering basic usage through complex edge cases
4. **Performance and maintainability** are preserved while adding sophisticated language features

### Phase 2 Completion (January 2025)

**Phase 2: Compound Commands** has been successfully completed, adding comprehensive support for subshells and brace groups. This phase demonstrated:

1. **Elegant delimiter parsing** using the `between` combinator for clean syntax handling
2. **Complex integration challenges** solved through careful parser ordering and AST structure preservation
3. **Sophisticated edge case handling** including nested compounds, pipeline integration, and and-or list compatibility
4. **Robust test coverage** with 27 compound command tests plus full integration test suite validation

**Key Technical Achievements:**
- Seamless integration of compound commands into existing control structure parsing
- Proper AST structure preservation without unnecessary Pipeline wrapping
- Complex scenario support: `(echo test) && { echo success; }` and deep nesting
- Full compatibility with all existing shell features (functions, control structures, I/O redirection)

### Phase 3 Completion (January 2025)

**Phase 3: Arithmetic Commands** has been successfully completed, adding comprehensive support for `((expression))` arithmetic command syntax. This phase demonstrated:

1. **Complete arithmetic expression support** including assignments, increments, and complex mathematical operations
2. **Seamless integration** with existing control structures (if, while, for) and shell constructs
3. **Proper AST unwrapping** to prevent unnecessary Pipeline/AndOrList wrapping of standalone control structures
4. **Robust variable handling** preserving `$` syntax when variables are tokenized separately
5. **Comprehensive testing** with 35 tests covering basic usage, edge cases, and integration scenarios

**Key Technical Achievements:**
- Full `((expression))` syntax support with proper parentheses tracking
- Integration into control structure parsing chain via elegant `or_else` composition
- Enhanced pipeline and and-or list building to prevent over-wrapping
- Variable preservation logic for different tokenization contexts
- Extensive test coverage ensuring reliability and compatibility

**Progress Update:**
With Phases 1, 2, and 3 complete, the parser combinator implementation now supports **~95% of critical shell syntax**, including all high-priority features plus essential arithmetic operations. The remaining phases focus on advanced features that enhance shell capability but are less frequently used in basic shell scripting.

This significant milestone validates the parser combinator approach for handling complex shell syntax while maintaining the elegance and composability that makes it valuable as an educational tool.