# Component Interaction Patterns

This document describes how PSH components interact with each other during various operations.

## Common Interaction Patterns

### 1. Simple Command Execution

```
User Input: "echo hello"

Shell.run_command()
  ├─→ Tokenizer.tokenize()
  ├─→ Parser.parse()
  ├─→ AliasManager.expand_aliases()  [if interactive]
  └─→ ExecutorManager.execute()
      └─→ StatementExecutor.execute()
          └─→ CommandExecutor.execute()
              ├─→ ExpansionManager.expand_arguments()
              │   ├─→ TildeExpander.expand()
              │   ├─→ VariableExpander.expand()
              │   └─→ GlobExpander.expand()
              ├─→ BuiltinRegistry.get("echo")
              └─→ EchoBuiltin.execute()
```

### 2. Pipeline Execution

```
User Input: "ls | grep test | wc -l"

Shell.run_command()
  └─→ ... (tokenize, parse, alias expansion)
      └─→ PipelineExecutor.execute()
          ├─→ Create pipes
          ├─→ Fork for each command
          │   ├─→ Child 1: CommandExecutor.execute_in_child("ls")
          │   ├─→ Child 2: CommandExecutor.execute_in_child("grep test")
          │   └─→ Child 3: CommandExecutor.execute_in_child("wc -l")
          ├─→ JobManager.create_job()
          ├─→ Set up process groups
          ├─→ JobManager.wait_for_job()
          └─→ Restore terminal control
```

### 3. Control Structure Execution

```
User Input: "if [ -f test.txt ]; then cat test.txt; fi"

Shell.run_command()
  └─→ ... (tokenize, parse)
      └─→ ControlFlowExecutor.execute_if()
          ├─→ Execute condition: StatementExecutor.execute()
          │   └─→ CommandExecutor.execute("[", "-f", "test.txt", "]")
          │       └─→ TestBuiltin.execute()
          ├─→ Check exit status
          └─→ Execute then-branch: StatementExecutor.execute()
              └─→ CommandExecutor.execute("cat", "test.txt")
```

### 4. Variable Assignment with Command Substitution

```
User Input: "result=$(ls | wc -l)"

Shell.run_command()
  └─→ CommandExecutor.execute()
      ├─→ Detect variable assignment
      └─→ ExpansionManager.expand_string_variables("$(ls | wc -l)")
          └─→ CommandSubstitution.execute()
              ├─→ Fork subprocess
              ├─→ Create pipe for output capture
              └─→ In child: Shell.run_command("ls | wc -l")
                  └─→ ... (full execution cycle)
```

### 5. Function Definition and Call

```
User Input: "greet() { echo Hello $1; }"
           "greet World"

# Definition
Shell.run_command()
  └─→ StatementExecutor.execute_toplevel()
      └─→ FunctionManager.define_function("greet", body_ast)

# Call
Shell.run_command()
  └─→ CommandExecutor.execute()
      ├─→ FunctionManager.get_function("greet")
      └─→ CommandExecutor._execute_function()
          ├─→ Save positional parameters
          ├─→ Set new positional parameters ["World"]
          ├─→ Push function to stack
          ├─→ StatementExecutor.execute_command_list(function.body)
          └─→ Restore environment
```

### 6. Script Execution

```
User Input: "psh script.sh arg1 arg2"

Shell.run_script()
  └─→ ScriptManager.run_script()
      ├─→ ScriptValidator.validate_script_file()
      ├─→ ShebangHandler.should_execute_with_shebang()
      ├─→ Set positional parameters ["arg1", "arg2"]
      └─→ ScriptExecutor.execute_script()
          └─→ SourceProcessor.execute_from_source()
              └─→ For each line/command:
                  └─→ Shell.run_command()
```

### 7. Interactive Session with Tab Completion

```
User Input: "cd /usr/lo[TAB]"

InteractiveManager.run_interactive_loop()
  └─→ REPLLoop.run()
      └─→ LineEditor.edit_line()
          └─→ On TAB key:
              └─→ CompletionManager.complete()
                  ├─→ Parse partial command
                  ├─→ Determine completion context
                  └─→ FileCompleter.get_completions("/usr/lo")
                      └─→ Return ["/usr/local/"]
```

### 8. Job Control Operations

