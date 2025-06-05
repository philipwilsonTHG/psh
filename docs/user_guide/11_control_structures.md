# Chapter 11: Control Structures

Control structures enable conditional execution and loops in shell scripts. PSH provides full support for if statements, while and for loops, case statements, and loop control commands. These constructs allow you to build complex program logic and automate repetitive tasks.

## 11.1 Conditional Statements (if/then/else/fi)

The if statement executes commands conditionally based on the exit status of test commands.

### Basic if Statement

```bash
# Simple if statement
psh$ if [ -f file.txt ]; then
>     echo "File exists"
> fi
File exists

# One-line if statement
psh$ if true; then echo "success"; fi
success

# Using command exit status
psh$ if ls /home; then
>     echo "Listed home directory"
> fi
/home/alice
Listed home directory

# Multiple commands in condition
psh$ if cd /tmp && ls -la; then
>     echo "Successfully changed directory and listed files"
> fi
```

### if/else Statement

```bash
# Basic if/else
psh$ if [ -f config.txt ]; then
>     echo "Config file found"
> else
>     echo "Config file missing"
> fi
Config file missing

# File existence check
psh$ filename="data.txt"
psh$ if [ -f "$filename" ]; then
>     echo "Processing $filename"
>     cat "$filename"
> else
>     echo "Creating $filename"
>     touch "$filename"
> fi
Creating data.txt

# Command success/failure
psh$ if ping -c 1 google.com >/dev/null 2>&1; then
>     echo "Network is up"
> else
>     echo "Network is down"
> fi
Network is up
```

### if/elif/else Statement

```bash
# Multiple conditions
psh$ score=85
psh$ if [ "$score" -ge 90 ]; then
>     echo "Grade: A"
> elif [ "$score" -ge 80 ]; then
>     echo "Grade: B"
> elif [ "$score" -ge 70 ]; then
>     echo "Grade: C"
> else
>     echo "Grade: F"
> fi
Grade: B

# File type detection
psh$ path="/etc/passwd"
psh$ if [ -f "$path" ]; then
>     echo "$path is a regular file"
> elif [ -d "$path" ]; then
>     echo "$path is a directory"
> elif [ -L "$path" ]; then
>     echo "$path is a symbolic link"
> else
>     echo "$path does not exist or is special"
> fi
/etc/passwd is a regular file

# Service status check
check_service() {
    local service="$1"
    if systemctl is-active "$service" >/dev/null 2>&1; then
        echo "$service is running"
    elif systemctl is-enabled "$service" >/dev/null 2>&1; then
        echo "$service is enabled but not running"
    else
        echo "$service is disabled"
    fi
}
```

### Complex Conditions

```bash
# Multiple test conditions
psh$ if [ -f file.txt ] && [ -r file.txt ]; then
>     echo "File exists and is readable"
> fi

# Using test command alternatives
psh$ if command -v git >/dev/null; then
>     echo "Git is installed"
> fi

# String comparisons
psh$ user="admin"
psh$ if [ "$user" = "admin" ] || [ "$user" = "root" ]; then
>     echo "Administrative user"
> fi

# Numeric comparisons
psh$ age=25
psh$ if [ "$age" -ge 18 ] && [ "$age" -le 65 ]; then
>     echo "Working age"
> fi

# Enhanced test with [[
psh$ if [[ "$user" =~ ^admin.* ]]; then
>     echo "Admin user detected"
> fi
```

## 11.2 While Loops (while/do/done)

While loops execute commands repeatedly as long as the condition remains true.

### Basic While Loop

```bash
# Simple counter
psh$ count=1
psh$ while [ "$count" -le 5 ]; do
>     echo "Count: $count"
>     count=$((count + 1))
> done
Count: 1
Count: 2
Count: 3
Count: 4
Count: 5

# Process files
psh$ while [ -f "input.txt" ]; do
>     echo "Processing input.txt"
>     mv input.txt processed.txt
>     sleep 1
> done

# Wait for condition
psh$ while ! ping -c 1 server.com >/dev/null 2>&1; do
>     echo "Waiting for server..."
>     sleep 5
> done
psh$ echo "Server is up!"
```

### Reading Input with While

