# Expansion Subsystem

This document provides guidance for working with the PSH expansion subsystem.

## Architecture Overview

The expansion subsystem transforms shell input through multiple stages before command execution. It implements POSIX-compliant expansion ordering with bash extensions.

```
Input Arguments → ExpansionManager → Expanded Arguments
                        ↓
    ┌──────────┬────────┼────────┬──────────┬──────────┐
    ↓          ↓        ↓        ↓          ↓          ↓
  Tilde    Variable  Command  Arithmetic  Word    Pathname
 Expander  Expander    Sub      Eval    Splitter  (Glob)
```

## Key Files

| File | Purpose |
|------|---------|
| `manager.py` | `ExpansionManager` - orchestrates all expansions in correct order |
| `base.py` | `ExpansionComponent` - abstract base class for expanders |
| `evaluator.py` | `ExpansionEvaluator` - evaluates expansion AST nodes |
| `variable.py` | `VariableExpander` - handles `$VAR`, `${VAR}`, arrays (~50KB) |
| `command_sub.py` | `CommandSubstitution` - handles `$(cmd)` and `` `cmd` `` |
| `tilde.py` | `TildeExpander` - handles `~` and `~user` |
| `glob.py` | `GlobExpander` - pathname expansion (wildcards) |
| `word_splitter.py` | `WordSplitter` - splits on IFS |
| `parameter_expansion.py` | Advanced parameter expansion (`${VAR:-default}`, etc.) |

## Core Patterns

### 1. ExpansionManager Orchestration

All expansions go through `ExpansionManager`:

```python
class ExpansionManager:
    def __init__(self, shell):
        self.variable_expander = VariableExpander(shell)
        self.command_sub = CommandSubstitution(shell)
        self.tilde_expander = TildeExpander(shell)
        self.glob_expander = GlobExpander(shell)
        self.word_splitter = WordSplitter()

    def expand_arguments(self, command: SimpleCommand) -> List[str]:
        """Expand all arguments in POSIX order."""
        ...
```

### 2. ExpansionComponent Base Class

All expanders inherit from a simple base:

```python
class ExpansionComponent(ABC):
    def __init__(self, shell_state: ShellState):
        self.state = shell_state

    @abstractmethod
    def expand(self, value: str) -> str:
        """Expand the given value."""
        pass
```

### 3. NULL Marker Pattern

To prevent unwanted glob expansion of escaped characters:

```python
# Escaped glob characters use NULL (\x00) marker
if next_char in '*?[':
    result.append(f'\x00{next_char}')  # Prevents glob matching

# Clean markers before final output
clean_word = word.replace('\x00', '')
```

## Expansion Order (POSIX)

The `expand_arguments()` method processes expansions in this order:

```
1. Brace Expansion      {a,b,c}         → Handled by tokenizer
2. Tilde Expansion      ~, ~user        → TildeExpander
3. Variable Expansion   $VAR, ${VAR}    → VariableExpander
4. Command Substitution $(cmd), `cmd`   → CommandSubstitution
5. Arithmetic Expansion $((expr))       → execute_arithmetic_expansion()
6. Word Splitting       on IFS          → WordSplitter
7. Pathname Expansion   *, ?, [...]     → GlobExpander
8. Quote Removal        remove quotes   → During processing
```

## Variable Expansion Details

The `VariableExpander` handles:

```python
# Simple variables
$VAR, ${VAR}

# Special variables
$?, $$, $!, $#, $@, $*, $0-$9

# Parameter expansion operators
${VAR:-default}   # Use default if unset/null
${VAR:=default}   # Assign default if unset/null
${VAR:+value}     # Use value if set
${VAR:?error}     # Error if unset/null
${#VAR}           # String length
${VAR%pattern}    # Remove shortest suffix
${VAR%%pattern}   # Remove longest suffix
${VAR#pattern}    # Remove shortest prefix
${VAR##pattern}   # Remove longest prefix
${VAR/pat/repl}   # Replace first match
${VAR//pat/repl}  # Replace all matches

# Array expansions
${arr[0]}, ${arr[@]}, ${arr[*]}, ${#arr[@]}
```

## Common Tasks

### Adding a New Expansion Type

1. Create expander class inheriting from `ExpansionComponent`:
```python
# In new_expander.py
from .base import ExpansionComponent

class NewExpander(ExpansionComponent):
    def expand(self, value: str) -> str:
        # Implement expansion logic
        return expanded_value
```

