# Chapter 16: Advanced Features

PSH includes several advanced features that provide powerful capabilities for complex scripting and interactive use. These features extend the shell's functionality beyond basic command execution, offering sophisticated text processing, debugging tools, and enhanced control structures.

## 16.1 Process Substitution

Process substitution allows you to treat the output of a command as a file, enabling powerful command combinations that would otherwise require temporary files.

### Input Process Substitution <()

```bash
# Basic syntax: <(command)
# Creates a file descriptor that provides command's output

# Compare directory listings
psh$ diff <(ls dir1) <(ls dir2)
< file1.txt
> file3.txt

# Compare sorted versions without temp files
psh$ diff <(sort file1.txt) <(sort file2.txt)

# Multiple process substitutions
psh$ paste <(cut -f1 data.csv) <(cut -f3 data.csv) <(cut -f5 data.csv)

# Process substitution with comm
psh$ comm -12 <(sort list1.txt | uniq) <(sort list2.txt | uniq)
# Shows lines common to both lists

# Use with while loops
psh$ while IFS= read -r line; do
>     echo "Processing: $line"
> done < <(find . -name "*.txt")
```

### Output Process Substitution >()

```bash
# Basic syntax: >(command)
# Creates a file descriptor that sends data to command's input

# Split output to multiple processors
psh$ echo "test data" | tee >(grep pattern1) >(grep pattern2)

# Log filtering to different files
psh$ tail -f app.log | tee \
>     >(grep ERROR > errors.log) \
>     >(grep WARN > warnings.log) \
>     >(grep INFO > info.log)

# Process and save simultaneously
psh$ some_command | tee >(gzip > output.gz) | grep important

# Multiple transformations
psh$ cat data.txt | tee \
>     >(sed 's/old/new/g' > modified.txt) \
>     >(tr '[:lower:]' '[:upper:]' > uppercase.txt) \
>     >(awk '{print $1}' > firstcol.txt)
```

### Advanced Process Substitution Examples

```bash
# Complex diff with preprocessing
psh$ diff \
>     <(grep -v '^#' config1.conf | sort) \
>     <(grep -v '^#' config2.conf | sort)

# Join on processed data
psh$ join \
>     <(sort -k1,1 file1.txt) \
>     <(sort -k1,1 file2.txt)

# Real-time log analysis
psh$ paste \
>     <(tail -f access.log | awk '{print $1}') \
>     <(tail -f access.log | awk '{print $7}')

# Compare command outputs
psh$ diff \
>     <(cd /old/project && find . -type f -exec md5sum {} \;) \
>     <(cd /new/project && find . -type f -exec md5sum {} \;)

# Process substitution in functions
compare_dirs() {
    local dir1="$1"
    local dir2="$2"
    diff <(cd "$dir1" && find . | sort) \
         <(cd "$dir2" && find . | sort)
}
```

### Process Substitution Internals

```bash
# View the file descriptor
psh$ echo <(echo hello)
/dev/fd/63

# Multiple process substitutions get different FDs
psh$ echo <(echo one) <(echo two) <(echo three)
/dev/fd/63 /dev/fd/62 /dev/fd/61

# Process substitution with exec
psh$ exec 3< <(seq 1 10)
psh$ read -u 3 line
psh$ echo $line
1
psh$ exec 3<&-  # Close the descriptor
```

## 16.2 Enhanced Test Operators [[ ]]

The `[[ ]]` construct provides enhanced testing capabilities with better syntax and additional operators compared to the traditional `[` command.

### String Comparison Enhancements

```bash
# Lexicographic comparison (not in [ ])
psh$ [[ "apple" < "banana" ]] && echo "apple comes first"
apple comes first

psh$ [[ "zebra" > "ant" ]] && echo "zebra comes after"
zebra comes after

# No word splitting inside [[ ]]
psh$ var="hello world"
psh$ [[ -n $var ]] && echo "Safe without quotes"
Safe without quotes

# Pattern matching (not regex)
psh$ [[ "hello.txt" == *.txt ]] && echo "Text file"
Text file

psh$ [[ "document.pdf" == *.@(pdf|doc) ]] && echo "Document"
Document
```

### Regular Expression Matching

