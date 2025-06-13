# Eval Builtin Implementation Plan for PSH

## Overview

The `eval` builtin concatenates its arguments into a single string, then parses and executes that string as shell commands. It's a powerful but potentially dangerous feature that enables dynamic code execution.

## How Bash's Eval Works

Based on testing and documentation:

1. **Argument Concatenation**: All arguments are joined with spaces
   - `eval echo "hello" "world"` → executes `echo hello world`
   
2. **Full Shell Processing**: The concatenated string goes through complete shell processing:
   - Tokenization
   - Alias expansion
   - Parsing
   - All expansions (variable, command substitution, arithmetic, etc.)
   - Execution
   
3. **Context Preservation**: Eval executes in the current shell context:
   - Variables set in eval persist
   - Functions defined in eval are available afterward
   - Current redirections and options apply
   
4. **Exit Status**:
   - Returns the exit status of the executed command(s)
   - Returns 0 if the argument is empty or only whitespace

## Architectural Changes for PSH

### 1. New Eval Builtin

Create `/Users/pwilson/src/psh/psh/builtins/eval_command.py`:

```python
"""Eval builtin implementation."""
from .base import Builtin, builtin


@builtin
class EvalBuiltin(Builtin):
    """Execute arguments as shell commands."""
    
    name = "eval"
    help_text = "Execute arguments as a shell command"
    
    def execute(self, args, shell):
        """Execute the eval builtin."""
        if not args:
            # Empty eval returns 0
            return 0
        
        # Concatenate all arguments with spaces
        command_string = ' '.join(args)
        
        # Execute using shell's run_command method
        # This ensures full processing: tokenization, parsing, execution
        return shell.run_command(command_string, add_to_history=False)
```

### 2. Key Design Decisions

#### a. Use Existing Infrastructure
- Leverage `shell.run_command()` which already handles the full pipeline:
  - Tokenization
  - Alias expansion
  - Parsing
  - Execution
- This ensures eval behaves exactly like regular command execution

#### b. No History Addition
- Commands executed via eval should not be added to history
- Pass `add_to_history=False` to `run_command()`

#### c. Current Shell Context
- Since eval uses the shell's existing `run_command()`, it automatically:
  - Executes in the current shell process
  - Preserves variable assignments
  - Keeps function definitions
  - Respects current options and settings

### 3. Implementation Steps

1. **Create the eval builtin** in `psh/builtins/eval_command.py`
2. **Import and register** in `psh/builtins/__init__.py`
3. **Add comprehensive tests** in `tests/test_eval.py`
4. **Update documentation** in CLAUDE.md and README.md

### 4. Test Cases

```python
def test_eval_basic(shell):
    """Test basic eval functionality."""
    assert shell.run_command('eval "echo hello"') == 0
    assert shell.run_command('eval echo world') == 0

def test_eval_variable_assignment(shell):
    """Test variable assignment in eval."""
    shell.run_command('eval "x=10"')
    assert shell.state.get_variable('x') == '10'

def test_eval_multiple_commands(shell):
    """Test multiple commands in eval."""
    assert shell.run_command('eval "echo first; echo second"') == 0

def test_eval_exit_status(shell):
    """Test eval exit status."""
    assert shell.run_command('eval "true"') == 0
    assert shell.run_command('eval "false"') == 1
    assert shell.run_command('eval ""') == 0  # Empty eval

def test_eval_command_substitution(shell):
    """Test command substitution in eval."""
    shell.run_command('eval "x=$(echo 42)"')
    assert shell.state.get_variable('x') == '42'

def test_eval_function_definition(shell):
    """Test function definition in eval."""
    shell.run_command('eval "greet() { echo Hello \$1; }"')
    assert shell.run_command('greet World') == 0

def test_eval_control_structures(shell):
    """Test control structures in eval."""
    assert shell.run_command('eval "if true; then echo yes; fi"') == 0
    assert shell.run_command('eval "for i in 1 2; do echo \$i; done"') == 0
```

### 5. Security Considerations

While eval is inherently risky (arbitrary code execution), PSH should:
- Document the security implications clearly
- Not add any additional restrictions beyond what bash does
- Let users make informed decisions about using eval

### 6. Edge Cases to Handle

1. **Empty arguments**: `eval` or `eval ""` should return 0
2. **Whitespace**: `eval "   "` should return 0
3. **Multiple arguments**: Properly join with spaces
4. **Special characters**: Let the tokenizer handle quotes, escapes, etc.
5. **Syntax errors**: Return appropriate error codes
6. **Nested eval**: `eval "eval 'echo nested'"` should work

### 7. No Architectural Changes Needed

The beauty of this approach is that **no core architectural changes are required**:
- PSH already has all the infrastructure needed
- The `run_command()` method provides the complete execution pipeline
- Eval becomes a thin wrapper that concatenates arguments and calls existing functionality

This makes eval both powerful and maintainable, while preserving PSH's educational clarity.

## Summary

Implementing eval in PSH is straightforward:
1. Create a simple builtin that concatenates arguments
2. Pass the result to `shell.run_command()`
3. Let existing infrastructure handle everything else

This approach ensures eval behaves exactly like bash's eval while maintaining code simplicity and reusability.