```bash
# Read lines from file
psh$ while read line; do
>     echo "Line: $line"
> done < input.txt

# Read fields from CSV
psh$ while IFS=, read name age city; do
>     echo "Name: $name, Age: $age, City: $city"
> done < data.csv

# Process command output
psh$ ps aux | while read user pid cpu mem rest; do
>     if [ "$cpu" -gt 50 ]; then
>         echo "High CPU process: $pid ($cpu%)"
>     fi
> done

# Interactive input
psh$ while true; do
>     read -p "Enter command (quit to exit): " cmd
>     [ "$cmd" = "quit" ] && break
>     echo "You entered: $cmd"
> done
```

### While Loop Patterns

```bash
# Infinite loop with break
psh$ counter=0
psh$ while true; do
>     echo "Iteration $counter"
>     counter=$((counter + 1))
>     [ "$counter" -gt 3 ] && break
> done

# File monitoring
psh$ while true; do
>     if [ -f new_data.txt ]; then
>         echo "Processing new data"
>         process_file new_data.txt
>         mv new_data.txt processed/
>     fi
>     sleep 10
> done

# Service monitoring
monitor_service() {
    local service="$1"
    while true; do
        if ! systemctl is-active "$service" >/dev/null; then
            echo "Service $service is down, restarting..."
            systemctl restart "$service"
        fi
        sleep 60
    done
}

# Log tail with processing
psh$ tail -f /var/log/app.log | while read line; do
>     if echo "$line" | grep -q "ERROR"; then
>         echo "Error detected: $line" | mail admin@company.com
>     fi
> done
```

## 11.3 For Loops

PSH supports both traditional for/in loops and C-style for loops.

### Traditional For Loops (for/in/do/done)

```bash
# Basic for loop
psh$ for i in 1 2 3 4 5; do
>     echo "Number: $i"
> done
Number: 1
Number: 2
Number: 3
Number: 4
Number: 5

# Iterate over files
psh$ for file in *.txt; do
>     echo "Processing $file"
>     wc -l "$file"
> done

# Iterate over command output
psh$ for user in $(cat /etc/passwd | cut -d: -f1); do
>     echo "User: $user"
> done

# Iterate over arguments
process_files() {
    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "Processing $file"
            # Process file here
        else
            echo "Warning: $file not found"
        fi
    done
}

# Range with brace expansion
psh$ for i in {1..10}; do
>     echo "Item $i"
> done

# Multiple variables (with arrays when supported)
psh$ for item in apple:red banana:yellow grape:purple; do
>     fruit=${item%:*}
>     color=${item#*:}
>     echo "$fruit is $color"
> done
apple is red
banana is yellow
grape is purple
```

### C-Style For Loops

```bash
# Basic C-style for loop
psh$ for ((i=1; i<=5; i++)); do
>     echo "Iteration $i"
> done
Iteration 1
Iteration 2
Iteration 3
Iteration 4
Iteration 5

# With step increment
psh$ for ((i=0; i<=10; i+=2)); do
>     echo "Even number: $i"
> done
Even number: 0
Even number: 2
Even number: 4
Even number: 6
Even number: 8
Even number: 10

# Countdown
psh$ for ((i=10; i>=1; i--)); do
>     echo "Countdown: $i"
>     sleep 1
> done
psh$ echo "Blast off!"

# Multiple variables
psh$ for ((i=1, j=10; i<=5; i++, j--)); do
>     echo "i=$i, j=$j"
> done
i=1, j=10
i=2, j=9
i=3, j=8
i=4, j=7
i=5, j=6

# Empty sections
psh$ i=1
psh$ for ((; i<=3; i++)); do
>     echo "Value: $i"
> done

# Infinite loop (use break to exit)
psh$ for ((;;)); do
>     echo "Infinite loop iteration"
>     sleep 1
>     break  # Remove this for true infinite loop
> done
```

### Advanced For Loop Patterns

```bash
# Nested loops
psh$ for i in {1..3}; do
>     for j in {a..c}; do
>         echo "$i$j"
>     done
> done
1a
1b
1c
2a
2b
2c
3a
3b
3c

# File processing with progress
process_directory() {
    local dir="$1"
    local total=$(find "$dir" -name "*.log" | wc -l)
    local count=0
    
    for file in "$dir"/*.log; do
        [ -f "$file" ] || continue
        count=$((count + 1))
        echo "Processing file $count of $total: $(basename "$file")"
        
        # Process file here
        grep ERROR "$file" > "${file%.log}_errors.txt"
    done
}

# Parallel processing simulation
psh$ for i in {1..5}; do
>     {
>         echo "Starting task $i"
>         sleep $i
>         echo "Completed task $i"
>     } &
> done
psh$ wait  # Wait for all background tasks

# Command substitution in for loop
psh$ for pid in $(ps aux | grep python | awk '{print $2}'); do
>     echo "Python process: $pid"
> done

# Reading from multiple files
psh$ for config in /etc/*.conf; do
>     echo "=== $config ==="
>     head -5 "$config"
>     echo
> done
```

