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

## Phase 2: Improved Token Collection (Medium Priority) ✅ COMPLETE

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
           
       def collect_arithmetic_expression(self,
                                       stop_condition=None,
                                       transform_redirects: bool = True) -> Tuple[List[Token], str]:
           """Collect tokens for arithmetic expression with special handling."""
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

3. **Apply to other balanced constructs**: ✅ COMPLETE
   - Command substitution `$(...)`  ✅ Already handled by lexer
   - Arithmetic expansion `$((...))` ✅ Already handled by lexer
   - Process substitution `<(...)` ✅ Already handled by lexer
   - Arithmetic expression parsing ✅ Refactored to use TokenStream
   - Composite argument parsing ✅ Refactored to use TokenStream
   - For loop iterable parsing ✅ Refactored to use TokenStream

### Files to Create/Modify
- New: `psh/token_stream.py` ✅ CREATED
- Modify: `psh/parser.py` ✅ MODIFIED (multiple refactorings)
- Tests: `tests/test_token_stream.py` ✅ CREATED (12 comprehensive tests)

### Completion Notes
- Successfully created TokenStream class with all planned functionality
- Added specialized `collect_arithmetic_expression` method for arithmetic parsing
- Refactored 6 parser methods to use TokenStream:
  - `_parse_array_key_tokens` - Uses `collect_until_balanced`
  - `parse_composite_argument` - Uses `peek_composite_sequence`
  - `_parse_for_iterable` - Uses `collect_until`
  - `_parse_arithmetic_section` - Uses `collect_arithmetic_expression`
  - `_parse_arithmetic_section_until_double_rparen` - Uses `collect_arithmetic_expression`
  - `_parse_arithmetic_expression_until_double_rparen` - Uses `collect_arithmetic_expression`
- Eliminated ~150 lines of manual token collection code
- All tests pass: arrays, associative arrays, arithmetic commands, C-style for loops

## Phase 3: Enhanced Composite Argument Handling (Medium Priority) ✅ COMPLETE

### Goal
Move composite argument detection to a dedicated phase between tokenization and parsing.

### Implementation Steps

1. **Create CompositeTokenProcessor** (3-4 hours) ✅ COMPLETE
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

2. **Add new COMPOSITE token type**: ✅ COMPLETE
   ```python
   class TokenType(Enum):
       # ... existing types ...
       COMPOSITE = auto()  # Merged adjacent tokens
   ```

3. **Update parser to handle COMPOSITE tokens** ✅ COMPLETE

### Benefits
- Simplifies parser logic
- Makes composite handling testable in isolation
- Could enable better error messages

### Files Modified
- Created: `psh/composite_processor.py` with CompositeToken and CompositeTokenProcessor classes
- Modified: `psh/token_types.py` - Added COMPOSITE token type
- Modified: `psh/parser.py` - Added optional use_composite_processor parameter and COMPOSITE handling
- Modified: `psh/parser_helpers.py` - Added COMPOSITE to WORD_LIKE tokens
- Created: `tests/test_composite_processor.py` - 12 comprehensive tests
- Created: `tests/test_parser_composite_integration.py` - 10 integration tests

### Completion Notes
- Successfully created CompositeTokenProcessor that identifies adjacent tokens
- Processor correctly handles quoted strings, variables, expansions, and special characters
- Parser can optionally use the processor via `use_composite_processor` parameter
- When enabled, composite tokens are pre-merged before parsing begins
- All existing tests pass, demonstrating backward compatibility
- The processor is particularly useful for cases where the lexer produces separate tokens that should be treated as a single argument (e.g., "hello"world)

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

## Phase 5: Parser Context Management (Low Priority) ✅ COMPLETE

### Goal
Encapsulate parser state for better maintainability.

### Implementation Steps

1. **Enhanced ParserContext class** (2 hours) ✅ COMPLETE
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

2. **Refactor parser to use context**: ✅ COMPLETE
   ```python
   def parse_enhanced_test_statement(self):
       with self.context:
           self.context.in_test_expr = True
           # Parse test expression
   ```

### Files Modified
- Modified: `psh/parser_helpers.py` - Enhanced ParseContext with context manager support
- Modified: `psh/parser.py` - Refactored parsing methods to use context manager
- Created: `tests/test_parser_context.py` - 7 unit tests for ParseContext
- Created: `tests/test_parser_context_integration.py` - 7 integration tests

### Completion Notes
- Enhanced existing ParseContext class rather than creating a new one
- Added context manager support with nested context handling
- Implemented proper state save/restore with stack for nested contexts
- Added new parser state flags: in_here_document, in_command_substitution, allow_empty_commands
- Refactored 4 parser methods to use context manager:
  - `parse_enhanced_test_statement` - Sets in_test_expr
  - `_parse_arithmetic_neutral` - Sets in_arithmetic
  - `parse_case_item` - Sets in_case_pattern  
  - `parse_compound_command` - Sets in_function_body
- All existing tests pass, demonstrating backward compatibility
- Context manager properly handles exceptions and nested usage

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