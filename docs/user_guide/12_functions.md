# Chapter 12: Functions

Functions in PSH allow you to define reusable blocks of code that can accept parameters and return values. PSH supports both POSIX-style function definitions and bash-style function syntax, along with local variables, recursion, and proper parameter handling.

## 12.1 Function Definition Syntax

PSH supports multiple ways to define functions, providing flexibility and compatibility with different shell standards.

### POSIX-Style Functions

```bash
# Basic function definition
psh$ greet() {
>     echo "Hello, World!"
> }
psh$ greet
Hello, World!

# Function with commands
psh$ backup_files() {
>     cp *.txt backup/
>     echo "Files backed up"
> }

# Single-line function
psh$ current_time() { date +%H:%M:%S; }
psh$ current_time
14:30:25

# Function with multiple commands
psh$ system_info() {
>     echo "System Information:"
>     echo "Hostname: $(hostname)"
>     echo "User: $(whoami)"
>     echo "Date: $(date)"
> }
```

### Function Keyword Syntax

```bash
# Bash-style function keyword (without parentheses)
psh$ function greet {
>     echo "Hello from function keyword!"
> }

# Function keyword with parentheses
psh$ function greet() {
>     echo "Hello with parentheses!"
> }

# Complex function with function keyword
psh$ function process_logs {
>     local logdir="/var/log"
>     for file in "$logdir"/*.log; do
>         echo "Processing $file"
>     done
> }
```

### Multi-line Function Definitions

```bash
# Complex function spanning multiple lines
psh$ create_user() {
>     local username="$1"
>     local home_dir="/home/$username"
>
>     if [ -z "$username" ]; then
>         echo "Usage: create_user <username>" >&2
>         return 1
>     fi
>
>     echo "Creating user $username with home directory $home_dir"
> }

# Function with here document
psh$ generate_config() {
>     local service="$1"
>     cat << EOF
> # Configuration for $service
> # Generated on $(date)
>
> [main]
> enabled=true
> debug=false
> EOF
> }
```

## 12.2 Function Parameters

Functions accept parameters and access them through positional parameters.

### Basic Parameter Usage

```bash
# Function with parameters
psh$ greet() {
>     echo "Hello, $1!"
> }
psh$ greet Alice
Hello, Alice!

# Multiple parameters
psh$ add_numbers() {
>     local result=$(($1 + $2))
>     echo "$1 + $2 = $result"
> }
psh$ add_numbers 5 3
5 + 3 = 8

# Parameter validation
psh$ copy_file() {
>     if [ $# -ne 2 ]; then
>         echo "Usage: copy_file <source> <destination>" >&2
>         return 1
>     fi
>
>     cp "$1" "$2"
>     echo "Copied $1 to $2"
> }
psh$ copy_file file1.txt file2.txt
Copied file1.txt to file2.txt
```

### Parameter Variables

```bash
# All parameter variables
psh$ show_params() {
>     echo "Function name: $0"
>     echo "First parameter: $1"
>     echo "Second parameter: $2"
>     echo "All parameters: $*"
>     echo "All parameters (array): $@"
>     echo "Number of parameters: $#"
> }
psh$ show_params hello world test
Function name: show_params
First parameter: hello
Second parameter: world
All parameters: hello world test
All parameters (array): hello world test
Number of parameters: 3
```

> **Note:** In PSH, `$0` inside a function returns the function name. In bash, `$0` returns the shell or script name instead. This is a behavioral difference to be aware of when porting scripts.

```bash
# Shifting parameters
psh$ process_all() {
>     local count=1
>     while [ $# -gt 0 ]; do
>         echo "Parameter $count: $1"
>         shift
>         count=$((count + 1))
>     done
> }
psh$ process_all one two three
Parameter 1: one
Parameter 2: two
Parameter 3: three

# Default parameter values
psh$ greet_user() {
>     local name="${1:-Guest}"
>     local greeting="${2:-Hello}"
>     echo "$greeting, $name!"
> }
psh$ greet_user
Hello, Guest!
psh$ greet_user Alice Hi
Hi, Alice!
```

### Advanced Parameter Handling

