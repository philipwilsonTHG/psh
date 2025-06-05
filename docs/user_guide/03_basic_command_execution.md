# Chapter 3: Basic Command Execution

## 3.1 Running External Commands

PSH can run any program available on your system. When you type a command, PSH searches for it in the directories listed in your PATH environment variable.

### How PSH Finds Commands

PSH follows these steps to execute a command:

1. Check if it's a built-in command (like `cd`, `echo`)
2. Check if it's a function you've defined
3. Check if it's an alias
4. Search for an external program in PATH

```bash
# View your PATH
psh$ echo $PATH
/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Which command will be run?
psh$ which ls
/bin/ls

# Run an external command
psh$ ls -l /tmp
total 8
drwx------  2 user user 4096 Jan 15 10:00 ssh-XXXXXX
drwx------  3 user user 4096 Jan 15 09:30 systemd-private-XXXXXX
```

### Absolute and Relative Paths

You can run programs using their full path:

```bash
# Absolute path
psh$ /bin/date
Mon Jan 15 10:45:23 PST 2024

# Relative path
psh$ ./myscript.sh
Hello from my script!

# Programs in current directory need ./
psh$ cat > hello.sh << 'EOF'
#!/usr/bin/env psh
echo "Hello, World!"
EOF
psh$ chmod +x hello.sh
psh$ hello.sh          # This won't work
psh: hello.sh: command not found
psh$ ./hello.sh        # This works
Hello, World!
```

### Command Not Found

When PSH can't find a command:

```bash
psh$ nonexistent
psh: nonexistent: command not found

# The exit status is 127 for "command not found"
psh$ echo $?
127
```

## 3.2 Command Arguments and Options

Commands can accept arguments and options that modify their behavior.

### Arguments

Arguments are values passed to commands:

```bash
# Single argument
psh$ echo Hello
Hello

# Multiple arguments
psh$ echo Hello World
Hello World

# Arguments with spaces need quotes
psh$ mkdir "My Documents"
psh$ ls
My Documents

# Without quotes, creates two directories
psh$ mkdir My Files
psh$ ls
Files  My  My Documents
```

### Options

Options (also called flags or switches) modify command behavior:

```bash
# Short options
psh$ ls -l              # Long format
psh$ ls -a              # Show hidden files
psh$ ls -la             # Combine options
psh$ ls -l -a           # Same as above

# Long options
psh$ ls --all           # Same as -a
psh$ ls --help          # Show help

# Options with values
psh$ grep -n "text" file.txt    # -n shows line numbers
psh$ sort -k 2 data.txt          # -k 2 sorts by second field
psh$ head -n 5 longfile.txt      # -n 5 shows first 5 lines
```

### Option Terminator (--)

Use `--` to separate options from arguments:

```bash
# Create a file named "-n"
psh$ touch -- -n
psh$ ls
-n

# Without --, echo would interpret -n as option
psh$ echo -n
psh$ echo -- -n
-n
```

## 3.3 Multiple Commands (;)

The semicolon (`;`) lets you run multiple commands on one line:

```bash
# Run commands sequentially
psh$ echo "First"; echo "Second"; echo "Third"
First
Second
Third

# Mix different commands
psh$ cd /tmp; pwd; ls | wc -l
/tmp
42

# Commands run regardless of previous success
psh$ false; echo "This still runs"
This still runs

# Each command's exit status is independent
psh$ true; false; echo $?
1
```

### Command Separation vs Line Continuation

```bash
# Multiple commands on multiple lines
psh$ echo "Line 1"
Line 1
psh$ echo "Line 2"
Line 2

# Equivalent using semicolons
psh$ echo "Line 1"; echo "Line 2"
Line 1
Line 2

# Line continuation with backslash
psh$ echo "This is a very long line that \
> continues on the next line"
This is a very long line that continues on the next line
```

## 3.4 Exit Status and $?

Every command returns an exit status (also called return code or exit code):
- 0 means success
- Non-zero means failure (1-255)

### Checking Exit Status

The special variable `$?` holds the exit status of the last command:

```bash
# Successful command
psh$ echo "Hello"
Hello
psh$ echo $?
0

# Failed command
psh$ ls /nonexistent
ls: cannot access '/nonexistent': No such file or directory
psh$ echo $?
2

# Test command examples
psh$ [ 5 -gt 3 ]
psh$ echo $?
0

psh$ [ 5 -lt 3 ]
psh$ echo $?
1
```

### Common Exit Codes

Different exit codes indicate different types of errors:

```bash
# Success
psh$ true
psh$ echo $?
0

# General error
psh$ false
psh$ echo $?
1

# Misuse of shell builtin
psh$ cd /nonexistent
cd: /nonexistent: No such file or directory
psh$ echo $?
1

# Command not found
psh$ nonexistentcommand
psh: nonexistentcommand: command not found
psh$ echo $?
127

# Command found but not executable
psh$ touch notexecutable
psh$ ./notexecutable
psh: ./notexecutable: Permission denied
psh$ echo $?
126
```

### Using Exit Status in Scripts

```bash
# Create a script that checks exit status
psh$ cat > check_file.sh << 'EOF'
#!/usr/bin/env psh

if [ -f "$1" ]; then
    echo "File exists: $1"
    exit 0
else
    echo "File not found: $1"
    exit 1
fi
EOF

psh$ chmod +x check_file.sh
psh$ ./check_file.sh /etc/passwd
File exists: /etc/passwd
psh$ echo $?
0

psh$ ./check_file.sh /nonexistent
File not found: /nonexistent
psh$ echo $?
1
```

## 3.5 Background Execution (&)

The ampersand (`&`) runs commands in the background, allowing you to continue using the shell:

### Basic Background Execution

```bash
# Run a long command in background
psh$ sleep 10 &
[1] 12345

# The shell is immediately available
psh$ echo "I can run other commands"
I can run other commands

# Check background jobs
psh$ jobs
[1]+ Running    sleep 10 &

# Wait for completion
psh$ # After 10 seconds...
[1]+ Done       sleep 10
```

### Background Process Details

```bash
# Multiple background jobs
psh$ sleep 20 & sleep 30 & sleep 40 &
[1] 12346
[2] 12347
[3] 12348

psh$ jobs
[1]  Running    sleep 20 &
[2]- Running    sleep 30 &
[3]+ Running    sleep 40 &

# The + indicates the current job
# The - indicates the previous job

# Bring job to foreground
psh$ fg %1
sleep 20
# (waits for completion)

# Send job back to background
psh$ sleep 60
^Z
[4]+ Stopped    sleep 60
psh$ bg
[4]+ sleep 60 &
```

### Background I/O

Background processes can still write to the terminal:

```bash
# Background process with output
psh$ (sleep 2; echo "Background says hello") &
[1] 12349
psh$ # Keep working...
# After 2 seconds:
Background says hello
[1]+ Done       (sleep 2; echo "Background says hello")

# Redirect output to avoid interruption
psh$ (sleep 2; echo "Background says hello") > bg_output.txt &
[1] 12350
psh$ # No interruption this time
[1]+ Done       (sleep 2; echo "Background says hello") > bg_output.txt
psh$ cat bg_output.txt
Background says hello
```

### Special Variable $!

The `$!` variable holds the PID of the last background process:

```bash
psh$ sleep 100 &
[1] 12351
psh$ echo "Background PID: $!"
Background PID: 12351

# You can use this to wait for specific processes
psh$ sleep 5 &
[2] 12352
psh$ pid=$!
psh$ echo "Waiting for process $pid"
Waiting for process 12352
psh$ wait $pid
[2]+ Done       sleep 5
```

## 3.6 Comments (#)

Comments help document your commands and scripts:

### Basic Comments

```bash
# This is a comment
psh$ echo "Hello" # This is also a comment
Hello

# Comments can span entire lines
psh$ # This entire line is a comment
psh$ 

# Everything after # is ignored
psh$ echo "Hello" # echo "This won't be printed"
Hello
```

### Comments in Scripts

