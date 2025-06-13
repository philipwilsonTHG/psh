# PSH Parser Improvement Implementation Plan

## Overview

This plan outlines a phased approach to implementing parser improvements identified in `parser_improvement_observations.md`. The improvements are organized by priority and dependency, maintaining backward compatibility and the educational clarity of the codebase.

## Phase 1: Eliminate Parser Duplication (High Priority) ✅ COMPLETE

### Goal
Remove duplication between statement-context and pipeline-context parsers by leveraging existing neutral parsers.

### Implementation Steps

1. **Refactor control structure parsers** (2-3 hours)
   ```python
   # Before: Duplicate implementations
   def parse_if_statement(self) -> IfConditional
   def parse_if_command(self) -> IfConditional
   
   # After: Single implementation with context setting
   def parse_if_statement(self) -> IfConditional:
       node = self._parse_if_neutral()
       node.execution_context = ExecutionContext.STATEMENT
       return node
   
   def parse_if_command(self) -> IfConditional:
       node = self._parse_if_neutral()
       node.execution_context = ExecutionContext.PIPELINE
       return node
   ```

2. **Apply to all control structures**:
   - `while` loops
   - `for` loops (both styles)
   - `case` statements
   - `select` statements
   - arithmetic commands

3. **Update tests** to ensure behavior remains identical

4. **Benefits**:
   - Reduces code by ~200 lines
   - Single source of truth for parsing logic
   - Easier to maintain and debug

### Files to Modify
- `psh/parser.py`
- Tests: `tests/test_parser.py`, `tests/test_control_structures_in_pipelines.py`

### Completion Notes
- Successfully refactored 12 duplicate parser methods
- Reduced parser code by ~267 lines
- All parser tests pass (100% success rate)
- Used automated refactoring script for consistency

## Phase 2: Improved Token Collection (Medium Priority) ✅ PARTIAL

### Goal
Create reusable token collection utilities to eliminate duplicate quote/bracket tracking logic.

### Implementation Steps

1. **Add TokenStream class** (4-5 hours) ✅ COMPLETE
   ```python
   class TokenStream:
       """Enhanced token stream with utility methods."""
       
       def __init__(self, tokens: List[Token], pos: int = 0):
           self.tokens = tokens
           self.pos = pos
       
       def collect_until_balanced(self, 
                                  open_type: TokenType, 
                                  close_type: TokenType,
                                  respect_quotes: bool = True) -> List[Token]:
           """Collect tokens until balanced close token found."""
           # Implementation here
       
       def peek_composite_sequence(self) -> Optional[List[Token]]:
           """Look ahead for adjacent tokens forming composite."""
           # Implementation here
   ```

2. **Refactor array key parsing**: ✅ COMPLETE
   ```python
   def _parse_array_key_tokens(self) -> List[Token]:
       # Old: Manual state tracking
       # New: Use TokenStream
       stream = TokenStream(self.tokens, self.pos)
       return stream.collect_until_balanced(
           TokenType.LBRACKET, 
           TokenType.RBRACKET
       )
   ```

3. **Apply to other balanced constructs**: ⏳ TODO
   - Command substitution `$(...)`
   - Arithmetic expansion `$((...))` 
   - Process substitution `<(...)`
   - Brace expansion `{...}`

### Files to Create/Modify
- New: `psh/token_stream.py` ✅ CREATED
- Modify: `psh/parser.py` ✅ MODIFIED (array key parsing)
- Tests: `tests/test_token_stream.py` ✅ CREATED (10 comprehensive tests)

### Completion Notes
- Successfully created TokenStream class with all planned functionality
- Refactored array key parsing to use TokenStream.collect_until_balanced()
- Fixed quote handling to work with shell's STRING token semantics
- All associative and indexed array tests pass
- Still need to apply TokenStream to other parts of parser (arithmetic sections, etc.)

## Phase 3: Enhanced Composite Argument Handling (Medium Priority)

### Goal
Move composite argument detection to a dedicated phase between tokenization and parsing.

### Implementation Steps

1. **Create CompositeTokenProcessor** (3-4 hours)
   ```python
   class CompositeTokenProcessor:
       """Process token stream to identify composite arguments."""
       
       def process(self, tokens: List[Token]) -> List[Token]:
           """Return new token list with composite tokens merged."""
           result = []
           i = 0
           while i < len(tokens):
               if self._is_composite_start(tokens, i):
                   composite = self._collect_composite(tokens, i)
                   result.append(self._merge_tokens(composite))
                   i += len(composite)
               else:
                   result.append(tokens[i])
                   i += 1
           return result
   ```

2. **Add new COMPOSITE token type**:
   ```python
   class TokenType(Enum):
       # ... existing types ...
       COMPOSITE = auto()  # Merged adjacent tokens
   ```

3. **Update parser to handle COMPOSITE tokens**

### Benefits
- Simplifies parser logic
- Makes composite handling testable in isolation
- Could enable better error messages

