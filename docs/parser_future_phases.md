# PSH Parser Future Phases: Detailed Design

This document provides detailed design and implementation guidance for the future phases of the PSH parser improvement plan: the AST Visitor Pattern (Phase 6) and Enhanced Error Recovery (Phase 7).

## Phase 6: AST Visitor Pattern

### Motivation

Currently, the PSH executor directly handles AST nodes through a series of `isinstance` checks and method calls. This approach has several limitations:

1. **Tight Coupling**: The executor is tightly coupled to the AST structure
2. **Difficult to Extend**: Adding new operations requires modifying executor code
3. **Testing Challenges**: Hard to test AST operations in isolation
4. **Code Duplication**: Similar traversal logic repeated in multiple places

The Visitor pattern would provide a clean separation between the AST structure and operations performed on it.

### Design Overview

```python
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar('T')

class ASTVisitor(ABC, Generic[T]):
    """Base class for AST visitors."""
    
    def visit(self, node: ASTNode) -> T:
        """Dispatch to appropriate visit method."""
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode) -> T:
        """Default visitor for unhandled nodes."""
        raise NotImplementedError(f"No visitor for {type(node).__name__}")
    
    # Abstract methods for each AST node type
    @abstractmethod
    def visit_SimpleCommand(self, node: SimpleCommand) -> T: ...
    
    @abstractmethod
    def visit_Pipeline(self, node: Pipeline) -> T: ...
    
    @abstractmethod
    def visit_CommandList(self, node: CommandList) -> T: ...
    
    # ... etc for all AST node types
```

### Concrete Visitor Implementations

#### 1. Executor Visitor

```python
class ExecutorVisitor(ASTVisitor[int]):
    """Visitor that executes AST nodes."""
    
    def __init__(self, shell_state: ShellState):
        self.shell_state = shell_state
        self.job_manager = JobManager()
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        """Execute a simple command."""
        # Expand arguments
        expanded_args = self._expand_arguments(node.args, node.arg_types)
        
        # Handle builtins
        if expanded_args and expanded_args[0] in BUILTINS:
            return self._execute_builtin(expanded_args, node.redirects)
        
        # Handle external commands
        return self._execute_external(expanded_args, node.redirects)
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        """Execute a pipeline."""
        if len(node.commands) == 1:
            return self.visit(node.commands[0])
        
        # Set up pipes and execute pipeline
        return self._execute_pipeline(node.commands)
    
    def visit_IfConditional(self, node: IfConditional) -> int:
        """Execute if/then/else conditional."""
        # Evaluate condition
        condition_status = self.visit(node.condition)
        
        if condition_status == 0:
            return self.visit(node.then_part)
        elif node.else_part:
            return self.visit(node.else_part)
        
        return 0
```

#### 2. AST Formatter Visitor

```python
class ASTFormatterVisitor(ASTVisitor[str]):
    """Visitor that pretty-prints AST nodes."""
    
    def __init__(self, indent: int = 2):
        self.indent = indent
        self.level = 0
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> str:
        """Format a simple command."""
        parts = []
        
        # Format array assignments
        for assignment in node.array_assignments:
            parts.append(self.visit(assignment))
        
        # Format command and arguments
        for arg, arg_type in zip(node.args, node.arg_types):
            if arg_type == 'STRING':
                parts.append(f'"{arg}"')
            elif arg_type == 'VARIABLE':
                parts.append(f'${arg}')
            else:
                parts.append(arg)
        
        # Format redirects
        for redirect in node.redirects:
            parts.append(self.visit(redirect))
        
        # Add background if needed
        if node.background:
            parts.append('&')
        
        return ' '.join(parts)
    
    def visit_Pipeline(self, node: Pipeline) -> str:
        """Format a pipeline."""
        return ' | '.join(self.visit(cmd) for cmd in node.commands)
```

#### 3. Validation Visitor

```python
class ValidationVisitor(ASTVisitor[List[str]]):
    """Visitor that validates AST correctness."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.in_function = False
        self.in_loop = 0
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> List[str]:
        """Validate a simple command."""
        if not node.args:
            self.errors.append("Empty command")
        
        # Check for common mistakes
        if node.args and node.args[0] == 'cd' and len(node.args) > 2:
            self.warnings.append("cd: too many arguments")
        
        return self.errors
    
    def visit_BreakStatement(self, node: BreakStatement) -> List[str]:
        """Validate break statement."""
        if self.in_loop == 0:
            self.errors.append("break: only meaningful in a loop")
        elif node.count and node.count > self.in_loop:
            self.errors.append(f"break: loop count {node.count} exceeds nesting level {self.in_loop}")
        
        return self.errors
    
    def visit_ForLoop(self, node: ForLoop) -> List[str]:
        """Validate for loop."""
        self.in_loop += 1
        
        # Validate loop body
        self.visit(node.body)
        
        self.in_loop -= 1
        return self.errors
```

