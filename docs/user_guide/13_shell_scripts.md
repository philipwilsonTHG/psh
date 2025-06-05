# Chapter 13: Shell Scripts

Shell scripts allow you to save and execute sequences of commands, creating reusable programs for automation, system administration, and complex tasks. PSH provides comprehensive scripting support with features for script execution, argument handling, and debugging.

## 13.1 Creating Shell Scripts

A shell script is a text file containing shell commands that can be executed as a program.

### Basic Script Structure

```bash
#!/usr/bin/env psh
# This is a shell script comment

# Script variables
SCRIPT_NAME="My First Script"
VERSION="1.0"

# Display information
echo "Running $SCRIPT_NAME v$VERSION"
echo "Current date: $(date)"
echo "Current user: $(whoami)"

# Exit with success
exit 0
```

### Making Scripts Executable

```bash
# Create a script file
psh$ cat > hello.sh << 'EOF'
> #!/usr/bin/env psh
> echo "Hello, World!"
> EOF

# Make it executable
psh$ chmod +x hello.sh

# Run the script
psh$ ./hello.sh
Hello, World!

# Run without execute permission
psh$ psh hello.sh
Hello, World!
```

### Script File Naming

```bash
# Common conventions
script.sh       # Shell script with .sh extension
backup-files    # Descriptive name without extension
setup.psh       # PSH-specific script
deploy_app      # Underscore separation

# Avoid these names
test            # Conflicts with test builtin
cd              # Conflicts with cd builtin
1script.sh      # Starting with number
my-script.txt   # Misleading extension
```

## 13.2 Shebang (#!) Line

The shebang line tells the system which interpreter to use for the script.

### Common Shebang Forms

```bash
#!/usr/bin/env psh    # Portable, finds psh in PATH
#!/usr/local/bin/psh  # Direct path to psh
#!/bin/sh            # POSIX shell (not PSH-specific)
#!/bin/bash          # Bash shell (for bash scripts)

# Example with different interpreters
psh$ cat > python_script.py << 'EOF'
> #!/usr/bin/env python3
> print("This is a Python script")
> EOF
psh$ chmod +x python_script.py
psh$ ./python_script.py
This is a Python script
```

### Shebang Best Practices

```bash
# Portable shebang (recommended)
#!/usr/bin/env psh

# With options (be careful - not all systems support this)
#!/usr/bin/env -S psh -x

# Direct path (less portable but faster)
#!/usr/local/bin/psh

# Fallback script that finds psh
#!/bin/sh
# Find and exec psh
command -v psh >/dev/null 2>&1 || { echo "psh not found"; exit 1; }
exec psh "$0" "$@"
```

## 13.3 Script Arguments and Parameters

Scripts can accept command-line arguments accessible through special parameters.

### Positional Parameters

```bash
#!/usr/bin/env psh
# script: show_args.sh

echo "Script name: $0"
echo "First argument: $1"
echo "Second argument: $2"
echo "Third argument: $3"
echo "Number of arguments: $#"
echo "All arguments (as string): $*"
echo "All arguments (as array): $@"

# Using arguments
psh$ ./show_args.sh hello world test
Script name: ./show_args.sh
First argument: hello
Second argument: world
Third argument: test
Number of arguments: 3
All arguments (as string): hello world test
All arguments (as array): hello world test
```

### Argument Processing

```bash
#!/usr/bin/env psh
# script: process_files.sh

# Check for required arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1> [file2] ..." >&2
    exit 1
fi

# Process each argument
echo "Processing $# files:"
for file in "$@"; do
    if [ -f "$file" ]; then
        echo "  $file: $(wc -l < "$file") lines"
    else
        echo "  $file: not found" >&2
    fi
done
```

### Shift Command

```bash
#!/usr/bin/env psh
# script: shift_demo.sh

# Process options before files
verbose=false
while [ $# -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            verbose=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-v] [files...]"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            # Stop processing options
            break
            ;;
    esac
done

# Remaining arguments are files
if [ "$verbose" = true ]; then
    echo "Verbose mode enabled"
    echo "Files to process: $*"
fi
```

### Default Values

