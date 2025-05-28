#!/usr/bin/env psh

# Sample shell function demonstrating conditional statements in psh
# This function checks if a file exists and performs different actions

check_file() {
    if [ -z "$1" ]; then
        echo "Usage: check_file <filename>"
        return 1
    fi
    
    if [ -f "$1" ]; then
        echo "File '$1' exists and is a regular file"
        if [ -r "$1" ]; then
            echo "File is readable"
            echo "File size: $(wc -c < "$1") bytes"
        else
            echo "File is not readable"
        fi
    elif [ -d "$1" ]; then
        echo "'$1' exists but is a directory"
    else
        echo "File '$1' does not exist"
        echo "Would you like me to create it? (This is just a demo message)"
    fi
}

# Another example function using arithmetic conditionals
check_number() {
    if [ -z "$1" ]; then
        echo "Usage: check_number <number>"
        return 1
    fi
    
    if [ "$1" -gt 100 ]; then
        echo "$1 is greater than 100"
    elif [ "$1" -gt 50 ]; then
        echo "$1 is between 51 and 100"
    elif [ "$1" -gt 0 ]; then
        echo "$1 is between 1 and 50"
    elif [ "$1" -eq 0 ]; then
        echo "$1 is zero"
    else
        echo "$1 is negative"
    fi
}

# Example function with nested conditionals
backup_file() {
    if [ -z "$1" ]; then
        echo "Usage: backup_file <filename>"
        return 1
    fi
    
    if [ -f "$1" ]; then
        backup_name="${1}.backup"
        if [ -f "$backup_name" ]; then
            echo "Backup already exists: $backup_name"
            echo "Creating numbered backup instead"
            counter=1
            while [ -f "${backup_name}.${counter}" ]; do
                counter=$((counter + 1))
            done
            backup_name="${backup_name}.${counter}"
        fi
        echo "Creating backup: $backup_name"
        # In a real implementation, you would copy the file here
        echo "cp '$1' '$backup_name'"
    else
        echo "Error: File '$1' does not exist"
        return 1
    fi
}

echo "Sample functions loaded:"
echo "  check_file <filename>    - Check if file exists and show info"
echo "  check_number <number>    - Categorize a number"
echo "  backup_file <filename>   - Create a backup with conditional naming"
echo ""
echo "Example usage:"
echo "  check_file /etc/passwd"
echo "  check_number 75"
echo "  backup_file sample_function.sh"