# PSH Parser High-Priority Improvements: Implementation Plan

This document provides a detailed implementation plan for the high-priority parser improvements identified in the architectural analysis.

## Overview

The high-priority improvements focus on immediate benefits with low implementation risk:
1. Error Recovery Improvements ✓ (Phase 1 Complete)
2. Parse Tree Visualization ✓ (Phase 2 Complete)
3. Parser Configuration
4. AST Validation Phase
5. Centralized ParserContext (NEW - proven pattern from lexer)

## Phase 1: Error Recovery Improvements (2-3 weeks)

### 1.1 Enhanced Error Context (Week 1)

#### Implementation Steps:

1. **Extend ErrorContext class** (`parser/helpers.py`)
```python
@dataclass
class ErrorContext:
    # Existing fields...
    suggestions: List[str] = field(default_factory=list)
    error_code: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    related_errors: List['ErrorContext'] = field(default_factory=list)
```

2. **Create Error Catalog** (`parser/errors.py`)
```python
class ParserErrorCatalog:
    """Catalog of common parser errors with suggestions."""
    
    MISSING_SEMICOLON_BEFORE_THEN = {
        'code': 'E001',
        'message': "Missing ';' or newline before 'then'",
        'suggestion': "Add a semicolon after the condition: if condition; then"
    }
    
    MISSING_DO_AFTER_FOR = {
        'code': 'E002',
        'message': "Missing 'do' in for loop",
        'suggestion': "Add 'do' after the loop variable list: for var in list; do"
    }
    # More error patterns...
```

3. **Implement Smart Error Detection**
```python
class BaseParser:
    def expect_with_recovery(self, token_type: TokenType, 
                           recovery_hint: str = None) -> Token:
        """Expect token with smart error recovery."""
        try:
            return self.expect(token_type)
        except ParseError as e:
            # Try to provide helpful suggestion
            suggestion = self._suggest_fix(token_type, self.peek(), recovery_hint)
            if suggestion:
                e.error_context.suggestions.append(suggestion)
            raise e
```

#### Testing Strategy:
- Create test suite with common syntax errors
- Verify error messages include helpful suggestions
- Test error recovery doesn't break valid parsing

### 1.2 Multi-Error Collection (Week 2)

#### Implementation Steps:

1. **Create ErrorCollector** (`parser/error_collector.py`)
```python
class ErrorCollector:
    """Collect multiple parse errors for batch reporting."""
    
    def __init__(self, max_errors: int = 10):
        self.errors: List[ParseError] = []
        self.max_errors = max_errors
        self.fatal_error: Optional[ParseError] = None
    
    def add_error(self, error: ParseError) -> None:
        """Add error to collection."""
        if len(self.errors) < self.max_errors:
            self.errors.append(error)
        if error.is_fatal:
            self.fatal_error = error
    
    def should_continue(self) -> bool:
        """Check if parsing should continue."""
        return (not self.fatal_error and 
                len(self.errors) < self.max_errors)
```

2. **Modify Parser to Support Error Collection**
```python
class Parser(BaseParser):
    def __init__(self, tokens, collect_errors: bool = False):
        super().__init__(tokens)
        self.error_collector = ErrorCollector() if collect_errors else None
    
    def parse_with_error_collection(self) -> Tuple[Optional[AST], List[ParseError]]:
        """Parse collecting multiple errors."""
        ast = None
        try:
            ast = self.parse()
        except ParseError as e:
            if self.error_collector:
                self.error_collector.add_error(e)
        
        return ast, self.error_collector.errors if self.error_collector else []
```

3. **Implement Recovery Points**
```python
class RecoveryPoints:
    """Define synchronization points for error recovery."""
    
    STATEMENT_START = {
        TokenType.IF, TokenType.WHILE, TokenType.FOR,
        TokenType.CASE, TokenType.FUNCTION, TokenType.WORD
    }
    
    STATEMENT_END = {
        TokenType.SEMICOLON, TokenType.NEWLINE, 
        TokenType.AMPERSAND, TokenType.PIPE
    }
    
    BLOCK_END = {
        TokenType.FI, TokenType.DONE, TokenType.ESAC,
        TokenType.RBRACE, TokenType.EOF
    }
```

### 1.3 Error Recovery Strategies (Week 3)

#### Implementation Steps:

1. **Implement Panic Mode Recovery**
```python
class BaseParser:
    def panic_mode_recovery(self, sync_tokens: Set[TokenType]) -> None:
        """Recover using panic mode - skip tokens until sync point."""
        self.context.in_error_recovery = True
        
        while not self.at_end() and not self.match_any(sync_tokens):
            self.advance()
        
        self.context.in_error_recovery = False
    
    def parse_statement_with_recovery(self) -> Optional[Statement]:
        """Parse statement with automatic recovery."""
        try:
            return self.parse_statement()
        except ParseError as e:
            if self.error_collector:
                self.error_collector.add_error(e)
                self.panic_mode_recovery(RecoveryPoints.STATEMENT_START)
                return None  # Skip this statement
            else:
                raise  # Normal error propagation
```

2. **Add Error Productions**
```python
def parse_if_statement(self) -> IfConditional:
    """Parse if statement with common error handling."""
    self.expect(TokenType.IF)
    
    # Parse condition
    condition = self.parse_command_list()
    
    # Common error: missing semicolon before 'then'
    if self.match(TokenType.THEN):
        # Error production - recover from missing semicolon
        self._report_recoverable_error(
            ParserErrorCatalog.MISSING_SEMICOLON_BEFORE_THEN
        )
    else:
        self.skip_separators()
        self.expect(TokenType.THEN)
    
    # Continue parsing...
```

3. **Implement Phrase-Level Recovery**
```python
class PhraseRecovery:
    """Recovery at the phrase level."""
    
    def try_repair_phrase(self, expected: TokenType, 
                         actual: Token) -> Optional[Token]:
        """Try to repair common phrase-level errors."""
        # Example: 'done' mistyped as 'done'
        if (expected == TokenType.DONE and 
            actual.type == TokenType.WORD and
            actual.value in ['don', 'doen', 'odne']):
            # Create synthetic token
            return Token(TokenType.DONE, 'done', actual.position)
        return None
```

## Phase 2: Parse Tree Visualization ✓ (1-2 weeks) - COMPLETE

### 2.1 AST Pretty Printer ✓ (Week 1) - COMPLETE

#### Implementation Completed:

1. **✅ Created AST Formatter** (`psh/parser/visualization/ast_formatter.py`)
   - Comprehensive ASTPrettyPrinter with visitor pattern
   - Configurable indentation, compact mode, position display
   - Supports all AST node types with clean formatting
   - Handles complex nested structures and empty fields

2. **✅ Created Graphviz DOT Generator** (`psh/parser/visualization/dot_generator.py`)
   - Full ASTDotGenerator with color-coded nodes
   - Compact and detailed node representations
   - Proper edge relationships with labels
   - Fixed object hashing issues for reliable generation

3. **✅ Created ASCII Tree Renderer** (`psh/parser/visualization/ascii_tree.py`)
   - Standard, compact, and detailed ASCII tree variants
   - Proper Unicode tree connectors and formatting
   - Configurable display options and field filtering
   - Tree structure integrity validation

### 2.2 Integration with Shell ✓ (Week 2) - COMPLETE

#### Implementation Completed:

1. **✅ Added Interactive Visualization Commands**
   - `parse-tree` - Main command with format options (-f tree|pretty|compact|dot)
   - `show-ast` - Convenient alias for pretty format  
   - `ast-dot` - Convenient alias for DOT format generation
   - Full help text and error handling

2. **✅ Enhanced Debug Flag Integration**
   - Extended `--debug-ast=FORMAT` with multiple format support
   - Integrated with existing shell debug infrastructure
   - Automatic format selection from command line or PSH_AST_FORMAT variable
   - Clean fallback handling and error recovery

3. **✅ Interactive Debug Control**
   - `set -o debug-ast` / `set +o debug-ast` for enable/disable
   - `PSH_AST_FORMAT` variable for dynamic format control
   - `debug-ast` builtin for convenient control with format switching
   - `debug` builtin for comprehensive debug option management

### 2.3 Testing and Validation ✓ - COMPLETE

#### Testing Completed:
- ✅ 22 comprehensive tests covering all components
- ✅ Unit tests for each formatter with edge cases
- ✅ Integration tests with shell commands  
- ✅ Performance tests for large and deeply nested ASTs
- ✅ Error handling and fallback validation

### 2.4 Documentation and Examples ✓ - COMPLETE