```bash
# =~ operator for regex matching
psh$ [[ "user@example.com" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]
psh$ echo $?
0

# Capture groups (when supported)
psh$ string="Version 2.4.6"
psh$ if [[ "$string" =~ Version[[:space:]]([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
>     echo "Major: ${BASH_REMATCH[1]}"
>     echo "Minor: ${BASH_REMATCH[2]}"
>     echo "Patch: ${BASH_REMATCH[3]}"
> fi

# Common regex patterns
psh$ # IP address validation
psh$ ip="192.168.1.1"
psh$ [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]

psh$ # Phone number
psh$ phone="123-456-7890"
psh$ [[ "$phone" =~ ^[0-9]{3}-[0-9]{3}-[0-9]{4}$ ]]

psh$ # File extension check
psh$ file="script.sh"
psh$ [[ "$file" =~ \.(sh|bash|zsh)$ ]] && echo "Shell script"
```

### Compound Conditions

```bash
# && and || inside [[ ]]
psh$ file="/etc/passwd"
psh$ [[ -f "$file" && -r "$file" ]] && echo "File exists and is readable"
File exists and is readable

psh$ [[ "$USER" == "root" || "$UID" -eq 0 ]] && echo "Running as root"

# Complex conditions
psh$ age=25
psh$ name="Alice"
psh$ [[ "$name" =~ ^[A-Z] && "$age" -ge 18 && "$age" -le 65 ]] && \
>     echo "Valid adult name"

# Negation with !
psh$ [[ ! -d "$dir" ]] && mkdir "$dir"

# Parentheses for grouping
psh$ [[ ( "$a" -eq 1 || "$b" -eq 2 ) && "$c" -eq 3 ]]
```

### [[ ]] vs [ ] Comparison

```bash
# Word splitting difference
psh$ var="hello world"
psh$ [ -n $var ]   # Error: too many arguments
psh$ [[ -n $var ]] # Works fine

# Empty variable handling
psh$ unset var
psh$ [ "$var" = "test" ]   # Works
psh$ [[ $var = "test" ]]   # Also works (safer)

# Pattern matching
psh$ [ "file.txt" == *.txt ]   # Doesn't work as expected
psh$ [[ "file.txt" == *.txt ]] # Works correctly

# Operators available in [[ ]] but not [ ]
# <, > for string comparison
# =~ for regex matching
# == with patterns
```

## 16.3 Debug and Diagnostic Features

PSH provides powerful debugging capabilities to help understand script execution and troubleshoot issues.

### AST (Abstract Syntax Tree) Debugging

```bash
# Show parsed AST before execution
psh$ psh --debug-ast -c 'echo $((2 + 3))'
=== AST ===
Pipeline:
  Command: SimpleCommand
    words: ['echo', ArithmeticExpansion(expression='2 + 3')]
    redirects: []
=== End AST ===
5

# Debug complex commands
psh$ psh --debug-ast -c 'for i in {1..3}; do echo $i; done'
=== AST ===
ForLoop:
  var: 'i'
  items: [BraceExpansion('{1..3}')]
  body: Pipeline:
    Command: SimpleCommand
      words: ['echo', Variable(name='i')]
=== End AST ===
1
2
3

# Enable AST debugging at runtime
psh$ set -o debug-ast
psh$ echo hello
=== AST ===
Pipeline:
  Command: SimpleCommand
    words: ['echo', 'hello']
    redirects: []
=== End AST ===
hello

# Disable AST debugging
psh$ set +o debug-ast
```

### Token-Level Debugging

```bash
# Show tokenization process
psh$ psh --debug-tokens -c 'echo "Hello, $USER!"'
=== Tokens ===
Token(WORD, 'echo', 1:1)
Token(STRING, '"Hello, $USER!"', 1:6)
Token(EOF, '', 1:21)
=== End Tokens ===
Hello, alice!

# Debug complex tokenization
psh$ psh --debug-tokens -c 'ls | grep -E "\.txt$" > files.txt'
=== Tokens ===
Token(WORD, 'ls', 1:1)
Token(PIPE, '|', 1:4)
Token(WORD, 'grep', 1:6)
Token(WORD, '-E', 1:11)
Token(STRING, '"\.txt$"', 1:14)
Token(REDIRECT, '>', 1:23)
Token(WORD, 'files.txt', 1:25)
Token(EOF, '', 1:34)
=== End Tokens ===

# Runtime token debugging
psh$ set -o debug-tokens
psh$ echo test
=== Tokens ===
Token(WORD, 'echo', 1:1)
Token(WORD, 'test', 1:6)
Token(EOF, '', 1:10)
=== End Tokens ===
test
```