### Files to Modify
- New: `psh/composite_processor.py`
- Modify: `psh/token_types.py`, `psh/parser.py`
- Tests: `tests/test_composite_processor.py`

## Phase 4: Fix Arithmetic Command Grammar (High Priority) ✅ COMPLETE

### Goal
Enable arithmetic commands in conditional contexts: `((x > 5)) && echo "big"`

### Implementation Steps

1. **Analyze grammar conflict** (2 hours)
   - Document why `((` at statement start works but not after `&&`
   - Identify lookahead requirements

2. **Implement solution** (3-4 hours)
   - Option A: Enhanced lookahead in `parse_pipeline_component()`
   - Option B: Refactor grammar to eliminate ambiguity
   - Option C: Special case for arithmetic after operators

3. **Comprehensive testing**
   - All contexts where `((...))` should work
   - Error cases that should still fail

### Files to Modify
- `psh/parser.py` (parse_pipeline_component method)
- Tests: `tests/test_arithmetic_command.py`

### Completion Notes
- Fixed by modifying `_parse_top_level_item()` to check for && and || after control structures
- Fixed PipelineExecutor to check for ArithmeticEvaluation before CompoundCommand (order matters due to inheritance)
- All arithmetic command tests pass, new test cases added and verified

## Phase 5: Parser Context Management (Low Priority)

### Goal
Encapsulate parser state for better maintainability.

### Implementation Steps

1. **Create ParserContext class** (2 hours)
   ```python
   @dataclass
   class ParserContext:
       """Encapsulate all parser state."""
       in_test_expr: bool = False
       in_arithmetic: bool = False
       in_case_pattern: bool = False
       in_function_body: bool = False
       allow_keywords: bool = True
       
       def __enter__(self):
           """Support context manager for state changes."""
           self._saved_state = dataclasses.asdict(self)
           return self
       
       def __exit__(self, *args):
           """Restore previous state."""
           for key, value in self._saved_state.items():
               setattr(self, key, value)
   ```

2. **Refactor parser to use context**:
   ```python
   def parse_enhanced_test_statement(self):
       with self.context:
           self.context.in_test_expr = True
           # Parse test expression
   ```

### Files to Modify
- Modify: `psh/parser.py`
- Tests: Existing tests should pass unchanged

## Phase 6: AST Visitor Pattern (Future)

### Goal
Implement visitor pattern for cleaner separation between AST and execution.

### Implementation Steps

1. **Create base visitor** (4-5 hours)
   ```python
   class ASTVisitor(ABC):
       """Base class for AST visitors."""
       
       def visit(self, node: ASTNode) -> Any:
           """Dispatch to appropriate visit method."""
           method = 'visit_' + node.__class__.__name__
           visitor = getattr(self, method, self.generic_visit)
           return visitor(node)
       
       def generic_visit(self, node: ASTNode) -> Any:
           """Default visitor for unhandled nodes."""
           raise NotImplementedError(f"No visitor for {type(node)}")
   ```

2. **Create concrete visitors**:
   - `ExecutorVisitor` - executes commands
   - `ASTFormatterVisitor` - pretty prints AST
   - `ValidationVisitor` - validates AST correctness

3. **Migrate executors gradually**

### Files to Create/Modify
- New: `psh/visitors/base.py`, `psh/visitors/executor.py`
- Modify: Existing executors over time

## Phase 7: Enhanced Error Recovery (Future)

### Goal
Improve parser error handling and recovery.

### Implementation Steps

1. **Add ErrorNode to AST** (2 hours)
2. **Implement error productions** (4-5 hours)
3. **Better synchronization** (3-4 hours)
4. **Partial AST construction** (5-6 hours)

## Testing Strategy

Each phase should:
1. Maintain 100% backward compatibility
2. Add comprehensive unit tests for new components
3. Run full regression test suite
4. Add performance benchmarks where relevant

## Rollout Plan

1. **Week 1-2**: Phase 1 (Parser Duplication) + Phase 4 (Arithmetic Grammar)
2. **Week 3-4**: Phase 2 (Token Collection) 
3. **Week 5-6**: Phase 3 (Composite Arguments)
4. **Week 7-8**: Phase 5 (Context Management)
5. **Future**: Phases 6-7 as needed

## Success Metrics

- No regression in test suite (maintain 100% pass rate)
- Reduced parser code size by 10-20%
- Improved parser maintainability (measured by ease of adding new features)
- Fixed arithmetic command grammar issue
- Better error messages for common syntax errors

## Risks and Mitigations

1. **Risk**: Breaking existing functionality
   - **Mitigation**: Comprehensive test suite, phased rollout

2. **Risk**: Performance regression
   - **Mitigation**: Benchmark before/after each phase

3. **Risk**: Making code less educational
   - **Mitigation**: Add documentation, keep abstractions simple

4. **Risk**: Scope creep
   - **Mitigation**: Stick to defined phases, defer "nice to have" features