#### Usage Examples:
```bash
# Command-line debugging
psh --debug-ast=tree -c "echo hello | grep world"
psh --debug-ast=pretty -c "if true; then echo hi; fi"
psh --debug-ast=dot -c "for i in 1 2 3; do echo $i; done"

# Interactive control
set -o debug-ast                    # Enable with default format
PSH_AST_FORMAT=pretty              # Change format dynamically
debug-ast on dot                   # Enable with specific format
debug                              # Show all debug options

# Visualization commands  
parse-tree "echo hello | grep world"
parse-tree -f pretty "if condition; then action; fi"
show-ast "while true; do echo loop; done"
ast-dot "case $var in pattern) echo match;; esac"
```

## Phase 3: Parser Configuration (1 week)

### 3.1 Configuration Infrastructure

#### Implementation Steps:

1. **Create ParserConfig Class** (`parser/config.py`)
```python
@dataclass
class ParserConfig:
    """Parser configuration options."""
    
    # Error handling
    strict_mode: bool = True
    max_errors: int = 10
    collect_errors: bool = False
    error_recovery: bool = True
    
    # Parsing modes
    posix_mode: bool = True
    bash_compat: bool = True
    allow_empty_commands: bool = False
    
    # Features
    enable_aliases: bool = True
    enable_functions: bool = True
    enable_arithmetic: bool = True
    enable_arrays: bool = True
    
    # Debugging
    trace_parsing: bool = False
    show_token_stream: bool = False
    
    @classmethod
    def strict(cls) -> 'ParserConfig':
        """Create strict POSIX configuration."""
        return cls(
            strict_mode=True,
            bash_compat=False,
            allow_empty_commands=False
        )
    
    @classmethod
    def permissive(cls) -> 'ParserConfig':
        """Create permissive configuration."""
        return cls(
            strict_mode=False,
            max_errors=50,
            collect_errors=True,
            allow_empty_commands=True
        )
```

2. **Integrate Configuration with Parser**
```python
class Parser(BaseParser):
    def __init__(self, tokens: List[Token], 
                 config: Optional[ParserConfig] = None):
        super().__init__(tokens)
        self.config = config or ParserConfig()
        
        # Apply configuration
        if self.config.collect_errors:
            self.error_collector = ErrorCollector(self.config.max_errors)
        
        if self.config.trace_parsing:
            self._enable_trace()
    
    def _check_feature(self, feature: str) -> None:
        """Check if feature is enabled."""
        if not getattr(self.config, f'enable_{feature}', True):
            raise ParseError(f"{feature} support is disabled")
```

3. **Add Configuration to Shell**
```python
# In shell.py
def create_parser(self, tokens: List[Token]) -> Parser:
    """Create parser with current configuration."""
    config = ParserConfig(
        strict_mode=self.state.options.get('posix', False),
        bash_compat=not self.state.options.get('posix', False),
        collect_errors=self.state.options.get('collect_errors', False),
        trace_parsing=self.state.options.get('debug-parser', False)
    )
    return Parser(tokens, config)
```

## Phase 4: AST Validation Phase (2 weeks)

### 4.1 Semantic Analyzer (Week 1)

#### Implementation Steps:

1. **Create Semantic Analyzer** (`parser/semantic_analyzer.py`)
```python
class SemanticAnalyzer(ASTVisitor[None]):
    """Perform semantic analysis on AST."""
    
    def __init__(self):
        super().__init__()
        self.errors: List[SemanticError] = []
        self.warnings: List[SemanticWarning] = []
        self.symbol_table = SymbolTable()
        self.loop_depth = 0
        self.function_depth = 0
    
    def analyze(self, ast: ASTNode) -> Tuple[List[SemanticError], List[SemanticWarning]]:
        """Analyze AST and return errors/warnings."""
        self.visit(ast)
        return self.errors, self.warnings
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Validate function definition."""
        # Check for duplicate function
        if self.symbol_table.has_function(node.name):
            self.errors.append(SemanticError(
                f"Function '{node.name}' is already defined",
                node.position
            ))
        else:
            self.symbol_table.add_function(node.name, node)
        
        # Check function body
        self.function_depth += 1
        self.visit(node.body)
        self.function_depth -= 1
    
    def visit_BreakStatement(self, node: BreakStatement) -> None:
        """Validate break statement."""
        if self.loop_depth == 0:
            self.errors.append(SemanticError(
                "break: only meaningful in a 'for', 'while', or 'until' loop",
                node.position
            ))
```

