# PSH vs Bash Differences Documentation

This directory contains documentation of differences between PSH and bash behavior, categorized by type and impact.

## Difference Categories

### 1. PSH Extensions
Features that PSH provides but bash doesn't (or implements differently).

#### Educational/Debug Features
- `--debug-ast`: Show AST structure before execution
- `--debug-tokens`: Show tokenization output  
- `--debug-expansion`: Trace variable/command expansion
- `--validate`: Parse and validate without executing

#### Enhanced Builtins
- `version`: Show PSH version information
- `help`: Context-aware help system

### 2. Bash-Specific Features (Not Implemented)
Features that bash provides but PSH intentionally doesn't support.

#### Advanced Conditionals
- `[[ ]]`: Bash extended test construct
- `(( ))`: Arithmetic evaluation construct

#### Arrays
- `declare -a`: Indexed array declaration
- `declare -A`: Associative array declaration  
- `${array[@]}`: Array expansion syntax
- `${#array[@]}`: Array length syntax

#### Advanced Parameter Expansion
- `${var^}`, `${var^^}`: Case conversion (first char/all chars to upper)
- `${var,}`, `${var,,}`: Case conversion (first char/all chars to lower)
- `${var/pattern/replacement}`: Pattern substitution
- `${var//pattern/replacement}`: Global pattern substitution

#### Process Substitution
- `<(command)`: Process substitution input
- `>(command)`: Process substitution output

#### Extended Globbing
- `?(pattern)`: Zero or one occurrence
- `+(pattern)`: One or more occurrences  
- `*(pattern)`: Zero or more occurrences
- `@(pattern)`: Exactly one occurrence
- `!(pattern)`: Not matching pattern

#### Bash Builtins
- `declare`: Variable/function declaration with attributes
- `local`: Local variables in functions
- `mapfile`/`readarray`: Read lines into array
- `shopt`: Shell option setting

### 3. Documented Behavioral Differences
Areas where PSH and bash both support a feature but with different behavior.

#### Directory Stack (pushd/popd)
- PSH and bash may handle directory stack operations slightly differently
- Output format may vary
- Error handling may differ

#### History Handling
- PSH may implement history differently than bash
- History expansion (`!!`, `!n`) not implemented in PSH
- History file format may differ

#### Signal Handling
- PSH may handle some signals differently than bash
- Trap behavior in functions may vary
- Job control signal handling differences

### 4. Known Limitations
Features that are partially implemented or have known issues.

#### Here Documents
- PSH here document processing has architectural limitations
- Variable expansion in here documents may not work identically
- Tab stripping (`<<-`) may not be fully implemented

#### Interactive Features
- Line editing capabilities may be limited
- Tab completion may not be fully implemented
- Prompt customization may be limited

#### I/O Redirection
- Advanced redirection features may not be supported
- File descriptor manipulation may be limited
- Some redirection combinations may not work

## Testing Strategy

### Conformance Tests
1. **POSIX Compliance**: Test features required by POSIX
2. **Bash Compatibility**: Test bash-specific features
3. **Difference Documentation**: Catalog and test known differences

### Test Categories
- **Identical**: PSH and bash produce identical results
- **Documented Difference**: Known and documented difference
- **PSH Extension**: PSH supports something bash doesn't  
- **Bash Specific**: Bash supports something PSH doesn't
- **PSH Bug**: Unexpected difference (potential bug)

### Usage in Tests
```python
# Test identical behavior
self.assert_identical_behavior('echo hello')

# Test documented difference
self.assert_documented_difference('version', 'VERSION_BUILTIN')

# Test PSH extension
self.assert_psh_extension('psh --debug-ast script.sh')

# Test bash-specific feature
self.assert_bash_specific('[[ "hello" == "hello" ]]')

# Investigate difference
result = self.check_behavior('complex_command')
```

## Updating Documentation

When adding new tests or discovering differences:

1. **Update the JSON catalog** (`psh_bash_differences.json`)
2. **Document the difference** in this README
3. **Add conformance tests** to verify the behavior
4. **Categorize appropriately** (extension, limitation, etc.)

## Compliance Goals

### POSIX Compliance Target: >95%
PSH should support all required POSIX shell features with identical behavior to bash.

### Bash Compatibility Target: >80%
PSH should support common bash features while documenting intentional differences.

### Quality Targets
- Zero undocumented differences in core features
- All differences should be intentional design decisions
- Clear documentation for users migrating from bash

## References

- [POSIX Shell Standard](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- [Bash Manual](https://www.gnu.org/software/bash/manual/bash.html)
- [PSH Architecture Documentation](../../../ARCHITECTURE.md)