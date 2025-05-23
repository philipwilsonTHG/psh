# Python Shell (psh) - Parser Architecture

## Recommendation: Hand-Written Recursive Descent Parser

Based on your preference and educational goals, I recommend a hand-written recursive descent parser with the following architecture:

### Key Components

1. **Tokenizer** (`tokenizer.py`)
   - Converts input string into tokens
   - Handles operators, quotes, variables
   - Clean separation from parsing logic

2. **AST Nodes** (`ast_nodes.py`)
   - Simple dataclasses for AST representation
   - Command, Pipeline, CommandList, Redirect

3. **Parser** (`parser.py`)
   - Recursive descent implementation
   - One function per grammar rule
   - Clear error reporting

4. **Shell** (`simple_shell.py`)
   - Basic executor for demonstration
   - Shows how to use the parser

### Architecture Benefits

1. **Educational Value**
   - Each parsing function maps directly to a grammar rule
   - Easy to trace through with a debugger
   - Clear separation of concerns

2. **Extensibility**
   - Easy to add new operators or syntax
   - Can incrementally add features
   - No external dependencies

3. **Error Handling**
   - Can provide context-aware error messages
   - Shows exact position of syntax errors
   - Easy to add error recovery

### Grammar

```
command_list → pipeline (SEMICOLON pipeline)* [SEMICOLON]
pipeline     → command (PIPE command)*
command      → word+ redirect* [AMPERSAND]
redirect     → REDIRECT_OP word
word         → WORD | STRING | VARIABLE
```

### Next Steps

1. **Implement Pipeline Execution**
   - Use subprocess with pipes
   - Handle proper process management

2. **Add More Built-ins**
   - pwd, echo, source, etc.
   - Job control (jobs, fg, bg)

3. **Enhance Variable Handling**
   - Environment vs shell variables
   - Special variables ($?, $$, $!)
   - Command substitution

4. **Add Control Structures**
   - if/then/else
   - for/while loops
   - functions

5. **Improve Interactive Features**
   - Line editing with readline
   - History support
   - Tab completion

### Testing

Run the demo to see the parser in action:
```bash
python3 demo.py
```

Run the simple shell:
```bash
python3 simple_shell.py
```

### Implementation Order

1. ✅ Basic tokenizer and parser
2. ✅ Simple command execution
3. ⬜ Pipeline execution
4. ⬜ Job control
5. ⬜ Advanced expansions
6. ⬜ Control structures
7. ⬜ Interactive features