```bash
#!/usr/bin/env psh
# script: defaults.sh

# Set default values for parameters
input_file="${1:-input.txt}"
output_file="${2:-output.txt}"
mode="${3:-process}"

echo "Input: $input_file"
echo "Output: $output_file"
echo "Mode: $mode"

# Using parameter expansion for defaults
NAME="${USER:-anonymous}"
HOME_DIR="${HOME:-/tmp}"
CONFIG="${CONFIG_FILE:-$HOME/.config/app.conf}"
```

## 13.4 Script Execution Methods

PSH provides multiple ways to execute scripts.

### Direct Execution

```bash
# With shebang and execute permission
psh$ ./script.sh arg1 arg2

# Using PATH
psh$ export PATH="$PATH:~/scripts"
psh$ script.sh    # Finds script.sh in ~/scripts

# Explicit interpreter
psh$ psh script.sh arg1 arg2
psh$ /usr/local/bin/psh script.sh
```

### Command String Execution

```bash
# Execute command string
psh$ psh -c 'echo "Hello from command string"'
Hello from command string

# With arguments
psh$ psh -c 'echo "Args: $@"' -- arg1 arg2 arg3
Args: arg1 arg2 arg3

# Multiple commands
psh$ psh -c 'cd /tmp; pwd; ls -la | head -5'
/tmp
total 48
drwxrwxrwt  12 root  wheel  384 Jan  5 10:30 .
drwxr-xr-x  20 root  wheel  640 Jan  1 00:00 ..
```

### Reading from Standard Input

```bash
# Pipe commands to psh
psh$ echo 'echo "Hello from stdin"' | psh
Hello from stdin

# Here document
psh$ psh << 'EOF'
> name="PSH User"
> echo "Welcome, $name"
> date
> EOF
Welcome, PSH User
Mon Jan 5 10:30:45 PST 2025

# Process substitution
psh$ psh <(echo 'echo "From process substitution"')
From process substitution
```

### Source Command

```bash
# Execute in current shell context
psh$ source script.sh
psh$ . script.sh    # Short form

# With arguments
psh$ source script.sh arg1 arg2

# Source from PATH
psh$ export PATH="$PATH:~/lib"
psh$ source utilities.sh    # Finds in ~/lib

# Difference from direct execution
psh$ cat > set_var.sh << 'EOF'
> MY_VAR="Hello"
> export MY_VAR
> EOF

psh$ ./set_var.sh
psh$ echo $MY_VAR
                    # Empty - ran in subshell

psh$ source set_var.sh
psh$ echo $MY_VAR
Hello               # Set in current shell
```

## 13.5 Script Organization

Well-organized scripts are easier to maintain and debug.

### Script Header

```bash
#!/usr/bin/env psh
#
# Script: backup_system.sh
# Purpose: Backup system configuration files
# Author: Your Name
# Date: January 5, 2025
# Version: 1.0
#
# Usage: backup_system.sh [-v] [-d destination]
#
# Options:
#   -v             Verbose output
#   -d destination Backup destination directory
#

# Script metadata
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly SCRIPT_VERSION="1.0"

# Default configuration
VERBOSE=false
DESTINATION="/backup"
```

### Function Definitions

```bash
#!/usr/bin/env psh

# Function definitions at the top
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options] <command>

Commands:
    start   Start the service
    stop    Stop the service
    status  Show service status
    
Options:
    -h, --help     Show this help
    -v, --verbose  Enable verbose output
    -c, --config   Config file path
EOF
}

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >&2
}

error() {
    log "ERROR" "$@"
    exit 1
}

info() {
    [ "$VERBOSE" = true ] && log "INFO" "$@"
}

# Main logic after functions
main() {
    # Process options
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Execute command
    case "${1:-}" in
        start|stop|status)
            "$1"
            ;;
        *)
            usage >&2
            exit 1
            ;;
    esac
}

# Call main with all arguments
main "$@"
```

### Error Handling