```bash
# Variable number of arguments
psh$ calculate_sum() {
>     local sum=0
>     for num in "$@"; do
>         sum=$((sum + num))
>     done
>     echo "Sum: $sum"
> }
psh$ calculate_sum 1 2 3 4 5
Sum: 15

# Options and arguments
psh$ backup_directory() {
>     local verbose=false
>     local compress=false
>     local target_dir=""
>
>     # Parse options
>     while [ $# -gt 0 ]; do
>         case "$1" in
>             -v|--verbose)
>                 verbose=true
>                 shift
>                 ;;
>             -c|--compress)
>                 compress=true
>                 shift
>                 ;;
>             -*)
>                 echo "Unknown option: $1" >&2
>                 return 1
>                 ;;
>             *)
>                 target_dir="$1"
>                 break
>                 ;;
>         esac
>     done
>
>     if [ -z "$target_dir" ]; then
>         echo "Usage: backup_directory [-v] [-c] <directory>" >&2
>         return 1
>     fi
>
>     [ "$verbose" = true ] && echo "Backing up $target_dir"
>
>     if [ "$compress" = true ]; then
>         tar -czf "${target_dir}_backup.tar.gz" "$target_dir"
>         [ "$verbose" = true ] && echo "Created compressed backup"
>     else
>         cp -r "$target_dir" "${target_dir}_backup"
>         [ "$verbose" = true ] && echo "Created directory backup"
>     fi
> }
```

## 12.3 Local Variables

PSH supports local variables that are scoped to functions, providing proper variable isolation.

### Basic Local Variables

```bash
# Local variable isolation
psh$ global_var="global value"
psh$ test_local() {
>     local global_var="local value"
>     echo "Inside function: $global_var"
> }
psh$ test_local
Inside function: local value
psh$ echo "Outside function: $global_var"
Outside function: global value

# Local without assignment
psh$ demo_local() {
>     local temp_var
>     temp_var="function-scoped"
>     echo "Temp var: $temp_var"
> }
psh$ demo_local
Temp var: function-scoped
psh$ echo "Outside: $temp_var"
Outside:

# Multiple local declarations
psh$ configure_app() {
>     local config_file="/etc/app.conf"
>     local log_level="info"
>     local debug_mode=false
>
>     echo "Config: $config_file"
>     echo "Log level: $log_level"
>     echo "Debug: $debug_mode"
> }
```

### Local Variable Inheritance

```bash
# Nested function access to outer locals (dynamic scoping)
psh$ outer_function() {
>     local outer_var="from outer"
>
>     inner_function() {
>         echo "Inner sees outer: $outer_var"
>     }
>
>     inner_function
>     echo "Outer var: $outer_var"
> }
psh$ outer_function
Inner sees outer: from outer
Outer var: from outer
```

### Local Arrays

```bash
# Local array handling
psh$ process_list() {
>     local -a files=("$@")
>     local count=${#files[@]}
>
>     echo "Processing $count files:"
>     for file in "${files[@]}"; do
>         echo "  - $file"
>     done
> }
psh$ process_list a.txt b.txt c.txt
Processing 3 files:
  - a.txt
  - b.txt
  - c.txt
```

## 12.4 Return Values and Exit Status

Functions can return values using the return statement and exit status codes.

### Return Statement

```bash
# Basic return
psh$ is_file() {
>     if [ -f "$1" ]; then
>         return 0  # Success
>     else
>         return 1  # Failure
>     fi
> }
psh$ if is_file "/etc/passwd"; then
>     echo "File exists"
> fi
File exists

# Return with status code
psh$ divide() {
>     if [ "$2" -eq 0 ]; then
>         echo "Error: Division by zero" >&2
>         return 2
>     fi
>     echo $(($1 / $2))
>     return 0
> }
psh$ divide 10 2
5
psh$ echo "Exit status: $?"
Exit status: 0

# Early return
psh$ validate_user() {
>     local username="$1"
>
>     [ -z "$username" ] && {
>         echo "Username required" >&2
>         return 1
>     }
>
>     [ ${#username} -lt 3 ] && {
>         echo "Username too short" >&2
>         return 2
>     }
>
>     echo "Valid username: $username"
>     return 0
> }
```

### Output Capture

```bash
# Function output capture
psh$ get_current_user() {
>     whoami
> }
psh$ user=$(get_current_user)
psh$ echo "Current user is: $user"
Current user is: alice

# Complex output function
psh$ system_summary() {
>     echo "=== System Summary ==="
>     echo "Hostname: $(hostname)"
>     echo "User: $(whoami)"
>     echo "Date: $(date)"
> }
psh$ summary=$(system_summary)
psh$ echo "$summary"

# Mixed output and return
psh$ check_service() {
>     local service="$1"
>
>     if command -v "$service" >/dev/null 2>&1; then
>         echo "$service is available"
>         return 0
>     else
>         echo "$service is not available"
>         return 1
>     fi
> }
```

## 12.5 Function Management

PSH provides commands to manage functions: listing, displaying, and removing them.

### Listing Functions