### Integration Strategy

1. **Gradual Migration**: Start with non-critical operations (formatting, validation)
2. **Maintain Compatibility**: Keep existing executor while developing visitor-based one
3. **Testing**: Each visitor can be tested independently
4. **Performance**: Monitor performance impact, optimize hot paths

### Benefits

1. **Separation of Concerns**: AST structure separate from operations
2. **Easy to Add Operations**: New visitors without modifying AST or existing code
3. **Type Safety**: Generic types ensure visitor returns consistent types
4. **Testability**: Each visitor can be unit tested independently
5. **Code Reuse**: Common traversal logic in base class

## Phase 7: Enhanced Error Recovery

### Motivation

Current parser error handling is basic - it throws an exception and stops. This makes the parser unsuitable for:

1. **IDE Integration**: IDEs need partial ASTs even with syntax errors
2. **Better Error Messages**: Multiple errors could be reported at once
3. **Syntax Highlighting**: Partial parsing needed for highlighting
4. **Interactive Use**: Better recovery improves user experience

### Design Overview

#### Error Node AST Type

```python
@dataclass
class ErrorNode(ASTNode):
    """AST node representing a parse error."""
    tokens: List[Token]          # Tokens that couldn't be parsed
    expected: List[TokenType]    # What was expected
    message: str                 # Error message
    partial_node: Optional[ASTNode] = None  # Partially parsed node if any
    
    def __repr__(self):
        return f"ErrorNode({self.message})"
```

#### Parser Error Recovery

```python
class Parser(BaseParser):
    def __init__(self, tokens: List[Token], recover_errors: bool = False):
        super().__init__(tokens)
        self.recover_errors = recover_errors
        self.errors: List[ErrorNode] = []
    
    def parse_with_recovery(self) -> Tuple[TopLevel, List[ErrorNode]]:
        """Parse with error recovery enabled."""
        self.recover_errors = True
        self.errors = []
        
        try:
            ast = self.parse()
            return ast, self.errors
        except ParseError:
            # Even top-level parse errors should be recoverable
            return self._recover_top_level(), self.errors
    
    def _recover_top_level(self) -> TopLevel:
        """Recover from top-level parse error."""
        top_level = TopLevel()
        
        while not self.at_end():
            try:
                item = self._parse_top_level_item()
                if item:
                    top_level.items.append(item)
            except ParseError as e:
                # Create error node and continue
                error_node = self._create_error_node(e)
                top_level.items.append(error_node)
                self.errors.append(error_node)
                
                # Synchronize to next statement
                self._synchronize_statement()
        
        return top_level
```

#### Error Recovery Strategies

1. **Panic Mode Recovery**
```python
def _synchronize_statement(self):
    """Skip tokens until we find a statement boundary."""
    # Common synchronization points
    SYNC_TOKENS = {
        TokenType.SEMICOLON,
        TokenType.NEWLINE,
        TokenType.FI,
        TokenType.DONE,
        TokenType.ESAC,
        TokenType.EOF
    }
    
    while not self.at_end() and not self.match_any(SYNC_TOKENS):
        self.advance()
    
    # Consume the sync token
    if not self.at_end():
        self.advance()
```

2. **Error Productions**
```python
def parse_if_statement(self) -> Union[IfConditional, ErrorNode]:
    """Parse if statement with error recovery."""
    start_pos = self.current
    
    try:
        return self._parse_if_neutral()
    except ParseError as e:
        if not self.recover_errors:
            raise
        
        # Try to recover
        partial = self._recover_if_statement(start_pos)
        return partial if partial else self._create_error_node(e)

def _recover_if_statement(self, start_pos: int) -> Optional[IfConditional]:
    """Try to recover a partial if statement."""
    # Reset to start
    self.current = start_pos
    self.advance()  # Skip 'if'
    
    # Try to find 'then'
    then_found = self._skip_until(TokenType.THEN)
    if not then_found:
        return None
    
    # Parse then part with recovery
    then_part = self._parse_command_list_with_recovery(
        end_tokens={TokenType.ELSE, TokenType.ELIF, TokenType.FI}
    )
    
    # ... continue recovery for else/elif/fi
```