```
User Input: "sleep 30 &"
           "jobs"
           "fg %1"

# Background job
Shell.run_command("sleep 30 &")
  └─→ CommandExecutor.execute()
      ├─→ Fork process
      ├─→ JobManager.create_job()
      └─→ Return immediately (background)

# List jobs
Shell.run_command("jobs")
  └─→ JobsBuiltin.execute()
      └─→ JobManager.list_jobs()

# Foreground job
Shell.run_command("fg %1")
  └─→ FgBuiltin.execute()
      ├─→ JobManager.get_job("%1")
      ├─→ Give terminal control to job
      └─→ JobManager.wait_for_job()
```

### 9. I/O Redirection

```
User Input: "echo hello > output.txt 2>&1"

Shell.run_command()
  └─→ CommandExecutor.execute()
      ├─→ IOManager.setup_builtin_redirections()
      │   ├─→ FileRedirector.redirect_stdout("output.txt")
      │   └─→ FileRedirector.duplicate_fd(2, 1)
      ├─→ EchoBuiltin.execute()
      └─→ IOManager.restore_builtin_redirections()
```

### 10. Process Substitution

```
User Input: "diff <(ls dir1) <(ls dir2)"

Shell.run_command()
  └─→ CommandExecutor.execute()
      └─→ ExpansionManager.expand_arguments()
          └─→ ProcessSubstitutionHandler.setup_process_substitutions()
              ├─→ Create FIFO for <(ls dir1)
              ├─→ Fork process to run "ls dir1" with output to FIFO
              ├─→ Create FIFO for <(ls dir2)
              ├─→ Fork process to run "ls dir2" with output to FIFO
              └─→ Replace arguments with FIFO paths
```

## Component Dependencies

### Direct Dependencies

```
Shell
  ├─→ ShellState
  ├─→ ExpansionManager
  ├─→ IOManager
  ├─→ ExecutorManager
  ├─→ ScriptManager
  ├─→ InteractiveManager
  ├─→ AliasManager
  ├─→ FunctionManager
  ├─→ JobManager
  └─→ BuiltinRegistry

ExpansionManager
  ├─→ VariableExpander → ShellState
  ├─→ CommandSubstitution → Shell (for execution)
  ├─→ TildeExpander → pwd module
  └─→ GlobExpander → glob module

ExecutorManager
  ├─→ CommandExecutor
  │   ├─→ ExpansionManager
  │   ├─→ IOManager
  │   ├─→ JobManager
  │   ├─→ FunctionManager
  │   └─→ BuiltinRegistry
  ├─→ PipelineExecutor
  │   ├─→ CommandExecutor
  │   └─→ JobManager
  ├─→ ControlFlowExecutor
  │   └─→ Shell (for command execution)
  └─→ StatementExecutor
      └─→ Shell (for command execution)
```

### Circular Dependencies Resolution

Some components need to call back to Shell for execution:
- **CommandSubstitution** needs to execute commands
- **ControlFlowExecutor** needs to execute condition commands
- **Functions** need to execute their body

This is resolved by:
1. Components hold a reference to Shell
2. They call public Shell methods (run_command, execute_command_list)
3. No direct access to Shell internals

## State Flow

### Read Flow
```
Component → ShellState.property → value
```

### Write Flow
```
Component → ShellState.set_variable() → validation → storage
```

### Special State Updates
- **Exit codes**: Updated after each command
- **Job state**: Updated by signal handlers
- **Function stack**: Maintained during function calls
- **Positional parameters**: Saved/restored for functions

## Error Propagation

### Exception Flow
```
Deep Component
  └─→ Raise Exception
      └─→ Caught by Executor
          └─→ Logged/Handled
              └─→ Return error exit code
```

### Special Exceptions
- **LoopBreak/LoopContinue**: Bubble up to enclosing loop
- **FunctionReturn**: Bubble up to function caller
- **ParseError**: Caught at top level, display error
- **KeyboardInterrupt**: Caught in REPL loop

## Performance Critical Paths

### Hot Paths
1. **Variable expansion**: Called for every command argument
2. **Builtin lookup**: O(1) dictionary lookup
3. **Function lookup**: O(1) dictionary lookup
4. **Alias expansion**: Recursive but with cycle detection

### Optimization Strategies
1. **Caching**: Frequently accessed state
2. **Lazy evaluation**: Expansions only when needed
3. **Early termination**: Short-circuit evaluation
4. **Minimal copying**: Pass references where possible