2. Add to `ExpansionManager.__init__()`:
```python
self.new_expander = NewExpander(shell)
```

3. Integrate into `expand_arguments()` at correct position in order

4. Add tests in `tests/unit/expansion/`

### Adding a Parameter Expansion Operator

1. Edit `parameter_expansion.py`

2. Add operator to the parsing logic

3. Implement the operation in the appropriate method

4. Add tests for the new operator

## Key Implementation Details

### Quote Handling

Different quote types affect expansion:

| Quote Type | Variable Expansion | Command Sub | Glob | Word Split |
|------------|-------------------|-------------|------|------------|
| Unquoted   | Yes               | Yes         | Yes  | Yes        |
| `"double"` | Yes               | Yes         | No   | No         |
| `'single'` | No                | No          | No   | No         |
| `$'ansi'`  | Escape sequences  | No          | No   | No         |

### Array Expansion in Quotes

Special handling for `"${arr[@]}"`:

```python
# "$@" and "${arr[@]}" in double quotes produce multiple arguments
if arg == '$@':
    args.extend(self.state.positional_params)
elif self.variable_expander.is_array_expansion(arg):
    expanded_list = self.variable_expander.expand_array_to_list(arg)
    args.extend(expanded_list)
```

### IFS Word Splitting

```python
def _split_with_ifs(self, text: str, quote_type: str) -> List[str]:
    if quote_type is not None:
        return [text]  # Quoted - no splitting

    ifs = self.state.get_variable('IFS', ' \t\n')
    return self.word_splitter.split(text, ifs)
```

### Command Substitution

```python
class CommandSubstitution:
    def execute(self, cmd_sub: str) -> str:
        # Extract command from $(...) or `...`
        # Create subprocess to execute
        # Capture and return stdout
        # Strip trailing newlines (POSIX behavior)
```

## Testing

```bash
# Run expansion unit tests
python -m pytest tests/unit/expansion/ -v

# Test specific expansion type
python -m pytest tests/unit/expansion/test_variable_expansion.py -v

# Debug expansion
python -m psh --debug-expansion -c "echo $HOME"
python -m psh --debug-expansion-detail -c 'echo "${arr[@]}"'
```

## Common Pitfalls

1. **Expansion Order Matters**: Variables must be expanded before command substitution results are word-split.

2. **Quote Preservation**: Track quote types carefully - they affect which expansions occur.

3. **Empty Expansions**: An unset variable in `"$var"` produces empty string, but unquoted `$var` produces nothing (no argument).

4. **Array vs Scalar**: `${arr[@]}` expands to multiple words, `${arr[*]}` joins with first IFS character.

5. **Nested Expansions**: Command substitution can contain variable expansions: `$(echo $HOME)`

6. **NULL Markers**: Don't forget to clean `\x00` markers before returning final values.

7. **IFS Edge Cases**: Empty IFS means no word splitting; unset IFS uses default `" \t\n"`.

## Debug Options

```bash
python -m psh --debug-expansion        # Show pre/post expansion
python -m psh --debug-expansion-detail # Trace each expansion step
```

Output example:
```
[EXPANSION] Expanding command: ['echo', '$HOME', '*.txt']
[EXPANSION]   Variable expansion: '$HOME' -> '/Users/user'
[EXPANSION]   Glob expansion: '*.txt' -> ['a.txt', 'b.txt']
[EXPANSION] Result: ['echo', '/Users/user', 'a.txt', 'b.txt']
```

## Integration Points

### With Shell State (`psh/core/state.py`)

- Variables: `shell.state.get_variable()`, `shell.state.set_variable()`
- Special variables: `shell.state.get_special_variable()`
- Positional params: `shell.state.positional_params`
- Options: `shell.state.options.get('noglob')`, etc.

### With Executor (`psh/executor/`)

- Called from `CommandExecutor` before command execution
- Process substitutions set up via `IOManager`

### With Parser (`psh/parser/`)

- Parser provides `arg_types` and `quote_types` metadata
- Word AST nodes can be expanded via `ExpansionEvaluator`

### With Arithmetic (`psh/arithmetic.py`)

- `execute_arithmetic_expansion()` calls `evaluate_arithmetic()`
- Variables in arithmetic are pre-expanded
