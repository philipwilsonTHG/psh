# PSH Parser High-Priority Improvements: Implementation Plan

This document provides a detailed implementation plan for the high-priority parser improvements identified in the architectural analysis.

## Overview

The high-priority improvements focus on immediate benefits with low implementation risk:
1. Error Recovery Improvements
2. Parse Tree Visualization
3. Parser Configuration
4. AST Validation Phase

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

## Phase 2: Parse Tree Visualization (1-2 weeks)

### 2.1 AST Pretty Printer (Week 1)

#### Implementation Steps:

1. **Create AST Formatter** (`parser/visualization/ast_formatter.py`)
```python
class ASTPrettyPrinter(ASTVisitor[str]):
    """Pretty print AST with indentation."""
    
    def __init__(self, indent_size: int = 2):
        super().__init__()
        self.indent_size = indent_size
        self.current_indent = 0
    
    def _indent(self) -> str:
        """Get current indentation."""
        return ' ' * (self.current_indent * self.indent_size)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> str:
        """Format simple command."""
        parts = [f"{self._indent()}SimpleCommand:"]
        self.current_indent += 1
        
        parts.append(f"{self._indent()}command: {node.args[0]}")
        if len(node.args) > 1:
            parts.append(f"{self._indent()}args: {node.args[1:]}")
        if node.redirects:
            parts.append(f"{self._indent()}redirects:")
            self.current_indent += 1
            for redirect in node.redirects:
                parts.append(self.visit(redirect))
            self.current_indent -= 1
        
        self.current_indent -= 1
        return '\n'.join(parts)
```

2. **Create Graphviz DOT Generator** (`parser/visualization/dot_generator.py`)
```python
class ASTDotGenerator(ASTVisitor[str]):
    """Generate Graphviz DOT format from AST."""
    
    def __init__(self):
        super().__init__()
        self.node_counter = 0
        self.nodes = []
        self.edges = []
    
    def _make_node_id(self) -> str:
        """Generate unique node ID."""
        self.node_counter += 1
        return f"node{self.node_counter}"
    
    def visit_Pipeline(self, node: Pipeline) -> str:
        """Generate DOT for pipeline."""
        node_id = self._make_node_id()
        label = "Pipeline"
        if node.negated:
            label = "! Pipeline"
        
        self.nodes.append(f'{node_id} [label="{label}"];')
        
        for i, command in enumerate(node.commands):
            child_id = self.visit(command)
            self.edges.append(f'{node_id} -> {child_id} [label="{i}"];')
        
        return node_id
    
    def to_dot(self, ast: ASTNode) -> str:
        """Convert AST to DOT format."""
        self.visit(ast)
        
        dot = ['digraph AST {']
        dot.append('  node [shape=box];')
        dot.extend(f'  {node}' for node in self.nodes)
        dot.extend(f'  {edge}' for edge in self.edges)
        dot.append('}')
        
        return '\n'.join(dot)
```

3. **Create ASCII Tree Renderer** (`parser/visualization/ascii_tree.py`)
```python
class AsciiTreeRenderer:
    """Render AST as ASCII art tree."""
    
    @staticmethod
    def render(node: ASTNode, prefix: str = "", is_last: bool = True) -> str:
        """Render node and children as ASCII tree."""
        lines = []
        
        # Current node
        connector = "└── " if is_last else "├── "
        lines.append(prefix + connector + str(node))
        
        # Prepare prefix for children
        extension = "    " if is_last else "│   "
        child_prefix = prefix + extension
        
        # Render children
        children = node.get_children()  # Implement in AST nodes
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            lines.append(AsciiTreeRenderer.render(
                child, child_prefix, is_last_child
            ))
        
        return '\n'.join(lines)
```

### 2.2 Integration with Shell (Week 2)

#### Implementation Steps:

1. **Add Visualization Commands**
```python
# Add to shell.py or create new builtin
class ParseTreeCommand:
    """Commands for parse tree visualization."""
    
    def show_ast(self, command: str, format: str = 'pretty') -> None:
        """Show AST for given command."""
        try:
            tokens = tokenize(command)
            parser = Parser(tokens)
            ast = parser.parse()
            
            if format == 'pretty':
                print(ASTPrettyPrinter().visit(ast))
            elif format == 'dot':
                print(ASTDotGenerator().to_dot(ast))
            elif format == 'ascii':
                print(AsciiTreeRenderer.render(ast))
            else:
                print(f"Unknown format: {format}")
        except ParseError as e:
            print(f"Parse error: {e}")
```

2. **Add Debug Flag for AST Display**
```python
# Enhance existing --debug-ast flag
def execute_with_ast_debug(self, ast: ASTNode) -> int:
    """Execute showing AST first."""
    if self.state.options.get('debug-ast'):
        print("=== Abstract Syntax Tree ===", file=sys.stderr)
        print(ASTPrettyPrinter().visit(ast), file=sys.stderr)
        print("=== Execution ===", file=sys.stderr)
    
    return self.executor.visit(ast)
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

### Week 1-3: Error Recovery
- Week 1: Enhanced error context and suggestions
- Week 2: Multi-error collection infrastructure
- Week 3: Recovery strategies implementation

### Week 4-5: Parse Tree Visualization
- Week 4: AST formatters (pretty, DOT, ASCII)
- Week 5: Shell integration and debugging

### Week 6: Parser Configuration
- Complete configuration system and integration

### Week 7-8: AST Validation
- Week 7: Semantic analyzer and symbol table
- Week 8: Validation rules and pipeline

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

1. **Error Recovery**
   - 90% of common syntax errors provide helpful suggestions
   - Parser can continue after 95% of non-fatal errors
   - Error messages rated "helpful" by users

2. **Visualization**
   - AST visualization available in 3 formats
   - Integration with --debug-ast flag
   - Useful for debugging complex commands

3. **Configuration**
   - Support for strict/permissive modes
   - Feature toggles working correctly
   - No performance impact when features disabled

4. **Validation**
   - Catch 95% of semantic errors before execution
   - Useful warnings for code quality
   - < 1% false positive rate

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

This implementation plan provides a structured approach to enhancing the PSH parser with immediate, tangible benefits while maintaining the system's educational value and stability.