```bash
# List all function definitions
psh$ declare -f
hello() {
    echo "Hello, $1!"
}
greet() {
    echo "Greetings!"
}

# List function names only
psh$ declare -F
declare -f greet
declare -f hello

# Show specific function definition
psh$ declare -f greet
greet() {
    echo "Greetings!"
}

# Check if specific name is a function
psh$ declare -F greet
declare -f greet

# Check function type
psh$ type greet
greet is a function
```

### Using typeset for Function Management

The `typeset` builtin provides Korn shell (ksh) compatibility and works identically to `declare`:

```bash
# Display all functions with their definitions
psh$ myfunc() { echo "test"; }
psh$ typeset -f myfunc
myfunc () {
    echo "test"
}

# Display only function names
psh$ typeset -F
declare -f myfunc
```

### Removing Functions

```bash
# Remove function
psh$ unset -f greet

# Verify removal
psh$ greet
psh: greet: command not found

# Safe function removal
psh$ remove_function() {
>     local func_name="$1"
>     if declare -f "$func_name" >/dev/null 2>&1; then
>         unset -f "$func_name"
>         echo "Function $func_name removed"
>     else
>         echo "Function $func_name not found"
>     fi
> }
```

### Function Introspection

```bash
# Check if a name is a function
psh$ is_function() {
>     declare -f "$1" >/dev/null 2>&1
> }
psh$ myfunc() { echo "test"; }
psh$ if is_function myfunc; then
>     echo "myfunc is a function"
> fi
myfunc is a function
```

## 12.6 Advanced Function Patterns

### Recursive Functions

```bash
# Factorial calculation
psh$ factorial() {
>     local n="$1"
>     if [ "$n" -le 1 ]; then
>         echo 1
>     else
>         local prev=$(factorial $((n - 1)))
>         echo $((n * prev))
>     fi
> }
psh$ factorial 5
120

# Fibonacci sequence
psh$ fibonacci() {
>     local n="$1"
>     if [ "$n" -le 1 ]; then
>         echo "$n"
>     else
>         local a=$(fibonacci $((n - 1)))
>         local b=$(fibonacci $((n - 2)))
>         echo $((a + b))
>     fi
> }
psh$ fibonacci 10
55

# Directory tree traversal
psh$ list_files_recursive() {
>     local dir="$1"
>     local indent="${2:-}"
>
>     for item in "$dir"/*; do
>         [ -e "$item" ] || continue
>         echo "$indent$(basename "$item")"
>         if [ -d "$item" ]; then
>             list_files_recursive "$item" "$indent  "
>         fi
>     done
> }
```

### Function Libraries

```bash
# Math library functions
abs() {
    local num="$1"
    echo $((num < 0 ? -num : num))
}

max() {
    local a="$1" b="$2"
    echo $((a > b ? a : b))
}

min() {
    local a="$1" b="$2"
    echo $((a < b ? a : b))
}

average() {
    local sum=0 count=0
    for num in "$@"; do
        sum=$((sum + num))
        count=$((count + 1))
    done
    echo $((sum / count))
}

# String library functions
uppercase() {
    echo "$1" | tr '[:lower:]' '[:upper:]'
}

lowercase() {
    echo "$1" | tr '[:upper:]' '[:lower:]'
}

string_length() {
    echo ${#1}
}
```

### Function Wrappers

```bash
# Timing wrapper
psh$ time_function() {
>     local func_name="$1"
>     shift
>
>     local start_time=$(date +%s)
>     "$func_name" "$@"
>     local result=$?
>     local end_time=$(date +%s)
>
>     echo "Function $func_name took $((end_time - start_time)) seconds" >&2
>     return $result
> }

# Logging wrapper
psh$ log_function() {
>     local func_name="$1"
>     shift
>
>     echo "[$(date)] Calling $func_name with args: $*" >&2
>     "$func_name" "$@"
>     local result=$?
>     echo "[$(date)] Function $func_name returned: $result" >&2
>     return $result
> }

# Retry wrapper
psh$ retry_function() {
>     local max_attempts="$1"
>     local func_name="$2"
>     shift 2
>
>     local attempt=1
>     while [ $attempt -le $max_attempts ]; do
>         if "$func_name" "$@"; then
>             return 0
>         fi
>         echo "Attempt $attempt failed, retrying..." >&2
>         attempt=$((attempt + 1))
>         sleep 1
>     done
>
>     echo "All $max_attempts attempts failed" >&2
>     return 1
> }
```

## 12.7 Practical Examples

### Configuration Management Functions