```bash
#!/usr/bin/env psh

# Exit on error (not fully implemented in PSH yet)
# set -e

# Error handler function
handle_error() {
    local exit_code=$?
    local line_number="$1"
    echo "Error on line $line_number: Command exited with status $exit_code" >&2
    exit $exit_code
}

# Manual error checking
create_backup() {
    local source="$1"
    local dest="$2"
    
    # Check source exists
    if [ ! -d "$source" ]; then
        echo "Error: Source directory '$source' not found" >&2
        return 1
    fi
    
    # Create destination
    if ! mkdir -p "$dest"; then
        echo "Error: Cannot create destination '$dest'" >&2
        return 1
    fi
    
    # Perform backup
    if ! cp -r "$source"/* "$dest/"; then
        echo "Error: Backup failed" >&2
        return 1
    fi
    
    echo "Backup completed successfully"
    return 0
}

# Cleanup on exit
cleanup() {
    echo "Cleaning up temporary files..."
    rm -f /tmp/backup.$$.*
}

# Set trap for cleanup
# trap cleanup EXIT  # Not fully implemented in PSH
```

## 13.6 Input and Output

Scripts can handle various forms of input and output.

### Reading User Input

```bash
#!/usr/bin/env psh

# Simple input
echo -n "Enter your name: "
read name
echo "Hello, $name!"

# With prompt
read -p "Enter password: " -s password
echo    # New line after password
echo "Password length: ${#password}"

# Multiple values
echo "Enter three numbers:"
read num1 num2 num3
sum=$((num1 + num2 + num3))
echo "Sum: $sum"

# Read with timeout
if read -t 5 -p "Quick! Enter something (5 seconds): " response; then
    echo "You entered: $response"
else
    echo "Too slow!"
fi

# Read single character
read -n 1 -p "Press any key to continue..."
echo
```

### File Operations

```bash
#!/usr/bin/env psh

# Reading files line by line
process_file() {
    local filename="$1"
    local line_num=0
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        echo "Line $line_num: $line"
    done < "$filename"
}

# Writing to files
create_config() {
    local config_file="$1"
    
    # Overwrite file
    cat > "$config_file" << EOF
# Configuration file
# Generated on $(date)

[settings]
debug=false
verbose=true
EOF
    
    # Append to file
    echo "log_file=/var/log/app.log" >> "$config_file"
}

# Temporary files
temp_file=$(mktemp)
echo "Using temporary file: $temp_file"

# Process data
sort input.txt > "$temp_file"
uniq "$temp_file" > output.txt

# Cleanup
rm -f "$temp_file"
```

### Logging

```bash
#!/usr/bin/env psh

# Logging functions
LOG_FILE="/var/log/myscript.log"
LOG_LEVEL="INFO"

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    # Also log to stderr for errors
    if [ "$level" = "ERROR" ] || [ "$level" = "FATAL" ]; then
        echo "[$timestamp] [$level] $message" >&2
    fi
}

debug() { [ "$LOG_LEVEL" = "DEBUG" ] && log "DEBUG" "$@"; }
info()  { log "INFO" "$@"; }
warn()  { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }
fatal() { log "FATAL" "$@"; exit 1; }

# Usage
info "Script started"
debug "Processing file: $filename"
warn "File size exceeds limit"
error "Cannot write to output"
fatal "Critical error - exiting"
```

## 13.7 Debugging Scripts

PSH provides several features for debugging scripts.

### Debug Output

```bash
#!/usr/bin/env psh

# Debug mode variable
DEBUG="${DEBUG:-false}"

debug() {
    [ "$DEBUG" = "true" ] && echo "DEBUG: $*" >&2
}

# Usage
debug "Starting process"
debug "Variable value: $var"

# Run with debugging
psh$ DEBUG=true ./script.sh
```

### Execution Tracing

```bash
# Show commands before execution (not fully implemented)
# set -x

# Manual trace
trace() {
    echo "+ $*" >&2
    "$@"
}

# Usage
trace cp source.txt dest.txt
trace rm -f temp.txt
```

### Debug Modes

```bash
# Show parsed AST
psh$ psh --debug-ast script.sh

# Show tokenization
psh$ psh --debug-tokens script.sh

# Show variable scopes
psh$ psh --debug-scopes script.sh

# Combine debug modes
psh$ psh --debug-ast --debug-tokens script.sh
```

### Error Diagnosis

