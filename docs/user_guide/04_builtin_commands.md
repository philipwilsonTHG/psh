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

# Show all shell options
psh$ set -o
edit_mode            emacs
debug-ast            off
debug-tokens         off
debug-scopes         off
errexit              off
nounset              off
xtrace               off
pipefail             off

# Shell option flags (short form)
psh$ set -e    # Enable errexit (exit on error)
psh$ set -u    # Enable nounset (error on undefined variables)
psh$ set -x    # Enable xtrace (print commands before execution)
psh$ set +e    # Disable errexit
psh$ set +u    # Disable nounset
psh$ set +x    # Disable xtrace

# Combine multiple options
psh$ set -eux  # Enable errexit, nounset, and xtrace
psh$ set +eux  # Disable all three

# Long form with -o
psh$ set -o errexit      # Same as set -e
psh$ set -o nounset      # Same as set -u
psh$ set -o xtrace       # Same as set -x
psh$ set -o pipefail     # Pipeline fails if any command fails
psh$ set +o errexit      # Same as set +e

# Shell Options in Detail:

# errexit (-e): Exit immediately on command failure
psh$ set -e
psh$ false
$ # Shell exits with status 1

# nounset (-u): Treat undefined variables as errors
psh$ set -u
psh$ echo $UNDEFINED_VAR
psh: $UNDEFINED_VAR: unbound variable
psh$ echo ${UNDEFINED_VAR:-default}  # OK with default
default

# xtrace (-x): Print commands before execution
psh$ set -x
psh$ echo "Hello"
+ echo Hello
Hello
psh$ VAR=test
+ VAR=test
psh$ echo $VAR
+ echo test
test

# pipefail: Return rightmost non-zero exit code in pipeline
psh$ set -o pipefail
psh$ false | true
psh$ echo $?
1  # Without pipefail, would be 0

# Debug options
psh$ set -o debug-ast    # Show parsed AST
psh$ set -o debug-tokens # Show tokenization
psh$ set -o debug-scopes # Show variable scope operations
psh$ set +o debug-ast    # Disable AST debugging
```

### declare - Declare Variables and Functions

Declare variables with attributes, display variable values and attributes, or show function definitions:

```bash
# Show all variables
psh$ declare
DISPLAY=:0
HOME=/home/alice
MYVAR=Hello
PS1=psh$ 
...

# Declare variables with attributes
psh$ declare -i count=0          # Integer variable
psh$ declare -l name="ALICE"     # Lowercase variable
psh$ declare -u city="london"    # Uppercase variable
psh$ declare -r PI=3.14159       # Readonly variable
psh$ declare -x MYAPP_CONFIG     # Export to environment
psh$ declare -a fruits           # Indexed array
psh$ declare -A colors           # Associative array

# Integer variables evaluate arithmetic on assignment
psh$ declare -i calc
psh$ calc="10 * 5"
psh$ echo $calc
50

# Case transformation
psh$ echo "$name $city"
alice LONDON

# Indexed arrays
psh$ declare -a indexed_colors=(red green blue)
psh$ echo ${indexed_colors[1]}
green

# Associative arrays
psh$ declare -A assoc_colors=([primary]="red" [secondary]="blue")
psh$ echo ${assoc_colors[primary]}
red

# Show variables with attributes
psh$ declare -p count name
declare -i count="0"
declare -l name="alice"

# Remove attributes with +
psh$ declare +l name    # Remove lowercase attribute
psh$ name="ALICE"
psh$ echo $name
ALICE

# Show all function definitions with -f
psh$ declare -f
hello() { 
    echo "Hello, $1!"
}
greet() { 
    echo "Greetings!"
}

# Show function names only with -F
psh$ declare -F
declare -f greet
declare -f hello

# Show specific function definition
psh$ declare -f hello
hello() { 
    echo "Hello, $1!"
}

# Combine multiple attributes
psh$ declare -ilx PORT=8080      # Integer, lowercase, exported
psh$ declare -ru VERSION=1.0     # Readonly, uppercase

# Attempting to modify readonly fails
psh$ PI=3.14
psh: PI: readonly variable
```

#### Variable Attributes

- **-i** : Integer - arithmetic evaluation on assignment
- **-l** : Lowercase - converts value to lowercase
- **-u** : Uppercase - converts value to uppercase  
- **-r** : Readonly - cannot be modified or unset
- **-x** : Export - variable is exported to environment
- **-a** : Array - variable is an indexed array
- **-A** : Associative Array - variable is an associative array (requires explicit declaration)
- **-p** : Print - display variables with their attributes

Attributes can be combined (e.g., `-ilx` for integer, lowercase, exported) and removed with `+` prefix (e.g., `+x` to unexport).

### typeset - Korn Shell Compatible Function Display

The `typeset` builtin is provided for compatibility with the Korn shell (ksh). It is exactly equivalent to `declare`:

```bash
# Show all variables (same as declare)
psh$ typeset
DISPLAY=:0
HOME=/home/alice
MYVAR=Hello
PS1=psh$ 
...

