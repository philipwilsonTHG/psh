# Chapter 9: Input/Output Redirection

I/O redirection is one of the most powerful features of the shell, allowing you to control where commands get their input and send their output. PSH supports all standard redirection operators, here documents, here strings, and advanced file descriptor manipulation.

## 9.1 Standard Streams (stdin, stdout, stderr)

Every process has three standard streams:
- **stdin** (0): Standard input - where commands read from
- **stdout** (1): Standard output - where commands write normal output
- **stderr** (2): Standard error - where commands write error messages

```bash
# Default behavior
psh$ echo "Hello"                    # stdout to terminal
Hello

psh$ read name                       # stdin from terminal
Alice
psh$ echo $name
Alice

psh$ ls /nonexistent                 # stderr to terminal
ls: cannot access '/nonexistent': No such file or directory

# File descriptors
# 0 = stdin
# 1 = stdout  
# 2 = stderr
```

## 9.2 Output Redirection (>, >>)

### Basic Output Redirection

```bash
# Redirect stdout to file (overwrite)
psh$ echo "Hello World" > output.txt
psh$ cat output.txt
Hello World

# Overwrite replaces existing content
psh$ echo "New content" > output.txt
psh$ cat output.txt
New content

# Append to file
psh$ echo "Line 1" > file.txt
psh$ echo "Line 2" >> file.txt
psh$ echo "Line 3" >> file.txt
psh$ cat file.txt
Line 1
Line 2
Line 3

# Create empty file
psh$ > empty.txt
psh$ ls -l empty.txt
-rw-r--r-- 1 alice alice 0 Jan 15 10:00 empty.txt

# Multiple commands
psh$ (echo "Header"; date; echo "Footer") > report.txt
psh$ cat report.txt
Header
Mon Jan 15 10:00:00 PST 2024
Footer
```

### Preventing Accidental Overwrites

```bash
# noclobber option (when implemented)
psh$ set -o noclobber
psh$ echo "data" > existing.txt
psh: existing.txt: cannot overwrite existing file

# Force overwrite with >|
psh$ echo "data" >| existing.txt    # Forces overwrite

# Or use append
psh$ echo "data" >> existing.txt    # Safe with noclobber
```

## 9.3 Input Redirection (<)

Input redirection reads from files instead of the keyboard:

```bash
# Read from file
psh$ wc -l < /etc/passwd
35

# Equivalent to
psh$ cat /etc/passwd | wc -l
35

# But more efficient (no cat process)

# Read variables from file
psh$ echo "Alice" > name.txt
psh$ read name < name.txt
psh$ echo "Hello, $name"
Hello, Alice

# Use with loops
psh$ cat > numbers.txt << EOF
1
2
3
4
5
EOF

psh$ while read num; do
>     echo "Number: $num"
> done < numbers.txt
Number: 1
Number: 2
Number: 3
Number: 4
Number: 5

# Sort a file
psh$ sort < unsorted.txt > sorted.txt
```

## 9.4 Error Redirection (2>, 2>>)

### Redirecting stderr

```bash
# Redirect stderr to file
psh$ ls /nonexistent 2> errors.txt
psh$ cat errors.txt
ls: cannot access '/nonexistent': No such file or directory

# Append stderr
psh$ ls /another_nonexistent 2>> errors.txt
psh$ cat errors.txt
ls: cannot access '/nonexistent': No such file or directory
ls: cannot access '/another_nonexistent': No such file or directory

# Discard stderr
psh$ ls /nonexistent 2> /dev/null
# No error output

# Separate stdout and stderr
psh$ find /etc -name "*.conf" > configs.txt 2> errors.txt

# Both to same file (wrong way)
psh$ command > output.txt 2> output.txt    # Race condition!

# Both to same file (right way)
psh$ command > output.txt 2>&1
```

### Practical stderr Handling