## 11.4 Case Statements (case/esac)

Case statements provide pattern matching for multiple conditions.

### Basic Case Statement

```bash
# Simple case statement
psh$ option="start"
psh$ case "$option" in
>     start)
>         echo "Starting service"
>         ;;
>     stop)
>         echo "Stopping service"
>         ;;
>     restart)
>         echo "Restarting service"
>         ;;
>     *)
>         echo "Unknown option: $option"
>         ;;
> esac
Starting service

# File extension handling
process_file() {
    local file="$1"
    case "$file" in
        *.txt)
            echo "Processing text file: $file"
            cat "$file"
            ;;
        *.csv)
            echo "Processing CSV file: $file"
            cut -d, -f1 "$file"
            ;;
        *.log)
            echo "Processing log file: $file"
            tail -10 "$file"
            ;;
        *)
            echo "Unknown file type: $file"
            ;;
    esac
}

# User input handling
psh$ read -p "Do you want to continue? (y/n): " answer
psh$ case "$answer" in
>     y|Y|yes|YES)
>         echo "Continuing..."
>         ;;
>     n|N|no|NO)
>         echo "Stopping..."
>         exit 0
>         ;;
>     *)
>         echo "Please answer yes or no"
>         ;;
> esac
```

### Pattern Matching

```bash
# Wildcard patterns
psh$ filename="report_2024.pdf"
psh$ case "$filename" in
>     *.pdf)
>         echo "PDF document"
>         ;;
>     *.doc|*.docx)
>         echo "Word document"
>         ;;
>     *.txt)
>         echo "Text file"
>         ;;
>     report_*)
>         echo "Report file"
>         ;;
>     *)
>         echo "Unknown file type"
>         ;;
> esac
PDF document

# Character classes
psh$ input="5"
psh$ case "$input" in
>     [0-9])
>         echo "Single digit"
>         ;;
>     [a-z])
>         echo "Lowercase letter"
>         ;;
>     [A-Z])
>         echo "Uppercase letter"
>         ;;
>     *)
>         echo "Other character"
>         ;;
> esac
Single digit

# Range patterns
check_grade() {
    local score="$1"
    case "$score" in
        [9][0-9]|100)
            echo "Grade: A"
            ;;
        [8][0-9])
            echo "Grade: B"
            ;;
        [7][0-9])
            echo "Grade: C"
            ;;
        [6][0-9])
            echo "Grade: D"
            ;;
        *)
            echo "Grade: F"
            ;;
    esac
}
```

### Advanced Case Features

```bash
# Fallthrough with ;&
psh$ value="2"
psh$ case "$value" in
>     1|2|3)
>         echo "Low value"
>         ;&  # Fallthrough to next case
>     [1-5])
>         echo "In range 1-5"
>         ;;
>     *)
>         echo "Other value"
>         ;;
> esac
Low value
In range 1-5

# Continue matching with ;;&
psh$ text="hello world"
psh$ case "$text" in
>     *hello*)
>         echo "Contains hello"
>         ;;&  # Continue matching
>     *world*)
>         echo "Contains world"
>         ;;&  # Continue matching
>     *o*)
>         echo "Contains letter o"
>         ;;
> esac
Contains hello
Contains world
Contains letter o

# Multiple commands per case
handle_signal() {
    local signal="$1"
    case "$signal" in
        TERM|INT)
            echo "Received termination signal: $signal"
            cleanup_resources
            save_state
            exit 0
            ;;
        HUP)
            echo "Received hangup signal, reloading config"
            reload_configuration
            ;;
        USR1)
            echo "Received user signal 1"
            toggle_debug_mode
            ;;
        *)
            echo "Unknown signal: $signal"
            ;;
    esac
}
```

## 11.5 Loop Control (break and continue)

Break and continue statements control loop execution flow.

### Break Statement