3. **Partial AST Construction**
```python
def _parse_command_list_with_recovery(self, 
                                     end_tokens: Set[TokenType]) -> CommandList:
    """Parse command list with error recovery."""
    command_list = CommandList()
    
    while not self.at_end() and not self.match_any(end_tokens):
        try:
            # Try to parse a statement
            stmt = self._parse_statement()
            if stmt:
                command_list.and_or_lists.append(stmt)
        except ParseError as e:
            if not self.recover_errors:
                raise
            
            # Create error node for this statement
            error = self._create_error_node(e)
            command_list.and_or_lists.append(error)
            self.errors.append(error)
            
            # Synchronize to next statement
            self._synchronize_statement()
    
    return command_list
```

#### Error Context Enhancement

```python
@dataclass
class EnhancedErrorContext(ErrorContext):
    """Enhanced error context with recovery information."""
    
    # Additional fields for better errors
    suggestions: List[str] = field(default_factory=list)
    error_code: str = ""
    severity: str = "error"  # error, warning, info
    
    # Location information
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    
    # Context lines
    lines_before: List[str] = field(default_factory=list)
    lines_after: List[str] = field(default_factory=list)
    
    def format_error_with_context(self) -> str:
        """Format error with full context."""
        parts = []
        
        # Error header
        parts.append(f"{self.severity}: {self.message}")
        if self.error_code:
            parts.append(f" [{self.error_code}]")
        parts.append("\n")
        
        # Location
        parts.append(f"  --> {self.start_line}:{self.start_column}\n")
        
        # Context with line numbers
        for i, line in enumerate(self.lines_before):
            line_no = self.start_line - len(self.lines_before) + i
            parts.append(f"{line_no:4} | {line}\n")
        
        # Error line with markers
        parts.append(f"{self.start_line:4} | {self.source_line}\n")
        parts.append("     | ")
        parts.append(" " * self.start_column)
        parts.append("^" * (self.end_column - self.start_column))
        parts.append("\n")
        
        # After context
        for i, line in enumerate(self.lines_after):
            line_no = self.start_line + i + 1
            parts.append(f"{line_no:4} | {line}\n")
        
        # Suggestions
        if self.suggestions:
            parts.append("\n")
            parts.append("help: ")
            parts.append("\n      ".join(self.suggestions))
            parts.append("\n")
        
        return "".join(parts)
```

### Error Recovery Examples

1. **Missing 'then' in if statement**
```bash
if [ -f /etc/passwd ]
    echo "Found"
fi

# Error recovery would:
# 1. Report missing 'then'
# 2. Insert implicit 'then' 
# 3. Continue parsing echo and fi
# 4. Produce valid AST with ErrorNode
```

2. **Unclosed quote**
```bash
echo "hello
echo "world"

# Error recovery would:
# 1. Report unclosed quote
# 2. Assume quote closes at newline
# 3. Continue parsing next command
# 4. Both echos in final AST
```

3. **Multiple errors**
```bash
if [ $x -eq 5
    echo "x is 5
elif [ $x -eq 6 ]
    echo "x is 6"
fi

# Error recovery would report:
# 1. Missing closing ]
# 2. Missing 'then' after if
# 3. Unclosed quote in first echo
# 4. Missing 'then' after elif
# But still produce a usable AST
```

### Integration with Visitor Pattern

```python
class ErrorReportingVisitor(ASTVisitor[None]):
    """Visitor that reports all errors in an AST."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.errors: List[EnhancedErrorContext] = []
    
    def visit_ErrorNode(self, node: ErrorNode) -> None:
        """Process error node."""
        # Create enhanced context
        context = self._enhance_error_context(node)
        self.errors.append(context)
    
    def report_all_errors(self) -> str:
        """Generate formatted error report."""
        if not self.errors:
            return ""
        
        parts = []
        parts.append(f"Found {len(self.errors)} error(s):\n\n")
        
        for error in self.errors:
            parts.append(error.format_error_with_context())
            parts.append("\n")
        
        return "".join(parts)
```

### Benefits

1. **Multiple Error Reporting**: Users see all errors at once
2. **Better IDE Support**: Partial ASTs enable better tooling
3. **Improved UX**: Parser continues despite errors
4. **Educational Value**: Shows how real parsers handle errors
5. **Debugging Aid**: Error nodes in AST help debugging

### Implementation Strategy

1. **Start Simple**: Basic panic mode recovery first
2. **Add Error Productions**: For common syntax errors
3. **Enhance Messages**: Better error context and suggestions
4. **Test Thoroughly**: Error recovery can introduce subtle bugs
5. **Performance**: Ensure recovery doesn't slow down valid parsing

## Summary

These future phases would significantly enhance the PSH parser:

- **Phase 6 (Visitor Pattern)**: Provides clean separation between AST and operations, making the codebase more maintainable and extensible
- **Phase 7 (Error Recovery)**: Makes the parser more robust and user-friendly, enabling better tooling support

Both phases follow established compiler design patterns and would make PSH's parser comparable to production-quality parsers while maintaining its educational value.