```bash
# Log errors while showing output
psh$ make 2> build_errors.log | tee build_output.log

# Silent command with error check
psh$ if command 2>/dev/null; then
>     echo "Success"
> else
>     echo "Failed"
> fi

# Capture both streams separately
psh$ command 1> stdout.txt 2> stderr.txt

# Swap stdout and stderr
psh$ command 3>&1 1>&2 2>&3 3>&-
# Complex but occasionally useful
```

## 9.5 Combining Streams (2>&1, >&2)

### Redirecting stderr to stdout

```bash
# Send stderr to stdout
psh$ ls /nonexistent 2>&1
ls: cannot access '/nonexistent': No such file or directory

# Capture both in a file
psh$ command > output.txt 2>&1

# Order matters!
psh$ command 2>&1 > output.txt    # Wrong - stderr still to terminal

# Pipe both stdout and stderr
psh$ find / -name "*.log" 2>&1 | grep -v "Permission denied"

# Shorthand for > file 2>&1
psh$ command &> output.txt         # Bash style (if supported)
psh$ command >& output.txt         # Csh style (if supported)
```

### Redirecting stdout to stderr

```bash
# Send output to stderr
psh$ echo "This is an error" >&2
This is an error    # Appears on stderr

# Useful in functions
error() {
    echo "Error: $*" >&2
}

warn() {
    echo "Warning: $*" >&2
}

# Usage
psh$ error "File not found"
Error: File not found

# In scripts
if [ ! -f "$file" ]; then
    echo "Cannot find $file" >&2
    exit 1
fi
```

## 9.6 Here Documents (<<, <<-)

Here documents provide multi-line input directly in scripts:

### Basic Here Documents

```bash
# Basic here document
psh$ cat << EOF
Line 1
Line 2
Line 3
EOF
Line 1
Line 2
Line 3

# With variable expansion
psh$ name="Alice"
psh$ cat << END
Hello, $name!
Today is $(date)
Your home is $HOME
END
Hello, Alice!
Today is Mon Jan 15 10:00:00 PST 2024
Your home is /home/alice

# Quoted delimiter prevents expansion
psh$ cat << 'EOF'
$HOME is literal
$(date) is literal
EOF
$HOME is literal
$(date) is literal

# Tab removal with <<-
psh$ cat <<- EOF
	Leading tabs removed
	But spaces remain
	    Mixed indentation
EOF
Leading tabs removed
But spaces remain
    Mixed indentation
```

### Here Documents in Scripts

```bash
#!/usr/bin/env psh
# Generate configuration files

# Create config file
cat > app.conf << EOF
# Application Configuration
# Generated on $(date)

[server]
host = localhost
port = 8080
workers = 4

[database]
driver = postgresql
host = ${DB_HOST:-localhost}
port = ${DB_PORT:-5432}
name = ${DB_NAME:-myapp}

[logging]
level = ${LOG_LEVEL:-info}
file = /var/log/app.log
EOF

# Create SQL script
cat > setup.sql << 'SQL'
-- Database setup script
CREATE DATABASE IF NOT EXISTS myapp;
USE myapp;

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, email) VALUES
    ('admin', 'admin@example.com'),
    ('user1', 'user1@example.com');
SQL

# Multi-line message
mail -s "Report" user@example.com << MESSAGE
Dear User,

Here is your daily report for $(date +%Y-%m-%d):

System Status: OK
Disk Usage: $(df -h / | awk 'NR==2 {print $5}')
Active Users: $(who | wc -l)

Best regards,
System Administrator
MESSAGE
```

## 9.7 Here Strings (<<<)

Here strings provide a single line of input:

```bash
# Basic here string
psh$ wc -w <<< "Hello World"
2

# Variable input
psh$ name="Alice"
psh$ read first last <<< "$name Smith"
psh$ echo "First: $first, Last: $last"
First: Alice, Last: Smith

# Command output as here string
psh$ read user host <<< "$(echo $USER@$HOSTNAME)"

# Useful for parsing
psh$ IFS=: read user pass uid gid rest <<< "root:x:0:0:root:/root:/bin/bash"
psh$ echo "User: $user, UID: $uid"
User: root, UID: 0

# Loop with here string
psh$ while read word; do
>     echo "Word: $word"
> done <<< "one two three"
Word: one two three

# For word splitting, use printf
psh$ printf '%s\n' one two three | while read word; do
>     echo "Word: $word"
> done
Word: one
Word: two
Word: three
```

## 9.8 File Descriptors

Beyond standard streams, you can work with custom file descriptors:

```bash
# Open file descriptor for reading
psh$ exec 3< input.txt

# Read from descriptor 3
psh$ read line <&3
psh$ echo "First line: $line"

# Open file descriptor for writing
psh$ exec 4> output.txt

# Write to descriptor 4
psh$ echo "Hello" >&4

# Close file descriptors
psh$ exec 3<&-
psh$ exec 4>&-

# Duplicate file descriptors
psh$ exec 5>&1      # Save stdout
psh$ exec 1> log.txt # Redirect stdout
psh$ echo "This goes to log"
psh$ exec 1>&5      # Restore stdout
psh$ exec 5>&-      # Close saved descriptor

# Read and write to same file
psh$ exec 3<> file.txt
```

### Advanced File Descriptor Usage

```bash
#!/usr/bin/env psh
# Logging with multiple file descriptors

# Setup logging
exec 3> debug.log    # Debug messages
exec 4> info.log     # Info messages  
exec 5> error.log    # Error messages

# Logging functions
debug() { echo "[DEBUG] $*" >&3; }
info() { echo "[INFO] $*" >&4; }
error() { echo "[ERROR] $*" >&5; }

# Use logging
debug "Script started"
info "Processing files"

for file in *.txt; do
    if [ -f "$file" ]; then
        info "Processing $file"
        debug "File size: $(wc -c < "$file")"
    else
        error "File not found: $file"
    fi
done

# Cleanup
exec 3>&- 4>&- 5>&-

# Temporary redirection
{
    echo "This block"
    echo "goes to"
    echo "block.txt"
} > block.txt

# Swapping streams
swap_streams() {
    # Swap stdout and stderr
    "$@" 3>&1 1>&2 2>&3 3>&-
}

# Test it
swap_streams echo "This goes to stderr"
```

## 9.9 Redirections on Control Structures

PSH allows redirections on entire control structures:

### Loops with Redirection

```bash
# Redirect entire loop output
psh$ for i in 1 2 3; do
>     echo "Number: $i"
> done > numbers.txt

psh$ cat numbers.txt
Number: 1
Number: 2
Number: 3

# While loop reading from file
psh$ while read line; do
>     echo "Processing: $line"
> done < input.txt > output.txt 2> errors.txt

# Redirect to loop input
psh$ for word in $(cat < words.txt); do
>     echo "Word: $word"
> done

# Append mode
psh$ for file in *.log; do
>     echo "=== $file ===" 
>     cat "$file"
> done >> combined.log
```

### Conditional Redirections

```bash
# Redirect if statement
psh$ if [ -f data.txt ]; then
>     cat data.txt
>     echo "---"
>     wc -l data.txt
> fi > report.txt

# Redirect case statement
psh$ case "$option" in
>     start)
>         echo "Starting service..."
>         systemctl start myservice
>         ;;
>     stop)
>         echo "Stopping service..."
>         systemctl stop myservice
>         ;;
> esac 2> service_errors.log

# Function with redirection
process_files() {
    for file in "$@"; do
        echo "Processing $file"
        # Process file
    done
} > process.log 2>&1
```

## Practical Examples

### Log File Processor

