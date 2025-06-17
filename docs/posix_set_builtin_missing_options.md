# Missing POSIX `set` Builtin Options in PSH

## Current PSH Implementation

PSH currently supports these `set` options:
- `-e` (errexit) - Exit on command failure
- `-u` (nounset) - Error on undefined variables
- `-x` (xtrace) - Print commands before execution
- `-o pipefail` - Pipeline fails if any command fails
- Various debug options (debug-ast, debug-tokens, etc.)
- Editor modes: `-o vi`, `-o emacs`

## Missing POSIX Options

Based on the POSIX specification, PSH is missing the following `set` options:

### 1. `-a` (allexport)
**Description**: When this option is on, the export attribute shall be set for each variable to which an assignment is performed.

**Implementation needed**:
- Modify variable assignment in shell to automatically export variables when `-a` is set
- Integrate with `VariableExpander` and `set_variable` methods
- Ensure proper scoping (assignments before commands shouldn't persist export)

### 2. `-b` (notify)
**Description**: Cause the shell to notify the user asynchronously of background job completions.

**Implementation needed**:
- Modify `JobManager` to print job completion messages asynchronously
- Format: `"[%d]%c %s%s\n", <job-number>, <current>, <status>, <job-name>`
- Integrate with existing job control infrastructure

### 3. `-C` (noclobber)
**Description**: Prevent existing files from being overwritten by the shell's '>' redirection operator.

**Implementation needed**:
- Modify `IOManager` and redirection handling
- Check if target file exists before opening with O_TRUNC
- Support `>|` operator to override noclobber
- Add error handling for noclobber violations

### 4. `-f` (noglob)
**Description**: The shell shall disable pathname expansion.

**Implementation needed**:
- Add flag check in `ExpansionManager.expand_glob`
- Skip glob expansion when `-f` is set
- Ensure other expansions still work

### 5. `-h` (hashcmds)
**Description**: Locate and remember utilities invoked by functions as those functions are defined.

**Implementation needed**:
- Create command hash table infrastructure
- Cache command locations during function definition
- Integrate with command lookup mechanism

### 6. `-m` (monitor)
**Description**: All jobs shall be run in their own process groups. Job control features.

**Implementation needed**:
- This is mostly implemented in PSH's job control
- Need to ensure all jobs get their own process groups
- Add job status change notifications

### 7. `-n` (noexec)
**Description**: The shell shall read commands but does not execute them.

**Implementation needed**:
- Add flag check in executor before running commands
- Still perform parsing and syntax checking
- Useful for syntax validation

### 8. `-v` (verbose)
**Description**: The shell shall write its input to standard error as it is read.

**Implementation needed**:
- Add input echoing in shell's main read loop
- Write each line to stderr as it's read
- Different from `-x` which shows after expansion

### 9. `-o ignoreeof`
**Description**: Prevent an interactive shell from exiting on end-of-file (Ctrl-D).

**Implementation needed**:
- Modify shell's EOF handling in interactive mode
- Require explicit `exit` command
- Add counter for consecutive EOFs (bash-style)

### 10. `-o nolog`
**Description**: Prevent the entry of function definitions into the command history.

**Implementation needed**:
- Add check in history recording mechanism
- Skip function definitions when nolog is set

## Implementation Strategy

### 1. Extend Shell State Options

```python
# In core/state.py
self.options = {
    # Existing options...
    'allexport': False,    # -a
    'notify': False,       # -b  
    'noclobber': False,    # -C
    'noglob': False,       # -f
    'hashcmds': False,     # -h
    'monitor': False,      # -m
    'noexec': False,       # -n
    'verbose': False,      # -v
    'ignoreeof': False,    # -o ignoreeof
    'nolog': False,        # -o nolog
}
```

### 2. Update SetBuiltin

```python
# Add to short_to_long mapping
short_to_long = {
    'a': 'allexport',
    'b': 'notify',
    'C': 'noclobber',
    'e': 'errexit',
    'f': 'noglob',
    'h': 'hashcmds',
    'm': 'monitor',
    'n': 'noexec',
    'u': 'nounset',
    'v': 'verbose',
    'x': 'xtrace',
}
```

### 3. Create Option Handlers

For each option, implement the behavior in the appropriate component:

- **allexport**: In `set_variable` method
- **notify**: In `JobManager` job completion handling
- **noclobber**: In `IOManager` output redirection
- **noglob**: In `ExpansionManager` glob expansion
- **hashcmds**: New `CommandHashTable` class
- **monitor**: In job control setup
- **noexec**: In executor's command execution
- **verbose**: In shell's input reading loop
- **ignoreeof**: In interactive shell's EOF handling
- **nolog**: In history recording

### 4. Special Variable $-

Update the `$-` special variable to reflect active single-letter options:

```python
def get_option_string(self):
    """Get string representation of set options for $-."""
    opts = []
    if self.options.get('allexport'): opts.append('a')
    if self.options.get('notify'): opts.append('b')
    if self.options.get('noclobber'): opts.append('C')
    if self.options.get('errexit'): opts.append('e')
    if self.options.get('noglob'): opts.append('f')
    if self.options.get('hashcmds'): opts.append('h')
    if self.options.get('monitor'): opts.append('m')
    if self.options.get('noexec'): opts.append('n')
    if self.options.get('nounset'): opts.append('u')
    if self.options.get('verbose'): opts.append('v')
    if self.options.get('xtrace'): opts.append('x')
    return ''.join(opts)
```

## Testing Requirements

Each option needs comprehensive tests:

1. **Basic functionality tests** - Option enables/disables correctly
2. **Integration tests** - Option interacts properly with shell features
3. **Edge case tests** - Corner cases and error conditions
4. **Bash comparison tests** - Behavior matches POSIX/bash

## Priority Order

Recommended implementation order based on usefulness and complexity:

1. **High Priority** (Most useful, moderate complexity):
   - `-f` (noglob) - Simple to implement, useful feature
   - `-C` (noclobber) - Important safety feature
   - `-n` (noexec) - Useful for script validation
   - `-v` (verbose) - Helpful for debugging

2. **Medium Priority** (Useful, more complex):
   - `-a` (allexport) - Useful for environment setup
   - `-b` (notify) - Enhances job control
   - `-o ignoreeof` - Quality of life improvement

3. **Low Priority** (Less commonly used):
   - `-h` (hashcmds) - Performance optimization
   - `-m` (monitor) - Mostly already implemented
   - `-o nolog` - Niche use case

## Notes

- The `-t` (read and execute one command then exit) and `-k` (place all assignments in environment) options were intentionally omitted from POSIX
- Some options like `-m` (monitor) are only required if the system supports the User Portability Utilities option
- The implementation should maintain backward compatibility with existing PSH scripts