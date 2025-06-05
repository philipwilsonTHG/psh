# Chapter 12: Functions

Functions in PSH allow you to define reusable blocks of code that can accept parameters and return values. PSH supports both POSIX-style function definitions and bash-style function syntax, along with local variables and proper parameter handling.

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
# Bash-style function keyword
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
>         tail -10 "$file"
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
>     if id "$username" >/dev/null 2>&1; then
>         echo "User $username already exists" >&2
>         return 1
>     fi
>     
>     useradd -m -d "$home_dir" "$username"
>     echo "User $username created with home directory $home_dir"
> }

# Function with here document
psh$ generate_config() {
>     local service="$1"
>     cat > "/etc/$service.conf" << EOF
> # Configuration for $service
> # Generated on $(date)
> 
> [main]
> enabled=true
> debug=false
> 
> [logging]
> level=info
> file=/var/log/$service.log
> EOF
>     echo "Configuration created for $service"
> }
```

## 12.2 Function Parameters

Functions can accept parameters and access them through positional parameters.

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
>         if [[ "$num" =~ ^[0-9]+$ ]]; then
>             sum=$((sum + num))
>         else
>             echo "Warning: '$num' is not a number" >&2
>         fi
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
# Nested function access to outer locals
psh$ outer_function() {
>     local outer_var="from outer"
>     
>     inner_function() {
>         local inner_var="from inner"
>         echo "Inner sees outer: $outer_var"
>         echo "Inner var: $inner_var"
>     }
>     
>     inner_function
>     echo "Outer var: $outer_var"
>     # This would be empty: echo "Outer sees inner: $inner_var"
> }
psh$ outer_function
Inner sees outer: from outer
Inner var: from inner
Outer var: from outer

# Local variable shadowing
psh$ shadowing_demo() {
>     local var="outer scope"
>     echo "Outer: $var"
>     
>     {
>         local var="inner scope"
>         echo "Inner: $var"
>     }
>     
>     echo "After inner: $var"
> }
psh$ shadowing_demo
Outer: outer scope
Inner: inner scope
After inner: outer scope
```

### Local Arrays and Special Variables

```bash
# Local array handling (when arrays are supported)
psh$ process_list() {
>     local -a files=("$@")
>     local count=${#files[@]}
>     
>     echo "Processing $count files:"
>     for file in "${files[@]}"; do
>         echo "  - $file"
>     done
> }

# Local parameters
psh$ function_with_locals() {
>     local func_name="$0"
>     local first_arg="$1"
>     local all_args=("$@")
>     
>     echo "Function: $func_name"
>     echo "First: $first_arg"
>     echo "Count: $#"
> }
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
>     echo "Uptime: $(uptime | cut -d',' -f1)"
>     echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
>     echo "Users: $(who | wc -l)"
>     echo "Disk: $(df -h / | tail -1 | awk '{print $5}')"
> }
psh$ summary=$(system_summary)
psh$ echo "$summary"

# Mixed output and return
psh$ check_service() {
>     local service="$1"
>     
>     if systemctl is-active "$service" >/dev/null 2>&1; then
>         echo "$service is running"
>         return 0
>     else
>         echo "$service is not running"
>         return 1
>     fi
> }
```

## 12.5 Function Management

PSH provides commands to manage functions: listing, displaying, and removing them.

### Listing Functions

```bash
# List all functions
psh$ declare -f

# Show specific function
psh$ declare -f greet

# Alternative: list functions with type
psh$ type greet
greet is a function

# Check if name is a function
psh$ is_function() {
>     declare -f "$1" >/dev/null 2>&1
> }
psh$ if is_function greet; then
>     echo "greet is a function"
> fi
```

### Removing Functions

```bash
# Remove function
psh$ unset -f greet

# Remove multiple functions
psh$ unset -f func1 func2 func3

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

### Function Information

```bash
# Function introspection
psh$ function_info() {
>     local func_name="$1"
>     
>     if declare -f "$func_name" >/dev/null 2>&1; then
>         echo "Function: $func_name"
>         echo "Type: $(type -t "$func_name")"
>         echo "Definition:"
>         declare -f "$func_name"
>     else
>         echo "Function $func_name not found"
>         return 1
>     fi
> }
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
>         [ ! -e "$item" ] && continue
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
psh$ # math_lib.sh
psh$ abs() {
>     local num="$1"
>     echo $((num < 0 ? -num : num))
> }

psh$ max() {
>     local a="$1" b="$2"
>     echo $((a > b ? a : b))
> }

psh$ min() {
>     local a="$1" b="$2"
>     echo $((a < b ? a : b))
> }

psh$ average() {
>     local sum=0 count=0
>     for num in "$@"; do
>         sum=$((sum + num))
>         count=$((count + 1))
>     done
>     echo $((sum / count))
> }