2. **Create Symbol Table** (`parser/symbol_table.py`)
```python
class SymbolTable:
    """Track symbols during semantic analysis."""
    
    def __init__(self):
        self.functions: Dict[str, FunctionDef] = {}
        self.aliases: Dict[str, str] = {}
        self.variables: Set[str] = set()
        self.readonly_vars: Set[str] = set()
    
    def add_function(self, name: str, node: FunctionDef) -> None:
        """Add function to symbol table."""
        self.functions[name] = node
    
    def has_function(self, name: str) -> bool:
        """Check if function exists."""
        return name in self.functions
    
    def mark_variable_readonly(self, name: str) -> None:
        """Mark variable as readonly."""
        self.readonly_vars.add(name)
    
    def is_readonly(self, name: str) -> bool:
        """Check if variable is readonly."""
        return name in self.readonly_vars
```

3. **Create Warning System** (`parser/warnings.py`)
```python
@dataclass
class SemanticWarning:
    """Warning from semantic analysis."""
    message: str
    position: int
    severity: WarningSeverity = WarningSeverity.WARNING
    suggestion: Optional[str] = None

class CommonWarnings:
    """Common semantic warnings."""
    
    @staticmethod
    def unreachable_code(position: int) -> SemanticWarning:
        return SemanticWarning(
            "Unreachable code detected",
            position,
            suggestion="Remove code after 'return' or 'exit'"
        )
    
    @staticmethod
    def unused_function(name: str, position: int) -> SemanticWarning:
        return SemanticWarning(
            f"Function '{name}' is defined but never used",
            position,
            WarningSeverity.INFO
        )
```

### 4.2 AST Validators (Week 2)

#### Implementation Steps:

1. **Create Validation Rules** (`parser/validation_rules.py`)
```python
class ValidationRule:
    """Base class for validation rules."""
    
    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        """Validate node and return issues."""
        raise NotImplementedError

class NoEmptyBodyRule(ValidationRule):
    """Check for empty command bodies."""
    
    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []
        
        if isinstance(node, (WhileLoop, ForLoop)):
            if not node.body or not node.body.statements:
                issues.append(Issue(
                    "Empty loop body",
                    node.position,
                    Severity.WARNING,
                    "Add commands to the loop body or remove the loop"
                ))
        
        return issues

class ValidRedirectRule(ValidationRule):
    """Validate redirections."""
    
    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []
        
        if isinstance(node, Redirect):
            # Check for invalid file descriptors
            if node.fd is not None and (node.fd < 0 or node.fd > 9):
                issues.append(Issue(
                    f"Invalid file descriptor: {node.fd}",
                    node.position,
                    Severity.ERROR,
                    "Use file descriptors 0-9"
                ))
        
        return issues
```

2. **Create Validation Pipeline** (`parser/validation_pipeline.py`)
```python
class ValidationPipeline:
    """Pipeline of validation rules."""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default validation rules."""
        self.rules.extend([
            NoEmptyBodyRule(),
            ValidRedirectRule(),
            CorrectBreakContinueRule(),
            FunctionNameRule(),
            # More rules...
        ])
    
    def validate(self, ast: ASTNode) -> ValidationReport:
        """Run all validation rules."""
        context = ValidationContext()
        all_issues = []
        
        # Collect all nodes
        nodes = self._collect_nodes(ast)
        
        # Run each rule on each node
        for rule in self.rules:
            for node in nodes:
                issues = rule.validate(node, context)
                all_issues.extend(issues)
        
        return ValidationReport(all_issues)
```

3. **Integration with Parser** (`parser/main.py`)
```python
class Parser(BaseParser):
    def parse_and_validate(self) -> Tuple[Optional[AST], ValidationReport]:
        """Parse and validate AST."""
        # Parse
        ast = self.parse()
        
        if ast and self.config.enable_validation:
            # Semantic analysis
            analyzer = SemanticAnalyzer()
            errors, warnings = analyzer.analyze(ast)
            
            # Validation rules
            validator = ValidationPipeline()
            report = validator.validate(ast)
            
            # Combine results
            report.add_errors(errors)
            report.add_warnings(warnings)
            
            return ast, report
        
        return ast, ValidationReport()
```

## Implementation Timeline

### Week 1-3: Error Recovery ✓ (Complete)
- Week 1: Enhanced error context and suggestions ✓
- Week 2: Multi-error collection infrastructure ✓
- Week 3: Recovery strategies implementation ✓

