# Appendix B: Example Scripts

This appendix contains a collection of scripts that demonstrate PSH's capabilities. All scripts have been tested and are guaranteed to work with PSH version 0.37.0 and later.

## Table of Contents

1. [Control Structures in Pipelines (v0.37.0)](#control-structures-in-pipelines-v0370) 🚀
2. [System Administration Scripts](#system-administration-scripts)
3. [Mathematical Scripts](#mathematical-scripts)
4. [Interactive Utilities](#interactive-utilities)
5. [Text Processing Scripts](#text-processing-scripts)
6. [Development Tools](#development-tools)
7. [Function Libraries](#function-libraries)
8. [Dynamic Programming with eval](#dynamic-programming-with-eval)

## Control Structures in Pipelines (v0.37.0) 🚀

PSH v0.37.0 introduces the ability to use control structures as pipeline components. The comprehensive demonstration script is available at `examples/control_structures_in_pipelines_demo.sh`.

### Quick Examples

```bash
#!/usr/bin/env psh
# Pipeline patterns available in PSH v0.37.0

# Data processing with while loops
echo -e "apple\nbanana\ncherry" | while read fruit; do
    echo "Processing: $fruit (${#fruit} characters)"
done

# Conditional processing with if statements
echo "42" | if [ $(cat) -gt 40 ]; then
    echo "✅ Number is greater than 40"
else
    echo "❌ Number is 40 or less"
fi

# Pattern matching with case statements
echo "script.sh" | case $(cat) in
    *.sh)  echo "📜 Shell script detected" ;;
    *.py)  echo "🐍 Python script detected" ;;
    *)     echo "❓ Unknown file type" ;;
esac

# Multi-stage pipeline processing
seq 1 3 | while read num; do
    echo "Group $num:" 
    echo "  x y z" | for item in a b c; do
        echo "    $num-$item"
    done
done

# Real-world log processing
echo "2024-01-06 ERROR Database connection failed" | while read date time level message; do
    case $level in
        ERROR) echo "🔴 $date $time: $message" ;;
        WARN)  echo "🟡 $date $time: $message" ;;
        INFO)  echo "🔵 $date $time: $message" ;;
        *)     echo "⚪ $date $time $level: $message" ;;
    esac
done
```

### Benefits

- **Enhanced Data Processing**: Create sophisticated data transformation pipelines
- **Improved Readability**: More intuitive pipeline logic
- **Increased Composability**: Mix control structures with traditional commands seamlessly
- **Enhanced Capability**: Control structures as pipeline components

For the complete demonstration with 50+ examples, run:
```bash
psh examples/control_structures_in_pipelines_demo.sh
```

## System Administration Scripts

### File Backup Script

```bash
#!/usr/bin/env psh
# backup.sh - Simple backup script with timestamping

# Function to create timestamped backup
backup_files() {
    local source_dir="$1"
    local backup_dir="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="backup_${timestamp}"
    
    # Validate arguments
    if [ -z "$source_dir" ] || [ -z "$backup_dir" ]; then
        echo "Usage: backup_files <source_dir> <backup_dir>" >&2
        return 1
    fi
    
    # Check if source exists
    if [ ! -d "$source_dir" ]; then
        echo "Error: Source directory '$source_dir' not found" >&2
        return 1
    fi
    
    # Create backup directory if needed
    if [ ! -d "$backup_dir" ]; then
        echo "Creating backup directory: $backup_dir"
        mkdir -p "$backup_dir"
    fi
    
    # Perform backup
    echo "Backing up $source_dir to $backup_dir/$backup_name"
    cp -r "$source_dir" "$backup_dir/$backup_name"
    
    # Check if backup succeeded
    if [ $? -eq 0 ]; then
        echo "Backup completed successfully"
        
        # Count files in backup
        local file_count=0
        for file in "$backup_dir/$backup_name"/*; do
            ((file_count++))
        done
        echo "Backed up $file_count items"
    else
        echo "Backup failed" >&2
        return 1
    fi
}

# Main script
if [ $# -ne 2 ]; then
    echo "Usage: $0 <source_directory> <backup_directory>"
    exit 1
fi

backup_files "$1" "$2"
```

### Directory Cleanup Script

```bash
#!/usr/bin/env psh
# cleanup.sh - Remove old files from specified directories

cleanup_old_files() {
    local dir="$1"
    local days="${2:-30}"  # Default to 30 days
    local count=0
    
    echo "Cleaning files older than $days days from $dir"
    
    # Find and remove old log files
    for file in "$dir"/*.log; do
        if [ -f "$file" ]; then
            # This is a simplified version - in real bash you'd use find
            echo "Would remove: $file"
            ((count++))
        fi
    done
    
    echo "Found $count old files"
}

# Process each directory
for dir in "$@"; do
    if [ -d "$dir" ]; then
        cleanup_old_files "$dir"
    else
        echo "Warning: $dir is not a directory"
    fi
done
```

### Robust System Update Script

This script demonstrates using shell options for production-quality error handling:

```bash
#!/usr/bin/env psh
# system_update.sh - Robust system update script with error handling
# Demonstrates: set -e, set -u, set -x, set -o pipefail

# Enable strict error handling
set -euo pipefail

# Script metadata
readonly SCRIPT_NAME=$(basename "$0")
readonly LOG_FILE="/var/log/system_update_$(date +%Y%m%d_%H%M%S).log"

# Enable debug mode if requested
[ "${DEBUG:-false}" = "true" ] && set -x

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
        log "ERROR" "This script must be run as root"
        exit 1
    fi
}

# Create system backup
create_backup() {
    log "INFO" "Creating system backup..."
    
    local backup_dir="/backup/system/$(date +%Y%m%d)"
    mkdir -p "$backup_dir"
    
    # Backup critical directories
    for dir in /etc /var/lib/dpkg /var/lib/rpm; do
        if [ -d "$dir" ]; then
            log "INFO" "Backing up $dir"
            tar -czf "$backup_dir/$(basename $dir).tar.gz" "$dir" 2>/dev/null || {
                log "WARN" "Failed to backup $dir, continuing anyway"
            }
        fi
    done
    
    log "INFO" "Backup completed: $backup_dir"
}

# Update package manager
update_packages() {
    log "INFO" "Updating package manager..."
    
    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        # Debian/Ubuntu
        apt-get update || {
            log "ERROR" "Failed to update package lists"
            return 1
        }
        
        # Use pipefail to catch download failures
        apt-get upgrade -y | tee -a "$LOG_FILE" || {
            log "ERROR" "Package upgrade failed"
            return 1
        }
        
    elif command -v yum >/dev/null 2>&1; then
        # RHEL/CentOS
        yum update -y | tee -a "$LOG_FILE" || {
            log "ERROR" "Package upgrade failed"
            return 1
        }
    else
        log "ERROR" "No supported package manager found"
        return 1
    fi
    
    log "INFO" "Package update completed"
}

# Check disk space
check_disk_space() {
    log "INFO" "Checking disk space..."
    
    local min_space_mb=1000
    local available_mb=$(df -m / | tail -1 | awk '{print $4}')
    
    if [ "$available_mb" -lt "$min_space_mb" ]; then
        log "ERROR" "Insufficient disk space: ${available_mb}MB available, ${min_space_mb}MB required"
        return 1
    fi
    
    log "INFO" "Disk space check passed: ${available_mb}MB available"
}

# Clean up old files
cleanup() {
    log "INFO" "Cleaning up old files..."
    
    # Temporarily disable errexit for cleanup
    set +e
    
    # Clean package cache
    if command -v apt-get >/dev/null 2>&1; then
        apt-get autoclean
        apt-get autoremove -y
    elif command -v yum >/dev/null 2>&1; then
        yum clean all
    fi
    
    # Remove old log files
    find /var/log -name "*.gz" -mtime +30 -delete 2>/dev/null
    
    # Re-enable errexit
    set -e
    
    log "INFO" "Cleanup completed"
}

# Main execution
main() {
    log "INFO" "Starting system update process"
    
    # Run all steps
    check_root
    check_disk_space
    create_backup
    
    if update_packages; then
        log "INFO" "System update completed successfully"
        cleanup
        exit 0
    else
        log "ERROR" "System update failed"
        exit 1
    fi
}

# Handle interrupts
handle_interrupt() {
    log "WARN" "Update interrupted by user"
    exit 130
}

# Trap not fully implemented in PSH yet
# trap handle_interrupt INT TERM

# Run main function
main "$@"
```

This script demonstrates:
- **set -euo pipefail**: Comprehensive error handling
- **Conditional error handling**: Using || with error blocks
- **Temporary option toggling**: Disabling errexit for cleanup
- **Proper logging**: All operations logged with timestamps
- **Validation**: Pre-flight checks before making changes
- **Error recovery**: Graceful handling of non-critical failures

## Mathematical Scripts

### Fibonacci Calculator

```bash
#!/usr/bin/env psh
# fibonacci.sh - Calculate Fibonacci numbers

fibonacci() {
    local n=$1
    
    if ((n <= 0)); then
        echo 0
        return
    elif ((n == 1)); then
        echo 1
        return
    fi
    
    local a=0
    local b=1
    local temp
    
    for ((i = 2; i <= n; i++)); do
        ((temp = a + b))
        a=$b
        b=$temp
    done
    
    echo $b
}

# Interactive mode
echo "Fibonacci Calculator"
echo "==================="

while true; do
    read -p "Enter a number (q to quit): " num
    
    if [ "$num" = "q" ]; then
        echo "Goodbye!"
        break
    fi
    
    # Validate input
    if [[ "$num" =~ ^[0-9]+$ ]]; then
        result=$(fibonacci $num)
        echo "Fibonacci($num) = $result"
    else
        echo "Please enter a valid positive number"
    fi
done
```

### Prime Number Checker

```bash
#!/usr/bin/env psh
# prime.sh - Check if numbers are prime

is_prime() {
    local n=$1
    
    if ((n <= 1)); then
        return 1
    fi
    
    if ((n <= 3)); then
        return 0
    fi
    
    if ((n % 2 == 0 || n % 3 == 0)); then
        return 1
    fi
    
    local i=5
    while ((i * i <= n)); do
        if ((n % i == 0 || n % (i + 2) == 0)); then
            return 1
        fi
        ((i += 6))
    done
    
    return 0
}

# Find primes in a range
find_primes() {
    local start=$1
    local end=$2
    local count=0
    
    echo "Prime numbers between $start and $end:"
    
    for ((n = start; n <= end; n++)); do
        if is_prime $n; then
            echo -n "$n "
            ((count++))
        fi
    done
    
    echo
    echo "Found $count prime numbers"
}

# Main program
if [ $# -eq 0 ]; then
    echo "Usage: $0 <number> - check if prime"
    echo "       $0 <start> <end> - find primes in range"
    exit 1
elif [ $# -eq 1 ]; then
    if is_prime $1; then
        echo "$1 is prime"
    else
        echo "$1 is not prime"
    fi
elif [ $# -eq 2 ]; then
    find_primes $1 $2
fi
```

## Interactive Utilities

### Password Generator

```bash
#!/usr/bin/env psh
# passgen.sh - Interactive password generator

generate_password() {
    local length=${1:-12}
    local chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    local password=""
    
    for ((i = 0; i < length; i++)); do
        # Generate random index (simplified - uses $RANDOM if available)
        local index=$((RANDOM % ${#chars}))
        password="${password}${chars:index:1}"
    done
    
    echo "$password"
}

# Interactive menu
show_menu() {
    echo
    echo "Password Generator"
    echo "=================="
    echo "1) Generate simple password (12 chars)"
    echo "2) Generate custom length password"
    echo "3) Generate PIN code"
    echo "4) Exit"
    echo
}

# Main loop
while true; do
    show_menu
    read -p "Choose option: " choice
    
    case $choice in
        1)
            echo "Generated password: $(generate_password)"
            ;;
        2)
            read -p "Enter password length: " length
            if [[ "$length" =~ ^[0-9]+$ ]] && ((length > 0)); then
                echo "Generated password: $(generate_password $length)"
            else
                echo "Invalid length"
            fi
            ;;
        3)
            read -s -n 4 -p "Enter 4-digit PIN: " pin
            echo
            read -s -n 4 -p "Confirm PIN: " confirm
            echo
            if [ "$pin" = "$confirm" ]; then
                echo "PIN set successfully"
            else
                echo "PINs don't match"
            fi
            ;;
        4)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
done
```

### System Information Dashboard

```bash
#!/usr/bin/env psh
# sysinfo.sh - Display system information

print_header() {
    local title="$1"
    local width=40
    local padding=$(( (width - ${#title}) / 2 ))
    
    echo
    for ((i = 0; i < width; i++)); do
        echo -n "="
    done
    echo
    
    for ((i = 0; i < padding; i++)); do
        echo -n " "
    done
    echo "$title"
    
    for ((i = 0; i < width; i++)); do
        echo -n "="
    done
    echo
}

show_disk_usage() {
    print_header "Disk Usage"
    df -h | head -5
}

show_memory_usage() {
    print_header "Memory Usage"
    if [ -f /proc/meminfo ]; then
        head -3 /proc/meminfo
    else
        echo "Memory information not available"
    fi
}

show_processes() {
    print_header "Top Processes"
    ps aux | head -10
}

show_uptime() {
    print_header "System Uptime"
    uptime
}

# Main menu
while true; do
    echo
    echo "System Information Dashboard"
    echo "============================"
    echo "1) Disk usage"
    echo "2) Memory usage"
    echo "3) Process list"
    echo "4) System uptime"
    echo "5) All information"
    echo "6) Exit"
    echo
    
    read -p "Select option: " opt
    
    case $opt in
        1) show_disk_usage ;;
        2) show_memory_usage ;;
        3) show_processes ;;
        4) show_uptime ;;
        5)
            show_uptime
            show_disk_usage
            show_memory_usage
            show_processes
            ;;
        6) exit 0 ;;
        *) echo "Invalid option" ;;
    esac
    
    read -p "Press Enter to continue..."
done
```

### File Manager with Select Menu

```bash
#!/usr/bin/env psh
# filemgr.sh - Interactive file manager using select

# File operations menu
file_operations() {
    local file="$1"
    local PS3="Operation for $file: "
    
    select operation in "View" "Edit" "Copy" "Move" "Delete" "Permissions" "Back"; do
        case "$operation" in
            "View")
                if [ -f "$file" ]; then
                    less "$file" 2>/dev/null || cat "$file"
                else
                    echo "Cannot view: $file is not a regular file"
                fi
                ;;
            "Edit")
                ${EDITOR:-vi} "$file"
                ;;
            "Copy")
                read -p "Copy to: " dest
                if [ -n "$dest" ]; then
                    cp "$file" "$dest" && echo "Copied to $dest"
                fi
                ;;
            "Move")
                read -p "Move to: " dest
                if [ -n "$dest" ]; then
                    mv "$file" "$dest" && echo "Moved to $dest"
                    break  # File no longer exists at original location
                fi
                ;;
            "Delete")
                read -p "Delete $file? (y/n): " confirm
                if [ "$confirm" = "y" ]; then
                    rm "$file" && echo "Deleted: $file"
                    break  # File no longer exists
                fi
                ;;
            "Permissions")
                ls -l "$file"
                read -p "New permissions (e.g., 644): " perms
                if [[ "$perms" =~ ^[0-7]{3}$ ]]; then
                    chmod "$perms" "$file" && echo "Permissions changed"
                else
                    echo "Invalid permissions format"
                fi
                ;;
            "Back")
                break
                ;;
            *)
                [ -n "$REPLY" ] && echo "Invalid option: $REPLY"
                ;;
        esac
    done
}

# Directory browser
browse_directory() {
    local dir="${1:-.}"
    local PS3="Select file: "
    
    while true; do
        echo
        echo "Current directory: $(pwd)"
        echo "===================="
        
        # Build file list with special entries
        local files=(".." $(ls -A))
        
        select file in "${files[@]}" "Quit"; do
            if [ "$file" = "Quit" ]; then
                return 0
            elif [ "$file" = ".." ]; then
                cd ..
                break  # Restart with new directory
            elif [ -d "$file" ]; then
                cd "$file"
                break  # Restart with new directory
            elif [ -f "$file" ]; then
                file_operations "$file"
                break  # Refresh file list
            elif [ -n "$file" ]; then
                echo "Unknown file type: $file"
            else
                [ -n "$REPLY" ] && echo "Invalid selection: $REPLY"
            fi
        done
    done
}

# Main script
echo "Interactive File Manager"
echo "======================="
browse_directory "$@"
```

### Service Manager with Select

```bash
#!/usr/bin/env psh
# svcmgr.sh - Service management using select

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "This script requires root privileges"
        echo "Please run with sudo"
        return 1
    fi
    return 0
}

# Service operations
service_menu() {
    local service="$1"
    local PS3="Action for $service: "
    
    select action in "Status" "Start" "Stop" "Restart" "Enable" "Disable" "Logs" "Back"; do
        case "$action" in
            "Status")
                systemctl status "$service"
                ;;
            "Start")
                systemctl start "$service" && \
                    echo "Started $service"
                ;;
            "Stop")
                systemctl stop "$service" && \
                    echo "Stopped $service"
                ;;
            "Restart")
                systemctl restart "$service" && \
                    echo "Restarted $service"
                ;;
            "Enable")
                systemctl enable "$service" && \
                    echo "Enabled $service"
                ;;
            "Disable")
                systemctl disable "$service" && \
                    echo "Disabled $service"
                ;;
            "Logs")
                journalctl -u "$service" -n 20
                ;;
            "Back")
                break
                ;;
            *)
                [ -n "$REPLY" ] && echo "Invalid option: $REPLY"
                ;;
        esac
        
        [ "$action" != "Back" ] && read -p "Press Enter to continue..."
    done
}

# Main menu
main_menu() {
    local PS3="Select service category: "
    
    select category in "System Services" "Network Services" "User Services" "All Services" "Search" "Exit"; do
        case "$category" in
            "System Services")
                PS3="Select service: "
                select svc in $(systemctl list-units --type=service --state=running | \
                    awk '/system.*\.service/ {print $1}' | head -10) "Back"; do
                    [ "$svc" = "Back" ] && break
                    [ -n "$svc" ] && service_menu "$svc"
                done
                PS3="Select service category: "
                ;;
            "Network Services")
                PS3="Select service: "
                select svc in "sshd" "nginx" "apache2" "mysql" "postgresql" "Back"; do
                    [ "$svc" = "Back" ] && break
                    service_menu "$svc.service"
                done
                PS3="Select service category: "
                ;;
            "User Services")
                PS3="Select service: "
                select svc in $(systemctl list-units --type=service --user | \
                    awk '{print $1}' | grep -v '^UNIT' | head -10) "Back"; do
                    [ "$svc" = "Back" ] && break
                    [ -n "$svc" ] && service_menu "$svc"
                done
                PS3="Select service category: "
                ;;
            "All Services")
                PS3="Select service: "
                select svc in $(systemctl list-unit-files --type=service | \
                    awk '{print $1}' | grep -v '^UNIT' | head -20) "Back"; do
                    [ "$svc" = "Back" ] && break
                    [ -n "$svc" ] && service_menu "$svc"
                done
                PS3="Select service category: "
                ;;
            "Search")
                read -p "Enter service name pattern: " pattern
                PS3="Select service: "
                select svc in $(systemctl list-unit-files --type=service | \
                    grep "$pattern" | awk '{print $1}') "Back"; do
                    [ "$svc" = "Back" ] && break
                    [ -n "$svc" ] && service_menu "$svc"
                done
                PS3="Select service category: "
                ;;
            "Exit")
                echo "Goodbye!"
                exit 0
                ;;
            *)
                [ -n "$REPLY" ] && echo "Invalid option: $REPLY"
                ;;
        esac
    done
}

# Main script
echo "Service Manager"
echo "==============="

if check_root; then
    main_menu
fi
```

## Text Processing Scripts

### Log Analyzer

```bash
#!/usr/bin/env psh
# loganalyze.sh - Analyze log files for patterns

analyze_log() {
    local logfile="$1"
    local pattern="${2:-ERROR}"
    
    if [ ! -f "$logfile" ]; then
        echo "Error: Log file not found: $logfile" >&2
        return 1
    fi
    
    echo "Analyzing $logfile for pattern: $pattern"
    echo "========================================"
    
    local count=0
    local line_num=0
    
    while read line; do
        ((line_num++))
        if [[ "$line" =~ $pattern ]]; then
            echo "Line $line_num: $line"
            ((count++))
        fi
    done < "$logfile"
    
    echo "========================================"
    echo "Found $count occurrences of '$pattern'"
}

# Process command line arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <logfile> [pattern]"
    echo "Default pattern is 'ERROR'"
    exit 1
fi

analyze_log "$@"
```

### CSV Processor

```bash
#!/usr/bin/env psh
# csvprocess.sh - Simple CSV file processor

process_csv() {
    local file="$1"
    local column="${2:-1}"
    
    if [ ! -f "$file" ]; then
        echo "Error: File not found: $file" >&2
        return 1
    fi
    
    echo "Processing column $column of $file"
    echo "===================================="
    
    local line_count=0
    local sum=0
    local is_numeric=1
    
    while read line; do
        ((line_count++))
        
        # Simple CSV parsing (assumes no quoted fields)
        local field_count=1
        local current_field=""
        local found_field=""
        
        for ((i = 0; i < ${#line}; i++)); do
            local char="${line:i:1}"
            
            if [ "$char" = "," ]; then
                if [ $field_count -eq $column ]; then
                    found_field="$current_field"
                    break
                fi
                ((field_count++))
                current_field=""
            else
                current_field="${current_field}${char}"
            fi
        done
        
        # Handle last field
        if [ -z "$found_field" ] && [ $field_count -eq $column ]; then
            found_field="$current_field"
        fi
        
        if [ -n "$found_field" ]; then
            echo "Row $line_count: $found_field"
            
            # Try to sum if numeric
            if [[ "$found_field" =~ ^[0-9]+$ ]]; then
                ((sum += found_field))
            else
                is_numeric=0
            fi
        fi
    done < "$file"
    
    echo "===================================="
    echo "Processed $line_count rows"
    
    if [ $is_numeric -eq 1 ] && [ $line_count -gt 0 ]; then
        echo "Sum of column $column: $sum"
        echo "Average: $((sum / line_count))"
    fi
}

# Main
if [ $# -eq 0 ]; then
    echo "Usage: $0 <csv_file> [column_number]"
    exit 1
fi

process_csv "$@"
```

## Development Tools

### Project Template Generator

```bash
#!/usr/bin/env psh
# mkproject.sh - Generate project directory structure

create_project() {
    local project_name="$1"
    local project_type="${2:-basic}"
    
    if [ -z "$project_name" ]; then
        echo "Error: Project name required" >&2
        return 1
    fi
    
    if [ -d "$project_name" ]; then
        echo "Error: Directory $project_name already exists" >&2
        return 1
    fi
    
    echo "Creating $project_type project: $project_name"
    
    # Create base structure
    mkdir -p "$project_name"/{src,tests,docs}
    
    # Create README
    cat > "$project_name/README.md" << EOF
# $project_name

## Description
Add project description here.

## Installation
Add installation instructions here.

## Usage
Add usage instructions here.

## License
Add license information here.
EOF
    
    # Create type-specific files
    case $project_type in
        python)
            touch "$project_name"/src/{__init__.py,main.py}
            touch "$project_name"/tests/{__init__.py,test_main.py}
            cat > "$project_name/requirements.txt" << EOF
# Add your dependencies here
EOF
            ;;
        shell)
            cat > "$project_name/src/main.sh" << EOF
#!/usr/bin/env psh
# $project_name main script

echo "Hello from $project_name!"
EOF
            chmod +x "$project_name/src/main.sh"
            ;;
        *)
            touch "$project_name/src/main"
            ;;
    esac
    
    # Create .gitignore
    cat > "$project_name/.gitignore" << EOF
# Temporary files
*.tmp
*.log

# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*~
EOF
    
    echo "Project $project_name created successfully!"
    echo "Structure:"
    ls -la "$project_name"
}

# Interactive mode
echo "Project Template Generator"
echo "========================="
echo
echo "Available project types:"
echo "1) basic - Simple project structure"
echo "2) python - Python project"
echo "3) shell - Shell script project"
echo

read -p "Enter project name: " name
read -p "Enter project type (1-3): " type_choice

case $type_choice in
    1) type="basic" ;;
    2) type="python" ;;
    3) type="shell" ;;
    *) type="basic" ;;
esac

create_project "$name" "$type"
```

### Test Runner

```bash
#!/usr/bin/env psh
# testrunner.sh - Simple test runner for shell scripts

run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected="$3"
    
    echo -n "Running $test_name... "
    
    # Run the test and capture output
    local output=$($test_command 2>&1)
    local exit_code=$?
    
    if [ "$expected" = "EXIT:$exit_code" ]; then
        echo "PASS"
        return 0
    elif [ "$output" = "$expected" ]; then
        echo "PASS"
        return 0
    else
        echo "FAIL"
        echo "  Expected: $expected"
        echo "  Got: $output (exit code: $exit_code)"
        return 1
    fi
}

# Test suite
run_tests() {
    local passed=0
    local failed=0
    
    echo "Running Test Suite"
    echo "=================="
    echo
    
    # Example tests
    if run_test "Echo test" "echo hello" "hello"; then
        ((passed++))
    else
        ((failed++))
    fi
    
    if run_test "Exit code test" "false" "EXIT:1"; then
        ((passed++))
    else
        ((failed++))
    fi
    
    if run_test "Arithmetic test" "echo $((2 + 2))" "4"; then
        ((passed++))
    else
        ((failed++))
    fi
    
    # Add your own tests here
    
    echo
    echo "=================="
    echo "Tests passed: $passed"
    echo "Tests failed: $failed"
    echo
    
    if [ $failed -eq 0 ]; then
        echo "All tests passed!"
        return 0
    else
        echo "Some tests failed."
        return 1
    fi
}

# Run the tests
run_tests
exit $?
```

## Function Libraries

### String Utilities Library

```bash
#!/usr/bin/env psh
# string_utils.sh - String manipulation functions

# Trim whitespace from string
trim() {
    local str="$1"
    # Remove leading whitespace
    while [[ "${str:0:1}" =~ [[:space:]] ]]; do
        str="${str:1}"
    done
    # Remove trailing whitespace
    while [[ "${str: -1}" =~ [[:space:]] ]]; do
        str="${str:0:-1}"
    done
    echo "$str"
}

# Convert to uppercase
to_upper() {
    local str="$1"
    echo "${str^^}"
}

# Convert to lowercase
to_lower() {
    local str="$1"
    echo "${str,,}"
}

# Capitalize first letter
capitalize() {
    local str="$1"
    echo "${str^}"
}

# Replace all occurrences
replace_all() {
    local str="$1"
    local search="$2"
    local replace="$3"
    echo "${str//$search/$replace}"
}

# Count occurrences of substring
count_substring() {
    local str="$1"
    local sub="$2"
    local temp="${str//$sub/}"
    local count=$(( (${#str} - ${#temp}) / ${#sub} ))
    echo $count
}

# Repeat string n times
repeat() {
    local str="$1"
    local n="$2"
    local result=""
    
    for ((i = 0; i < n; i++)); do
        result="${result}${str}"
    done
    
    echo "$result"
}

# Check if string starts with prefix
starts_with() {
    local str="$1"
    local prefix="$2"
    [[ "${str:0:${#prefix}}" = "$prefix" ]]
}

# Check if string ends with suffix
ends_with() {
    local str="$1"
    local suffix="$2"
    [[ "${str: -${#suffix}}" = "$suffix" ]]
}

# Example usage (uncomment to test)
# echo "Trim: '$(trim "  hello world  ")'"
# echo "Upper: $(to_upper "Hello World")"
# echo "Lower: $(to_lower "Hello World")"
# echo "Capitalize: $(capitalize "hello world")"
# echo "Replace: $(replace_all "hello world" "o" "0")"
# echo "Count 'l': $(count_substring "hello world" "l")"
# echo "Repeat: $(repeat "abc" 3)"
# starts_with "hello world" "hello" && echo "Starts with hello"
# ends_with "hello world" "world" && echo "Ends with world"
```

### Math Utilities Library

```bash
#!/usr/bin/env psh
# math_utils.sh - Mathematical functions

# Absolute value
abs() {
    local n=$1
    if ((n < 0)); then
        echo $((-n))
    else
        echo $n
    fi
}

# Minimum of two numbers
min() {
    local a=$1
    local b=$2
    if ((a < b)); then
        echo $a
    else
        echo $b
    fi
}

# Maximum of two numbers
max() {
    local a=$1
    local b=$2
    if ((a > b)); then
        echo $a
    else
        echo $b
    fi
}

# Power function (integer exponents)
pow() {
    local base=$1
    local exp=$2
    local result=1
    
    if ((exp < 0)); then
        echo "Error: Negative exponents not supported" >&2
        return 1
    fi
    
    for ((i = 0; i < exp; i++)); do
        ((result *= base))
    done
    
    echo $result
}

# Factorial
factorial() {
    local n=$1
    
    if ((n < 0)); then
        echo "Error: Factorial of negative number" >&2
        return 1
    elif ((n <= 1)); then
        echo 1
    else
        local result=1
        for ((i = 2; i <= n; i++)); do
            ((result *= i))
        done
        echo $result
    fi
}

# Greatest common divisor
gcd() {
    local a=$1
    local b=$2
    
    while ((b != 0)); do
        local temp=$b
        ((b = a % b))
        a=$temp
    done
    
    echo $(abs $a)
}

# Least common multiple
lcm() {
    local a=$1
    local b=$2
    local g=$(gcd $a $b)
    echo $(( (a * b) / g ))
}

# Sum of array elements (space-separated)
sum() {
    local total=0
    for num in $@; do
        ((total += num))
    done
    echo $total
}

# Average of array elements
avg() {
    local total=$(sum $@)
    local count=$#
    if ((count > 0)); then
        echo $((total / count))
    else
        echo 0
    fi
}

# Example usage (uncomment to test)
# echo "abs(-5) = $(abs -5)"
# echo "min(10, 5) = $(min 10 5)"
# echo "max(10, 5) = $(max 10 5)"
# echo "pow(2, 8) = $(pow 2 8)"
# echo "factorial(5) = $(factorial 5)"
# echo "gcd(48, 18) = $(gcd 48 18)"
# echo "lcm(12, 18) = $(lcm 12 18)"
# echo "sum 1 2 3 4 5 = $(sum 1 2 3 4 5)"
# echo "avg 10 20 30 40 50 = $(avg 10 20 30 40 50)"
```

## Tips for Writing PSH Scripts

1. **Always use proper quoting** - Double-quote variables to prevent word splitting
2. **Check return values** - Use `$?` or conditional execution (`&&`, `||`)
3. **Use functions** - Break complex scripts into reusable functions
4. **Add error handling** - Check if files/directories exist before operations
5. **Use local variables** - Prevent variable pollution in functions
6. **Comment your code** - Explain complex logic for future maintenance
7. **Test incrementally** - Test each function independently
8. **Handle edge cases** - Empty inputs, missing files, invalid arguments

## Script Template

Here's a template for well-structured PSH scripts:

```bash
#!/usr/bin/env psh
# script_name.sh - Brief description
#
# Usage: script_name.sh [options] arguments
#
# Options:
#   -h, --help    Show this help message
#   -v, --verbose Enable verbose output
#
# Author: Your Name
# Date: YYYY-MM-DD

# Global variables
VERBOSE=0
SCRIPT_NAME=$(basename "$0")

# Functions
usage() {
    echo "Usage: $SCRIPT_NAME [options] arguments"
    echo
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo "  -v, --verbose Enable verbose output"
    exit 0
}

error() {
    echo "Error: $1" >&2
    exit 1
}

verbose() {
    if [ $VERBOSE -eq 1 ]; then
        echo "Verbose: $1" >&2
    fi
}

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            break
            ;;
    esac
done

# Main logic
main() {
    verbose "Starting $SCRIPT_NAME"
    
    # Your code here
    
    verbose "Completed successfully"
}

# Run main function
main "$@"
```

## Dynamic Programming with eval

### Configuration-Driven Script

```bash
#!/usr/bin/env psh
# config_runner.sh - Execute commands based on configuration

# Function to read and execute config file
run_config() {
    local config_file="$1"
    
    if [ ! -f "$config_file" ]; then
        echo "Error: Config file not found: $config_file" >&2
        return 1
    fi
    
    echo "Processing configuration: $config_file"
    
    # Read configuration file
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        
        case "$key" in
            action)
                action_cmd="$value"
                ;;
            target)
                target_path="$value"
                ;;
            options)
                cmd_options="$value"
                ;;
            execute)
                # Build and execute command
                if [[ -n "$action_cmd" ]] && [[ -n "$target_path" ]]; then
                    echo "Executing: $action_cmd $cmd_options $target_path"
                    eval "$action_cmd $cmd_options '$target_path'"
                    action_cmd=""
                    target_path=""
                    cmd_options=""
                fi
                ;;
        esac
    done < "$config_file"
}

# Example config file (config.txt):
# action=ls
# options=-la
# target=/tmp
# execute=true
# 
# action=echo
# target=Hello from config
# execute=true

# Usage
if [ $# -eq 0 ]; then
    echo "Usage: $0 <config_file>"
    exit 1
fi

run_config "$1"
```

### Dynamic Environment Setup

```bash
#!/usr/bin/env psh
# env_setup.sh - Dynamic environment configuration

# Function to set up environment based on project type
setup_project_env() {
    local project_type="$1"
    local project_name="$2"
    
    case "$project_type" in
        python)
            env_vars=(
                "PYTHONPATH=./src:./lib"
                "VIRTUAL_ENV=venv"
                "PROJECT_TYPE=python"
            )
            ;;
        node)
            env_vars=(
                "NODE_PATH=./node_modules"
                "NODE_ENV=development"
                "PROJECT_TYPE=node"
            )
            ;;
        java)
            env_vars=(
                "CLASSPATH=./src:./lib/*"
                "JAVA_HOME=/usr/lib/jvm/default"
                "PROJECT_TYPE=java"
            )
            ;;
        *)
            echo "Unknown project type: $project_type" >&2
            return 1
            ;;
    esac
    
    # Set project-specific variables dynamically
    for var in "${env_vars[@]}"; do
        IFS='=' read -r name value <<< "$var"
        eval "export ${project_name}_${name}='$value'"
        eval "echo \"Set ${project_name}_${name}=\$${project_name}_${name}\""
    done
    
    # Create project activation function
    eval "${project_name}_activate() {
        echo \"Activating $project_name environment\"
        for var in \"${env_vars[@]}\"; do
            IFS='=' read -r name value <<< \"\$var\"
            eval \"export \$name='\$value'\"
        done
        export PS1=\"($project_name) \$PS1\"
    }"
    
    echo "Created activation function: ${project_name}_activate"
}

# Usage examples
echo "Setting up development environments..."
setup_project_env "python" "myapi"
setup_project_env "node" "frontend"

# Now you can activate with: myapi_activate or frontend_activate
```

### Command Template Engine

```bash
#!/usr/bin/env psh
# template_engine.sh - Process command templates

# Function to execute command template
execute_template() {
    local template="$1"
    shift
    
    # Parse template replacements
    local cmd="$template"
    
    for replacement in "$@"; do
        IFS='=' read -r placeholder value <<< "$replacement"
        cmd="${cmd//\{\{$placeholder\}\}/$value}"
    done
    
    echo "Executing: $cmd"
    eval "$cmd"
}

# Function to process batch templates
process_batch() {
    local template_file="$1"
    
    while IFS='|' read -r template vars; do
        # Skip comments
        [[ "$template" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$template" ]] && continue
        
        echo "Processing template: $template"
        
        # Parse variables
        IFS=',' read -ra var_array <<< "$vars"
        execute_template "$template" "${var_array[@]}"
        echo "---"
    done < "$template_file"
}

# Examples of use
echo "=== Single Template Example ==="
execute_template "echo 'Hello {{name}}, you are {{age}} years old'" \
    "name=Alice" "age=30"

execute_template "ls {{flags}} {{directory}}" \
    "flags=-la" "directory=/tmp"

# Example batch file (templates.txt):
# echo 'Processing {{file}} with {{tool}}'|file=data.csv,tool=awk
# mkdir -p {{path}}/{{project}}|path=/tmp,project=myapp
# cp {{source}} {{dest}}|source=file.txt,dest=/backup/file.txt

echo "=== Batch Template Example ==="
cat > /tmp/templates.txt << 'EOF'
echo 'Processing {{file}} with {{tool}}'|file=data.csv,tool=awk
mkdir -p {{path}}/{{project}}|path=/tmp,project=myapp
echo 'Project {{project}} created in {{path}}'|path=/tmp,project=myapp
EOF

process_batch "/tmp/templates.txt"
rm -f /tmp/templates.txt
```

### Dynamic Function Factory

```bash
#!/usr/bin/env psh
# function_factory.sh - Create functions dynamically

# Create getter/setter functions for a data structure
create_object() {
    local object_name="$1"
    shift
    
    echo "Creating object: $object_name"
    
    # Create getter and setter for each field
    for field in "$@"; do
        # Create getter function
        eval "${object_name}_get_${field}() {
            eval \"echo \\\$${object_name}_${field}\"
        }"
        
        # Create setter function
        eval "${object_name}_set_${field}() {
            eval \"${object_name}_${field}=\\\$1\"
        }"
        
        echo "  - Created ${object_name}_get_${field} and ${object_name}_set_${field}"
    done
    
    # Create show function
    eval "${object_name}_show() {
        echo \"Object: $object_name\"
        for field in $*; do
            eval \"echo \\\"  \$field: \\\$${object_name}_\$field\\\"\"
        done
    }"
    
    echo "  - Created ${object_name}_show"
}

# Create validation functions
create_validator() {
    local validator_name="$1"
    local validation_rule="$2"
    
    eval "${validator_name}() {
        local value=\"\$1\"
        if $validation_rule; then
            return 0
        else
            echo \"Validation failed for: \$value\" >&2
            return 1
        fi
    }"
    
    echo "Created validator: $validator_name"
}

# Usage examples
echo "=== Creating User Object ==="
create_object "user" "name" "email" "age"

# Use the created functions
user_set_name "Alice"
user_set_email "alice@example.com"
user_set_age "30"

echo "Getting user data:"
echo "Name: $(user_get_name)"
echo "Email: $(user_get_email)"
echo "Age: $(user_get_age)"

echo
user_show

echo
echo "=== Creating Validators ==="
create_validator "validate_email" '[[ "$value" =~ ^[^@]+@[^@]+$ ]]'
create_validator "validate_age" '[[ "$value" =~ ^[0-9]+$ ]] && (( value >= 0 && value <= 150 ))'

# Test validators
echo "Testing validators:"
validate_email "alice@example.com" && echo "Email valid"
validate_email "invalid-email" || echo "Email invalid"
validate_age "30" && echo "Age valid"
validate_age "200" || echo "Age invalid"
```

## Next Steps

- Experiment with these scripts to understand PSH capabilities
- Modify scripts to suit your specific needs
- Combine techniques from different examples
- Pay special attention to the eval examples for dynamic programming
- Share your scripts with the PSH community

Remember that PSH is designed for educational purposes. These scripts demonstrate core shell programming concepts while working within PSH's current feature set. When using eval, always validate input carefully to maintain security.