```bash
#!/usr/bin/env psh
# Advanced log processing with I/O redirection

# Create named pipes for real-time processing
mkfifo /tmp/errors.pipe /tmp/warnings.pipe /tmp/info.pipe 2>/dev/null

# Start background processors
grep ERROR < /tmp/errors.pipe > errors.log &
ERROR_PID=$!

grep WARN < /tmp/warnings.pipe > warnings.log &
WARN_PID=$!

grep INFO < /tmp/info.pipe > info.log &
INFO_PID=$!

# Process main log
tail -f /var/log/app.log | while read line; do
    echo "$line" | tee /tmp/errors.pipe /tmp/warnings.pipe /tmp/info.pipe > all.log
done

# Cleanup on exit
trap "kill $ERROR_PID $WARN_PID $INFO_PID; rm -f /tmp/*.pipe" EXIT
```

### Backup Script with Logging

```bash
#!/usr/bin/env psh
# Backup with comprehensive logging

BACKUP_DIR="/backup"
LOG_DIR="/var/log/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Setup logging
exec 3> "$LOG_DIR/backup_$DATE.log"
exec 4>&1  # Save stdout

# Redirect stdout to log, keep stderr on terminal
exec 1>&3

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

show() {
    # Show on terminal and log
    echo "$*" >&4
    log "$*"
}

error() {
    echo "ERROR: $*" >&2
    log "ERROR: $*"
}

# Start backup
show "Starting backup at $(date)"

# Backup function
backup_directory() {
    local src="$1"
    local name="$(basename "$src")"
    local target="$BACKUP_DIR/${name}_$DATE.tar.gz"
    
    log "Backing up $src to $target"
    
    if tar -czf "$target" -C "$(dirname "$src")" "$name" 2>&1; then
        local size=$(du -h "$target" | cut -f1)
        show "✓ $name backed up successfully ($size)"
    else
        error "Failed to backup $name"
        return 1
    fi
}

# Backup multiple directories
for dir in /home /etc /var/www; do
    if [ -d "$dir" ]; then
        backup_directory "$dir"
    else
        error "Directory not found: $dir"
    fi
done

# Summary
show "Backup completed at $(date)"
log "Disk usage: $(df -h "$BACKUP_DIR" | tail -1)"

# Restore descriptors
exec 1>&4 4>&- 3>&-

# Email report
mail -s "Backup Report $DATE" admin@example.com < "$LOG_DIR/backup_$DATE.log"
```

### Interactive Script with Clean I/O

```bash
#!/usr/bin/env psh
# Interactive menu with proper I/O handling

# Save and restore terminal
exec 5<&0  # Save stdin
exec 6>&1  # Save stdout

# Temporary files for output
TEMP_OUT=$(mktemp)
TEMP_ERR=$(mktemp)

# Cleanup function
cleanup() {
    exec 0<&5 5<&-  # Restore stdin
    exec 1>&6 6>&-  # Restore stdout
    rm -f "$TEMP_OUT" "$TEMP_ERR"
}
trap cleanup EXIT

# Menu function
show_menu() {
    cat << 'MENU'
=== System Tools ===
1) Show system info
2) Check disk space  
3) View process list
4) Network status
5) Exit
MENU
}

# Process choice with output capture
process_choice() {
    local choice=$1
    
    # Capture output and errors
    case $choice in
        1) uname -a; uptime; free -h ;;
        2) df -h ;;
        3) ps aux | head -20 ;;
        4) netstat -tln 2>/dev/null || ss -tln ;;
        5) return 1 ;;
        *) echo "Invalid choice" >&2; return 0 ;;
    esac > "$TEMP_OUT" 2> "$TEMP_ERR"
    
    # Display results
    if [ -s "$TEMP_OUT" ]; then
        echo -e "\n--- Output ---"
        cat "$TEMP_OUT"
    fi
    
    if [ -s "$TEMP_ERR" ]; then
        echo -e "\n--- Errors ---" >&2
        cat "$TEMP_ERR" >&2
    fi
    
    return 0
}

# Main loop
while true; do
    show_menu
    read -p "Enter choice: " choice
    
    process_choice "$choice" || break
    
    echo -e "\nPress Enter to continue..."
    read
    clear
done

echo "Goodbye!"
```