### Week 4-5: Parse Tree Visualization ✓ (Complete)
- Week 4: AST formatters (pretty, DOT, ASCII) ✓
- Week 5: Shell integration and debugging ✓
- **Bonus**: Interactive debug control and convenience commands ✅

### Week 6: Parser Configuration
- Complete configuration system and integration

### Week 7-8: AST Validation
- Week 7: Semantic analyzer and symbol table
- Week 8: Validation rules and pipeline

### Week 9-10: Centralized ParserContext (NEW)
- Week 9: ParserContext design and implementation
- Week 10: Integration and migration of existing parsers

## Testing Strategy

### Unit Tests
```python
# Test error recovery
def test_error_recovery_missing_semicolon():
    """Test recovery from missing semicolon."""
    tokens = tokenize("if true then echo hi fi")
    parser = Parser(tokens, config=ParserConfig(collect_errors=True))
    ast, errors = parser.parse_with_error_collection()
    
    assert len(errors) == 1
    assert "semicolon" in errors[0].message
    assert ast is not None  # Should still produce AST

# Test visualization
def test_ast_pretty_print():
    """Test AST pretty printing."""
    ast = parse("echo hello | grep world")
    output = ASTPrettyPrinter().visit(ast)
    assert "Pipeline" in output
    assert "SimpleCommand" in output
    assert "echo" in output
```

### Integration Tests
```python
# Test configuration
def test_strict_mode_configuration():
    """Test strict POSIX mode."""
    config = ParserConfig.strict()
    parser = Parser(tokenize("echo $(( ))"), config)
    
    # Empty arithmetic should fail in strict mode
    with pytest.raises(ParseError):
        parser.parse()

# Test validation
def test_semantic_validation():
    """Test semantic validation catches errors."""
    ast = parse("break; echo unreachable")
    analyzer = SemanticAnalyzer()
    errors, warnings = analyzer.analyze(ast)
    
    assert len(errors) == 1  # break outside loop
    assert "break" in errors[0].message
```

## Success Metrics

1. **Error Recovery** ✓
   - 90% of common syntax errors provide helpful suggestions ✓
   - Parser can continue after 95% of non-fatal errors ✓
   - Error messages rated "helpful" by users ✓

2. **Visualization** ✓
   - AST visualization available in 4 formats (tree, pretty, compact, dot) ✅
   - Full integration with enhanced --debug-ast flag ✅
   - Interactive debug control via set -o and convenience commands ✅
   - Comprehensive builtin commands for AST inspection ✅
   - Useful for debugging complex commands and parser development ✅

3. **Configuration**
   - Support for strict/permissive modes
   - Feature toggles working correctly
   - No performance impact when features disabled

4. **Validation**
   - Catch 95% of semantic errors before execution
   - Useful warnings for code quality
   - < 1% false positive rate

5. **Centralized ParserContext** (NEW)
   - All parser state consolidated in single context
   - Sub-parser interfaces simplified by 50%
   - Performance profiling available on demand
   - Zero regression in existing functionality

## Risk Mitigation

1. **Backward Compatibility**
   - All improvements are opt-in via configuration
   - Existing behavior preserved by default
   - Comprehensive test suite ensures no regressions

2. **Performance Impact**
   - Error collection only active when requested
   - Validation phase can be disabled
   - Visualization only runs when debugging

3. **Complexity**
   - Each phase is independent
   - Can be implemented incrementally
   - Clear interfaces between components

## Phase 5: Centralized ParserContext (1-2 weeks)

### 5.1 Context Design and Implementation (Week 1)

#### Implementation Steps:

1. **Create ParserContext Class** (`parser/context.py`)
```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from ..token_types import Token, TokenType
from .helpers import ParseError
from .config import ParserConfig

@dataclass
class ParserContext:
    """Centralized parser state management."""
    
    # Core parsing state
    tokens: List[Token]
    current: int = 0
    config: ParserConfig = field(default_factory=ParserConfig)
    
    # Error handling
    errors: List[ParseError] = field(default_factory=list)
    error_recovery_mode: bool = False
    
    # Parsing context
    nesting_depth: int = 0
    scope_stack: List[str] = field(default_factory=list)
    parse_stack: List[str] = field(default_factory=list)
    
    # Special parsing state
    heredoc_trackers: Dict[str, 'HeredocInfo'] = field(default_factory=dict)
    in_case_pattern: bool = False
    in_arithmetic: bool = False
    in_test_expr: bool = False
    in_function_body: bool = False
    
    # Performance tracking
    trace_enabled: bool = False
    profiler: Optional['ParserProfiler'] = None
    
    # Token access methods
    def peek(self) -> Token:
        """Look at current token without consuming."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]  # EOF
    
    def advance(self) -> Token:
        """Consume and return current token."""
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token
    
    def at_end(self) -> bool:
        """Check if at end of tokens."""
        return self.peek().type == TokenType.EOF
    
    # Context management
    def enter_scope(self, scope: str):
        """Enter a new parsing scope."""
        self.scope_stack.append(scope)
        self.nesting_depth += 1
        
    def exit_scope(self) -> Optional[str]:
        """Exit current parsing scope."""
        if self.scope_stack:
            self.nesting_depth -= 1
            return self.scope_stack.pop()
        return None
    
    # Rule tracking for profiling/debugging
    def enter_rule(self, rule_name: str):
        """Enter a parse rule."""
        self.parse_stack.append(rule_name)
        if self.trace_enabled:
            indent = "  " * len(self.parse_stack)
            print(f"{indent}→ {rule_name} @ {self.peek()}")
        if self.profiler:
            self.profiler.enter_rule(rule_name)
    
    def exit_rule(self, rule_name: str):
        """Exit a parse rule."""
        if self.parse_stack and self.parse_stack[-1] == rule_name:
            self.parse_stack.pop()
        if self.trace_enabled:
            indent = "  " * len(self.parse_stack)
            print(f"{indent}← {rule_name}")
        if self.profiler:
            self.profiler.exit_rule(rule_name)
```

2. **Migrate Parser State** (`parser/base.py`)
```python
class BaseParser:
    """Base parser with ParserContext."""
    
    def __init__(self, ctx: ParserContext):
        self.ctx = ctx
    
    # Delegate token operations to context
    def peek(self) -> Token:
        return self.ctx.peek()
    
    def advance(self) -> Token:
        return self.ctx.advance()
    
    def at_end(self) -> bool:
        return self.ctx.at_end()
    
    # Use context for state management
    def expect(self, token_type: TokenType) -> Token:
        token = self.peek()
        if token.type != token_type:
            error = self._create_error(f"Expected {token_type}, got {token.type}")
            if self.ctx.config.collect_errors:
                self.ctx.errors.append(error)
                # Try recovery
                self._recover_from_error()
            else:
                raise error
        return self.advance()
```

3. **Update Sub-parsers** (`parser/*.py`)
```python
# Before:
class StatementParser:
    def __init__(self, parent_parser):
        self.parser = parent_parser
        self.tokens = parent_parser.tokens
        # Copy various state...

# After:
class StatementParser:
    def __init__(self, ctx: ParserContext):
        self.ctx = ctx
    
    def parse_statement(self):
        self.ctx.enter_rule("statement")
        try:
            # Parsing logic using self.ctx
            result = self._parse_statement_impl()
            return result
        finally:
            self.ctx.exit_rule("statement")
```

### 5.2 Integration and Migration (Week 2)

#### Implementation Steps:

1. **Create Context Factory** (`parser/context_factory.py`)
```python
class ParserContextFactory:
    """Factory for creating parser contexts."""
    
    @staticmethod
    def create(tokens: List[Token], 
               config: Optional[ParserConfig] = None,
               **kwargs) -> ParserContext:
        """Create parser context with configuration."""
        config = config or ParserConfig()
        
        ctx = ParserContext(
            tokens=tokens,
            config=config,
            trace_enabled=config.trace_parsing,
            **kwargs
        )
        
        if config.profile_parsing:
            ctx.profiler = ParserProfiler(config)
        
        return ctx
    
    @staticmethod
    def create_for_repl(initial_tokens: List[Token] = None) -> ParserContext:
        """Create context optimized for REPL use."""
        config = ParserConfig(
            collect_errors=True,
            error_recovery=True,
            interactive_mode=True
        )
        tokens = initial_tokens or []
        return ParserContextFactory.create(tokens, config)
```