```bash
#!/usr/bin/env psh
# Configuration management library

CONFIG_FILE="/etc/myapp/config.conf"

# Read configuration value
get_config() {
    local section="$1"
    local key="$2"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Configuration file not found" >&2
        return 1
    fi

    awk -v section="[$section]" -v key="$key" '
        $0 == section { in_section = 1; next }
        /^\[/ { in_section = 0; next }
        in_section && $0 ~ "^" key "=" {
            split($0, parts, "=")
            print parts[2]
            exit
        }
    ' "$CONFIG_FILE"
}

# Validate configuration
validate_config() {
    local errors=0

    echo "Validating configuration..."

    for section in database server logging; do
        if [ ! -f "$CONFIG_FILE" ] || [ -z "$(grep "^\[$section\]" "$CONFIG_FILE")" ]; then
            echo "Error: Missing section [$section]" >&2
            errors=$((errors + 1))
        fi
    done

    if [ $errors -eq 0 ]; then
        echo "Configuration is valid"
        return 0
    else
        echo "Configuration has $errors errors"
        return 1
    fi
}

# Main function for command-line usage
main() {
    case "${1:-help}" in
        get)
            if [ $# -ne 3 ]; then
                echo "Usage: $0 get <section> <key>"
                return 1
            fi
            get_config "$2" "$3"
            ;;
        validate)
            validate_config
            ;;
        help)
            echo "Usage: $0 {get|validate|help}"
            ;;
        *)
            echo "Unknown command: $1"
            return 1
            ;;
    esac
}

main "$@"
```

### Network Monitoring Functions

```bash
#!/usr/bin/env psh
# Network monitoring functions

PING_TIMEOUT=3
PING_COUNT=1
LOG_FILE="/var/log/network_monitor.log"

log_message() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Check if host is reachable
ping_host() {
    local host="$1"
    local timeout="${2:-$PING_TIMEOUT}"
    local count="${3:-$PING_COUNT}"

    if ping -c "$count" -W "$timeout" "$host" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check TCP port
check_port() {
    local host="$1"
    local port="$2"
    local timeout="${3:-5}"

    if command -v nc >/dev/null; then
        nc -z -w "$timeout" "$host" "$port" >/dev/null 2>&1
    else
        echo "No network tools available" >&2
        return 1
    fi
}

# Monitor single host
monitor_host() {
    local host="$1"
    local services="${2:-ping}"
    local interval="${3:-60}"

    log_message "INFO" "Starting monitoring for $host"

    while true; do
        local status="UP"

        for service in $services; do
            case "$service" in
                ping)
                    if [ "$(ping_host "$host")" ]; then
                        :  # OK
                    else
                        status="DOWN"
                    fi
                    ;;
                ssh)
                    if [ "$(check_port "$host" 22)" ]; then
                        :
                    else
                        status="DEGRADED"
                    fi
                    ;;
            esac
        done

        if [ "$status" = "UP" ]; then
            log_message "INFO" "$host is $status"
        else
            log_message "ERROR" "$host is $status"
        fi

        sleep "$interval"
    done
}

# Main
case "${1:-help}" in
    ping)
        ping_host "$2" && echo "UP" || echo "DOWN"
        ;;
    port)
        check_port "$2" "$3" && echo "OPEN" || echo "CLOSED"
        ;;
    monitor)
        monitor_host "$2" "$3" "$4"
        ;;
    help)
        echo "Usage: $0 {ping <host>|port <host> <port>|monitor <host> [services] [interval]}"
        ;;
    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
```

## Summary

Functions in PSH provide powerful code organization and reusability:

1. **Definition Syntax**: Both POSIX `name()` and bash `function name` styles
2. **Parameters**: Positional parameters ($1, $2, etc.) with special variables ($#, $@, $*)
3. **Local Variables**: Function-scoped variables with `local` keyword, including local arrays (`local -a`)
4. **Return Values**: Exit status with `return` command and output capture with `$()`
5. **Function Management**: List with `declare -f`/`typeset -f`, names with `declare -F`, remove with `unset -f`, type check with `type`
6. **Recursion**: Full support for recursive functions with proper local variable scoping
7. **Advanced Patterns**: Function libraries, wrappers, and option parsing

Key concepts:
- Functions create isolated variable environments with `local`
- Local variables prevent global namespace pollution
- Parameter handling enables flexible function interfaces
- Return statements control function exit status (0-255)
- Output capture with `$()` provides return-value-like semantics
- Functions can be recursive with proper base cases
- `$0` in PSH functions returns the function name (differs from bash)

Functions are essential for building maintainable shell scripts and creating reusable code libraries for system administration, automation, and data processing tasks.

---

[← Previous: Chapter 11 - Control Structures](11_control_structures.md) | [Next: Chapter 13 - Shell Scripts →](13_shell_scripts.md)