# Show all function definitions
psh$ typeset -f
hello() { 
    echo "Hello, $1!"
}
greet() { 
    echo "Greetings!"
}

# Show function names only
psh$ typeset -F
declare -f greet
declare -f hello

# Show specific function
psh$ typeset -f hello
hello() { 
    echo "Hello, $1!"
}

# Multiple functions
psh$ typeset -f hello greet
hello() { 
    echo "Hello, $1!"
}
greet() { 
    echo "Greetings!"
}

# Check function existence
psh$ typeset -F greet hello nonexistent
declare -f greet
declare -f hello
psh: typeset: nonexistent: not found

# All features work identically to declare
psh$ typeset -F | grep hello
declare -f hello
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

### kill - Send Signals to Processes

Send signals to running processes or list available signals:

```bash
# Send default signal (TERM) to a process
psh$ sleep 300 &
[1] 12345
psh$ kill 12345

# Send specific signal by name
psh$ sleep 300 &
[1] 12346
psh$ kill -KILL 12346
psh$ kill -HUP 12347
psh$ kill -INT 12348

# Send signal by number
psh$ kill -9 12349    # SIGKILL
psh$ kill -15 12350   # SIGTERM
psh$ kill -1 12351    # SIGHUP

# Using -s option
psh$ kill -s TERM 12352
psh$ kill -s KILL 12353

# Kill multiple processes
psh$ kill 12354 12355 12356
psh$ kill -TERM 12357 12358

# Kill jobs using job specifications
psh$ sleep 300 &
[1] 12359
psh$ sleep 400 &
[2] 12360
psh$ kill %1          # Kill job 1
psh$ kill %2          # Kill job 2
psh$ kill %+          # Kill current job
psh$ kill %-          # Kill previous job

# Kill process groups (negative PID)
psh$ kill -TERM -12361    # Send TERM to process group 12361

# Test if process exists (signal 0)
psh$ kill -0 12362
psh$ echo $?
0     # Process exists

psh$ kill -0 99999
kill: (99999) - No such process
psh$ echo $?
1     # Process doesn't exist

# List all available signals
psh$ kill -l
1) SIGHUP      	2) SIGINT      	3) SIGQUIT     	4) SIGILL      
5) SIGTRAP     	6) SIGABRT     	7) 7           	8) SIGFPE      
9) SIGKILL     	10) SIGBUS     	11) SIGSEGV    	12) SIGSYS     
13) SIGPIPE    	14) SIGALRM    	15) SIGTERM    	16) SIGURG     
17) SIGSTOP    	18) SIGTSTP    	19) SIGCONT    	20) SIGCHLD    
21) SIGTTIN    	22) SIGTTOU    	23) SIGIO      	24) SIGXCPU    
25) SIGXFSZ    	26) SIGVTALRM  	27) SIGPROF    	28) SIGWINCH   
29) 29         	30) SIGUSR1    	31) SIGUSR2

# Show signal name for exit status
psh$ kill -l 143
SIGTERM

psh$ kill -l 137
SIGKILL

# Common use cases
# Gracefully terminate a process
psh$ kill -TERM 12363   # Or just: kill 12363

# Force kill an unresponsive process
psh$ kill -KILL 12364   # Or: kill -9 12364

# Reload configuration (for daemons)
psh$ kill -HUP 12365

# Suspend a process
psh$ kill -STOP 12366

# Resume a suspended process
psh$ kill -CONT 12366

# Interrupt a process (like Ctrl-C)
psh$ kill -INT 12367

# Error handling examples
psh$ kill 99999
kill: (99999) - No such process

psh$ kill -INVALID 12368
kill: invalid signal name: INVALID

psh$ kill %99
kill: %99: no such job
```

#### Signal Reference

Common signals used with kill:

- **TERM (15)**: Terminate process gracefully (default)
- **KILL (9)**: Force kill process (cannot be caught or ignored)
- **HUP (1)**: Hangup - often used to reload configuration
- **INT (2)**: Interrupt - equivalent to Ctrl-C
- **QUIT (3)**: Quit - equivalent to Ctrl-\
- **STOP (19)**: Suspend process (cannot be caught)
- **CONT (18)**: Resume suspended process
- **USR1 (10)**: User-defined signal 1
- **USR2 (12)**: User-defined signal 2

#### Job Control Integration

The kill command integrates seamlessly with PSH's job control:

```bash
# Start some background jobs
psh$ sleep 100 &
[1] 12369
psh$ sleep 200 &
[2] 12370
psh$ find / -name "*.log" 2>/dev/null &
[3] 12371

# Kill specific jobs
psh$ kill %1          # Kill job 1 (sleep 100)
psh$ kill %find       # Kill job matching "find"

# Kill all processes in a job (pipelines)
psh$ cat file | grep pattern | sort &
[4] 12372
psh$ kill %4          # Kills all processes in the pipeline

# Combining with job control commands
psh$ jobs
[2]  Running    sleep 200 &
[3]- Running    find / -name "*.log" 2>/dev/null &

psh$ kill %2
psh$ jobs
[3]+ Running    find / -name "*.log" 2>/dev/null &
```

#### Exit Status

- **0**: At least one signal was sent successfully
- **1**: Error occurred (process not found, permission denied, etc.)
- **2**: Invalid arguments or usage

### trap - Handle Signals and Shell Exit

The `trap` command sets up signal handlers and exit traps for robust shell script cleanup:

```bash
# Set up basic signal handling
psh$ trap 'echo "Interrupted by user"' INT
psh$ # Press Ctrl-C to see the trap execute

# Clean exit trap
psh$ trap 'echo "Script exiting, cleaning up..."' EXIT
psh$ exit

# Multiple signals with same handler
psh$ trap 'cleanup_function' INT TERM HUP QUIT

# Ignore a signal
psh$ trap '' QUIT
psh$ # Now SIGQUIT (Ctrl-\) is ignored

# Reset signal to default behavior
psh$ trap - INT
psh$ # INT signal now has default behavior

# List all available signals
psh$ trap -l
 -) DEBUG
 -) ERR
 -) EXIT
 1) SIGHUP
 2) SIGINT
 3) SIGQUIT
 ...

# Show current trap settings
psh$ trap -p
trap -- 'cleanup_function' INT
trap -- '' QUIT

# Show specific trap
psh$ trap -p EXIT
trap -- 'echo "Exiting"' EXIT
```

#### Common Trap Patterns

**Cleanup on Exit:**
```bash
#!/usr/bin/env psh
# Cleanup temporary files on exit
tempfile=$(mktemp)
trap 'rm -f "$tempfile"' EXIT

echo "Working with $tempfile..."
# Script will clean up automatically
```

**Graceful Shutdown:**
```bash
#!/usr/bin/env psh
# Handle Ctrl-C gracefully
cleanup() {
    echo "Cleaning up..."
    kill $bg_pid 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start background work
long_running_command &
bg_pid=$!
wait $bg_pid
```

**Signal Forwarding:**
```bash
#!/usr/bin/env psh
# Forward signals to child process
child_pid=""

forward_signal() {
    if [ -n "$child_pid" ]; then
        kill -TERM $child_pid
    fi
    exit 0
}

trap forward_signal INT TERM

# Start child and wait
important_process &
child_pid=$!
wait $child_pid
```

#### Signal Reference

Commonly trapped signals:

- **INT (2)**: Interrupt (Ctrl-C)
- **TERM (15)**: Termination request
- **HUP (1)**: Hangup (terminal closed)
- **QUIT (3)**: Quit (Ctrl-\)
- **USR1 (10)**: User-defined signal 1
- **USR2 (12)**: User-defined signal 2

Special trap conditions:

- **EXIT**: Shell or script exit
- **DEBUG**: Before each command (bash extension)
- **ERR**: Command returns non-zero (bash extension)

#### Syntax Summary

```bash
trap [action] [signal...]    # Set trap
trap -l                      # List signals
trap -p [signal...]         # Show traps
trap '' signal              # Ignore signal
trap - signal               # Reset to default
```

#### Exit Status

- **0**: Trap set successfully
- **1**: Invalid signal specification
- **2**: Invalid usage or arguments

## 4.6 Command Help and Information

### help - Display Builtin Command Information

The `help` builtin provides comprehensive documentation for PSH's built-in commands:

```bash
# Show all available builtins
psh$ help
PSH Shell, version 0.55.0
These shell commands are defined internally. Type 'help name' to find out more
about the function 'name'.

 .                              : [arguments]
 [                              alias
 bg                             cd
 declare                        echo [-neE] [arg ...]
 env                            eval
 exec [command [argument ...]]  exit [n]
 export                         false
 fg                             help [-dms] [pattern ...]
 history                        jobs
 local                          pwd
 read                           return
 set                            source
 test                           true
 typeset                        unalias
 unset                          version

# Get detailed help for a specific builtin
psh$ help echo
echo: echo [-neE] [arg ...]
    
    Display arguments separated by spaces, followed by a newline.
    If no arguments are given, print a blank line.
    
    Options:
        -n    Do not output the trailing newline
        -e    Enable interpretation of backslash escape sequences
        -E    Disable interpretation of backslash escapes (default)
    
    Escape sequences (with -e):
        \a    Alert (bell)
        \b    Backspace
        \c    Suppress further output
        \e    Escape character
        \f    Form feed
        \n    New line
        \r    Carriage return
        \t    Horizontal tab
        \v    Vertical tab
        \\    Backslash
        \0nnn Character with octal value nnn (0 prefix required)
        \xhh  Character with hex value hh (1 to 2 digits)
        \uhhhh    Unicode character with hex value hhhh (4 digits)
        \Uhhhhhhhh Unicode character with hex value hhhhhhhh (8 digits)

# Get help for multiple builtins
psh$ help cd pwd
cd: cd [dir]
    Change the current directory to DIR.
    
    The default DIR is the value of the HOME shell variable.
    The variable CDPATH defines the search path for the directory
    containing DIR.
    
    Special directories:
      ~     User's home directory
      -     Previous working directory
    
    Exit Status:
    Returns 0 if the directory is changed; non-zero otherwise.

pwd: pwd
    Print the current working directory

# Pattern matching to find builtins
psh$ help e*
echo: echo [-neE] [arg ...]
    Display text

env: env [NAME=VALUE]... [COMMAND [ARG]...]
    Display or set environment variables.
    
    When called without arguments, prints all environment variables.
    When called with NAME=VALUE pairs, sets those variables for COMMAND.
    When called with COMMAND, executes COMMAND with the modified environment.

eval: eval [arg ...]
    Execute arguments as shell commands

exec: exec [command [argument ...]]
    Execute commands and manipulate file descriptors

exit: exit [n]
    Exit the shell

export: export [name[=value] ...]
    Set export attribute for shell variables

# Description mode - shows one-line descriptions
psh$ help -d
. - Dot command (alias for source).
: - Null command that returns success
[ - [ command (alias for test).
alias - Define or display aliases.
bg - Resume job in background.
cd - Change directory.
declare - Declare variables and functions with attributes.
echo - Display text
env - Display or modify environment variables.
eval - Execute arguments as shell commands.
exec - Execute commands and manipulate file descriptors
exit - Exit the shell
export - Export variables to environment.
false - Always return failure
fg - Bring job to foreground.
help - Display information about builtin commands
history - Display command history.
jobs - List active jobs.
local - Create local variables within functions.
pwd - Print the current working directory
read - Read a line from standard input and assign to variables.
return - Return from a function with optional exit code.
set - Set shell options and positional parameters.
source - Execute commands from a file in the current shell.
test - Test command for conditionals.
true - Always return success
typeset - Typeset builtin - alias for declare (ksh compatibility).
unalias - Remove aliases.
unset - Unset variables and functions.
version - Display version information.

# Synopsis mode - shows just command syntax
psh$ help -s echo pwd read
echo: echo [-neE] [arg ...]
pwd: pwd
read: read [-r] [-p prompt] [-s] [-t timeout] [-n chars] [-d delim] [name ...]

# Manpage format - detailed documentation
psh$ help -m help
NAME
    help - Display information about builtin commands

SYNOPSIS
    help [-dms] [pattern ...]

DESCRIPTION
    help: help [-dms] [pattern ...]
        Display information about builtin commands.

        Displays brief summaries of builtin commands. If PATTERN is
        specified, gives detailed help on all commands matching PATTERN,
        otherwise the list of help topics is printed.

        Options:
          -d    output short description for each topic
          -m    display usage in pseudo-manpage format
          -s    output only a short usage synopsis for each topic matching
                PATTERN

        Arguments:
          PATTERN    Pattern specifying a help topic

        Exit Status:
        Returns success unless PATTERN is not found or an invalid option is given.

# Pattern matching examples
psh$ help "[cde]*"  # Commands starting with c, d, or e
psh$ help "*read*"  # Commands containing 'read'
psh$ help "??"      # Two-character commands (cd, bg, fg)

# Error handling
psh$ help nonexistent
help: no help topics match 'nonexistent'

psh$ help -x
help: invalid option: '-x'
Usage: help [-dms] [pattern ...]
```

#### Help Pattern Matching

The help command supports glob-style pattern matching using these special characters:

- `*` - Matches any sequence of characters
- `?` - Matches any single character  
- `[abc]` - Matches any character in the set (a, b, or c)
- `[a-z]` - Matches any character in the range (a through z)
- `[!abc]` - Matches any character NOT in the set