```bash
#!/usr/bin/env psh

# Add line numbers to errors
error_with_line() {
    local line_no="${BASH_LINENO[0]}"  # Not available in PSH
    echo "Error at line $line_no: $1" >&2
    exit 1
}

# Validate before proceeding
validate_environment() {
    local errors=0
    
    # Check required commands
    for cmd in git docker python3; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: Required command '$cmd' not found" >&2
            errors=$((errors + 1))
        fi
    done
    
    # Check required files
    for file in config.json secrets.env; do
        if [ ! -f "$file" ]; then
            echo "Error: Required file '$file' not found" >&2
            errors=$((errors + 1))
        fi
    done
    
    if [ $errors -gt 0 ]; then
        echo "Found $errors errors. Please fix before continuing." >&2
        exit 1
    fi
}
```

## 13.8 Script Portability

Writing scripts that work across different environments.

### POSIX Compatibility

```bash
#!/bin/sh
# POSIX-compatible script (not PSH-specific)

# Use POSIX features only
if [ -f "$file" ]; then
    echo "File exists"
fi

# Avoid bash/PSH-specific features
# No [[ ]] operator
# No (( )) arithmetic
# No arrays
# No local keyword (use subshells)
```

### Environment Detection

```bash
#!/usr/bin/env psh

# Detect operating system
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$NAME"
    elif [ "$(uname)" = "Darwin" ]; then
        echo "macOS"
    elif [ "$(uname)" = "Linux" ]; then
        echo "Linux"
    else
        echo "Unknown"
    fi
}

# Detect shell
detect_shell() {
    case "$SHELL" in
        */bash) echo "bash" ;;
        */zsh)  echo "zsh" ;;
        */psh)  echo "psh" ;;
        *)      echo "unknown" ;;
    esac
}

# Platform-specific code
OS=$(detect_os)
case "$OS" in
    macOS)
        # macOS specific commands
        alias ls='ls -G'
        ;;
    Linux)
        # Linux specific commands
        alias ls='ls --color=auto'
        ;;
esac
```

### Path Handling

```bash
#!/usr/bin/env psh

# Portable path construction
join_path() {
    local IFS="/"
    echo "$*"
}

# Get script directory portably
get_script_dir() {
    local source="${BASH_SOURCE[0]}"  # PSH: use $0
    local dir="$(cd "$(dirname "$0")" && pwd)"
    echo "$dir"
}

# Find command in PATH
find_command() {
    local cmd="$1"
    command -v "$cmd" 2>/dev/null
}

# Ensure PATH includes common locations
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
```

## 13.9 RC Files and Initialization

PSH supports initialization files for customizing the shell environment.

### RC File Loading

```bash
# Default RC file location
~/.pshrc

# RC file is loaded for:
- Interactive shells
- When explicitly sourced

# RC file is NOT loaded for:
- Non-interactive scripts
- When using --norc option
```

### Sample .pshrc

```bash
# ~/.pshrc - PSH initialization file

# Shell options (when implemented)
# set -o vi          # Vi key bindings
# set -o ignoreeof   # Prevent Ctrl-D logout

# Environment variables
export EDITOR="vim"
export PAGER="less"
export PATH="$HOME/bin:$PATH"

# Aliases
alias ll='ls -la'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias df='df -h'
alias du='du -h'

# Prompt customization
export PS1='\[\e[32m\]\u@\h\[\e[0m\]:\[\e[34m\]\w\[\e[0m\]\$ '
export PS2='\[\e[33m\]> \[\e[0m\]'

# Functions
mkcd() {
    mkdir -p "$1" && cd "$1"
}

backup() {
    cp "$1" "$1.bak.$(date +%Y%m%d_%H%M%S)"
}

# Source additional configurations
if [ -d "$HOME/.psh.d" ]; then
    for file in "$HOME/.psh.d"/*.sh; do
        [ -f "$file" ] && source "$file"
    done
fi

# Machine-specific settings
if [ -f "$HOME/.pshrc.local" ]; then
    source "$HOME/.pshrc.local"
fi

# Welcome message
echo "Welcome to PSH - Python Shell"
echo "Today is $(date '+%A, %B %d, %Y')"
```

### Custom RC Files

```bash
# Use custom RC file
psh$ psh --rcfile ~/myconfig.sh

# Skip RC file loading
psh$ psh --norc

# Check if running interactively in RC file
if [ -n "$PS1" ]; then
    # Interactive shell settings
    echo "Interactive mode"
else
    # Non-interactive settings
    :
fi
```

## 13.10 Practical Script Examples