```bash
psh$ cat > script_with_comments.sh << 'EOF'
#!/usr/bin/env psh
# This script demonstrates comments
# Author: Your Name
# Date: January 2024

# Set a variable
name="PSH User"  # Store the user's name

# Print a greeting
echo "Hello, $name!"  # Greet the user

# The next line is commented out:
# echo "This line won't run"

# Multi-line comments can be done like this:
# Line 1 of comment
# Line 2 of comment
# Line 3 of comment
EOF

psh$ chmod +x script_with_comments.sh
psh$ ./script_with_comments.sh
Hello, PSH User!
```

### When # Is Not a Comment

The `#` character is only a comment when it appears at a word boundary:

```bash
# This is a comment
psh$ echo "Hello #World"    # # inside quotes is not a comment
Hello #World

psh$ echo Hello#World       # # in middle of word is not a comment
Hello#World

# But this # starts a comment
psh$ echo Hello #World
Hello

# In arithmetic expansion
psh$ echo $((2#101))        # Binary number, not a comment
5
```

### Shebang (#!)

The shebang is a special comment on the first line of scripts:

```bash
#!/usr/bin/env psh
# This tells the system to use psh to run this script

#!/bin/bash
# This would use bash instead

#!/usr/bin/python3
# This would use Python 3
```

## Practical Examples

### System Information Script

```bash
psh$ cat > sysinfo.sh << 'EOF'
#!/usr/bin/env psh
# Simple system information script

echo "=== System Information ==="
echo

# Hostname
echo "Hostname: $(hostname)"

# Current date and time
echo "Date: $(date)"

# Current user
echo "User: $USER"

# Home directory
echo "Home: $HOME"

# Current directory
echo "PWD: $(pwd)"

# System uptime (if available)
echo "Uptime: $(uptime 2>/dev/null || echo 'Not available')"

# Disk usage of current directory
echo
echo "=== Disk Usage ==="
df -h .

# Count files in current directory
file_count=$(ls -1 | wc -l)
echo
echo "Files in current directory: $file_count"
EOF

psh$ chmod +x sysinfo.sh
psh$ ./sysinfo.sh
=== System Information ===

Hostname: mycomputer
Date: Mon Jan 15 11:30:45 PST 2024
User: alice
Home: /home/alice
PWD: /home/alice/scripts
Uptime: 11:30:45 up 5 days, 3:15, 2 users, load average: 0.15, 0.20, 0.18

=== Disk Usage ===
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   15G   33G  32% /

Files in current directory: 12
```

### Backup Script with Error Checking

```bash
psh$ cat > backup.sh << 'EOF'
#!/usr/bin/env psh
# Simple backup script with error checking

# Check if source directory provided
if [ -z "$1" ]; then
    echo "Usage: $0 <source_directory>"
    exit 1
fi

SOURCE="$1"
BACKUP_DIR="$HOME/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}.tar.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if source exists
if [ ! -d "$SOURCE" ]; then
    echo "Error: Source directory '$SOURCE' not found"
    exit 1
fi

echo "Creating backup of $SOURCE..."

# Create the backup
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}" "$SOURCE" 2>/dev/null &
TAR_PID=$!

# Show progress while backing up
while ps -p $TAR_PID > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo

# Check if backup succeeded
wait $TAR_PID
if [ $? -eq 0 ]; then
    echo "Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}"
    ls -lh "${BACKUP_DIR}/${BACKUP_NAME}"
else
    echo "Error: Backup failed"
    exit 1
fi
EOF

psh$ chmod +x backup.sh
psh$ ./backup.sh Documents
Creating backup of Documents...
.....
Backup completed: /home/alice/backups/backup_20240115_113145.tar.gz
-rw-r--r-- 1 alice alice 2.3M Jan 15 11:31 /home/alice/backups/backup_20240115_113145.tar.gz
```

## Summary

In this chapter, you learned:
- How PSH finds and executes external commands
- How to pass arguments and options to commands
- How to run multiple commands with semicolons
- How exit status works and how to check it with `$?`
- How to run commands in the background with `&`
- How to use comments to document your commands

These fundamentals of command execution form the basis for all shell operations. In the next chapter, we'll explore PSH's built-in commands, which provide essential functionality without calling external programs.

---

[← Previous: Chapter 2 - Getting Started](02_getting_started.md) | [Next: Chapter 4 - Built-in Commands →](04_builtin_commands.md)