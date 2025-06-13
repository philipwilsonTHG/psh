#!/usr/bin/env psh
# Demo script for validation - contains various issues

# Undefined variable usage
echo "Welcome $UNDEFINED_USER"

# Typo in command
grpe "pattern" file.txt

# Unquoted variable that may cause word splitting
FILES=$HOME/docs/*.txt
ls $FILES

# Deprecated command
which python

# Dangerous eval usage
USER_INPUT="echo test"
eval $USER_INPUT

# World-writable permissions
chmod 777 /tmp/myfile

# Function with local variable
process_files() {
    local count=0
    for file in $@; do  # Unquoted $@
        # Potential undefined variable
        echo "Processing: $file in $WORK_DIR"
        count=$((count + 1))
    done
    echo "Processed $count files"
}

# Using undefined function variable outside
echo "Total: $count"

# Command injection risk
echo "User said: $USER_COMMENT; rm -rf /"

# Missing quotes on test
if [ -f $SOME_FILE ]; then
    echo "File exists"
fi

# Case statement with duplicate patterns
case "$ACTION" in
    start)
        echo "Starting..."
        ;;
    stop)
        echo "Stopping..."
        ;;
    start)  # Duplicate!
        echo "Already started?"
        ;;
esac

# Empty command
 

# Good practices that should not trigger warnings
HOME_BACKUP="${HOME}_backup"
echo "Backing up to ${HOME_BACKUP:-/tmp/backup}"

# Intentional glob with ls
ls *.sh

# Properly quoted variable
echo "User: $USER"

# Using special variables (should not warn)
echo "Script: $0, Args: $@, Count: $#"
echo "PID: $$, Last exit: $?"