2. **Update Main Parser** (`parser/main.py`)
```python
class Parser(BaseParser):
    """Main parser using centralized context."""
    
    def __init__(self, tokens: List[Token], 
                 config: Optional[ParserConfig] = None,
                 context: Optional[ParserContext] = None):
        # Allow passing existing context or create new one
        if context:
            self.ctx = context
        else:
            self.ctx = ParserContextFactory.create(tokens, config)
        
        super().__init__(self.ctx)
        
        # Initialize sub-parsers with shared context
        self.statements = StatementParser(self.ctx)
        self.commands = CommandParser(self.ctx)
        self.control = ControlStructureParser(self.ctx)
        # ... etc
    
    def parse(self) -> AST:
        """Parse with context management."""
        self.ctx.enter_rule("program")
        try:
            ast = self._parse_program()
            
            # Check for errors if collecting
            if self.ctx.config.collect_errors and self.ctx.errors:
                return MultiErrorParseResult(ast, self.ctx.errors)
            
            return ast
        finally:
            self.ctx.exit_rule("program")
            
            # Generate profiling report if enabled
            if self.ctx.profiler:
                self.ctx.profiler.report()
```

3. **Add Context Persistence** (`parser/context_persistence.py`)
```python
class ContextSnapshot:
    """Snapshot of parser context for backtracking."""
    
    def __init__(self, ctx: ParserContext):
        self.current = ctx.current
        self.scope_stack = ctx.scope_stack.copy()
        self.nesting_depth = ctx.nesting_depth
        self.errors_count = len(ctx.errors)
    
    def restore(self, ctx: ParserContext):
        """Restore context to snapshot state."""
        ctx.current = self.current
        ctx.scope_stack = self.scope_stack.copy()
        ctx.nesting_depth = self.nesting_depth
        # Truncate errors to snapshot point
        ctx.errors = ctx.errors[:self.errors_count]

class BacktrackingParser(BaseParser):
    """Parser with backtracking support via context snapshots."""
    
    def try_parse(self, parse_func):
        """Try parsing with automatic backtracking."""
        snapshot = ContextSnapshot(self.ctx)
        try:
            return parse_func()
        except ParseError:
            snapshot.restore(self.ctx)
            return None
```

#### Testing Strategy:

1. **Unit Tests for ParserContext**
```python
def test_parser_context_initialization():
    """Test context creation and initialization."""
    tokens = tokenize("echo hello")
    ctx = ParserContext(tokens)
    
    assert ctx.current == 0
    assert not ctx.at_end()
    assert ctx.peek().type == TokenType.WORD
    assert ctx.nesting_depth == 0

def test_parser_context_scope_management():
    """Test scope tracking."""
    ctx = ParserContext([])
    
    ctx.enter_scope("function")
    assert ctx.scope_stack == ["function"]
    assert ctx.nesting_depth == 1
    
    ctx.enter_scope("loop")
    assert ctx.scope_stack == ["function", "loop"]
    assert ctx.nesting_depth == 2
    
    assert ctx.exit_scope() == "loop"
    assert ctx.nesting_depth == 1
```

2. **Integration Tests**
```python
def test_parser_with_context():
    """Test parser using centralized context."""
    tokens = tokenize("if true; then echo hi; fi")
    config = ParserConfig(trace_parsing=True)
    
    parser = Parser(tokens, config)
    ast = parser.parse()
    
    # Context should track parsing
    assert parser.ctx.current == len(tokens) - 1  # At EOF
    assert len(parser.ctx.parse_stack) == 0  # All rules exited

def test_context_error_collection():
    """Test error collection via context."""
    tokens = tokenize("if true then echo hi fi")  # Missing semicolons
    config = ParserConfig(collect_errors=True)
    
    parser = Parser(tokens, config)
    result = parser.parse()
    
    assert len(parser.ctx.errors) > 0
    assert any("semicolon" in str(e) for e in parser.ctx.errors)
```

### Benefits of Centralized ParserContext:

1. **Cleaner Interfaces**: Sub-parsers only need the context, not multiple parameters
2. **Easier Testing**: Mock or configure context for specific test scenarios
3. **Better State Management**: All parser state in one place, no scattered variables
4. **Performance Tracking**: Built-in support for profiling and tracing
5. **Extensibility**: Easy to add new parser-wide features via context
6. **Consistency**: All sub-parsers use the same state access patterns

### Migration Path:

1. **Week 1**: Implement ParserContext and factory
2. **Week 2**: 
   - Migrate BaseParser to use context
   - Update 1-2 sub-parsers as proof of concept
   - Add comprehensive tests
3. **Follow-up**: Gradually migrate remaining sub-parsers

This implementation plan provides a structured approach to enhancing the PSH parser with immediate, tangible benefits while maintaining the system's educational value and stability.