```bash
# Basic break
psh$ for i in {1..10}; do
>     if [ "$i" -eq 5 ]; then
>         break
>     fi
>     echo "Number: $i"
> done
Number: 1
Number: 2
Number: 3
Number: 4

# Break from while loop
psh$ count=1
psh$ while true; do
>     echo "Count: $count"
>     count=$((count + 1))
>     if [ "$count" -gt 3 ]; then
>         break
>     fi
> done
Count: 1
Count: 2
Count: 3

# Interactive break
psh$ while read -p "Enter command (quit to exit): " cmd; do
>     if [ "$cmd" = "quit" ]; then
>         break
>     fi
>     echo "Processing: $cmd"
> done
```

### Continue Statement

```bash
# Basic continue
psh$ for i in {1..5}; do
>     if [ "$i" -eq 3 ]; then
>         continue
>     fi
>     echo "Number: $i"
> done
Number: 1
Number: 2
Number: 4
Number: 5

# Skip processing certain files
psh$ for file in *.txt; do
>     if [[ "$file" =~ ^backup_ ]]; then
>         echo "Skipping backup file: $file"
>         continue
>     fi
>     echo "Processing: $file"
> done

# Error handling with continue
process_files() {
    for file in "$@"; do
        if [ ! -f "$file" ]; then
            echo "Warning: $file not found, skipping"
            continue
        fi
        
        if [ ! -r "$file" ]; then
            echo "Warning: $file not readable, skipping"
            continue
        fi
        
        echo "Processing $file"
        # Process file here
    done
}
```

### Multi-level Break and Continue

```bash
# Break from nested loops
psh$ for i in {1..3}; do
>     for j in {1..3}; do
>         echo "i=$i, j=$j"
>         if [ "$i" -eq 2 ] && [ "$j" -eq 2 ]; then
>             break 2  # Break from both loops
>         fi
>     done
> done
i=1, j=1
i=1, j=2
i=1, j=3
i=2, j=1
i=2, j=2

# Continue outer loop
psh$ for i in {1..3}; do
>     echo "Outer loop: $i"
>     for j in {1..3}; do
>         if [ "$j" -eq 2 ]; then
>             continue 2  # Continue outer loop
>         fi
>         echo "  Inner loop: $j"
>     done
>     echo "End of outer loop $i"
> done
Outer loop: 1
  Inner loop: 1
Outer loop: 2
  Inner loop: 1
Outer loop: 3
  Inner loop: 1
```

## 11.6 Enhanced Test Operators [[ ]]

PSH supports enhanced test syntax with additional operators.

### String Comparisons

```bash
# Lexicographic comparison
psh$ if [[ "apple" < "banana" ]]; then
>     echo "apple comes before banana"
> fi
apple comes before banana

# Pattern matching
psh$ filename="report.txt"
psh$ if [[ "$filename" =~ \.txt$ ]]; then
>     echo "Text file detected"
> fi
Text file detected

# Multiple conditions
psh$ user="admin"
psh$ if [[ "$user" == "admin" && -f "/etc/passwd" ]]; then
>     echo "Admin user with passwd file"
> fi
Admin user with passwd file

# No word splitting
psh$ text="hello world"
psh$ if [[ $text == "hello world" ]]; then  # No quotes needed
>     echo "Match found"
> fi
Match found
```

### Regular Expression Matching

```bash
# Email validation
validate_email() {
    local email="$1"
    if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        echo "Valid email: $email"
    else
        echo "Invalid email: $email"
    fi
}

# IP address validation
validate_ip() {
    local ip="$1"
    if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "Valid IP format: $ip"
    else
        echo "Invalid IP format: $ip"
    fi
}

# Log parsing
parse_log_line() {
    local line="$1"
    if [[ "$line" =~ ^([0-9-]+)\ ([0-9:]+)\ \[([A-Z]+)\]\ (.+)$ ]]; then
        local date="${BASH_REMATCH[1]}"
        local time="${BASH_REMATCH[2]}"
        local level="${BASH_REMATCH[3]}"
        local message="${BASH_REMATCH[4]}"
        echo "Date: $date, Time: $time, Level: $level, Message: $message"
    fi
}
```

## 11.7 Practical Examples

### System Administration Script

