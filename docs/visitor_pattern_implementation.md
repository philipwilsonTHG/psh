# PSH Visitor Pattern Implementation

This document describes the implementation of the Visitor Pattern (Phase 6) for the PSH parser, providing a clean separation between AST structure and operations performed on the AST.

## Overview

The visitor pattern implementation provides:

1. **Separation of Concerns**: AST structure is separate from operations
2. **Extensibility**: New operations can be added without modifying AST nodes
3. **Type Safety**: Generic types ensure consistent return types
4. **Testability**: Each visitor can be tested independently
5. **Reusability**: Common traversal logic is in the base class

## Architecture

### Base Classes

#### `ASTVisitor[T]`
The generic base class for all visitors:
- Uses double dispatch via the `visit()` method
- Automatically routes to `visit_NodeType()` methods
- Provides `generic_visit()` for unhandled nodes
- Type parameter `T` specifies the return type

#### `ASTTransformer`
A specialized visitor that returns modified AST nodes:
- Extends `ASTVisitor[ASTNode]`
- Used for AST transformations and optimizations
- Provides `transform_children()` helper method

### Concrete Visitors

#### `FormatterVisitor`
Formats AST nodes as readable shell script:
```python
formatter = FormatterVisitor(indent=2)
formatted_code = formatter.visit(ast)
print(formatted_code)
```

#### `ValidatorVisitor`
Performs semantic validation and collects issues:
```python
validator = ValidatorVisitor()
validator.visit(ast)
print(validator.get_summary())
```

#### `ExecutorVisitor` (Demonstration)
Shows how execution could be refactored using visitors:
```python
executor = ExecutorVisitor(shell_state)
exit_code = executor.visit(ast)
```

## Usage Examples

### Basic Usage

```python
from psh.visitor import FormatterVisitor, ValidatorVisitor
from psh.parser import Parser
from psh.state_machine_lexer import Lexer

# Parse some shell code
lexer = Lexer('echo "Hello, World!" | grep Hello')
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()

# Format the AST
formatter = FormatterVisitor()
print(formatter.visit(ast))

# Validate the AST
validator = ValidatorVisitor()
validator.visit(ast)
if validator.issues:
    print(validator.get_summary())
```

### Creating Custom Visitors

```python
from psh.visitor.base import ASTVisitor
from psh.ast_nodes import SimpleCommand, FunctionDef

class FunctionFinderVisitor(ASTVisitor[None]):
    """Find all function definitions in the AST."""
    
    def __init__(self):
        self.functions = []
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self.functions.append(node.name)
        # Visit the function body to find nested functions
        self.visit(node.body)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        # Don't need to do anything for commands
        pass
    
    def generic_visit(self, node) -> None:
        # For other nodes, visit their children
        # Implementation would traverse child nodes
        pass

# Use the custom visitor
finder = FunctionFinderVisitor()
finder.visit(ast)
print(f"Found functions: {finder.functions}")
```

### Combining Multiple Visitors

```python
from psh.visitor.base import CompositeVisitor

# Run multiple analysis passes
visitors = [
    FormatterVisitor(),
    ValidatorVisitor(),
    FunctionFinderVisitor()
]

composite = CompositeVisitor(visitors)
composite.visit(ast)
```

## Implementation Details

### Double Dispatch

The visitor pattern uses double dispatch to determine which method to call:

1. First dispatch: `visitor.visit(node)` - polymorphic on visitor type
2. Second dispatch: `visit_NodeType(node)` - based on node's runtime type

```python
def visit(self, node: ASTNode) -> T:
    method_name = f'visit_{node.__class__.__name__}'
    visitor = getattr(self, method_name, self.generic_visit)
    return visitor(node)
```

### Type Safety

The implementation uses Python's generic types for type safety:

```python
T = TypeVar('T')

class ASTVisitor(ABC, Generic[T]):
    def visit(self, node: ASTNode) -> T:
        # Return type is consistent across all visit methods
```

### Error Handling

Visitors can handle unknown nodes in different ways:

1. **Raise Error** (default): `generic_visit()` raises `NotImplementedError`
2. **Ignore**: Override `generic_visit()` to do nothing
3. **Traverse Children**: Override to visit child nodes
4. **Log Warning**: Override to log and continue

## Benefits

### 1. Separation of Concerns
- AST nodes only contain structure, no behavior
- Operations are in separate visitor classes
- Easy to understand and maintain

### 2. Open/Closed Principle
- Open for extension: Add new visitors
- Closed for modification: Don't change AST nodes

### 3. Single Responsibility
- Each visitor has one clear purpose
- FormatterVisitor only formats
- ValidatorVisitor only validates

### 4. Testability
- Test visitors independently
- Mock AST structures for unit tests
- No complex setup required

### 5. Reusability
- Share visitors between different tools
- Compose visitors for complex operations
- Reuse traversal logic

## Integration Strategy

The visitor pattern can be gradually integrated:

1. **Phase 1**: Use for non-critical operations (formatting, validation)
2. **Phase 2**: Add more analysis visitors (optimization, type checking)
3. **Phase 3**: Refactor executor to use visitor pattern
4. **Phase 4**: Full migration of all AST operations

## Performance Considerations

- Virtual method calls have slight overhead
- Caching can improve repeated traversals
- Hot paths can be optimized with specialized visitors
- Consider memory usage for large ASTs

## Future Enhancements

1. **Async Visitors**: For parallel AST processing
2. **Streaming Visitors**: For large AST processing
3. **Incremental Visitors**: For IDE integration
4. **Visitor Combinators**: For composing complex operations
5. **Memoizing Visitors**: For caching results

## Testing

Run the visitor pattern tests:

```bash
python -m pytest tests/test_visitor_pattern.py -v
```

Run the demonstration:

```bash
python examples/visitor_demo.py
```

## Conclusion

The visitor pattern implementation provides a clean, extensible architecture for AST operations in PSH. It demonstrates best practices in compiler design while maintaining the educational clarity of the codebase.