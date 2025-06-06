# PSH v0.36.0 Release Notes

## Eval Builtin Implementation

This release adds the `eval` builtin command to PSH, enabling dynamic command execution from strings.

### New Features

#### Eval Builtin Command

The `eval` builtin allows you to execute arguments as shell commands, providing powerful dynamic programming capabilities:

```bash
# Basic usage
eval "echo hello"

# Variable assignment
eval "name='PSH Shell'"
echo $name  # outputs: PSH Shell

# Multiple commands
eval "echo first; echo second"

# Dynamic command building
cmd="echo"
msg="Dynamic message"
eval "$cmd '$msg'"

# Function definition
eval "greet() { echo 'Hello, \$1!'; }"
greet World

# Control structures
eval "for i in 1 2 3; do echo 'Number: \$i'; done"

# Pipelines
eval "echo hello | grep hello"

# Command substitution
eval "result=\$(date); echo 'Time: \$result'"

# Nested eval
eval "eval \"echo 'nested'\""
```

#### Key Characteristics

- **Full Shell Processing**: All arguments are concatenated with spaces and processed through complete shell pipeline (tokenization, parsing, expansions, execution)
- **Current Context**: Executes in the current shell context - variables assigned and functions defined in eval persist
- **Exit Status**: Returns the exit status of the executed command(s), or 0 if empty
- **Bash Compatible**: Behavior matches bash's eval builtin
- **No History Pollution**: Commands executed via eval don't appear in command history

#### Implementation Details

- **Simple Architecture**: Just 38 lines of code leveraging existing shell infrastructure
- **No Core Changes**: Uses existing `shell.run_command()` method for execution
- **Educational Value**: Demonstrates how powerful features can be built on solid foundations
- **Comprehensive Tests**: 17 test cases covering all usage scenarios

### Examples and Demo

A comprehensive demo script is included at `examples/eval_demo.sh` showcasing:
- Basic eval usage
- Variable assignment and expansion
- Dynamic command building
- Function definitions
- Control structures
- Pipelines and command substitution
- Nested eval calls
- Exit status handling

Run the demo with:
```bash
psh examples/eval_demo.sh
```

### Security Considerations

Like bash's eval, this feature enables arbitrary code execution. Users should be cautious when using eval with untrusted input. The implementation provides no additional restrictions beyond what bash does.

### Test Results

- **New Tests**: 17 comprehensive eval tests added
- **Total Tests**: 788 passing (up from 771 in v0.35.1)
- **Test Coverage**: All eval functionality including edge cases, error handling, and complex scenarios

### Documentation Updates

- Updated CLAUDE.md to include eval in builtin lists
- Added comprehensive implementation plan in `docs/eval_implementation_plan.md`
- Enhanced architectural documentation showing component reuse

## Summary

- **Version**: 0.36.0
- **Type**: Feature release (minor version bump)
- **Tests**: 788 passed, 28 skipped, 5 xfailed
- **Compatibility**: No breaking changes - fully backward compatible
- **Dependencies**: No new dependencies

This release demonstrates PSH's architectural strength - complex features can be implemented simply by building on existing robust components. The eval builtin provides powerful dynamic programming capabilities while maintaining the shell's educational clarity and component-based design.