# Chapter 4: Built-in Commands

Built-in commands are implemented directly within PSH rather than as external programs. They execute faster and have direct access to the shell's internal state, making them essential for shell operation.

## 4.1 Core Built-ins

These fundamental built-ins control the shell itself.

### exit - Exit the Shell

The `exit` command terminates the current shell session:

```bash
# Exit with success status
psh$ exit
$ # Back to parent shell

# Exit with specific status code
psh$ exit 0    # Success
psh$ exit 1    # General error
psh$ exit 127  # Command not found

# Exit status in scripts
psh$ cat > check_and_exit.sh << 'EOF'
#!/usr/bin/env psh
if [ ! -f required.txt ]; then
    echo "Error: required.txt not found"
    exit 1
fi
echo "File found, continuing..."
exit 0
EOF
```

### : (colon) - Null Command

The `:` command does nothing but always returns success (0):

```bash
# Basic usage
psh$ :
psh$ echo $?
0

# Useful for infinite loops
psh$ while :; do
>     echo "Press Ctrl-C to stop"
>     sleep 1
> done

# Placeholder in conditionals
psh$ if [ -f file.txt ]; then
>     :  # TODO: Add file processing here
> else
>     echo "File not found"
> fi

# Parameter expansion side effects
psh$ : ${VAR:=default}  # Set VAR to default if unset
psh$ echo $VAR
default
```

### true and false - Boolean Commands

These commands return fixed exit statuses:

```bash
# true always succeeds
psh$ true
psh$ echo $?
0

# false always fails
psh$ false
psh$ echo $?
1

# Useful in conditionals
psh$ if true; then echo "Always runs"; fi
Always runs

psh$ if false; then echo "Never runs"; fi

# Testing logic
psh$ true && echo "Success" || echo "Failure"
Success

psh$ false && echo "Success" || echo "Failure"  
Failure

# Infinite loops
psh$ while true; do
>     # Your code here
>     break  # Need explicit break
> done
```

## 4.2 Directory Navigation

### cd - Change Directory

Navigate through the filesystem:

```bash
# Change to specific directory
psh$ cd /tmp
psh$ pwd
/tmp

# Go to home directory
psh$ cd
psh$ pwd
/home/alice

# Also with ~
psh$ cd ~
psh$ pwd
/home/alice

# Previous directory
psh$ cd /tmp
psh$ cd /var
psh$ cd -
/tmp
psh$ pwd
/tmp

# Relative paths
psh$ cd ..        # Parent directory
psh$ cd ../..     # Two levels up
psh$ cd ./subdir  # Subdirectory

# Following symlinks
psh$ ln -s /tmp mylink
psh$ cd mylink
psh$ pwd
/tmp
```

### pwd - Print Working Directory

Show the current directory:

```bash
# Basic usage
psh$ pwd
/home/alice

# In scripts, capture the directory
psh$ current_dir=$(pwd)
psh$ echo "We are in: $current_dir"
We are in: /home/alice

# After following symlinks
psh$ mkdir -p /tmp/real_dir
psh$ ln -s /tmp/real_dir /tmp/link_dir
psh$ cd /tmp/link_dir
psh$ pwd
/tmp/real_dir
```

## 4.3 Environment Management

### export - Set Environment Variables

Export variables to child processes:

```bash
# Export a new variable
psh$ export MYVAR="Hello"
psh$ echo $MYVAR
Hello

# Export existing variable
psh$ NAME="Alice"
psh$ export NAME
psh$ psh -c 'echo $NAME'  # Child process sees it
Alice

# Export with assignment
psh$ export PATH="$PATH:/my/custom/bin"

# View all exported variables
psh$ export
DISPLAY=:0
HOME=/home/alice
LANG=en_US.UTF-8
MYVAR=Hello
NAME=Alice
PATH=/usr/local/bin:/usr/bin:/bin:/my/custom/bin
...

# Export multiple variables
psh$ export VAR1=value1 VAR2=value2 VAR3=value3
```

