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

### Phase 2: Compound Commands (Weeks 4-7)

#### Objective
Add support for subshells and brace groups for proper command grouping.

#### Technical Design
```python
# Subshell parser
def subshell_parser() -> Parser[Subshell]:
    """Parse (command list) syntax."""
    return seq(
        literal('('),
        whitespace,
        command_list_parser,
        whitespace,
        literal(')')
    ).map(lambda x: Subshell(x[2]))

# Brace group parser
def brace_group_parser() -> Parser[BraceGroup]:
    """Parse { command list; } syntax."""
    return seq(
        literal('{'),
        whitespace,
        command_list_parser,
        whitespace,
        literal('}')
    ).map(lambda x: BraceGroup(x[2]))
```

#### Implementation Tasks
1. **Week 4**: Subshell implementation
   - Create `subshell_parser` combinator
   - Handle variable scoping semantics
   - Integrate with pipeline parser

2. **Week 5**: Brace group implementation
   - Create `brace_group_parser` combinator
   - Ensure proper semicolon/newline handling
   - Maintain current shell context

3. **Week 6**: Integration and edge cases
   - Handle nested compound commands
   - Redirections on compound commands
   - Background execution support

4. **Week 7**: Comprehensive testing
   - Test variable scoping
   - Test exit status propagation
   - Performance benchmarking

#### Test Cases
```bash
# Subshells
(cd /tmp && ls) && echo "back in $PWD"
(export VAR=value; echo $VAR); echo ${VAR:-unset}

# Brace groups
{ echo "header"; cat data; echo "footer"; } > output.txt
{ read x; read y; echo $((x + y)); } < numbers.txt

# Complex nesting
{ (cd dir1 && tar cf -) | (cd dir2 && tar xf -); } 2>errors.log
```

### Phase 3: Arithmetic Commands (Weeks 8-9)

#### Objective
Implement arithmetic command syntax for mathematical operations.

#### Technical Design
```python
def arithmetic_command_parser() -> Parser[ArithmeticCommand]:
    """Parse ((expression)) command syntax."""
    return seq(
        literal('('),
        literal('('),
        arithmetic_expression_parser,
        literal(')'),
        literal(')')
    ).map(lambda x: ArithmeticCommand(x[2]))
```

#### Implementation Tasks
1. **Week 8**: Parser implementation
   - Distinguish from arithmetic expansion `$((...))`
   - Support all arithmetic operators
   - Handle assignment operations

2. **Week 9**: Integration and testing
   - Exit status semantics (0 if true, 1 if false)
   - Side effects (variable assignments)
   - Loop integration testing

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
| 2 | Compound Commands | 4 weeks | HIGH | 🔲 Pending |
| 3 | Arithmetic Commands | 2 weeks | MEDIUM | 🔲 Pending |
| 4 | Enhanced Test Expressions | 4 weeks | MEDIUM | 🔲 Pending |
| 5 | Array Support | 3 weeks | MEDIUM | 🔲 Pending |
| 6 | Advanced I/O & Select | 2 weeks | LOW | 🔲 Pending |

**Progress**: 1/6 phases completed (16.7%)  
**Remaining Duration**: 15 weeks (3.75 months)

## Conclusion

This implementation plan provides a systematic approach to achieving parser combinator feature parity. By focusing on high-impact features first and maintaining rigorous testing standards, we can deliver a fully-featured functional parser that serves both educational and production purposes. The modular approach allows for incremental delivery and validation, reducing risk while maintaining momentum.

The successful completion of this plan will demonstrate that parser combinators can handle the full complexity of shell syntax while maintaining the elegance and composability that makes them valuable as educational tools. This achievement would position PSH's parser combinator as a reference implementation for functional parsing of complex, real-world languages.

## Phase 1 Completion Notes (January 2025)

**Phase 1: Process Substitution** has been successfully completed, marking the first major milestone in achieving parser combinator feature parity. The implementation demonstrates that:

1. **Parser combinators can elegantly handle complex shell syntax** like process substitution
2. **Full integration is possible** with existing AST infrastructure and execution systems
3. **Comprehensive testing ensures reliability** with 26 tests covering basic usage through complex edge cases
4. **Performance and maintainability** are preserved while adding sophisticated language features

This foundation validates the approach for completing the remaining phases and achieving full parser combinator feature parity with the recursive descent implementation.