```bash
#!/usr/bin/env psh
# System maintenance script with control structures

# Configuration
LOG_FILE="/var/log/maintenance.log"
MAX_DISK_USAGE=80
BACKUP_DIR="/backup"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_disk_usage() {
    log "Checking disk usage..."
    
    while read filesystem size used avail percent mount; do
        # Skip header and special filesystems
        [[ "$filesystem" == "Filesystem" ]] && continue
        [[ "$filesystem" =~ ^(tmpfs|devtmpfs|udev) ]] && continue
        
        # Extract percentage number
        usage=${percent%\%}
        
        if [ "$usage" -gt "$MAX_DISK_USAGE" ]; then
            log "WARNING: $mount is ${usage}% full"
            
            case "$mount" in
                /var/log)
                    log "Cleaning old log files..."
                    find /var/log -name "*.log.*" -mtime +7 -delete
                    ;;
                /tmp)
                    log "Cleaning temporary files..."
                    find /tmp -type f -mtime +1 -delete
                    ;;
                *)
                    log "Manual intervention needed for $mount"
                    ;;
            esac
        else
            log "OK: $mount is ${usage}% full"
        fi
    done < <(df -h)
}

update_system() {
    log "Updating system packages..."
    
    if command -v apt >/dev/null; then
        apt update && apt upgrade -y
    elif command -v yum >/dev/null; then
        yum update -y
    elif command -v pacman >/dev/null; then
        pacman -Syu --noconfirm
    else
        log "Unknown package manager"
        return 1
    fi
}

backup_configs() {
    log "Backing up configuration files..."
    
    local backup_date=$(date +%Y%m%d)
    local backup_path="$BACKUP_DIR/configs_$backup_date"
    
    mkdir -p "$backup_path"
    
    for config in /etc/passwd /etc/group /etc/fstab /etc/hosts; do
        if [ -f "$config" ]; then
            cp "$config" "$backup_path/"
            log "Backed up $config"
        else
            log "Config file not found: $config"
        fi
    done
    
    # Compress backup
    tar -czf "$backup_path.tar.gz" -C "$BACKUP_DIR" "configs_$backup_date"
    rm -rf "$backup_path"
    log "Backup created: $backup_path.tar.gz"
}

main() {
    log "Starting maintenance script"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log "ERROR: This script must be run as root"
        exit 1
    fi
    
    # Main maintenance tasks
    for task in check_disk_usage update_system backup_configs; do
        log "Running task: $task"
        
        if $task; then
            log "Task completed successfully: $task"
        else
            log "Task failed: $task"
        fi
        
        sleep 2
    done
    
    log "Maintenance script completed"
}

# Run main function
main "$@"
```

### Log Analysis Script

```bash
#!/usr/bin/env psh
# Advanced log analysis with control structures

analyze_apache_log() {
    local logfile="$1"
    local start_date="${2:-yesterday}"
    
    if [ ! -f "$logfile" ]; then
        echo "Error: Log file not found: $logfile"
        return 1
    fi
    
    echo "=== Apache Log Analysis ==="
    echo "File: $logfile"
    echo "Analysis Date: $(date)"
    echo
    
    # IP Analysis
    echo "=== Top 10 IP Addresses ==="
    awk '{print $1}' "$logfile" | \
    while read ip; do
        # Validate IP format
        if [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "$ip"
        fi
    done | \
    sort | uniq -c | sort -nr | head -10 | \
    while read count ip; do
        printf "%8d %s\n" "$count" "$ip"
    done
    echo
    
    # Status Code Analysis
    echo "=== HTTP Status Codes ==="
    awk '{print $9}' "$logfile" | \
    while read status; do
        case "$status" in
            2[0-9][0-9]) echo "success" ;;
            3[0-9][0-9]) echo "redirect" ;;
            4[0-9][0-9]) echo "client_error" ;;
            5[0-9][0-9]) echo "server_error" ;;
            *) continue ;;
        esac
    done | \
    sort | uniq -c | sort -nr
    echo
    
    # Error Analysis
    echo "=== Error Requests (4xx, 5xx) ==="
    awk '$9 ~ /^[45][0-9][0-9]$/ {print $0}' "$logfile" | \
    while read line; do
        # Extract relevant fields
        set $line
        ip="$1"
        timestamp="$4"
        method="$6"
        url="$7"
        status="$9"
        
        echo "[$status] $ip $method $url"
    done | head -20
    echo
    
    # Hourly Traffic
    echo "=== Traffic by Hour ==="
    awk '{print $4}' "$logfile" | \
    cut -d: -f2 | \
    sort | uniq -c | \
    while read count hour; do
        printf "Hour %02d: %5d requests\n" "$hour" "$count"
    done
}

# Interactive mode
interactive_mode() {
    while true; do
        echo
        echo "=== Log Analysis Menu ==="
        echo "1) Analyze Apache log"
        echo "2) Find large files"
        echo "3) Monitor real-time logs"
        echo "4) Exit"
        echo
        read -p "Choose option [1-4]: " choice
        
        case "$choice" in
            1)
                read -p "Enter log file path: " logfile
                analyze_apache_log "$logfile"
                ;;
            2)
                read -p "Enter directory to search: " directory
                find "$directory" -type f -size +100M 2>/dev/null | \
                while read file; do
                    size=$(du -h "$file" | cut -f1)
                    echo "$size $file"
                done | sort -hr
                ;;
            3)
                read -p "Enter log file to monitor: " logfile
                if [ -f "$logfile" ]; then
                    echo "Monitoring $logfile (Ctrl+C to stop)..."
                    tail -f "$logfile" | \
                    while read line; do
                        if [[ "$line" =~ ERROR|CRITICAL|FATAL ]]; then
                            echo "ALERT: $line"
                        fi
                    done
                else
                    echo "File not found: $logfile"
                fi
                ;;
            4)
                echo "Goodbye!"
                break
                ;;
            *)
                echo "Invalid option"
                ;;
        esac
    done
}

# Main script
case "${1:-interactive}" in
    analyze)
        analyze_apache_log "$2" "$3"
        ;;
    interactive)
        interactive_mode
        ;;
    *)
        echo "Usage: $0 {analyze <logfile> [date]|interactive}"
        exit 1
        ;;
esac
```