```bash
# Find all commands with specific patterns
psh$ help "*set*"    # Commands containing 'set'
unset: unset [-f] [-v] name ...
    Unset variables and functions

set: set [--] [arg ...]
    Set shell options and positional parameters

typeset: typeset [-f] [-F] [name ...]
    Typeset builtin - alias for declare (ksh compatibility)

psh$ help "?"        # Single character commands
:: : [arguments]
    Null command that returns success

[: [ arg ... ]
    [ command (alias for test)

psh$ help "[jfb]g"   # Commands matching pattern (fg, bg)
bg: bg [job_spec]
    Resume job in background

fg: fg [job_spec]
    Bring job to foreground
```

#### Help Options

- **No options**: Default behavior - shows command listing or detailed help
- **-d**: Description mode - shows "command - description" format for all builtins
- **-s**: Synopsis mode - shows only the command syntax/usage line
- **-m**: Manpage mode - shows formatted manual page with NAME, SYNOPSIS, DESCRIPTION

Options can be combined, with later options taking precedence:
```bash
psh$ help -ds echo   # -s overrides -d, shows synopsis
echo: echo [-neE] [arg ...]
```

#### Exit Status

- Returns 0 on success
- Returns 1 if no patterns match any builtins
- Returns 2 if invalid options are provided

#### Self-Documentation

The help system provides complete self-documentation for PSH:

```bash
# Learn about PSH without external documentation
psh$ help help      # Learn how to use help itself
psh$ help -d        # Overview of all available commands
psh$ help set       # Learn about shell options
psh$ help read      # Learn about input handling
psh$ help declare   # Learn about variable management
```

This makes PSH educational and self-discoverable - users can learn shell features directly through the shell interface, similar to bash's help system.

## 4.7 Other Built-ins

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

## 4.8 Test Commands

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

## 4.9 Process Control

### exec - Execute Commands or Manipulate File Descriptors

The `exec` builtin executes commands or applies file descriptor redirections permanently to the current shell:

```bash
# Mode 1: exec without command - apply redirections permanently
psh$ exec > output.txt
psh$ echo "This goes to the file"
psh$ pwd    # Also redirected to file
psh$ exec 2>&1  # Redirect stderr to stdout permanently

# Mode 2: exec with command - replace the shell process
psh$ exec echo "This replaces the shell"
This replaces the shell
$ # Shell has been replaced by echo command

# Practical redirection examples
psh$ exec 3< input.txt    # Open file descriptor 3 for reading
psh$ exec 4> output.txt   # Open file descriptor 4 for writing  
psh$ exec 5>&1           # Duplicate stdout to fd 5

# Common use in shell scripts
#!/usr/bin/env psh
# Redirect all script output to log file
exec > /var/log/script.log 2>&1

echo "Starting script..."
echo "This will be logged"
date
echo "Script completed"

# Environment variable assignment with exec
psh$ DEBUG=1 exec > debug.log  # Set variable and redirect

# Using exec to close file descriptors
psh$ exec 3<&-  # Close file descriptor 3
psh$ exec 4>&-  # Close file descriptor 4
```

#### Mode 1: Redirection Only

When used without a command, `exec` applies redirections permanently to the current shell:

```bash
# Basic output redirection
psh$ exec > log.txt
psh$ echo "All output goes to log.txt now"
psh$ ls -la
psh$ cat log.txt
All output goes to log.txt now
# ... ls output ...

# Input redirection  
psh$ echo -e "line1\nline2\nline3" > input.txt
psh$ exec < input.txt
psh$ read line1; echo "First: $line1"
First: line1
psh$ read line2; echo "Second: $line2"  
Second: line2

# Error redirection
psh$ exec 2> errors.log
psh$ ls nonexistent 2>/dev/null || echo "Error logged"
Error logged
psh$ cat errors.log
ls: cannot access 'nonexistent': No such file or directory

# File descriptor duplication
psh$ exec 3>&1     # Save stdout to fd 3
psh$ exec > temp.txt # Redirect stdout to file
psh$ echo "To file"
psh$ exec 1>&3     # Restore stdout from fd 3
psh$ echo "To terminal"
To terminal
psh$ cat temp.txt
To file

# Multiple redirections at once
psh$ exec < input.txt > output.txt 2> error.txt
# Now stdin, stdout, stderr are all redirected

# Here documents with exec
psh$ exec << 'EOF'
line 1
line 2
EOF
psh$ read first; echo "Got: $first"
Got: line 1
```

#### Mode 2: Command Execution

When given a command, `exec` replaces the current shell process entirely:

```bash
# Replace shell with another command
psh$ exec cat /etc/passwd
# Shell is replaced by cat, output shows, then process exits

# Replace with another shell
psh$ exec bash
bash$ # Now running bash instead of psh

# Replace with script
psh$ exec ./myscript.sh
# Shell is replaced by the script

# With environment variables
psh$ PATH=/usr/bin exec env
# Shows environment with modified PATH, then exits

# Common in shell wrapper scripts
#!/usr/bin/env psh
# Setup script that eventually replaces itself
export MYAPP_CONFIG=/etc/myapp
export MYAPP_LOG=/var/log/myapp
exec /usr/bin/myapp "$@"  # Replace with the real program
```

#### Error Handling

The `exec` builtin provides proper POSIX error codes:

```bash
# Command not found
psh$ exec nonexistent_command
exec: nonexistent_command: command not found
psh$ echo $?
127

# Permission denied  
psh$ touch /tmp/no_exec
psh$ chmod 644 /tmp/no_exec  # Remove execute permission
psh$ exec /tmp/no_exec
exec: /tmp/no_exec: Permission denied  
psh$ echo $?
126

# Cannot exec builtins
psh$ exec echo
exec: echo: cannot exec a builtin
psh$ echo $?
1

# Cannot exec functions
psh$ myfunc() { echo "test"; }
psh$ exec myfunc
exec: myfunc: cannot exec a function
psh$ echo $?
1

# Redirection errors
psh$ exec > /dev/null/invalid
exec: cannot redirect: No such file or directory
psh$ echo $?
1
```

#### Environment Variables

Environment variable assignments are processed for both modes:

```bash
# Mode 1: Variables set permanently in shell
psh$ DEBUG=1 VERBOSE=1 exec > debug.log
psh$ echo $DEBUG $VERBOSE
1 1

# Mode 2: Variables passed to exec'd command
psh$ DEBUG=1 exec env | grep DEBUG
DEBUG=1
# Shell is replaced by env command

# Multiple assignments
psh$ VAR1=value1 VAR2=value2 exec > output.txt
psh$ echo "$VAR1 $VAR2"  # Output goes to file
```

#### Advanced Usage

**Script Initialization:**
```bash
#!/usr/bin/env psh
# Common pattern: setup and redirect all output
exec > "$LOGFILE" 2>&1
exec 3>&1  # Save original stdout for user messages

echo "Script started at $(date)"
# All output now goes to log

# Send message to user via saved stdout
echo "Check log file: $LOGFILE" >&3
```

**File Descriptor Management:**
```bash
# Open multiple files for processing
exec 3< input1.txt
exec 4< input2.txt  
exec 5> output.txt

# Process data from both inputs
while read -u 3 line1 && read -u 4 line2; do
    echo "$line1 | $line2" >&5
done

# Close when done
exec 3<&- 4<&- 5>&-
```

**Backup and Restore Streams:**
```bash
# Save original streams
exec 6>&1  # Save stdout  
exec 7>&2  # Save stderr

# Redirect everything to log
exec > script.log 2>&1

# Do work that gets logged
echo "This goes to log"
ls nonexistent  # Error also logged

# Restore original streams  
exec 1>&6 2>&7 6>&- 7>&-

# Back to normal
echo "This goes to terminal"
```

#### Security Considerations

Unlike `eval`, `exec` is generally safe as it doesn't interpret shell syntax in arguments:

```bash
# Safe - exec doesn't parse shell syntax
user_input="/bin/echo hello; rm -rf /"
exec "$user_input"  # Tries to exec that exact filename, fails safely

# Still validate paths for exec with command
case "$program" in
    /usr/bin/*|/bin/*) exec "$program" ;;
    *) echo "Invalid program path" ;;
esac
```

#### Exit Status

- **Mode 1** (redirection only): Returns 0 on success, 1 on redirection errors
- **Mode 2** (with command): Does not return (process is replaced), or returns error codes:
  - 126: Permission denied or cannot execute
  - 127: Command not found
  - 1: Cannot exec builtin or function

## 4.10 Dynamic Command Execution

### eval - Execute Commands from String

The `eval` builtin executes its arguments as shell commands, enabling dynamic command execution:

```bash
# Basic usage
psh$ eval "echo hello"
hello

# Multiple arguments are joined with spaces
psh$ eval echo "hello" "world"
hello world

# Variable assignment in eval
psh$ eval "name='Alice'"
psh$ echo $name
Alice

# Multiple commands
psh$ eval "echo first; echo second"
first
second

# Dynamic command building
psh$ cmd="echo"
psh$ msg="Dynamic message"
psh$ eval "$cmd '$msg'"
Dynamic message

# Using variables to build complex commands
psh$ operation="ls"
psh$ flags="-la"
psh$ target="/tmp"
psh$ eval "$operation $flags $target"
total 48
drwxrwxrwt 15 root root 4096 Jan 15 12:00 .
drwxr-xr-x 20 root root 4096 Jan 10 08:00 ..
...

# Function definition in eval
psh$ eval "greet() { echo \"Hello, \$1!\"; }"
psh$ greet World
Hello, World!

# Control structures in eval
psh$ eval "for i in 1 2 3; do echo \"Number: \$i\"; done"
Number: 1
Number: 2
Number: 3

# Conditional execution
psh$ eval "if [ -f /etc/passwd ]; then echo 'File exists'; fi"
File exists

# Pipelines in eval
psh$ eval "echo -e 'apple\\nbanana\\ncherry' | grep an"
banana

# Command substitution in eval
psh$ eval "current_time=\$(date); echo \"Time: \$current_time\""
Time: Mon Jan 15 12:00:00 UTC 2024

# I/O redirection
psh$ eval "echo 'test data' > /tmp/eval_test.txt"
psh$ cat /tmp/eval_test.txt
test data

# Nested eval (use with caution)
psh$ eval "eval \"echo 'nested execution'\""
nested execution

# Exit status handling
psh$ eval "true"
psh$ echo $?
0

psh$ eval "false"
psh$ echo $?
1

# Empty eval returns success
psh$ eval ""
psh$ echo $?
0

# Error handling
psh$ eval "nonexistent_command"
psh: nonexistent_command: command not found
psh$ echo $?
127
```

#### Practical Eval Examples

**Configuration Scripts:**
```bash
# Load configuration dynamically
config_file="/etc/myapp.conf"
if [ -f "$config_file" ]; then
    # Source config file through eval for security
    while IFS='=' read -r key value; do
        [[ $key =~ ^[A-Z_][A-Z0-9_]*$ ]] && eval "$key='$value'"
    done < "$config_file"
fi
```

**Command Dispatch:**
```bash
# Simple command dispatcher
action="$1"
case "$action" in
    start)   cmd="systemctl start myservice" ;;
    stop)    cmd="systemctl stop myservice" ;;
    restart) cmd="systemctl restart myservice" ;;
    status)  cmd="systemctl status myservice" ;;
    *)       echo "Usage: $0 {start|stop|restart|status}"; exit 1 ;;
esac

echo "Executing: $cmd"
eval "$cmd"
```

**Dynamic Variable Names:**
```bash
# Set multiple similar variables
for i in {1..5}; do
    eval "var_$i='Value $i'"
done

# Access them later
for i in {1..5}; do
    eval "echo \"Variable $i: \$var_$i\""
done
```

#### Security Considerations

**⚠️ Warning: eval can execute arbitrary code. Never use eval with untrusted input!**

```bash
# DANGEROUS - Don't do this
user_input="$1"
eval "$user_input"  # Could execute: rm -rf /

# SAFER - Validate input first
case "$user_input" in
    [a-zA-Z0-9_-]*) eval "$safe_command $user_input" ;;
    *) echo "Invalid input" ;;
esac

# SAFEST - Use alternatives when possible
case "$user_input" in
    start)   start_service ;;
    stop)    stop_service ;;
    status)  check_status ;;
esac
```

#### When to Use eval

**Good use cases:**
- Configuration scripts that set variables dynamically
- Command dispatchers with known, safe commands
- Complex parameter expansion scenarios
- Building commands from validated components

**Avoid eval when:**
- Processing user input directly
- Simple variable assignment would work
- Alternative approaches are available
- Security is a primary concern

#### Exit Status

The `eval` command returns the exit status of the last command executed:
- Returns 0 if arguments are empty or whitespace only
- Returns the exit status of the executed command(s)
- Returns 127 if the command is not found
- Returns appropriate exit codes for syntax errors

## 4.11 Positional Parameter Management

PSH provides built-ins for managing positional parameters ($1, $2, etc.) and parsing command-line options.

### shift - Shift Positional Parameters

The `shift` command removes positional parameters from the beginning of the list:

```bash
# Basic usage - shift by 1
psh$ set -- arg1 arg2 arg3 arg4
psh$ echo "Args: $@"
Args: arg1 arg2 arg3 arg4
psh$ shift
psh$ echo "Args: $@"
Args: arg2 arg3 arg4

# Shift by specific amount
psh$ set -- one two three four five
psh$ shift 2
psh$ echo "Args: $@"
Args: three four five

# Shift all parameters
psh$ set -- a b c
psh$ shift 3
psh$ echo "Args: $@"
Args:

# Error cases
psh$ set -- x y
psh$ shift 5  # More than available
psh$ echo $?
1

psh$ shift -1  # Negative not allowed
shift: shift count must be non-negative
```

#### Practical Shift Examples

**Processing Script Arguments:**
```bash
#!/usr/bin/env psh
# Process options until we find non-option arguments

while [ $# -gt 0 ]; do
    case "$1" in
        -v|--verbose)
            verbose=1
            shift
            ;;
        -f|--file)
            file="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Remaining arguments are in $@
echo "Remaining args: $@"
```

