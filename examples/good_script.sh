#!/usr/bin/env psh
# Example of a well-written script that passes validation

# Define variables before use
WORK_DIR="/tmp/work"
USER="$(whoami)"

# Properly quoted variables
echo "Welcome, $USER"

# Using grep correctly (no typo)
grep "pattern" file.txt 2>/dev/null || echo "Pattern not found"

# Quoted variables to prevent word splitting
FILES="$HOME/docs/*.txt"
if [ -d "$HOME/docs" ]; then
    ls "$FILES" 2>/dev/null || echo "No text files found"
fi

# Using command -v instead of which (portable)
if command -v python >/dev/null 2>&1; then
    echo "Python is installed"
fi

# Safe command execution without eval
COMMAND="echo"
ARGS="Hello, World!"
$COMMAND "$ARGS"

# Secure file permissions
touch /tmp/myfile
chmod 644 /tmp/myfile  # Read/write for owner, read for others

# Function with proper variable scoping
process_files() {
    local count=0
    local work_dir="${WORK_DIR:-/tmp}"
    
    # Properly quoted $@
    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "Processing: $file in $work_dir"
            count=$((count + 1))
        fi
    done
    echo "Processed $count files"
}

# Call function with arguments
process_files *.sh

# Proper quoting in test commands
SOME_FILE="/etc/passwd"
if [ -f "$SOME_FILE" ]; then
    echo "File exists: $SOME_FILE"
fi

# Case statement without duplicates
ACTION="${1:-start}"
case "$ACTION" in
    start)
        echo "Starting service..."
        ;;
    stop)
        echo "Stopping service..."
        ;;
    restart)
        echo "Restarting service..."
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac

# Using special variables correctly
echo "Script: $0"
echo "Arguments: $#"
echo "All args: $*"
echo "PID: $$"
echo "Last exit status: $?"

# Array handling (if supported)
declare -a myarray
myarray=(one two three)
echo "Array elements: ${myarray[@]}"

exit 0