### System Backup Script

```bash
#!/usr/bin/env psh
#
# backup.sh - System backup script
# Usage: backup.sh [-v] [-c] <source> <destination>

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERBOSE=false
COMPRESS=false

# Functions
usage() {
    cat << EOF
Usage: $0 [options] <source> <destination>

Options:
    -v, --verbose    Verbose output
    -c, --compress   Compress backup
    -h, --help       Show this help

Examples:
    $0 /home/user /backup/
    $0 -c /etc /backup/configs/
EOF
}

log() {
    [ "$VERBOSE" = true ] && echo "[$(date '+%H:%M:%S')] $*"
}

perform_backup() {
    local source="$1"
    local dest="$2"
    local backup_name="backup_${TIMESTAMP}"
    
    # Validate source
    if [ ! -e "$source" ]; then
        echo "Error: Source '$source' does not exist" >&2
        return 1
    fi
    
    # Create destination
    mkdir -p "$dest" || {
        echo "Error: Cannot create destination directory" >&2
        return 1
    }
    
    log "Starting backup of $source"
    
    if [ "$COMPRESS" = true ]; then
        # Compressed backup
        backup_file="$dest/${backup_name}.tar.gz"
        log "Creating compressed backup: $backup_file"
        
        tar -czf "$backup_file" -C "$(dirname "$source")" "$(basename "$source")" || {
            echo "Error: Backup failed" >&2
            return 1
        }
        
        log "Compressed size: $(du -h "$backup_file" | cut -f1)"
    else
        # Regular copy
        backup_dir="$dest/$backup_name"
        log "Copying to: $backup_dir"
        
        cp -r "$source" "$backup_dir" || {
            echo "Error: Backup failed" >&2
            return 1
        }
        
        log "Backup size: $(du -sh "$backup_dir" | cut -f1)"
    fi
    
    echo "Backup completed successfully"
    return 0
}

# Main script
main() {
    # Parse options
    while [ $# -gt 0 ]; do
        case "$1" in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -c|--compress)
                COMPRESS=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                echo "Unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Check arguments
    if [ $# -ne 2 ]; then
        echo "Error: Source and destination required" >&2
        usage >&2
        exit 1
    fi
    
    # Perform backup
    perform_backup "$1" "$2"
}

# Run main
main "$@"
```

### Log File Analyzer

```bash
#!/usr/bin/env psh
#
# analyze_logs.sh - Analyze log files for patterns

# Configuration
DEFAULT_LINES=100
DEFAULT_PATTERN="ERROR|WARN"

# Functions
analyze_file() {
    local file="$1"
    local pattern="$2"
    local lines="$3"
    
    echo "=== Analyzing: $file ==="
    echo "Pattern: $pattern"
    echo
    
    # Count occurrences
    local count=$(grep -c "$pattern" "$file" 2>/dev/null || echo 0)
    echo "Total matches: $count"
    
    if [ $count -gt 0 ]; then
        echo
        echo "Recent matches (last $lines):"
        grep "$pattern" "$file" | tail -n "$lines" | while IFS= read -r line; do
            echo "  $line"
        done
        
        echo
        echo "Summary by hour:"
        grep "$pattern" "$file" | \
        awk '{print substr($0, 1, 13)}' | \
        sort | uniq -c | tail -10
    fi
    
    echo
}

# Main
main() {
    local pattern="$DEFAULT_PATTERN"
    local lines="$DEFAULT_LINES"
    local files=()
    
    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            -p|--pattern)
                pattern="$2"
                shift 2
                ;;
            -n|--lines)
                lines="$2"
                shift 2
                ;;
            -h|--help)
                cat << EOF
Usage: $0 [options] <logfile> [logfile...]

Options:
    -p, --pattern <regex>  Search pattern (default: ERROR|WARN)
    -n, --lines <num>      Number of recent lines to show (default: 100)
    -h, --help            Show this help

Examples:
    $0 /var/log/syslog
    $0 -p "CRITICAL|FATAL" -n 50 app.log
    $0 -p "connection refused" *.log
EOF
                exit 0
                ;;
            -*)
                echo "Unknown option: $1" >&2
                exit 1
                ;;
            *)
                files+=("$1")
                shift
                ;;
        esac
    done
    
    # Check for files
    if [ ${#files[@]} -eq 0 ]; then
        echo "Error: No log files specified" >&2
        exit 1
    fi
    
    # Analyze each file
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            analyze_file "$file" "$pattern" "$lines"
        else
            echo "Warning: File not found: $file" >&2
        fi
    done
}

main "$@"
```

