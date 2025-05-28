# Bash Shell Script Implementation Summary

## Overview
Bash implements shell scripts as text files containing shell commands that can be executed either in a subshell (execution) or in the current shell (sourcing).

## Script Recognition and Execution

### 1. What Makes a File a Script
- Any text file containing valid shell commands
- Does NOT require a specific extension (.sh is convention only)
- Can have a shebang line (#!) to specify interpreter
- Must have read permission; execute permission needed for direct execution

### 2. Execution Methods

#### Direct Execution (`./script.sh`)
- Requires execute permission (`chmod +x`)
- Creates a new process (subshell)
- Environment changes don't affect parent shell
- Exit status is preserved
- Process hierarchy: parent → bash → script

#### Source/Dot Command (`source script.sh` or `. script.sh`)
- Does NOT require execute permission (only read)
- Runs in current shell process
- All changes affect current environment (variables, functions, aliases, cwd)
- No new process created
- Used for configuration files (.bashrc, .profile)

#### Explicit Interpreter (`bash script.sh`)
- Does NOT require execute permission
- Creates new bash process
- Ignores shebang line
- Useful for running scripts without execute permission

### 3. Shebang (#!) Processing

The shebang line must:
- Be the very first line of the file
- Start with `#!` (no spaces before)
- Specify absolute path to interpreter or use `/usr/bin/env`

Examples:
```bash
#!/bin/bash              # Direct path
#!/usr/bin/env python3   # Using env for portability
#!/bin/sh               # POSIX shell
```

Execution flow with shebang:
1. Kernel reads first two bytes
2. If `#!`, kernel reads interpreter path
3. Executes: `interpreter [args] script remaining-args`
4. Original script becomes argument to interpreter

### 4. Argument Handling

Special variables for scripts:
- `$0` - Script name (as invoked)
- `$1, $2, ...` - Positional parameters
- `$#` - Number of arguments
- `$@` - All arguments (preserves word boundaries when quoted)
- `$*` - All arguments (single string when quoted)
- `$$` - Process ID of script
- `$!` - PID of last background command
- `$?` - Exit status of last command

Key differences between `$@` and `$*`:
```bash
# With args: "arg 1" "arg2"
for arg in "$@"; do  # Preserves: "arg 1", "arg2"
for arg in "$*"; do  # Becomes: "arg 1 arg2"
```

### 5. Environment Setup

#### Executed Scripts (Subshell)
- Inherit parent's environment variables
- Inherit parent's shell options (mostly)
- Get fresh positional parameters
- SHLVL incremented
- Non-interactive mode by default
- No prompt variables (PS1, etc.)
- No command history
- No job control

#### Sourced Scripts (Current Shell)
- Share all current shell state
- Modifications persist after script ends
- Can define functions and aliases
- Can change directory
- Access to shell history
- Retains interactive mode if parent is interactive

### 6. Permission Requirements

| Method | Read | Execute | Notes |
|--------|------|---------|--------|
| `./script` | ✓ | ✓ | Direct execution |
| `bash script` | ✓ | ✗ | Explicit interpreter |
| `source script` | ✓ | ✗ | Current shell |
| `. script` | ✓ | ✗ | Current shell |

Exit codes for permission errors:
- 126: Permission denied (file exists but not executable)
- 127: Command not found (file doesn't exist)

### 7. Interactive vs Non-Interactive Mode

Scripts run non-interactively by default, which affects:
- No prompt expansion
- No job control (`jobs`, `fg`, `bg` unavailable)
- No command history
- Different signal handling
- Some commands behave differently

Check interactive mode:
```bash
if [[ $- == *i* ]]; then
    echo "Interactive"
fi
```

### 8. Script Execution Flow

1. **Parse command line**
   - Determine execution method
   - Check permissions

2. **For direct execution**:
   - Kernel checks shebang
   - Spawns interpreter process
   - Or returns "Exec format error" for binaries

3. **Initialize script environment**:
   - Set positional parameters
   - Increment SHLVL
   - Set $0
   - Clear aliases (unless sourced)
   - Reset signal handlers

4. **Read and parse script**:
   - Line by line for non-sourced
   - Entire file for sourced (can affect behavior)

5. **Execute commands**:
   - Normal command processing
   - Exit on errors if `set -e`

6. **Cleanup**:
   - Return exit status
   - For sourced: no cleanup (changes persist)

## Implementation Considerations for psh

### Core Requirements

1. **Script Recognition**
   - Check if file exists and is readable
   - Parse shebang if present
   - Handle text vs binary detection

2. **Execution Modes**
   - Implement subshell execution (fork/exec)
   - Implement source builtin (parse in current context)
   - Different environment handling for each

3. **Argument Management**
   - Set up positional parameters before execution
   - Implement shift builtin
   - Handle $@, $*, $# correctly

4. **Permission Handling**
   - Check read permission for all methods
   - Check execute permission for direct execution
   - Return appropriate error codes

5. **Parser Integration**
   - Switch input from stdin to file
   - Handle EOF correctly
   - Preserve line numbers for error reporting

### Suggested Implementation Phases

1. **Phase 1**: Basic script execution
   - Read script file
   - Execute in subshell
   - Basic argument passing

2. **Phase 2**: Source builtin
   - Execute in current shell
   - Preserve environment changes

3. **Phase 3**: Shebang support
   - Parse #! line
   - Exec appropriate interpreter

4. **Phase 4**: Advanced features
   - Permission checking
   - Binary file detection
   - Proper error codes
   - Line number tracking

### Key Differences from Interactive Mode

1. No readline/line editing
2. EOF ends script (vs. logout)
3. No prompt expansion
4. Batch error handling
5. Different default signal handling

### Security Considerations

1. Always check permissions before execution
2. Sanitize PATH for script execution
3. Handle relative vs absolute paths correctly
4. Prevent arbitrary code execution via shebangs
5. Consider implications of sourcing untrusted scripts