### unset - Remove Variables

Remove variables and functions:

```bash
# Unset a variable
psh$ VAR="test"
psh$ echo $VAR
test
psh$ unset VAR
psh$ echo $VAR

# Unset multiple variables
psh$ A=1 B=2 C=3
psh$ unset A B C

# Unset a function
psh$ hello() { echo "Hello!"; }
psh$ hello
Hello!
psh$ unset -f hello
psh$ hello
psh: hello: command not found

# Unset doesn't fail for non-existent variables
psh$ unset NONEXISTENT  # No error
```

### env - Display Environment

Show or modify the environment:

```bash
# Show all environment variables
psh$ env
PATH=/usr/local/bin:/usr/bin:/bin
HOME=/home/alice
USER=alice
SHELL=/usr/bin/psh
...

# Search for specific variables
psh$ env | grep HOME
HOME=/home/alice

# Run command with modified environment
psh$ env VAR=value command
psh$ env PATH=/custom/path which ls
/custom/path/ls

# Clear environment and run command
psh$ env -i /bin/echo $HOME
# (empty - HOME not set in cleared environment)
```

### set - Shell Options and Parameters

Configure shell behavior and positional parameters:

```bash
# Show all shell variables
psh$ set
DISPLAY=:0
HOME=/home/alice
NAME=Alice
PS1=psh$ 
PS2=> 
...

# Set positional parameters
psh$ set apple banana cherry
psh$ echo $1
apple
psh$ echo $2
banana
psh$ echo $@
apple banana cherry

# Use -- to handle arguments starting with -
psh$ set -- -x file.txt
psh$ echo $1
-x

# Show shell options
psh$ set -o
edit_mode            emacs
debug-ast            off
debug-tokens         off

# Enable debug options
psh$ set -o debug-ast
psh$ echo test
=== AST ===
TopLevel:
  CommandList:
    AndOrList:
      Pipeline:
        Command: ['echo', 'test']
=== End AST ===
test

# Disable debug options
psh$ set +o debug-ast
```

### declare - Declare Variables and Functions

Display or set variable attributes:

```bash
# Show all variables
psh$ declare
DISPLAY=:0
HOME=/home/alice
MYVAR=Hello
PS1=psh$ 
...

# Show all functions
psh$ declare -f
hello() {
    echo "Hello, $1!"
}
greet() {
    echo "Greetings!"
}

# Show specific function
psh$ declare -f hello
hello() {
    echo "Hello, $1!"
}

# Currently, declare mainly shows information
# Full attribute support (like -r for readonly) is planned
```

## 4.4 Input/Output

### echo - Display Text

Output text with various options:

```bash
# Basic output
psh$ echo "Hello, World!"
Hello, World!

# Multiple arguments
psh$ echo Hello World
Hello World

# Without newline (-n flag)
psh$ echo -n "No newline"
No newlinepsh$ 

# Enable escape sequences (-e flag)
psh$ echo -e "Line 1\nLine 2\nLine 3"
Line 1
Line 2
Line 3

# Escape sequences with -e
psh$ echo -e "Tab\there"
Tab     here
psh$ echo -e "Back\bspace"
Bacspace
psh$ echo -e "\033[31mRed text\033[0m"
Red text  # (shown in red)

# Disable escapes explicitly (-E flag, default)
psh$ echo -E "No\nescapes"
No\nescapes

# Unicode support
psh$ echo -e "\u2665 \u2663 \u2660 \u2666"
♥ ♣ ♠ ♦

# Octal sequences
psh$ echo -e "\0101\0102\0103"
ABC

# Suppress further output with \c
psh$ echo -e "First\cThis won't appear"
First
```

### read - Read User Input

Read input into variables with various options:

```bash
# Basic input
psh$ read name
Alice
psh$ echo "Hello, $name"
Hello, Alice

# With prompt (-p flag)
psh$ read -p "Enter your name: " name
Enter your name: Bob
psh$ echo "Hello, $name"
Hello, Bob

# Silent input for passwords (-s flag)
psh$ read -sp "Password: " pass
Password: 
psh$ echo  # Add newline after silent input
psh$ echo "Got password of length ${#pass}"
Got password of length 8

# Read with timeout (-t flag)
psh$ read -t 5 -p "Quick! Enter something: " response
Quick! Enter something: # (waits 5 seconds)
psh$ echo $?
142  # Special exit code for timeout

# Read exact number of characters (-n flag)
psh$ read -n 4 -p "Enter 4-digit PIN: " pin
Enter 4-digit PIN: 1234psh$ echo " PIN is $pin"
 PIN is 1234

# Custom delimiter (-d flag)
psh$ read -d ':' -p "Enter data until colon: " data
Enter data until colon: hello world:psh$ echo " Got: $data"
 Got: hello world

# Combining options
psh$ read -sn 6 -p "Enter 6-char password: " password
Enter 6-char password: psh$ echo
psh$ echo "Password set"
Password set

# Raw mode - preserve backslashes (-r flag)
psh$ read -r line
C:\Users\alice\Documents
psh$ echo "$line"
C:\Users\alice\Documents

# Without -r, backslashes are processed
psh$ read line
C:\Users\alice\Documents
psh$ echo "$line"
C:Usersalice\Documents
```

## 4.5 Job Control

### jobs - List Jobs

Show background and suspended jobs:

```bash
# Start some background jobs
psh$ sleep 100 &
[1] 12345
psh$ sleep 200 &
[2] 12346
psh$ sleep 300 &
[3] 12347

# List all jobs
psh$ jobs
[1]  Running    sleep 100 &
[2]- Running    sleep 200 &
[3]+ Running    sleep 300 &

# Suspend a foreground job
psh$ sleep 400
^Z
[4]+ Stopped    sleep 400

psh$ jobs
[1]  Running    sleep 100 &
[2]  Running    sleep 200 &
[3]- Running    sleep 300 &
[4]+ Stopped    sleep 400

# + indicates current job
# - indicates previous job
```

### fg - Foreground a Job

Bring a background or suspended job to the foreground:

```bash
# Continue the current job
psh$ fg
sleep 400
# (now waiting for sleep to finish)

# Bring specific job to foreground
psh$ jobs
[1]  Running    sleep 100 &
[2]- Running    sleep 200 &
[3]+ Running    sleep 300 &

psh$ fg %1
sleep 100
# (waits for job 1)

# Using job specifications
psh$ fg %+    # Current job
psh$ fg %-    # Previous job
psh$ fg %2    # Job number 2

# Pattern matching
psh$ sleep 1000 &
[1] 12348
psh$ fg %sle   # Matches "sleep"
sleep 1000
```

### bg - Background a Job

Resume a suspended job in the background:

```bash
# Suspend a job
psh$ find / -name "*.log" 2>/dev/null
^Z
[1]+ Stopped    find / -name "*.log" 2>/dev/null

# Resume in background
psh$ bg
[1]+ find / -name "*.log" 2>/dev/null &

# Background specific job
psh$ sleep 100
^Z
[2]+ Stopped    sleep 100
psh$ sleep 200
^Z
[3]+ Stopped    sleep 200

psh$ jobs
[1]  Running    find / -name "*.log" 2>/dev/null &
[2]- Stopped    sleep 100
[3]+ Stopped    sleep 200

psh$ bg %2
[2]- sleep 100 &
```

## 4.6 Other Built-ins

### source (.) - Execute Script in Current Shell

Run commands from a file in the current shell environment:

```bash
# Create a script with variables and functions
psh$ cat > setup.sh << 'EOF'
# Setup script
export PROJECT_DIR="/home/alice/project"
export DEBUG=1

greet() {
    echo "Hello from setup.sh!"
}

alias ll='ls -la'
echo "Environment configured!"
EOF

# Source the script
psh$ source setup.sh
Environment configured!
psh$ echo $PROJECT_DIR
/home/alice/project
psh$ greet
Hello from setup.sh!

# Using . (dot) command (same as source)
psh$ . setup.sh
Environment configured!

# Source with arguments
psh$ cat > args.sh << 'EOF'
echo "Script name: $0"
echo "First arg: $1"
echo "Second arg: $2"
EOF

psh$ source args.sh one two
Script name: psh
First arg: one
Second arg: two
```

### history - Command History

View and manage command history:

```bash
# Show recent commands
psh$ history
  496  cd /tmp
  497  ls -la
  498  echo "test"
  499  pwd
  500  history

# Show last N commands
psh$ history 3
  498  echo "test"
  499  pwd
  500  history

# Search history (with grep)
psh$ history | grep cd
  481  cd /home/alice
  492  cd Documents
  496  cd /tmp

# Clear history
psh$ history -c
psh$ history
  1  history

# History expansion (if implemented)
psh$ !499    # Run command 499
pwd
/tmp

psh$ !!      # Run last command
pwd
/tmp
```

### return - Return from Function

Exit from a shell function with optional status:

```bash
# Basic return
psh$ validate_file() {
>     if [ ! -f "$1" ]; then
>         echo "Error: File not found"
>         return 1
>     fi
>     echo "File is valid"
>     return 0
> }

psh$ validate_file /etc/passwd
File is valid
psh$ echo $?
0

psh$ validate_file /nonexistent
Error: File not found
psh$ echo $?
1

# Return without value (uses last command's exit status)
psh$ check_root() {
>     [ $UID -eq 0 ]
>     return
> }

# Return can only be used in functions
psh$ return
return: can only `return' from a function or sourced script
```

### alias and unalias - Manage Aliases

Create shortcuts for commands:

```bash
# Create aliases
psh$ alias ll='ls -la'
psh$ alias la='ls -A'
psh$ alias ..='cd ..'
psh$ alias ...='cd ../..'

# Use aliases
psh$ ll
total 48
drwxr-xr-x  5 alice alice 4096 Jan 15 12:00 .
drwxr-xr-x 20 alice alice 4096 Jan 14 09:00 ..
-rw-r--r--  1 alice alice  215 Jan 15 10:00 file.txt

# Show all aliases
psh$ alias
alias ..='cd ..'
alias ...='cd ../..'
alias la='ls -A'
alias ll='ls -la'

# Show specific alias
psh$ alias ll
alias ll='ls -la'

# Alias with multiple commands
psh$ alias backup='echo "Starting backup..."; tar -czf backup.tar.gz .'

# Remove aliases
psh$ unalias ll
psh$ ll
psh: ll: command not found

# Remove all aliases
psh$ unalias -a
```

## 4.7 Test Commands

### test and [ - Conditional Testing

Evaluate conditional expressions:

```bash
# String tests
psh$ [ "hello" = "hello" ]
psh$ echo $?
0

psh$ [ "hello" != "world" ]
psh$ echo $?
0

psh$ [ -z "" ]          # Empty string
psh$ echo $?
0

psh$ [ -n "text" ]      # Non-empty string
psh$ echo $?
0

# Numeric comparisons
psh$ [ 5 -eq 5 ]        # Equal
psh$ [ 5 -ne 10 ]       # Not equal
psh$ [ 5 -lt 10 ]       # Less than
psh$ [ 10 -gt 5 ]       # Greater than
psh$ [ 5 -le 5 ]        # Less or equal
psh$ [ 5 -ge 5 ]        # Greater or equal