### Build System with Error Handling

```bash
#!/usr/bin/env psh
# Comprehensive build system with control structures

# Configuration
BUILD_DIR="build"
SOURCE_DIR="src"
INSTALL_PREFIX="/usr/local"
PARALLEL_JOBS=$(nproc 2>/dev/null || echo 4)

# Build states
declare -a BUILD_STEPS=(
    "clean"
    "configure" 
    "compile"
    "test"
    "package"
    "install"
)

# Error tracking
BUILD_ERRORS=()
BUILD_WARNINGS=()

log_message() {
    local level="$1"
    shift
    echo "[$(date '+%H:%M:%S')] [$level] $*"
}

log_error() {
    log_message "ERROR" "$@"
    BUILD_ERRORS+=("$*")
}

log_warning() {
    log_message "WARN" "$@"
    BUILD_WARNINGS+=("$*")
}

log_info() {
    log_message "INFO" "$@"
}

cleanup_build() {
    log_info "Cleaning build directory"
    
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
    
    if [ $? -eq 0 ]; then
        log_info "Build directory cleaned"
        return 0
    else
        log_error "Failed to clean build directory"
        return 1
    fi
}

configure_build() {
    log_info "Configuring build"
    
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR" || {
        log_error "Cannot change to build directory"
        return 1
    }
    
    if [ -f "../CMakeLists.txt" ]; then
        cmake -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" ..
    elif [ -f "../configure" ]; then
        ../configure --prefix="$INSTALL_PREFIX"
    elif [ -f "../Makefile" ]; then
        # Copy Makefile if present
        cp ../Makefile .
    else
        log_error "No build system found"
        return 1
    fi
    
    local result=$?
    cd ..
    
    if [ $result -eq 0 ]; then
        log_info "Configuration completed"
    else
        log_error "Configuration failed"
    fi
    
    return $result
}

compile_project() {
    log_info "Compiling project"
    
    cd "$BUILD_DIR" || {
        log_error "Cannot change to build directory"
        return 1
    }
    
    # Capture build output
    make -j"$PARALLEL_JOBS" 2>&1 | while read line; do
        case "$line" in
            *error:*|*Error:*|*ERROR*)
                log_error "Compile error: $line"
                ;;
            *warning:*|*Warning:*|*WARNING*)
                log_warning "Compile warning: $line"
                ;;
            *)
                echo "$line"
                ;;
        esac
    done
    
    local result=${PIPESTATUS[0]}
    cd ..
    
    if [ $result -eq 0 ]; then
        log_info "Compilation completed"
    else
        log_error "Compilation failed"
    fi
    
    return $result
}

run_tests() {
    log_info "Running tests"
    
    cd "$BUILD_DIR" || {
        log_error "Cannot change to build directory"
        return 1
    }
    
    if [ -f "Makefile" ] && grep -q "test:" Makefile; then
        make test
    elif command -v ctest >/dev/null; then
        ctest --output-on-failure
    else
        log_warning "No tests found"
        cd ..
        return 0
    fi
    
    local result=$?
    cd ..
    
    if [ $result -eq 0 ]; then
        log_info "All tests passed"
    else
        log_error "Some tests failed"
    fi
    
    return $result
}

package_project() {
    log_info "Creating package"
    
    cd "$BUILD_DIR" || {
        log_error "Cannot change to build directory"
        return 1
    }
    
    if grep -q "package:" Makefile 2>/dev/null; then
        make package
    elif command -v cpack >/dev/null; then
        cpack
    else
        log_warning "No packaging system found"
        cd ..
        return 0
    fi
    
    local result=$?
    cd ..
    
    if [ $result -eq 0 ]; then
        log_info "Package created"
    else
        log_error "Package creation failed"
    fi
    
    return $result
}

install_project() {
    log_info "Installing project"
    
    if [ "$EUID" -ne 0 ] && [[ "$INSTALL_PREFIX" =~ ^/usr ]]; then
        log_error "Root privileges required for installation to $INSTALL_PREFIX"
        return 1
    fi
    
    cd "$BUILD_DIR" || {
        log_error "Cannot change to build directory"
        return 1
    }
    
    make install
    local result=$?
    cd ..
    
    if [ $result -eq 0 ]; then
        log_info "Installation completed"
    else
        log_error "Installation failed"
    fi
    
    return $result
}

# Main build function
run_build() {
    local steps=("$@")
    
    # If no steps specified, run all
    if [ ${#steps[@]} -eq 0 ]; then
        steps=("${BUILD_STEPS[@]}")
    fi
    
    log_info "Starting build process"
    log_info "Steps to execute: ${steps[*]}"
    
    local start_time=$(date +%s)
    local failed_step=""
    
    for step in "${steps[@]}"; do
        log_info "Executing step: $step"
        
        case "$step" in
            clean)     cleanup_build ;;
            configure) configure_build ;;
            compile)   compile_project ;;
            test)      run_tests ;;
            package)   package_project ;;
            install)   install_project ;;
            *)
                log_error "Unknown build step: $step"
                failed_step="$step"
                break
                ;;
        esac
        
        if [ $? -ne 0 ]; then
            failed_step="$step"
            break
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Build summary
    echo
    log_info "=== Build Summary ==="
    log_info "Duration: ${duration}s"
    log_info "Errors: ${#BUILD_ERRORS[@]}"
    log_info "Warnings: ${#BUILD_WARNINGS[@]}"
    
    if [ -n "$failed_step" ]; then
        log_error "Build failed at step: $failed_step"
        return 1
    else
        log_info "Build completed successfully"
        return 0
    fi
}

# Command line interface
case "${1:-help}" in
    clean)
        cleanup_build
        ;;
    configure)
        configure_build
        ;;
    build)
        run_build clean configure compile
        ;;
    test)
        run_build clean configure compile test
        ;;
    package)
        run_build clean configure compile test package
        ;;
    install)
        run_build clean configure compile test package install
        ;;
    all)
        run_build
        ;;
    help)
        echo "Usage: $0 {clean|configure|build|test|package|install|all|help}"
        echo
        echo "Steps:"
        for step in "${BUILD_STEPS[@]}"; do
            echo "  $step"
        done
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
```

## Summary

Control structures are essential for building complex shell scripts:

1. **if/then/else/fi**: Conditional execution based on command exit status
2. **while/do/done**: Repeat commands while condition is true
3. **for/in/do/done**: Iterate over lists of items
4. **for ((;;))**: C-style loops with arithmetic expressions
5. **case/esac**: Pattern matching for multiple conditions
6. **break/continue**: Control loop flow with optional levels
7. **[[ ]]**: Enhanced test operators with regex and string comparison

Key concepts:
- All control structures use command exit status for decisions
- Proper quoting is essential for string comparisons
- Nested structures enable complex program logic
- Loop control statements provide fine-grained flow control
- Pattern matching in case statements supports wildcards and ranges
- Enhanced test operators provide more powerful condition testing

Control structures enable you to automate complex tasks, handle various conditions, and build robust shell scripts for system administration and data processing.

---

[← Previous: Chapter 10 - Pipelines and Lists](10_pipelines_and_lists.md) | [Next: Chapter 12 - Functions →](12_functions.md)