### Variable Scope Debugging

```bash
# Debug local variable scopes
psh$ psh --debug-scopes script.sh
[SCOPE] Entering function: main
[SCOPE] Creating local variable: count
[SCOPE] Variable lookup: count (found in local scope)
[SCOPE] Exiting function: main

# Example with nested functions
psh$ cat > scope_demo.sh << 'EOF'
> outer() {
>     local x=1
>     inner() {
>         local y=2
>         echo "$x $y"
>     }
>     inner
> }
> outer
> EOF

psh$ psh --debug-scopes scope_demo.sh
[SCOPE] Entering function: outer
[SCOPE] Creating local variable: x
[SCOPE] Entering function: inner
[SCOPE] Creating local variable: y
[SCOPE] Variable lookup: x (found in parent scope)
[SCOPE] Variable lookup: y (found in local scope)
1 2
[SCOPE] Exiting function: inner
[SCOPE] Exiting function: outer
```

### Combining Debug Modes

```bash
# Multiple debug flags
psh$ psh --debug-ast --debug-tokens -c 'echo $HOME'
=== Tokens ===
Token(WORD, 'echo', 1:1)
Token(VARIABLE, '$HOME', 1:6)
Token(EOF, '', 1:11)
=== End Tokens ===
=== AST ===
Pipeline:
  Command: SimpleCommand
    words: ['echo', Variable(name='HOME')]
    redirects: []
=== End AST ===
/home/user

# All debug modes
psh$ psh --debug-ast --debug-tokens --debug-scopes script.sh

# Runtime control
psh$ set -o debug-ast
psh$ set -o debug-tokens
psh$ set -o  # Show all settings
debug-ast      on
debug-tokens   on
emacs          on
vi             off
```

## 16.4 Advanced Parameter Expansion

PSH supports sophisticated parameter expansion operations for string manipulation.

### Length Operations

```bash
# String length
psh$ var="Hello, World!"
psh$ echo ${#var}
13

# Array length (when arrays are supported)
psh$ set -- one two three
psh$ echo ${#}
3
psh$ echo ${#*}
3
psh$ echo ${#@}
3

# Length of specific parameter
psh$ echo ${#1}  # Length of $1
3
```

### Pattern Removal

```bash
# Remove from beginning (# and ##)
psh$ file="/path/to/file.txt"
psh$ echo ${file#*/}      # Remove first /
path/to/file.txt
psh$ echo ${file##*/}     # Remove up to last /
file.txt

# Remove from end (% and %%)
psh$ echo ${file%/*}      # Remove last /
/path/to
psh$ echo ${file%%/*}     # Remove from first /
                          # (empty)

# Practical examples
psh$ # Get file extension
psh$ filename="document.pdf"
psh$ echo ${filename##*.}
pdf

psh$ # Get filename without extension
psh$ echo ${filename%.*}
document

psh$ # Remove path and extension
psh$ fullpath="/home/user/file.tar.gz"
psh$ name=${fullpath##*/}
psh$ echo ${name%%.*}
file
```

### Pattern Substitution

```bash
# Single substitution
psh$ text="hello hello world"
psh$ echo ${text/hello/hi}
hi hello world

# Global substitution
psh$ echo ${text//hello/hi}
hi hi world

# Anchored substitution
psh$ echo ${text/#hello/hi}    # Beginning
hi hello world
psh$ echo ${text/%world/universe}  # End
hello hello universe

# Delete pattern
psh$ echo ${text/hello/}       # Delete first
 hello world
psh$ echo ${text//hello/}      # Delete all
  world

# Complex patterns
psh$ path="/usr/local/bin"
psh$ echo ${path//\//|}        # Replace all / with |
|usr|local|bin
```