**Function with Variable Arguments:**
```bash
# Function that processes pairs of arguments
process_pairs() {
    while [ $# -ge 2 ]; do
        echo "Pair: $1 = $2"
        shift 2
    done
    
    if [ $# -eq 1 ]; then
        echo "Odd argument: $1"
    fi
}

process_pairs key1 value1 key2 value2 key3
```

### getopts - Parse Option Arguments

The `getopts` builtin provides POSIX-compliant option parsing:

```bash
# Basic option parsing
while getopts "hvo:" opt; do
    case $opt in
        h)
            echo "Usage: $0 [-h] [-v] [-o output]"
            exit 0
            ;;
        v)
            verbose=1
            ;;
        o)
            output="$OPTARG"
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

# Shift past the options
shift $((OPTIND - 1))
echo "Remaining args: $@"
```

#### getopts Features

**Option Arguments:**
```bash
# Options with required arguments (followed by :)
while getopts "f:d:v" opt; do
    case $opt in
        f)  file="$OPTARG" ;;
        d)  dir="$OPTARG" ;;
        v)  verbose=1 ;;
    esac
done
```

**Silent Error Reporting:**
```bash
# Leading : enables silent mode
while getopts ":f:v" opt; do
    case $opt in
        f)  file="$OPTARG" ;;
        v)  verbose=1 ;;
        :)  # Missing argument
            echo "Option -$OPTARG requires an argument" >&2
            exit 1
            ;;
        \?) # Invalid option
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done
```

**Clustered Options:**
```bash
# Handles: script -vfa file.txt
# Same as: script -v -f -a file.txt
while getopts "vf:a" opt; do
    case $opt in
        v)  verbose=1 ;;
        f)  file="$OPTARG" ;;
        a)  all=1 ;;
    esac
done
```

#### getopts Variables

- **OPTIND**: Index of next argument to process (starts at 1)
- **OPTARG**: Argument value for options requiring arguments
- **OPTERR**: Controls error message printing (1=enabled, 0=disabled)

```bash
# Reset option parsing
OPTIND=1

# Disable error messages
OPTERR=0

# Parse custom argument list
set -- -f file.txt -v
while getopts "f:v" opt; do
    echo "Option: $opt, OPTARG: $OPTARG, OPTIND: $OPTIND"
done
```

### command - Bypass Functions and Aliases

The `command` builtin executes commands while bypassing shell functions and aliases:

```bash
# Basic usage - bypass alias/function
psh$ alias ls='ls --color=auto'
psh$ ls           # Uses alias
psh$ command ls   # Bypasses alias

# Create function that shadows external command
psh$ grep() { echo "Function grep called"; }
psh$ grep test    # Calls function
Function grep called
psh$ command grep test file.txt  # Calls external grep

# Check if command exists
psh$ command -v ls
/bin/ls
psh$ command -v nonexistent
psh$ echo $?
1

# Verbose command information
psh$ command -V echo
echo is a shell builtin
psh$ command -V ls
ls is /bin/ls

# Use default PATH
psh$ PATH=/fake/path command -p ls  # Still finds ls
```

#### Practical command Examples

**Safe Command Execution:**
```bash
# Ensure we call external commands, not functions
backup_files() {
    # Always use external tar, not potential function
    command tar -czf backup.tar.gz "$@"
}

# Check command availability
if command -v git >/dev/null 2>&1; then
    echo "Git is installed"
else
    echo "Git is not installed"
fi
```

**Wrapper Functions:**
```bash
# Create wrapper that adds functionality
ls() {
    # Add header
    echo "=== Directory: $PWD ==="
    # Call real ls
    command ls "$@"
    # Add footer
    echo "=== Total: $(command ls -1 "$@" 2>/dev/null | wc -l) items ==="
}
```

**Portable Scripts:**
```bash
#!/usr/bin/env psh
# Use command -p for portable scripts

# Find files using POSIX utilities
command -p find . -type f -name "*.txt" |
command -p sort |
command -p head -10
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
- Job control (jobs, fg, bg, kill)
- Command help and information (help)
- Script execution (source)
- Conditional testing (test, [, [[)
- Process control (exec)
- Dynamic command execution (eval)

These commands execute quickly since they don't require forking new processes, and they have direct access to shell internals. Understanding built-ins is crucial for effective shell scripting and interactive use.

In the next chapter, we'll explore variables and parameters, building on the environment management commands covered here.

---

[← Previous: Chapter 3 - Basic Command Execution](03_basic_command_execution.md) | [Next: Chapter 5 - Variables and Parameters →](05_variables_and_parameters.md)