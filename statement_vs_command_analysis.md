# Statement vs Command Types Analysis

## Overview

The codebase uses a dual type system for control structures, with both Statement and Command variants for each control structure (e.g., `WhileStatement` vs `WhileCommand`). This design enables control structures to be used in two distinct contexts:

1. **Statements**: Top-level constructs that can stand alone
2. **Commands**: Pipeline-compatible constructs that can be part of a pipeline

## Type Hierarchy

```
ASTNode
├── Statement (base for top-level constructs)
│   ├── AndOrList
│   ├── IfStatement
│   ├── WhileStatement
│   ├── ForStatement
│   ├── CStyleForStatement
│   ├── CaseStatement
│   ├── SelectStatement
│   ├── ArithmeticCommand
│   ├── BreakStatement
│   ├── ContinueStatement
│   ├── FunctionDef
│   └── EnhancedTestStatement
│
└── Command (base for pipeline components)
    ├── SimpleCommand (traditional commands with args)
    └── CompoundCommand (control structures in pipelines)
        ├── WhileCommand
        ├── ForCommand
        ├── CStyleForCommand
        ├── IfCommand
        ├── CaseCommand
        ├── SelectCommand
        └── ArithmeticCompoundCommand
```

## Key Differences

### 1. **Parsing Context**

**Statements** are parsed in:
- `parse_statement()` - Top-level statement parsing
- `parse_command_list()` - Statement lists
- Direct parsing methods like `parse_if_statement()`, `parse_while_statement()`

**Commands** are parsed in:
- `parse_pipeline_component()` - Pipeline component parsing
- Methods like `parse_if_command()`, `parse_while_command()`

### 2. **Usage Patterns**

**Statements** appear:
- At the top level of scripts
- As standalone control structures
- In function bodies
- After semicolons or newlines

Example:
```bash
# These are statements
if [ "$x" -eq 1 ]; then
    echo "one"
fi

while read line; do
    echo "$line"
done
```

**Commands** appear:
- As components of pipelines
- After pipe operators (|)
- Can be mixed with simple commands

Example:
```bash
# These are commands in pipelines
echo "data" | while read line; do echo "$line"; done
seq 1 5 | for i in $(cat); do echo $i; done
```

### 3. **Execution Context**

**Statements** are executed by:
- `ControlFlowExecutor` in `executor/control_flow.py`
- Methods like `execute_if()`, `execute_while()`
- Run in the current shell process

**Commands** are executed by:
- `PipelineExecutor` in `executor/pipeline.py`
- `_execute_compound_in_subshell()` for compound commands
- Run in forked subshell processes when in pipelines

### 4. **Feature Differences**

**Commands** have additional properties:
- `background: bool` - Can be backgrounded with &
- Execute in subshells when part of pipelines
- Variable changes don't affect parent shell

**Statements**:
- Execute in the current shell
- Variable changes persist
- Cannot be directly used in pipelines

## Implementation Details

### Parser Logic

The parser determines which variant to create based on context:

```python
def parse_pipeline_component(self) -> Command:
    """Parse a single component of a pipeline."""
    if self.match(TokenType.WHILE):
        return self.parse_while_command()  # Returns WhileCommand
    # ...

def parse_statement(self) -> Optional[Statement]:
    """Parse a single statement."""
    if self.match(TokenType.WHILE):
        return self.parse_while_statement()  # Returns WhileStatement
    # ...
```

### Executor Routing

The executor routes based on type:

```python
# In PipelineExecutor._execute_in_child()
if isinstance(command, SimpleCommand):
    return self.shell.executor_manager.command_executor.execute_in_child(command)
elif isinstance(command, CompoundCommand):
    return self._execute_compound_in_subshell(command)

# In ControlFlowExecutor.execute()
if isinstance(node, IfStatement):
    return self.execute_if(node)
elif isinstance(node, WhileStatement):
    return self.execute_while(node)
```

## Design Rationale

This dual-type design enables the revolutionary v0.37.0 feature:
- Control structures can now be used anywhere in pipelines
- Maintains backward compatibility (statements work as before)
- Clear separation between shell-level and pipeline-level execution
- Proper process isolation for pipeline components
- Educational clarity about execution contexts

## Examples

### Statement Usage
```bash
# Traditional statement form
for i in 1 2 3; do
    echo $i
done > output.txt

# Variable persists
x=1
while [ $x -lt 5 ]; do
    x=$((x + 1))
done
echo $x  # prints 5
```

### Command Usage
```bash
# Pipeline form - runs in subshell
echo "1 2 3" | for i in $(cat); do echo $i; done

# Variable doesn't persist (subshell)
x=1
echo "test" | while read line; do x=5; done
echo $x  # prints 1 (not 5)
```

## Summary

The Statement/Command duality is a sophisticated design pattern that enables PSH to support control structures in pipelines while maintaining proper shell semantics. Statements execute in the current shell for traditional usage, while Commands execute in subshells for pipeline compatibility. This architecture successfully addresses the limitation documented in TODO.md while preserving backward compatibility and educational clarity.