### Substring Extraction

```bash
# Basic substring
psh$ var="Hello, World!"
psh$ echo ${var:0:5}          # From 0, length 5
Hello
psh$ echo ${var:7:5}          # From 7, length 5
World

# From position to end
psh$ echo ${var:7}            # From position 7
World!

# Negative offsets
psh$ echo ${var: -6}          # Last 6 characters
World!
psh$ echo ${var: -6:5}        # From -6, length 5
World

# With parameters
psh$ set -- "Hello, World!"
psh$ echo ${1:0:5}
Hello
```

### Case Modification

```bash
# First character uppercase
psh$ name="alice"
psh$ echo ${name^}
Alice

# All uppercase
psh$ echo ${name^^}
ALICE

# First character lowercase
psh$ NAME="ALICE"
psh$ echo ${NAME,}
aLICE

# All lowercase
psh$ echo ${NAME,,}
alice

# Pattern-based case modification
psh$ text="hello world"
psh$ echo ${text^[hw]}        # Uppercase h or w
Hello world
psh$ echo ${text^^[aeiou]}    # Uppercase vowels
hEllO wOrld
```

### Variable Name Matching

```bash
# List variables by prefix
psh$ PATH_HOME=/home
psh$ PATH_BIN=/bin
psh$ PATH_LIB=/lib
psh$ echo ${!PATH*}
PATH PATH_BIN PATH_HOME PATH_LIB

psh$ echo ${!PATH@}
PATH PATH_BIN PATH_HOME PATH_LIB

# Practical use
psh$ # Find all LC_ variables
psh$ echo ${!LC_*}
LC_ALL LC_CTYPE LC_TIME

# In loops
psh$ for var in ${!USER*}; do
>     echo "$var=${!var}"
> done
USER=alice
USERNAME=alice
USER_HOME=/home/alice
```

## 16.5 Arithmetic Commands

The `(( ))` construct provides arithmetic evaluation with conditional exit status.

### Basic Arithmetic Commands

```bash
# Arithmetic evaluation
psh$ ((5 + 3))
psh$ echo $?
0              # Non-zero result gives exit status 0

psh$ ((5 - 5))
psh$ echo $?
1              # Zero result gives exit status 1

# Variable assignment
psh$ ((x = 10))
psh$ echo $x
10

psh$ ((x++))
psh$ echo $x
11

# Multiple expressions
psh$ ((a = 5, b = 10, c = a + b))
psh$ echo $c
15
```

### Arithmetic Conditionals

```bash
# In if statements
psh$ x=10
psh$ if ((x > 5)); then
>     echo "x is greater than 5"
> fi
x is greater than 5

# Complex conditions
psh$ if ((x > 0 && x < 20)); then
>     echo "x is between 0 and 20"
> fi

# Arithmetic in while loops
psh$ i=0
psh$ while ((i < 5)); do
>     echo $i
>     ((i++))
> done
0
1
2
3
4

# Ternary operator
psh$ ((result = x > 10 ? 1 : 0))
psh$ echo $result
0
```

### C-Style For Loops

```bash
# Basic C-style for loop
psh$ for ((i=0; i<5; i++)); do
>     echo "Iteration $i"
> done
Iteration 0
Iteration 1
Iteration 2
Iteration 3
Iteration 4

# Multiple variables
psh$ for ((i=0, j=10; i<5; i++, j--)); do
>     echo "i=$i, j=$j"
> done
i=0, j=10
i=1, j=9
i=2, j=8
i=3, j=7
i=4, j=6

# Empty sections
psh$ i=0
psh$ for ((; i<3; i++)); do
>     echo $i
> done

# Infinite loop (use with care)
psh$ for ((;;)); do
>     read -p "Enter 'quit' to exit: " input
>     [[ "$input" == "quit" ]] && break
> done
```

## 16.6 Advanced I/O Features

### Advanced Redirections