### Data Pipeline Builder

```bash
#!/usr/bin/env psh
# Build complex data processing pipelines

# Pipeline components
extract_data() {
    local source="$1"
    case "$source" in
        *.gz)  zcat "$source" ;;
        *.bz2) bzcat "$source" ;;
        *.zip) unzip -p "$source" ;;
        *)     cat "$source" ;;
    esac
}

transform_data() {
    local format="$1"
    case "$format" in
        csv)
            # Convert to CSV
            awk '{print $1","$2","$3}'
            ;;
        json)
            # Convert to JSON
            awk '{print "{\"col1\":\""$1"\",\"col2\":\""$2"\",\"col3\":\""$3"\"}"}'
            ;;
        tsv)
            # Tab-separated
            awk '{print $1"\t"$2"\t"$3}'
            ;;
    esac
}

# Build pipeline
process_file() {
    local input="$1"
    local output="$2"
    local format="${3:-csv}"
    local errors="errors_$(date +%s).log"
    
    {
        extract_data "$input" |
        grep -v "^#" |              # Remove comments
        sed 's/[[:space:]]\+/ /g' | # Normalize whitespace  
        transform_data "$format" |
        sort |
        uniq
    } > "$output" 2> "$errors"
    
    # Check results
    if [ -s "$errors" ]; then
        echo "Errors occurred during processing:" >&2
        cat "$errors" >&2
    else
        rm -f "$errors"
    fi
    
    echo "Processed $(wc -l < "$output") lines"
}

# Usage
process_file "data.txt.gz" "output.csv" "csv"
process_file "logs.bz2" "output.json" "json"
```

## Common Patterns and Tips

### Safe Redirection Practices

```bash
# Always check before overwriting
if [ -f important.txt ]; then
    echo "File exists, backing up..."
    cp important.txt important.txt.bak
fi
command > important.txt

# Use tee for both display and save
command | tee output.txt

# Append with timestamp
echo "[$(date)] Log entry" >> logfile.txt

# Atomic file replacement
command > newfile.tmp && mv newfile.tmp finalfile.txt
```

### Debugging with Redirection

```bash
# Debug mode with conditional output
DEBUG=${DEBUG:-0}
debug() {
    [ "$DEBUG" -eq 1 ] && echo "DEBUG: $*" >&2
}

# Verbose logging
VERBOSE=${VERBOSE:-0}
exec 3>/dev/null
[ "$VERBOSE" -eq 1 ] && exec 3>&2

echo "Always shown"
echo "Only in verbose mode" >&3
```

## Summary

I/O redirection in PSH provides powerful control over data flow:

1. **Basic Redirection**: `>` (overwrite), `>>` (append), `<` (input)
2. **Error Handling**: `2>`, `2>>`, `2>&1` for stderr management
3. **Here Documents**: `<<` for multi-line input
4. **Here Strings**: `<<<` for single-line input
5. **File Descriptors**: Advanced I/O with numbered descriptors
6. **Combined Redirections**: Multiple streams to different destinations
7. **Control Structure Redirections**: Redirect entire loops and conditionals

Key concepts:
- Three standard streams: stdin (0), stdout (1), stderr (2)
- Redirection order matters: `> file 2>&1` vs `2>&1 > file`
- Use `2>&1` to combine stderr with stdout
- Here documents can expand variables or be literal
- File descriptors enable complex I/O patterns
- Always handle errors appropriately

I/O redirection is fundamental to shell scripting, enabling log files, error handling, data processing pipelines, and clean separation of output types. In the next chapter, we'll explore pipelines and command lists.

---

[← Previous: Chapter 8 - Quoting and Escaping](08_quoting_and_escaping.md) | [Next: Chapter 10 - Pipelines and Lists →](10_pipelines_and_lists.md)