# ~/.pshrc Implementation Plan

## Overview

The ~/.pshrc file would be automatically sourced when psh starts in interactive mode, allowing users to customize their shell environment with aliases, functions, variables, and settings. This design follows bash's ~/.bashrc conventions while fitting naturally into psh's existing architecture.

## When to Load ~/.pshrc

### Load ~/.pshrc when:
- Shell is started interactively (no script file, no -c command)
- Standard input is a terminal (isatty() check)
- The file exists and is readable
- No --norc flag is specified

### Don't load ~/.pshrc when:
- Running with `-c "command"` flag
- Executing a script file (`psh script.sh`)
- Standard input is not a terminal (piped input)
- Running with `--norc` flag (proposed new option)

## Implementation Details

### 1. Add RC file loading to Shell initialization

```python
# In shell.py, Shell.__init__, after history loading (around line 55):
if not self.is_script_mode and sys.stdin.isatty() and not args.norc:
    self._load_rc_file()
```

### 2. Create the RC file loader method

```python
def _load_rc_file(self):
    """Load ~/.pshrc if it exists."""
    rc_file = os.path.expanduser("~/.pshrc")
    if os.path.isfile(rc_file) and os.access(rc_file, os.R_OK):
        try:
            # Store current context
            old_script_name = self.variables.get('0', 'psh')
            self.variables['0'] = rc_file
            
            # Source the file without adding to history
            from .input_sources import FileInput
            with FileInput(rc_file) as input_source:
                self._execute_from_source(input_source, add_to_history=False)
            
            # Restore context
            self.variables['0'] = old_script_name
            
        except Exception as e:
            # Print warning but continue shell startup
            print(f"psh: warning: error loading {rc_file}: {e}", file=sys.stderr)
```

### 3. Add command line options

```python
# In __main__.py, add to argument parser:
parser.add_argument('--norc', action='store_true',
                    help="Do not read ~/.pshrc on startup")
parser.add_argument('--rcfile', type=str, metavar='FILE',
                    help="Read FILE instead of ~/.pshrc")
```

### 4. Update Shell constructor signature

```python
# Add parameters to Shell.__init__:
def __init__(self, script_name=None, is_script_mode=False, norc=False, rcfile=None):
    self.norc = norc
    self.rcfile = rcfile
    # ... rest of initialization
```

## Example ~/.pshrc File

```bash
# ~/.pshrc - psh initialization file

# ========== Aliases ==========
# File operations
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'

# Directory navigation
alias ..='cd ..'
alias ...='cd ../..'
alias cdl='cd "$1" && ls'

# Git shortcuts
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'

# Safety aliases
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# ========== Functions ==========
# Create directory and cd into it
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# Extract various archive types
extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.gz|*.tgz) tar xzf "$1" ;;
            *.tar.bz2) tar xjf "$1" ;;
            *.zip) unzip "$1" ;;
            *.gz) gunzip "$1" ;;
            *) echo "Unknown archive type: $1" ;;
        esac
    else
        echo "File not found: $1"
    fi
}

# Find files by name
ff() {
    find . -name "*$1*" -type f
}

# ========== Environment Variables ==========
export EDITOR=vim
export PAGER=less
export LESS='-R'

# Add personal bin to PATH
if [ -d "$HOME/bin" ]; then
    export PATH="$HOME/bin:$PATH"
fi

# ========== Shell Options ==========
# Use vi key bindings
set -o vi

# ========== Shell Variables ==========
# History settings
HISTSIZE=1000

# ========== Completion Setup ==========
# (When programmable completion is implemented)
# complete -f -X '!*.py' python

# ========== Prompt Customization ==========
# (When PS1 is implemented)
# PS1='[\u@\h \W]$ '

# ========== Local Machine Settings ==========
# Source local settings if they exist
if [ -f ~/.pshrc.local ]; then
    source ~/.pshrc.local
fi
```

## Order of Operations

1. Shell initialization begins
2. Basic environment setup
3. Load command history
4. Check if interactive mode
5. Load /etc/pshrc (if implemented)
6. Load ~/.pshrc (or --rcfile alternative)
7. Process remaining command line arguments
8. Start interactive loop or execute command

## Security Considerations

### File Permission Checks
```python
def _is_safe_rc_file(self, filepath):
    """Check if rc file is safe to execute."""
    try:
        stat_info = os.stat(filepath)
        # Check if file is owned by user or root
        if stat_info.st_uid not in (os.getuid(), 0):
            return False
        # Check if file is world-writable
        if stat_info.st_mode & 0o002:
            return False
        return True
    except OSError:
        return False
```

### Additional Security Measures
- Only source files with proper ownership
- Warn about world-writable rc files
- Option to disable rc file loading (--norc)
- Clear error messages for permission issues

## Error Handling Strategy

1. **Syntax Errors**: Print warning but continue shell startup
2. **File Not Found**: Silently skip (normal case)
3. **Permission Denied**: Print warning about permissions
4. **Execution Errors**: Catch and report but don't crash
5. **Circular Source**: Detect and prevent infinite loops

## Testing Considerations

### Test Cases
1. Normal interactive startup with ~/.pshrc
2. Startup with --norc flag
3. Startup with --rcfile pointing to test file
4. RC file with syntax errors
5. RC file with runtime errors
6. Non-existent RC file
7. RC file with wrong permissions
8. Script mode should not load RC file
9. Piped input should not load RC file

### Debug Support
```bash
# Debug RC file loading
psh --verbose-rc  # Show each line as it's executed
psh --dry-run-rc  # Parse but don't execute RC file
```

## Future Extensions

### 1. Login Shell Support
- `~/.psh_profile` - Executed for login shells
- `~/.psh_login` - Alternative login file
- Login shell detection via `-l` flag

### 2. Logout Processing
- `~/.psh_logout` - Commands to run on exit
- Cleanup tasks, session logging, etc.

### 3. System-wide Configuration
- `/etc/pshrc` - System defaults before user RC
- `/etc/psh_profile` - System login defaults

### 4. Environment-based Loading
```bash
# In ~/.pshrc
if [ "$HOSTNAME" = "dev-server" ]; then
    source ~/.pshrc.dev
fi
```

### 5. RC File Management Commands
```bash
# Built-in commands for RC file management
psh --show-rc      # Display processed RC file
psh --reload-rc    # Reload RC file in current shell
psh --check-rc     # Validate RC file syntax
```

## Benefits

1. **User Customization**: Personalized shell environment
2. **Productivity**: Instant access to aliases and functions
3. **Consistency**: Same environment across sessions
4. **Portability**: Share configurations between systems
5. **Educational Value**: Demonstrates shell initialization concepts
6. **Migration Path**: Easy transition from bash for users

## Implementation Priority

### Phase 1 (Core Functionality)
- Basic ~/.pshrc loading for interactive shells
- --norc command line flag
- Error handling and recovery

### Phase 2 (Enhanced Features)
- --rcfile option
- Security checks
- System-wide /etc/pshrc

### Phase 3 (Advanced Features)
- Login shell support
- Logout processing
- Debug/verbose modes
- RC file validation tools

This implementation plan provides a solid foundation for adding RC file support to psh while maintaining compatibility with bash conventions and the educational goals of the project.