```bash
# Multiple redirections
psh$ command < input.txt > output.txt 2> error.txt

# Redirect specific file descriptors
psh$ exec 3< input.txt     # Open FD 3 for reading
psh$ exec 4> output.txt    # Open FD 4 for writing
psh$ read -u 3 line        # Read from FD 3
psh$ echo "data" >&4       # Write to FD 4
psh$ exec 3<&-             # Close FD 3
psh$ exec 4>&-             # Close FD 4

# Here documents with suppressed tabs
psh$ cat <<-EOF
>     This line has tabs
>     They are removed
> EOF
This line has tabs
They are removed

# Here strings
psh$ grep "pattern" <<< "test pattern string"
test pattern string
```

### Advanced Read Options

```bash
# Read with prompt
psh$ read -p "Enter your name: " name
Enter your name: Alice
psh$ echo "Hello, $name"
Hello, Alice

# Silent reading (passwords)
psh$ read -s -p "Password: " password
Password: 
psh$ echo    # New line after silent input

# Read with timeout
psh$ if read -t 5 -p "Quick! Enter something: " response; then
>     echo "You entered: $response"
> else
>     echo "Too slow! (timeout)"
> fi

# Read exact number of characters
psh$ read -n 4 -p "Enter 4-digit PIN: " pin
Enter 4-digit PIN: 1234psh$ echo
psh$ echo "PIN: $pin"
PIN: 1234

# Custom delimiter
psh$ read -d ':' -p "Enter data (end with :): " data
Enter data (end with :): hello world:psh$ echo
psh$ echo "Data: $data"
Data: hello world
```

## 16.7 Advanced Shell Options

### Runtime Configuration

```bash
# View all options
psh$ set -o
debug-ast      off
debug-tokens   off
emacs          on
vi             off

# Enable options
psh$ set -o vi            # Vi mode
psh$ set -o debug-ast     # AST debugging

# Disable options
psh$ set +o vi            # Disable vi mode
psh$ set +o debug-ast     # Disable AST debugging

# Future options (when implemented)
# set -e    # Exit on error
# set -u    # Error on undefined variables
# set -x    # Print commands before execution
# set -o pipefail  # Pipeline fails if any command fails
```

### Advanced Prompt Features

```bash
# Conditional prompts
psh$ PS1='$(if [ $? -eq 0 ]; then echo "✓"; else echo "✗"; fi) \u@\h:\w\$ '
✓ user@host:~$ false
✗ user@host:~$ true
✓ user@host:~$ 

# Git branch in prompt
psh$ git_branch() {
>     git branch 2>/dev/null | grep '^*' | sed 's/* //'
> }
psh$ PS1='\u@\h:\w$(git_branch)\$ '
user@host:~/project(main)$ 

# Dynamic color based on exit status
psh$ PS1='$(if [ $? -eq 0 ]; then
>     echo "\[\e[32m\]✓\[\e[0m\]"
> else
>     echo "\[\e[31m\]✗\[\e[0m\]"
> fi) \u@\h:\w\$ '

# Command timer in prompt
psh$ SECONDS=0
psh$ PS1='[$SECONDS] \u@\h:\w\$ '
[0] user@host:~$ sleep 2
[2] user@host:~$ 
```

## 16.8 Advanced Scripting Patterns

### Error Handling Patterns

```bash
#!/usr/bin/env psh

# Error handler with line numbers
error_handler() {
    local line_no=$1
    local exit_code=$2
    echo "Error on line $line_no: Command exited with status $exit_code" >&2
    exit $exit_code
}

# Wrapper for safe execution
safe_exec() {
    "$@" || error_handler ${BASH_LINENO[0]} $?
}

# Usage
safe_exec cd /nonexistent
safe_exec rm important_file
```

### Parallel Execution

```bash
# Run commands in parallel
psh$ for file in *.txt; do
>     process_file "$file" &
> done
> wait  # Wait for all background jobs

# Limited parallelism
psh$ max_jobs=4
psh$ job_count=0
psh$ for file in *.txt; do
>     process_file "$file" &
>     ((job_count++))
>     if ((job_count >= max_jobs)); then
>         wait -n  # Wait for any job to finish
>         ((job_count--))
>     fi
> done
> wait  # Wait for remaining jobs
```

### Advanced Function Patterns

