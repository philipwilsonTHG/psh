# PSH Architecture and Sequence Diagrams

This document shows high-level architectural diagrams and sequence diagrams for the Python Shell (PSH) codebase.

## Architecture Overview

```mermaid
graph TD
    Shell((Shell))
    Lexer(StateMachineLexer)
    Parser(RecursiveDescentParser)
    Expander(ExpansionManager)
    Executor(ExecutorVisitor)
    Builtins(Builtins & JobControl)
    Shell -->|input command line| Lexer
    Lexer -->|tokens| Parser
    Parser -->|AST| Expander
    Expander -->|expanded AST| Executor
    Executor --> Builtins
    Executor --> Shell
```

**Description:**
- **Shell:** The main orchestrator receiving user input or scripts.
- **Lexer:** Tokenizes input preserving quotes, variables, and command substitutions.
- **Parser:** Parses tokens into Abstract Syntax Tree (AST) using recursive descent.
- **ExpansionManager:** Performs variable expansion, command substitution, globbing.
- **ExecutorVisitor:** Executes the expanded AST, managing jobs, redirection, builtins.

## Command Execution Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Shell
    participant Lexer
    participant Parser
    participant Expander
    participant Executor
    participant Builtins
    User->>Shell: Enter command line
    Shell->>Lexer: Tokenize input
    Lexer-->>Shell: Return token list
    Shell->>Parser: Parse tokens into AST
    Parser-->>Shell: Return AST
    Shell->>Expander: Expand AST (variables, commands)
    Expander-->>Shell: Return expanded AST
    Shell->>Executor: Execute expanded AST
    Executor->>Builtins: Execute built-in commands or functions
    Executor-->>Shell: Return execution status
    Shell-->>User: Display output or prompt
```

This diagram shows the synchronous flow of a command from user input through the core components of the PSH shell.

## Notes

- Each component is modular and extensible.
- Visitor pattern is used in Executor to separate AST processing logic.
- ExpansionManager handles complex shell expansions before execution.
- Asynchronous job management and signal handling occur within Executor and JobControl modules.
