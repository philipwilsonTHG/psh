# Visitor Pattern Phase 2: Enhanced Validation

## Overview

Phase 2 of the visitor pattern integration adds comprehensive script validation capabilities to PSH through the `EnhancedValidatorVisitor`. This provides static analysis to catch common shell scripting errors before runtime.

## Features

### 1. Undefined Variable Detection

Tracks variable definitions and usage across scopes:
- Detects use of undefined variables
- Understands variable scoping (global vs function-local)
- Recognizes special variables ($?, $$, $HOME, etc.)
- Handles parameter expansions with defaults (${VAR:-default})
- Tracks variables defined by `read`, `for` loops, etc.

```bash
# Detected issues:
echo "$UNDEFINED"  # Warning: undefined variable
func() {
    local x=1
}
echo "$x"  # Warning: x is local to func
```

### 2. Command Validation

Checks command usage:
- Detects common typos (grpe → grep, pyton → python)
- Suggests modern alternatives (which → command -v)
- Validates builtin command usage

```bash
# Detected issues:
grpe "pattern" file  # Warning: typo - did you mean 'grep'?
which python        # Info: consider 'command -v' instead
```

### 3. Quoting Analysis

Identifies potential word splitting and globbing issues:
- Warns about unquoted variables that may split
- Detects unintentional pathname expansion
- Special handling for test command arguments

```bash
# Detected issues:
FILES=$HOME/*.txt
ls $FILES          # Warning: unquoted, may cause word splitting
[ -f $FILE ]       # Warning: quote variables in tests
```

### 4. Security Checks

Identifies potential security vulnerabilities:
- Dangerous commands (eval, source with untrusted input)
- Command injection risks
- Insecure file permissions

```bash
# Detected issues:
eval "$USER_INPUT"     # Warning: arbitrary code execution risk
chmod 777 file        # Warning: world-writable security risk
echo "$INPUT;rm -rf /" # Error: potential command injection
```

### 5. Code Quality Checks

Additional quality improvements:
- Duplicate case patterns
- Empty commands
- Function naming issues
- Array handling

## Usage

### Command Line

```bash
# Validate a script without executing
psh --validate script.sh

# Validate command from -c flag
psh --validate -c 'echo $UNDEFINED'

# Validate from stdin
echo 'chmod 777 file' | psh --validate
```

### Programmatic Usage

```python
from psh.visitor import EnhancedValidatorVisitor, ValidatorConfig
from psh.parser import parse
from psh.state_machine_lexer import tokenize

# Parse script
tokens = tokenize(script_content)
ast = parse(tokens)

# Configure validation
config = ValidatorConfig(
    check_undefined_vars=True,
    check_security=True,
    check_quoting=True,
    check_typos=True
)

# Run validation
validator = EnhancedValidatorVisitor(config)
validator.visit(ast)

# Get results
print(validator.get_summary())
```

## Configuration

The `ValidatorConfig` class allows customization:

```python
config = ValidatorConfig(
    # Feature toggles
    check_undefined_vars=True,
    check_command_exists=True,
    check_quoting=True,
    check_security=True,
    
    # Specific options
    warn_undefined_in_conditionals=True,
    ignore_undefined_with_defaults=True,
    check_typos=True,
    warn_dangerous_commands=True
)
```

## Output Format

Validation results are categorized by severity:

```
Found 5 issue(s):
  - 2 error(s)
  - 2 warning(s)
  - 1 info message(s)

ERRORS:
  [SimpleCommand]: Potential command injection in argument: $user_input;rm -rf /
  [IfConditional] in if statement: Empty condition

WARNINGS:
  [SimpleCommand]: Possible use of undefined variable '$OUTPUT_DIR'
  [SimpleCommand]: Security: Avoid 'eval' - it can execute arbitrary code

INFOS:
  [SimpleCommand]: Consider using 'command -v' instead of 'which'
```

## Implementation Details

### Variable Tracking

The `VariableTracker` class maintains a stack of variable scopes:
- Global scope (always at bottom)
- Function scopes (pushed/popped on entry/exit)
- Tracks variable attributes (exported, readonly, array, etc.)

### Special Variables

Automatically recognized as defined:
- Positional parameters: $0, $1, $2, etc.
- Special parameters: $?, $$, $!, $#, $@, $*, etc.
- Common environment: HOME, PATH, USER, SHELL, etc.

### Context Awareness

The validator maintains context for better error messages:
- Current function name
- Loop nesting level
- Control structure context

## Examples

### Example 1: Undefined Variables

```bash
#!/bin/bash
echo "Hello, $NAME"  # Warning: undefined variable

# Fix:
NAME="${1:-World}"
echo "Hello, $NAME"  # OK - defined before use
```

### Example 2: Quoting Issues

```bash
# Problem:
FILE_LIST=$HOME/docs/*.txt
rm $FILE_LIST  # Warning: unquoted glob expansion

# Fix:
FILE_LIST="$HOME/docs/*.txt"
rm "$FILE_LIST"  # Treats as literal string

# Or use array:
files=("$HOME/docs/"*.txt)
rm "${files[@]}"  # Proper array expansion
```

### Example 3: Security Issues

```bash
# Problem:
user_cmd="$1"
eval "$user_cmd"  # Warning: code injection risk

# Fix:
case "$1" in
    start|stop|status)
        "$1"_service  # Call specific function
        ;;
    *)
        echo "Invalid command" >&2
        exit 1
        ;;
esac
```

## Benefits

1. **Early Error Detection**: Catch bugs before runtime
2. **Security**: Identify vulnerabilities during development
3. **Code Quality**: Enforce best practices
4. **Education**: Learn proper shell scripting techniques
5. **CI/CD Integration**: Validate scripts in pipelines

## Future Enhancements

- Performance optimization suggestions
- Complexity metrics
- Dead code detection
- Cross-file analysis
- Auto-fix suggestions

## Conclusion

The enhanced validator demonstrates the power of the visitor pattern, providing sophisticated static analysis while maintaining clean separation from the AST structure. It helps developers write more robust, secure shell scripts.