```bash
# Function with named parameters
psh$ function parse_args() {
>     local name=""
>     local age=""
>     local city=""
>     
>     while [[ $# -gt 0 ]]; do
>         case "$1" in
>             --name=*) name="${1#*=}"; shift ;;
>             --age=*) age="${1#*=}"; shift ;;
>             --city=*) city="${1#*=}"; shift ;;
>             *) echo "Unknown option: $1" >&2; return 1 ;;
>         esac
>     done
>     
>     echo "Name: $name, Age: $age, City: $city"
> }

psh$ parse_args --name=Alice --age=30 --city="New York"
Name: Alice, Age: 30, City: New York

# Recursive directory processor
psh$ process_tree() {
>     local dir="${1:-.}"
>     local indent="${2:-}"
>     
>     echo "${indent}Processing: $dir"
>     
>     for item in "$dir"/*; do
>         [ -e "$item" ] || continue
>         
>         if [ -d "$item" ]; then
>             process_tree "$item" "$indent  "
>         else
>             echo "$indent  File: ${item##*/}"
>         fi
>     done
> }
```

## 16.9 Integration with External Tools

### Advanced Pipeline Patterns

```bash
# Complex data processing pipeline
psh$ cat access.log | \
>     grep -v "bot" | \
>     awk '{print $1, $7}' | \
>     sort | \
>     uniq -c | \
>     sort -rn | \
>     head -20 | \
>     while read count ip url; do
>         printf "%6d %-15s %s\n" "$count" "$ip" "$url"
>     done

# Parallel processing with xargs (when available)
psh$ find . -name "*.jpg" -print0 | \
>     xargs -0 -P 4 -I {} convert {} -resize 800x600 small/{}

# Stream processing with continuous output
psh$ tail -f application.log | \
>     while IFS= read -r line; do
>         if [[ "$line" =~ ERROR ]]; then
>             echo "$(date): $line" >> errors.log
>             send_alert "$line"
>         fi
>     done
```

## 16.10 Performance Optimization

### Efficient Shell Patterns

```bash
# Avoid command substitution in loops
# Bad:
psh$ for file in $(ls *.txt); do
>     process "$file"
> done

# Good:
psh$ for file in *.txt; do
>     [ -e "$file" ] || continue
>     process "$file"
> done

# Minimize subshells
# Bad:
psh$ result=$(echo "$string" | tr '[:lower:]' '[:upper:]')

# Good:
psh$ result=${string^^}  # Using parameter expansion

# Batch operations
# Bad:
psh$ for i in {1..1000}; do
>     echo "$i" >> output.txt
> done

# Good:
psh$ for i in {1..1000}; do
>     echo "$i"
> done > output.txt

# Read files efficiently
# Bad:
psh$ while read line; do
>     process "$line"
> done < <(cat file.txt)

# Good:
psh$ while IFS= read -r line; do
>     process "$line"
> done < file.txt
```

## Summary

PSH's advanced features provide powerful capabilities for complex shell programming:

1. **Process Substitution**: `<()` and `>()` for treating command output as files
2. **Enhanced Test Operators**: `[[ ]]` with regex matching and better syntax
3. **Debug Features**: AST, token, and scope debugging for troubleshooting
4. **Advanced Parameter Expansion**: String manipulation without external commands
5. **Arithmetic Commands**: `(( ))` for C-style arithmetic and conditionals
6. **Advanced I/O**: File descriptors, here documents, advanced read options
7. **Shell Options**: Runtime configuration and debugging controls
8. **Advanced Patterns**: Error handling, parallel execution, complex functions
9. **External Integration**: Sophisticated pipeline and tool integration
10. **Performance**: Optimization techniques for efficient scripts

Key concepts:
- Process substitution eliminates temporary files
- Enhanced test operators provide safer, more powerful conditionals
- Debug features help understand script execution
- Parameter expansion reduces dependency on external commands
- Arithmetic commands enable C-style programming constructs
- Advanced patterns solve complex real-world problems
- Performance optimization makes scripts more efficient

These advanced features make PSH a sophisticated shell implementation suitable for complex scripting tasks while maintaining clarity for educational purposes.

---

[← Previous: Chapter 15 - Job Control](15_job_control.md) | [Next: Chapter 17 - Differences from Bash →](17_differences_from_bash.md)