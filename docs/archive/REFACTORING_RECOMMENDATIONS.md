# Refactoring Recommendations for psh

Based on a careful analysis of the codebase, here are the recommended refactoring opportunities for the lexer, parser, and execution subsystems.

## Lexer Subsystem (`psh/lexer/`)

The lexer is a state machine, which is a solid foundation. However, it can be improved for clarity, maintainability, and performance.

### Recommendations:

1.  **Decompose `StateMachineLexer`**: The main `StateMachineLexer` class in `psh/lexer/core.py` is too large. It should be broken down into smaller, more focused components. The high-level state machine loop should be separated from the low-level character parsing logic.
2.  **Unify State Representation**: The lexer currently uses a `LexerState` enum alongside several boolean flags (`in_double_brackets`, `command_position`, etc.). This makes the state hard to track. These flags should be consolidated into the main `LexerState` enum for more explicit and predictable state management.
3.  **Decouple Helper Functions**: Methods in `helpers.py` are too dependent on the lexer's internal state. They should be refactored to be more functional by passing context as parameters, which will improve modularity and testability.
4.  **Simplify Quoted String Parsing**: The logic for handling single and double quotes is spread across multiple methods. This should be unified into a single, parameterized function to reduce redundancy and improve clarity.
5.  **(Advanced) Adopt a Scanned Approach**: For a significant performance improvement, consider moving from the current character-by-character processing loop to a regex-based scanner (e.g., `re.scanner`). This would allow the lexer to find token boundaries more efficiently.

## Parser Subsystem (`psh/parser/`)

The parser is well-structured with a modular design. The main opportunity is to reduce coupling and simplify the parsing process.

### Recommendations:

1.  **Invert Dependencies**: The specialized parsers (e.g., `CommandParser`) currently hold a reference to the main `Parser` instance, creating tight coupling. This should be inverted. The main `Parser` should drive the process, passing the token stream to stateless sub-parsers. This will make the components easier to test in isolation.
2.  **Pre-process Composite Tokens**: The logic for parsing composite arguments is complex and brittle. A mandatory token composition phase should be run before parsing to merge adjacent `WORD`, `STRING`, and `VARIABLE` tokens into a single `COMPOSITE` token. This will simplify the parser by allowing it to operate on a higher level of abstraction.
3.  **Remove `_neutral` Methods**: The pattern of `_parse_*_neutral()` methods adds unnecessary boilerplate. Parsing methods should return AST nodes directly, and the caller should be responsible for setting the execution context based on the node's position in the AST.
4.  **Adopt Precedence Climbing for Operators**: The manual logic for parsing pipelines and `and/or` lists is complex. It should be replaced with a standard precedence-climbing or Pratt parsing algorithm to handle operators like `|`, `&&`, and `||` in a more robust and extensible way.
5.  **Restructure `ParseContext`**: The `ParseContext` class has become a collection of boolean flags. It should be refactored to use a stack-based approach to manage nested parsing contexts, making the parser's state easier to track.

## Execution Subsystem (`psh/executor/` and `psh/visitor/`)

The execution subsystem is well-designed around the Visitor pattern, but the implementation can be made more modular and robust.

### Recommendations:

1.  **Simplify `ExecutorVisitor`**: The `ExecutorVisitor` currently acts as a "God Object." It should be refactored into a pure dispatcher whose only responsibility is to traverse the AST and delegate to specialized, stateless executors.
2.  **Immutable `ExecutionContext`**: The `ExecutionContext` should be made immutable, or state changes should be managed with a context manager. When entering a new context (like a loop), a *new* context object should be created. This makes state management safer and more predictable.
3.  **Decouple Executors**: Executors should not create instances of other executors (e.g., `FunctionOperationExecutor` creating an `ExecutorVisitor`). The main execution loop should manage the visitor's traversal, and the visitor should be passed into the specialized executors when needed.
4.  **Centralize Traversal Logic**: All AST traversal logic should be kept within the `ExecutorVisitor`. Specialized executors should focus on the logic for a specific node and should not be responsible for traversing its children.
5.  **Create a `BaseAnalysisVisitor`**: The various analysis visitors (`LinterVisitor`, `SecurityVisitor`, etc.) have overlapping logic for tasks like variable tracking. A `BaseAnalysisVisitor` should be created to provide this common infrastructure, reducing code duplication and making the visitors more maintainable.
