#!/usr/bin/env psh
# Demo script showing shift, getopts, and command builtins

echo "=== Shift Demo ==="
echo "Original args: $@"
echo "Arg count: $#"

# Shift once
shift
echo "After shift: $@"
echo "Arg count: $#"

# Shift by 2
shift 2
echo "After shift 2: $@"
echo "Arg count: $#"

echo -e "\n=== Getopts Demo ==="
# Reset for getopts demo
set -- -v -f myfile.txt -o output.log remaining args

# Parse options
verbose=0
file=""
output=""

while getopts "vf:o:" opt; do
    case $opt in
        v)
            verbose=1
            echo "Verbose mode enabled"
            ;;
        f)
            file="$OPTARG"
            echo "File: $file"
            ;;
        o)
            output="$OPTARG"
            echo "Output: $output"
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            ;;
    esac
done

# Shift past the options
shift $((OPTIND - 1))
echo "Remaining args after getopts: $@"

echo -e "\n=== Command Demo ==="
# Show command info
echo "Checking 'echo' command:"
command -v echo
command -V echo

echo -e "\nChecking 'grep' command:"
command -v grep
command -V grep

# Create a function that shadows a command
ls() {
    echo "This is the ls function, not the real ls!"
}

echo -e "\nCalling ls normally (uses function):"
ls

echo -e "\nCalling ls with command (bypasses function):"
command ls -la | head -5

echo -e "\n=== Combined Example: Option Parser ==="
# Function that uses all three builtins
parse_args() {
    local verbose=0
    local debug=0
    local file=""
    
    # Parse options with getopts
    while getopts "vdf:" opt; do
        case $opt in
            v) verbose=1 ;;
            d) debug=1 ;;
            f) file="$OPTARG" ;;
        esac
    done
    
    # Shift past options
    shift $((OPTIND - 1))
    
    # Show results
    echo "Options parsed:"
    echo "  Verbose: $verbose"
    echo "  Debug: $debug"
    echo "  File: $file"
    echo "  Remaining args: $@"
    
    # Use command to ensure we get real utilities
    if [ -n "$file" ] && command -v cat >/dev/null; then
        echo "Would process file with: command cat '$file'"
    fi
}

# Test the function
echo "Calling: parse_args -v -d -f config.txt arg1 arg2"
OPTIND=1  # Reset OPTIND for function call
parse_args -v -d -f config.txt arg1 arg2