# File tests
psh$ [ -f /etc/passwd ]  # Regular file
psh$ [ -d /tmp ]         # Directory
psh$ [ -e /etc ]         # Exists
psh$ [ -r file.txt ]     # Readable
psh$ [ -w file.txt ]     # Writable
psh$ [ -x script.sh ]    # Executable
psh$ [ -s file.txt ]     # Non-empty file

# Using test command (same as [)
psh$ test -f /etc/passwd
psh$ echo $?
0

# Combining conditions
psh$ [ -f file.txt ] && [ -r file.txt ]
psh$ [ 5 -gt 3 ] || [ 2 -gt 4 ]
```

### [[ ]] - Enhanced Test

Advanced conditional testing with better syntax:

```bash
# No word splitting - safer with variables
psh$ var="hello world"
psh$ [[ $var = "hello world" ]]  # Works without quotes
psh$ echo $?
0

# Pattern matching
psh$ [[ "hello" = h* ]]
psh$ echo $?
0

# Regular expression matching
psh$ [[ "user@example.com" =~ ^[^@]+@[^@]+$ ]]
psh$ echo $?
0

# String comparison (lexicographic)
psh$ [[ "apple" < "banana" ]]
psh$ echo $?
0

# Compound conditions
psh$ [[ -f file.txt && -r file.txt ]]
psh$ [[ $USER = "alice" || $USER = "bob" ]]

# Negation
psh$ [[ ! -f nonexistent.txt ]]
psh$ echo $?
0
```

## Practical Examples

### System Administration Script

```bash
#!/usr/bin/env psh
# System check script using built-ins

# Function to check service
check_service() {
    local service=$1
    if pgrep -x "$service" > /dev/null; then
        echo "[OK] $service is running"
        return 0
    else
        echo "[FAIL] $service is not running"
        return 1
    fi
}

# Main checks
echo "=== System Status Check ==="
echo

# Check disk space
echo "Disk Usage:"
df -h / | grep -v Filesystem

# Check important services
for service in sshd cron nginx; do
    check_service "$service"
done

# Check for updates (Debian/Ubuntu)
if [ -f /usr/bin/apt ]; then
    echo
    echo "Checking for updates..."
    updates=$(apt list --upgradable 2>/dev/null | grep -c upgradable)
    echo "Available updates: $((updates - 1))"
fi

# Check system load
echo
echo "System Load:"
uptime

# Exit with appropriate status
[ $failed -gt 0 ] && exit 1 || exit 0
```

### Interactive Menu System

```bash
#!/usr/bin/env psh
# Interactive menu using built-ins

show_menu() {
    echo
    echo "=== Main Menu ==="
    echo "1) Show system info"
    echo "2) List files"
    echo "3) Check disk space"
    echo "4) Show network info"
    echo "5) Exit"
    echo
}

while true; do
    show_menu
    read -p "Select option: " choice
    
    case $choice in
        1)
            echo "Hostname: $(hostname)"
            echo "User: $USER"
            echo "Home: $HOME"
            echo "Shell: $SHELL"
            ;;
        2)
            ls -la
            ;;
        3)
            df -h
            ;;
        4)
            ip addr 2>/dev/null || ifconfig
            ;;
        5)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
    
    read -p "Press Enter to continue..."
done
```

## Summary

Built-in commands are the core of PSH functionality. They provide:
- Essential shell control (exit, :, true, false)
- Navigation capabilities (cd, pwd)
- Environment management (export, unset, env, set, declare)
- I/O operations (echo, read)
- Job control (jobs, fg, bg)
- Script execution (source)
- Conditional testing (test, [, [[)

These commands execute quickly since they don't require forking new processes, and they have direct access to shell internals. Understanding built-ins is crucial for effective shell scripting and interactive use.

In the next chapter, we'll explore variables and parameters, building on the environment management commands covered here.

---

[← Previous: Chapter 3 - Basic Command Execution](03_basic_command_execution.md) | [Next: Chapter 5 - Variables and Parameters →](05_variables_and_parameters.md)