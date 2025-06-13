# Read Builtin Implementation Strategy for PSH

## Overview

The `read` builtin is essential for shell scripting, allowing scripts to read user input and process files line by line. This document outlines the implementation strategy for adding the read builtin to psh.

## Implementation Phases

### Phase 1: Core POSIX Functionality (MVP)

Implement the basic POSIX-compliant read functionality:

```bash
read [-r] var...
```

#### Features:
1. Read a line from stdin
2. Split input based on IFS (Internal Field Separator)
3. Assign fields to specified variables
4. Handle -r option (raw mode - no backslash interpretation)
5. Default to REPLY variable if no variables specified
6. Proper exit codes (0 for success, >0 for EOF)

#### Implementation Details:
- Create `psh/builtins/read_builtin.py`
- Use `sys.stdin.readline()` for basic input
- Implement IFS-based field splitting
- Handle variable assignment through shell's variable system
- Support backslash escape sequences (unless -r specified)

### Phase 2: Interactive Features

Add interactive terminal support:

1. **Silent mode (-s)**: Don't echo characters (for passwords)
   - Use termios to disable echo
   - Restore terminal settings after reading

2. **Prompt (-p)**: Display prompt without newline
   - Print to stderr (bash behavior)
   - No trailing newline

3. **Character limit (-n)**: Read only N characters
   - Use terminal raw mode for character-by-character reading
   - Stop at delimiter or N characters

### Phase 3: Advanced Features

1. **Timeout (-t)**: Time-limited input
   - Use select() or similar for timeout support
   - Return exit code >128 on timeout

2. **Delimiter (-d)**: Custom delimiter instead of newline
   - Support empty string for null delimiter
   - Handle multi-character delimiters

3. **File descriptor (-u)**: Read from specific fd
   - Support reading from arbitrary file descriptors
   - Default to fd 0 (stdin)

### Phase 4: Bash Extensions (Optional)

1. **Array support (-a)**: Assign to array indices
2. **Readline integration (-e)**: Enable tab completion
3. **Initial text (-i)**: Pre-fill readline buffer
4. **Exact character count (-N)**: Ignore delimiters

## Code Structure

```python
# psh/builtins/read_builtin.py

import sys
import os
import termios
import tty
import select
from typing import List, Optional
from .base import Builtin
from .registry import builtin

@builtin
class ReadBuiltin(Builtin):
    """Read a line from standard input."""
    
    @property
    def name(self) -> str:
        return "read"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse options
        raw_mode = False
        silent = False
        prompt = None
        timeout = None
        delimiter = '\n'
        max_chars = None
        fd = 0
        
        # Option parsing logic
        i = 1
        while i < len(args):
            if args[i] == '-r':
                raw_mode = True
            elif args[i] == '-s':
                silent = True
            elif args[i] == '-p' and i + 1 < len(args):
                prompt = args[i + 1]
                i += 1
            elif args[i] == '-t' and i + 1 < len(args):
                timeout = float(args[i + 1])
                i += 1
            elif args[i] == '-d' and i + 1 < len(args):
                delimiter = args[i + 1] or '\0'
                i += 1
            elif args[i] == '-n' and i + 1 < len(args):
                max_chars = int(args[i + 1])
                i += 1
            elif args[i] == '-u' and i + 1 < len(args):
                fd = int(args[i + 1])
                i += 1
            elif args[i].startswith('-'):
                print(f"read: {args[i]}: invalid option", file=sys.stderr)
                return 2
            else:
                break
            i += 1
        
        # Get variable names
        var_names = args[i:] if i < len(args) else ['REPLY']
        
        # Read input
        try:
            if timeout:
                line = self._read_with_timeout(fd, timeout, delimiter, max_chars, silent)
            elif silent or max_chars:
                line = self._read_special(fd, delimiter, max_chars, silent)
            else:
                line = self._read_normal(fd, delimiter, prompt)
            
            if line is None:  # EOF or timeout
                return 1
            
            # Process the line
            if not raw_mode:
                line = self._process_escapes(line)
            
            # Split based on IFS and assign to variables
            self._assign_variables(line, var_names, shell)
            
            return 0
            
        except KeyboardInterrupt:
            return 130
        except Exception as e:
            print(f"read: {e}", file=sys.stderr)
            return 1
```

## Testing Strategy

### Unit Tests
1. Basic reading and variable assignment
2. IFS handling (default and custom)
3. Raw mode vs escape processing
4. EOF and error handling
5. Multiple variable assignment
6. Silent mode
7. Timeout behavior
8. Custom delimiters

### Integration Tests
1. Reading in loops (`while read`)
2. Pipeline integration (`command | while read`)
3. Here documents and here strings
4. File descriptor redirection
5. Interactive password prompts
6. Script automation scenarios

## Implementation Priority

1. **High Priority** (Phase 1):
   - Basic read functionality
   - -r option
   - IFS handling
   - Variable assignment

2. **Medium Priority** (Phase 2):
   - -s (silent) option
   - -p (prompt) option
   - -n (char limit) option

3. **Lower Priority** (Phase 3-4):
   - -t (timeout) option
   - -d (delimiter) option
   - -u (file descriptor) option
   - Array support (-a)

## Compatibility Considerations

1. **POSIX Compliance**: Core functionality must match POSIX specification
2. **Bash Compatibility**: Common bash extensions should work similarly
3. **Error Messages**: Match bash error message format
4. **Exit Codes**: Use standard exit codes (0, 1, 130 for Ctrl-C)

## Known Challenges

1. **Terminal Handling**: Raw mode and echo control require careful termios management
2. **Signal Handling**: Proper cleanup on interruption (Ctrl-C)
3. **Timeout Implementation**: Platform-specific considerations
4. **IFS Edge Cases**: Multiple delimiters, whitespace handling
5. **Line Continuation**: Backslash-newline handling in non-raw mode

## Examples to Support

```bash
# Basic usage
read name
echo "Hello, $name"

# Multiple variables
read first last
echo "$last, $first"

# Silent password
read -s -p "Password: " pass
echo

# Timeout
if read -t 5 response; then
    echo "Got: $response"
else
    echo "Timeout!"
fi

# File processing
while IFS=: read -r user _ uid gid _ home shell; do
    echo "$user ($uid): $home"
done < /etc/passwd

# Custom delimiter
IFS=$'\t' read -r col1 col2 col3

# Here string (bash)
read var <<< "some string"
```

## Success Criteria

1. All basic POSIX read functionality works correctly
2. Common bash extensions are supported
3. Proper error handling and exit codes
4. Terminal state properly managed
5. Integration with existing shell features (variables, IFS, redirection)
6. Comprehensive test coverage
7. Clear documentation and examples