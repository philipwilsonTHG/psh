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