# String library functions
psh$ # string_lib.sh
psh$ uppercase() {
>     echo "$1" | tr '[:lower:]' '[:upper:]'
> }

psh$ lowercase() {
>     echo "$1" | tr '[:upper:]' '[:lower:]'
> }

psh$ trim() {
>     local str="$1"
>     # Remove leading whitespace
>     str="${str#"${str%%[![:space:]]*}"}"
>     # Remove trailing whitespace
>     str="${str%"${str##*[![:space:]]}"}"
>     echo "$str"
> }

psh$ string_length() {
>     echo ${#1}
> }
```

### Function Decorators and Wrappers

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

# Error handling wrapper
psh$ safe_function() {
>     local func_name="$1"
>     shift
>     
>     if ! "$func_name" "$@"; then
>         echo "Error in function $func_name" >&2
>         return 1
>     fi
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

# Global configuration
CONFIG_DIR="/etc/myapp"
CONFIG_FILE="$CONFIG_DIR/config.conf"
BACKUP_DIR="$CONFIG_DIR/backups"

# Initialize configuration
init_config() {
    local force=false
    
    # Parse options
    while [ $# -gt 0 ]; do
        case "$1" in
            --force) force=true; shift ;;
            *) echo "Unknown option: $1" >&2; return 1 ;;
        esac
    done
    
    # Check if config exists
    if [ -f "$CONFIG_FILE" ] && [ "$force" = false ]; then
        echo "Configuration already exists. Use --force to overwrite."
        return 1
    fi
    
    # Create directories
    mkdir -p "$CONFIG_DIR" "$BACKUP_DIR"
    
    # Create default configuration
    cat > "$CONFIG_FILE" << 'EOF'
# MyApp Configuration
# Generated on $(date)

[database]
host=localhost
port=5432
name=myapp
user=myapp

[server]
host=0.0.0.0
port=8080
workers=4

[logging]
level=info
file=/var/log/myapp.log
EOF
    
    echo "Configuration initialized: $CONFIG_FILE"
}

# Read configuration value
get_config() {
    local section="$1"
    local key="$2"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Configuration file not found" >&2
        return 1
    fi
    
    # Find section and extract value
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

# Set configuration value
set_config() {
    local section="$1"
    local key="$2"
    local value="$3"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Configuration file not found" >&2
        return 1
    fi
    
    # Backup current config
    backup_config
    
    # Create temporary file with updated config
    local temp_file=$(mktemp)
    awk -v section="[$section]" -v key="$key" -v value="$value" '
        $0 == section { 
            in_section = 1
            print
            next
        }
        /^\[/ && in_section {
            if (!found) print key "=" value
            in_section = 0
            found = 0
        }
        in_section && $0 ~ "^" key "=" {
            print key "=" value
            found = 1
            next
        }
        { print }
        END {
            if (in_section && !found) print key "=" value
        }
    ' "$CONFIG_FILE" > "$temp_file"
    
    # Replace original with updated config
    mv "$temp_file" "$CONFIG_FILE"
    echo "Updated $section.$key = $value"
}

# Backup configuration
backup_config() {
    if [ -f "$CONFIG_FILE" ]; then
        local backup_name="config_$(date +%Y%m%d_%H%M%S).conf"
        cp "$CONFIG_FILE" "$BACKUP_DIR/$backup_name"
        echo "Configuration backed up: $backup_name"
    fi
}

# List configuration
list_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Configuration file not found" >&2
        return 1
    fi
    
    echo "=== Configuration ==="
    cat "$CONFIG_FILE" | while read line; do
        case "$line" in
            \#*) echo "$line" ;;  # Comments
            \[*\]) echo; echo "$line" ;;  # Sections
            *=*) echo "  $line" ;;  # Key-value pairs
            "") echo ;;  # Empty lines
        esac
    done
}

# Validate configuration
validate_config() {
    local errors=0
    
    echo "Validating configuration..."
    
    # Check required sections
    for section in database server logging; do
        if ! grep -q "^\[$section\]" "$CONFIG_FILE"; then
            echo "Error: Missing section [$section]" >&2
            errors=$((errors + 1))
        fi
    done
    
    # Check required keys
    local required_keys=(
        "database.host"
        "database.port"
        "server.port"
        "logging.level"
    )
    
    for key_path in "${required_keys[@]}"; do
        local section="${key_path%%.*}"
        local key="${key_path##*.}"
        local value=$(get_config "$section" "$key")
        
        if [ -z "$value" ]; then
            echo "Error: Missing required key $key_path" >&2
            errors=$((errors + 1))
        fi
    done
    
    # Validate port numbers
    for port_key in "database.port" "server.port"; do
        local section="${port_key%%.*}"
        local key="${port_key##*.}"
        local port=$(get_config "$section" "$key")
        
        if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
            echo "Error: Invalid port number for $port_key: $port" >&2
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
        init)
            shift
            init_config "$@"
            ;;
        get)
            if [ $# -ne 3 ]; then
                echo "Usage: $0 get <section> <key>"
                return 1
            fi
            get_config "$2" "$3"
            ;;
        set)
            if [ $# -ne 4 ]; then
                echo "Usage: $0 set <section> <key> <value>"
                return 1
            fi
            set_config "$2" "$3" "$4"
            ;;
        list)
            list_config
            ;;
        validate)
            validate_config
            ;;
        backup)
            backup_config
            ;;
        help)
            echo "Usage: $0 {init|get|set|list|validate|backup|help}"
            echo
            echo "Commands:"
            echo "  init [--force]      Initialize configuration"
            echo "  get <section> <key> Get configuration value"
            echo "  set <section> <key> <value> Set configuration value"
            echo "  list                List all configuration"
            echo "  validate            Validate configuration"
            echo "  backup              Backup current configuration"
            echo "  help                Show this help"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            return 1
            ;;
    esac
}

# Run main if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
```

### Network Monitoring Functions

```bash
#!/usr/bin/env psh
# Network monitoring functions

# Configuration
PING_TIMEOUT=3
PING_COUNT=1
LOG_FILE="/var/log/network_monitor.log"

# Logging function
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
        # Use netcat if available
        nc -z -w "$timeout" "$host" "$port" >/dev/null 2>&1
    elif command -v telnet >/dev/null; then
        # Fallback to telnet
        timeout "$timeout" telnet "$host" "$port" </dev/null >/dev/null 2>&1
    else
        # Use bash built-in if available
        timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null
    fi
}

# Check HTTP/HTTPS service
check_http() {
    local url="$1"
    local expected_code="${2:-200}"
    local timeout="${3:-10}"
    
    if command -v curl >/dev/null; then
        local response_code=$(curl -s -o /dev/null -w "%{http_code}" \
                             --max-time "$timeout" "$url" 2>/dev/null)
        [ "$response_code" = "$expected_code" ]
    elif command -v wget >/dev/null; then
        wget --timeout="$timeout" --spider -q "$url" 2>/dev/null
    else
        log_message "ERROR" "No HTTP client available (curl or wget)"
        return 1
    fi
}

# Monitor single host
monitor_host() {
    local host="$1"
    local services="${2:-ping}"
    local interval="${3:-60}"
    
    log_message "INFO" "Starting monitoring for $host (services: $services, interval: ${interval}s)"
    
    while true; do
        local status="UP"
        local failed_services=()
        
        # Check each service
        for service in $services; do
            case "$service" in
                ping)
                    if ! ping_host "$host"; then
                        status="DOWN"
                        failed_services+=("ping")
                    fi
                    ;;
                ssh)
                    if ! check_port "$host" 22; then
                        status="DEGRADED"
                        failed_services+=("ssh")
                    fi
                    ;;
                http)
                    if ! check_http "http://$host"; then
                        status="DEGRADED"
                        failed_services+=("http")
                    fi
                    ;;
                https)
                    if ! check_http "https://$host"; then
                        status="DEGRADED"
                        failed_services+=("https")
                    fi
                    ;;
                *)
                    log_message "WARN" "Unknown service: $service"
                    ;;
            esac
        done
        
        # Log status
        if [ "$status" = "UP" ]; then
            log_message "INFO" "$host is $status"
        else
            log_message "ERROR" "$host is $status (failed: ${failed_services[*]})"
        fi
        
        sleep "$interval"
    done
}

# Monitor multiple hosts
monitor_multiple() {
    local config_file="$1"
    
    if [ ! -f "$config_file" ]; then
        echo "Configuration file not found: $config_file" >&2
        return 1
    fi
    
    log_message "INFO" "Starting multiple host monitoring from $config_file"
    
    # Read configuration and start monitoring processes
    while IFS=: read -r host services interval; do
        # Skip comments and empty lines
        [[ "$host" =~ ^#.*$ ]] && continue
        [ -z "$host" ] && continue
        
        # Set defaults
        services="${services:-ping}"
        interval="${interval:-60}"
        
        # Start monitoring in background
        {
            monitor_host "$host" "$services" "$interval"
        } &
        
        log_message "INFO" "Started monitoring for $host (PID: $!)"
    done < "$config_file"
    
    # Wait for all background processes
    wait
}

# Generate monitoring report
generate_report() {
    local log_file="${1:-$LOG_FILE}"
    local hours="${2:-24}"
    
    if [ ! -f "$log_file" ]; then
        echo "Log file not found: $log_file" >&2
        return 1
    fi
    
    echo "=== Network Monitoring Report ==="
    echo "Period: Last $hours hours"
    echo "Generated: $(date)"
    echo
    
    # Extract recent logs
    local cutoff_time=$(date -d "$hours hours ago" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
                       date -v-${hours}H '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
    
    # Host status summary
    echo "=== Host Status Summary ==="
    awk -v cutoff="$cutoff_time" '
        $0 >= cutoff {
            if ($4 == "[ERROR]" && match($0, /([a-zA-Z0-9.-]+) is DOWN/, arr)) {
                down_hosts[arr[1]]++
            } else if ($4 == "[INFO]" && match($0, /([a-zA-Z0-9.-]+) is UP/, arr)) {
                up_hosts[arr[1]]++
            }
        }
        END {
            print "Hosts with issues:"
            for (host in down_hosts) {
                printf "  %s: %d DOWN events\n", host, down_hosts[host]
            }
            print ""
            print "Healthy hosts:"
            for (host in up_hosts) {
                if (!(host in down_hosts)) {
                    printf "  %s: stable\n", host
                }
            }
        }
    ' "$log_file"
    
    echo
    
    # Error summary
    echo "=== Error Summary ==="
    grep "\[ERROR\]" "$log_file" | \
    tail -20 | \
    while read line; do
        echo "  $line"
    done
}

# Interactive monitoring dashboard
dashboard() {
    local config_file="$1"
    local refresh_interval="${2:-5}"
    
    while true; do
        clear
        echo "=== Network Monitoring Dashboard ==="
        echo "Time: $(date)"
        echo "Refresh interval: ${refresh_interval}s"
        echo "Press Ctrl+C to exit"
        echo
        
        # Show recent status for each host
        if [ -f "$config_file" ]; then
            while IFS=: read -r host services interval; do
                [[ "$host" =~ ^#.*$ ]] && continue
                [ -z "$host" ] && continue
                
                echo -n "Testing $host... "
                if ping_host "$host" 1 1; then
                    echo "UP"
                else
                    echo "DOWN"
                fi
            done < "$config_file"
        fi
        
        echo
        echo "Recent errors:"
        tail -5 "$LOG_FILE" 2>/dev/null | grep "\[ERROR\]" || echo "  No recent errors"
        
        sleep "$refresh_interval"
    done
}

# Main function
main() {
    case "${1:-help}" in
        ping)
            ping_host "$2"
            ;;
        port)
            check_port "$2" "$3"
            ;;
        http)
            check_http "$2" "$3"
            ;;
        monitor)
            monitor_host "$2" "$3" "$4"
            ;;
        multi)
            monitor_multiple "$2"
            ;;
        report)
            generate_report "$2" "$3"
            ;;
        dashboard)
            dashboard "$2" "$3"
            ;;
        help)
            cat << 'EOF'
Usage: network_monitor.sh <command> [options]

Commands:
  ping <host>                    - Test if host is reachable
  port <host> <port>            - Test if TCP port is open
  http <url> [code]             - Test HTTP service
  monitor <host> [services] [interval] - Monitor single host
  multi <config_file>           - Monitor multiple hosts from config
  report [log_file] [hours]     - Generate monitoring report
  dashboard <config_file> [interval] - Interactive dashboard
  help                          - Show this help

Config file format (host:services:interval):
  example.com:ping,http:60
  database.local:ping,ssh:30
  # This is a comment

Services: ping, ssh, http, https
EOF
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            return 1
            ;;
    esac
}

# Run main if script is executed directly
main "$@"
```

## Summary

Functions in PSH provide powerful code organization and reusability:

1. **Definition Syntax**: Both POSIX `name()` and bash `function name` styles
2. **Parameters**: Positional parameters ($1, $2, etc.) with special variables ($#, $@, $*)
3. **Local Variables**: Function-scoped variables with `local` keyword
4. **Return Values**: Exit status with `return` command and output capture
5. **Function Management**: List with `declare -f`, remove with `unset -f`
6. **Advanced Patterns**: Recursion, libraries, wrappers, and decorators

Key concepts:
- Functions create isolated execution environments
- Local variables prevent global namespace pollution
- Parameter handling enables flexible function interfaces
- Return statements control function exit status
- Functions can be recursive with proper base cases
- Function libraries promote code reuse
- Wrapper functions enable cross-cutting concerns

Functions are essential for building maintainable shell scripts and creating reusable code libraries for system administration, automation, and complex data processing tasks.

---

[← Previous: Chapter 11 - Control Structures](11_control_structures.md) | [Next: Chapter 13 - Shell Scripts →](13_shell_scripts.md)