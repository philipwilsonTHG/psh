# Command Substitution Implementation Strategy

## Overview

This document outlines the strategy for implementing command substitution with POSIX semantics in the Python Shell (psh), supporting both modern `$(command)` and legacy `` `command` `` syntax.

## 1. Two Syntaxes to Support

- **Modern**: `$(command)` - Preferred, supports nesting easily
- **Legacy**: `` `command` `` - Backticks, limited nesting support

## 2. Tokenization Strategy

We'll use the simple approach of creating tokens with preserved content:

```python
Token(TokenType.COMMAND_SUB, "$(ls -la)")
Token(TokenType.COMMAND_SUB_BACKTICK, "`date`")
```

This is simpler than nested tokenization and sufficient for our needs.

## 3. Parsing Strategy

Command substitutions will be treated as expandable elements similar to variables:

```python
# In the AST
@dataclass
class CommandSubstitution(ASTNode):
    command: str  # The command to execute
    syntax: str   # "$(...)" or "`...`"
```

The parser should handle them in argument positions, storing them for later expansion.

## 4. Execution Strategy

Execute during the expansion phase, before the main command runs:

```python
def expand_command_substitution(self, cmd_sub: str) -> str:
    # Remove $(...) or `...` markers
    command = extract_command(cmd_sub)
    
    # Execute in a subprocess and capture output
    result = subprocess.run(
        ["python3", sys.argv[0], "-c", command],
        capture_output=True,
        text=True,
        env=self.env
    )
    
    # POSIX: strip trailing newlines only
    output = result.stdout.rstrip('\n')
    
    # POSIX: word splitting on the result
    return output
```

## 5. Key POSIX Semantics

1. **Trailing newline removal**: Only trailing newlines are stripped
2. **Word splitting**: Result undergoes word splitting unless quoted
3. **Exit status**: Available in `$?` after substitution
4. **Nested execution**: Runs in a subshell with its own environment
5. **Signal handling**: Inherits signal dispositions but not traps

## 6. Implementation Phases

### Phase 1: Basic `$()` support
- Tokenize `$(...)` preserving content
- Execute during expansion
- Handle in unquoted contexts with word splitting

### Phase 2: Backtick support
- Add `` `...` `` tokenization
- Handle escape sequences (`\$`, `\\`, `` \` ``)
- Share execution logic with `$()`

### Phase 3: Advanced features
- Nested command substitution
- Proper subshell isolation
- Integration with other expansions

## 7. Edge Cases to Handle

```bash
# Nested substitution
echo $(echo $(date))

# Mixed quotes
echo "Today is $(date)"
echo 'Today is $(date)'  # No expansion in single quotes

# Escape handling in backticks
echo `echo \$USER`       # Should output $USER
echo `echo \\`          # Should output \

# Multi-line commands
echo $(echo "line1"
       echo "line2")

# Command substitution in redirections (bash extension)
cat < $(echo /etc/passwd)
```

## 8. Implementation Details

### Tokenizer Changes

1. Add new token types: `COMMAND_SUB` and `COMMAND_SUB_BACKTICK`
2. Implement `read_command_substitution()` method
3. Handle parenthesis/backtick balancing
4. Preserve inner command for execution

### Parser Changes

1. Treat command substitutions as valid in argument positions
2. Store the full substitution for later expansion
3. Track whether substitution appears in quoted context

### Execution Changes

1. Add expansion phase before command execution
2. Execute substitutions in subprocesses
3. Apply word splitting to results (if unquoted)
4. Update `$?` with substitution exit status

## 9. Testing Strategy

### Basic Tests
- Simple command substitution: `echo $(date)`
- Command substitution with arguments: `echo $(ls -la)`
- Multiple substitutions: `echo $(date) $(whoami)`

### Quote Interaction Tests
- Double quotes: `echo "Today is $(date)"`
- Single quotes: `echo 'No expansion $(date)'`
- Mixed quotes: `echo "$(echo 'hello world')"`

### Nesting Tests
- Nested substitution: `echo $(echo $(date))`
- Deep nesting: `echo $(echo $(echo $(date)))`

### Error Handling Tests
- Syntax errors: `echo $(ls`
- Failed commands: `echo $(nonexistentcmd)`
- Empty output: `echo $(true)`

### Integration Tests
- With variables: `echo $(echo $USER)`
- With globs: `echo $(ls *.txt)`
- With redirections: `echo $(cat < file.txt)`
- In redirections: `cat < $(echo file.txt)`

### Exit Status Tests
- Success: `$(true); echo $?` should output 0
- Failure: `$(false); echo $?` should output 1
- With pipelines: `$(false | true); echo $?`

## 10. Future Enhancements

1. **Arithmetic expansion**: `$((2 + 2))`
2. **Process substitution**: `<(command)` and `>(command)`
3. **Brace expansion**: `{a,b,c}` 
4. **Tilde expansion**: `~` and `~user`

## Implementation Order

1. Start with basic `$()` tokenization and execution
2. Add proper word splitting
3. Implement backtick support with escape handling
4. Add nested substitution support
5. Handle all edge cases and quote interactions