### Service Manager Script

```bash
#!/usr/bin/env psh
#
# service_manager.sh - Manage application services

# Configuration
SERVICE_DIR="/opt/services"
PID_DIR="/var/run"
LOG_DIR="/var/log/services"

# Service functions
start_service() {
    local service="$1"
    local pid_file="$PID_DIR/$service.pid"
    
    # Check if already running
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo "Service $service is already running"
        return 0
    fi
    
    echo "Starting service: $service"
    
    # Start service in background
    case "$service" in
        web)
            cd "$SERVICE_DIR/web" && \
            ./server.py > "$LOG_DIR/web.log" 2>&1 &
            echo $! > "$pid_file"
            ;;
        database)
            cd "$SERVICE_DIR/db" && \
            ./database --daemon --log "$LOG_DIR/db.log" &
            echo $! > "$pid_file"
            ;;
        *)
            echo "Unknown service: $service" >&2
            return 1
            ;;
    esac
    
    # Verify startup
    sleep 2
    if kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo "Service $service started successfully (PID: $(cat "$pid_file"))"
        return 0
    else
        echo "Failed to start service $service" >&2
        rm -f "$pid_file"
        return 1
    fi
}

stop_service() {
    local service="$1"
    local pid_file="$PID_DIR/$service.pid"
    
    if [ ! -f "$pid_file" ]; then
        echo "Service $service is not running"
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Stopping service: $service (PID: $pid)"
        kill "$pid"
        
        # Wait for graceful shutdown
        local count=0
        while [ $count -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if needed
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force stopping service"
            kill -9 "$pid"
        fi
        
        rm -f "$pid_file"
        echo "Service $service stopped"
    else
        echo "Service $service is not running (stale PID file)"
        rm -f "$pid_file"
    fi
}

status_service() {
    local service="$1"
    local pid_file="$PID_DIR/$service.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Service $service is running (PID: $pid)"
            return 0
        else
            echo "Service $service is not running (stale PID file)"
            return 1
        fi
    else
        echo "Service $service is not running"
        return 1
    fi
}

# Main
case "${1:-help}" in
    start)
        start_service "$2"
        ;;
    stop)
        stop_service "$2"
        ;;
    restart)
        stop_service "$2"
        sleep 2
        start_service "$2"
        ;;
    status)
        if [ -z "$2" ]; then
            # Show all services
            for service in web database; do
                status_service "$service"
            done
        else
            status_service "$2"
        fi
        ;;
    help|*)
        cat << EOF
Usage: $0 {start|stop|restart|status} [service]

Services:
    web       Web application server
    database  Database server

Examples:
    $0 start web
    $0 stop database
    $0 status
EOF
        [ "$1" != "help" ] && exit 1
        ;;
esac
```

## Summary

Shell scripting in PSH provides powerful automation capabilities:

1. **Script Creation**: Text files with shell commands and shebang lines
2. **Execution Methods**: Direct execution, command strings, stdin, sourcing
3. **Arguments**: Positional parameters and special variables for flexibility
4. **Organization**: Headers, functions, error handling for maintainability
5. **I/O Handling**: User input, file operations, logging capabilities
6. **Debugging**: Debug modes, tracing, error diagnosis tools
7. **Portability**: Environment detection and path handling
8. **RC Files**: Shell customization and initialization
9. **Practical Examples**: Real-world scripts for common tasks

Key concepts:
- Scripts are programs written in shell language
- Shebang line determines the interpreter
- Arguments are accessible via positional parameters
- Functions and organization improve maintainability
- Error handling is crucial for robust scripts
- Debug features help identify and fix issues
- RC files customize the shell environment

Shell scripting enables automation of repetitive tasks, system administration, deployment processes, and complex workflows, making it an essential skill for effective command-line usage.

---

[← Previous: Chapter 12 - Functions](12_functions.md) | [Next: Chapter 14 - Interactive Features →](14_interactive_features.md)