# Chapter 5: Variables and Parameters

Variables are fundamental to shell programming. They store data that can be used throughout your scripts and interactive sessions. PSH supports shell variables, environment variables, special variables, and advanced parameter expansion features.

## 5.1 Variable Assignment and Usage

### Basic Variable Assignment

Variables in PSH follow these rules:
- Names start with a letter or underscore
- Can contain letters, numbers, and underscores
- Case-sensitive
- No spaces around the = sign

```bash
# Basic assignment
psh$ name="Alice"
psh$ age=25
psh$ city="New York"

# Using variables
psh$ echo "Hello, $name"
Hello, Alice

psh$ echo "Age: $age, City: $city"
Age: 25, City: New York

# Variable names are case-sensitive
psh$ Name="Bob"
psh$ echo "$name vs $Name"
Alice vs Bob

# No spaces allowed around =
psh$ var = "value"     # Wrong - runs 'var' command
psh: var: command not found

psh$ var= "value"      # Wrong - runs "value" with empty var
psh: value: command not found

psh$ var ="value"      # Wrong - runs 'var' command  
psh: var: command not found

psh$ var="value"       # Correct
```

### Variable Naming Conventions

```bash
# Valid variable names
psh$ user_name="alice"
psh$ USER_NAME="ALICE"
psh$ _private="hidden"
psh$ var123="numeric"
psh$ myVar="camelCase"

# Invalid names (won't work)
psh$ 123var="bad"      # Can't start with number
psh$ my-var="bad"      # No hyphens allowed
psh$ my var="bad"      # No spaces allowed
psh$ my.var="bad"      # No dots allowed

# Convention: Use UPPERCASE for environment/constants
psh$ readonly MAX_RETRIES=3
psh$ export DATABASE_URL="postgresql://localhost/mydb"

# Convention: Use lowercase for local variables
psh$ counter=0
psh$ temp_file="/tmp/data.tmp"
```

### Variable Scope

```bash
# Variables are global by default
psh$ global_var="I'm global"

psh$ show_var() {
>     echo "Inside function: $global_var"
>     global_var="Modified in function"
> }

psh$ show_var
Inside function: I'm global
psh$ echo "After function: $global_var"
After function: Modified in function

# Local variables in functions
psh$ test_locals() {
>     local local_var="I'm local"
>     echo "Inside function: $local_var"
> }

psh$ test_locals
Inside function: I'm local
psh$ echo "Outside function: $local_var"
Outside function: 
```

## 5.2 Environment vs Shell Variables

### Shell Variables

Shell variables exist only within the current shell:

```bash
# Create shell variable
psh$ MY_VAR="shell variable"
psh$ echo $MY_VAR
shell variable

# Not visible to child processes
psh$ psh -c 'echo "Child sees: $MY_VAR"'
Child sees: 

# View all shell variables with set
psh$ set | grep MY_VAR
MY_VAR=shell variable
```

### Environment Variables

Environment variables are passed to child processes:

```bash
# Export to environment
psh$ export ENV_VAR="environment variable"
psh$ echo $ENV_VAR
environment variable

# Visible to child processes
psh$ psh -c 'echo "Child sees: $ENV_VAR"'
Child sees: environment variable

# Export existing variable
psh$ ANOTHER_VAR="test"
psh$ psh -c 'echo "Before export: $ANOTHER_VAR"'
Before export: 
psh$ export ANOTHER_VAR
psh$ psh -c 'echo "After export: $ANOTHER_VAR"'
After export: test

# View environment with env
psh$ env | grep ENV_VAR
ENV_VAR=environment variable
```

### Common Environment Variables

```bash
# System-defined variables
psh$ echo $HOME
/home/alice

psh$ echo $USER
alice

psh$ echo $PATH
/usr/local/bin:/usr/bin:/bin

psh$ echo $PWD
/home/alice/documents

psh$ echo $SHELL
/usr/bin/psh

# Modify PATH
psh$ export PATH="$PATH:/home/alice/bin"
psh$ echo $PATH
/usr/local/bin:/usr/bin:/bin:/home/alice/bin

# Temporary environment for one command
psh$ TEMP_VAR=value command
psh$ echo $TEMP_VAR  # Not set in current shell
```

## 5.3 Special Variables

PSH provides several special variables with specific meanings:

### Positional Parameters

```bash
# In scripts or functions
# script.sh:
#!/usr/bin/env psh
echo "Script name: $0"
echo "First argument: $1"
echo "Second argument: $2"
echo "Third argument: $3"
echo "All arguments: $@"
echo "All as string: $*"
echo "Number of arguments: $#"

# Running the script
psh$ ./script.sh apple banana cherry
Script name: ./script.sh
First argument: apple
Second argument: banana
Third argument: cherry
All arguments: apple banana cherry
All as string: apple banana cherry
Number of arguments: 3

# Difference between $@ and $*
psh$ show_args() {
>     echo "Using \$@:"
>     for arg in "$@"; do
>         echo "  [$arg]"
>     done
>     echo "Using \$*:"
>     for arg in "$*"; do
>         echo "  [$arg]"
>     done
> }

psh$ show_args "hello world" "foo bar"
Using $@:
  [hello world]
  [foo bar]
Using $*:
  [hello world foo bar]
```

### Process Variables

```bash
# Current process ID
psh$ echo $$
12345

# Last background process ID
psh$ sleep 100 &
[1] 12346
psh$ echo $!
12346

# Exit status of last command
psh$ true
psh$ echo $?
0

psh$ false
psh$ echo $?
1

psh$ ls /nonexistent
ls: cannot access '/nonexistent': No such file or directory
psh$ echo $?
2
```

### Other Special Variables

```bash
# Current options (when implemented)
psh$ echo $-
# (would show current shell options)

# Shell version variables
psh$ echo $BASH_VERSION  # For compatibility
psh$ echo $PSH_VERSION   # PSH-specific

# IFS (Internal Field Separator)
psh$ echo "$IFS" | od -c
0000000      \t  \n
0000003

# Change IFS for parsing
psh$ IFS=:
psh$ read -r user pass uid gid rest < /etc/passwd
psh$ echo "User: $user, UID: $uid"
User: root, UID: 0
psh$ IFS=$' \t\n'  # Reset to default
```

## 5.4 Variable Expansion

### Basic Expansion

```bash
# Simple expansion
psh$ var="hello"
psh$ echo $var
hello

# Braces for clarity
psh$ echo ${var}
hello

# Braces required for disambiguation
psh$ prefix="pre"
psh$ echo "$prefix_fix"      # Looking for prefix_fix variable

psh$ echo "${prefix}_fix"    # Correct
pre_fix

# Concatenation
psh$ file="document"
psh$ echo "${file}.txt"
document.txt

# In strings
psh$ name="Alice"
psh$ echo "Hello, $name! Welcome to ${name}'s profile."
Hello, Alice! Welcome to Alice's profile.
```

### Default Values

```bash
# Use default if variable is unset or empty
psh$ echo ${username:-guest}
guest

psh$ username="alice"
psh$ echo ${username:-guest}
alice

# Set and use default if unset
psh$ echo ${config:=/etc/myapp.conf}
/etc/myapp.conf
psh$ echo $config
/etc/myapp.conf

# Display error if unset
psh$ echo ${required:?Error: required variable not set}
psh: required: Error: required variable not set

# Use alternate value if set
psh$ var="set"
psh$ echo ${var:+exists}
exists
psh$ echo ${unset:+exists}

```

### Indirect Expansion

```bash
# Variable containing another variable's name
psh$ color="red"
psh$ red="FF0000"
psh$ varname="red"
psh$ echo ${!varname}
FF0000

# Useful for dynamic variable access
psh$ for i in 1 2 3; do
>     varname="item_$i"
>     declare $varname="Value $i"
> done

psh$ echo $item_1
Value 1
psh$ echo $item_2
Value 2
```

## 5.5 Advanced Parameter Expansion

PSH supports all bash parameter expansion features:

### String Length

```bash
# Length of string
psh$ str="Hello, World!"
psh$ echo ${#str}
13

# Length of array elements
psh$ set -- one two three
psh$ echo ${#@}
3
psh$ echo ${#*}
3

# Length of specific positional parameter
psh$ echo ${#1}
3
psh$ echo ${#2}
3
```

### Pattern Removal

```bash
# Remove from beginning (# for shortest, ## for longest)
psh$ file="/home/alice/documents/report.txt"

psh$ echo ${file#*/}      # Remove shortest match from start
home/alice/documents/report.txt

psh$ echo ${file##*/}     # Remove longest match from start
report.txt

# Remove from end (% for shortest, %% for longest)
psh$ echo ${file%/*}      # Remove shortest match from end
/home/alice/documents

psh$ echo ${file%%/*}     # Remove longest match from end
(empty - removed everything)

# Practical examples
psh$ filename="archive.tar.gz"
psh$ echo ${filename%.gz}      # Remove .gz
archive.tar
psh$ echo ${filename%%.*}      # Remove all extensions
archive

# Remove path to get basename
psh$ path="/usr/local/bin/script.sh"
psh$ echo ${path##*/}
script.sh

# Remove filename to get directory
psh$ echo ${path%/*}
/usr/local/bin
```

### Pattern Substitution

```bash
# Replace first occurrence
psh$ text="hello hello world"
psh$ echo ${text/hello/hi}
hi hello world

# Replace all occurrences
psh$ echo ${text//hello/hi}
hi hi world

# Replace at beginning
psh$ echo ${text/#hello/hi}
hi hello world

# Replace at end
psh$ file="document.txt"
psh$ echo ${file/%txt/pdf}
document.pdf

# Delete pattern (replace with nothing)
psh$ spaces="hello   world   test"
psh$ echo ${spaces// /}
helloworldtest

# Case conversion in replacement
psh$ name="alice"
psh$ echo ${name/a/A}      # First 'a' to 'A'
Alice
psh$ echo ${name//a/A}     # All 'a' to 'A'
Alice
```

### Substring Extraction

```bash
# Extract substring ${var:offset:length}
psh$ str="Hello, World!"
psh$ echo ${str:0:5}
Hello
psh$ echo ${str:7:5}
World
psh$ echo ${str:7}        # From offset to end
World!

# Negative offsets (from end)
psh$ echo ${str: -6}      # Last 6 characters (note space)
World!
psh$ echo ${str: -6:5}    # 5 chars starting 6 from end
World

# With positional parameters
psh$ set -- apple banana cherry date elderberry
psh$ echo ${@:2:3}        # Three arguments starting from $2
banana cherry date
psh$ echo ${@:4}          # From $4 to end
date elderberry
```

### Case Modification

```bash
# Convert to uppercase
psh$ name="alice smith"
psh$ echo ${name^}        # First character
Alice smith
psh$ echo ${name^^}       # All characters
ALICE SMITH

# Convert to lowercase
psh$ NAME="ALICE SMITH"
psh$ echo ${NAME,}        # First character
aLICE SMITH
psh$ echo ${NAME,,}       # All characters
alice smith

# Pattern-based case conversion
psh$ text="hello world"
psh$ echo ${text^^[aeiou]}    # Uppercase vowels
hEllO wOrld

psh$ TEXT="HELLO WORLD"
psh$ echo ${TEXT,,[AEIOU]}    # Lowercase vowels
HeLLo WoRLD

# Capitalize each word
psh$ words="the quick brown fox"
psh$ echo ${words^}           # Just first char
The quick brown fox

# To capitalize each word, use a loop
psh$ result=""
psh$ for word in $words; do
>     result="$result${word^} "
> done
psh$ echo "$result"
The Quick Brown Fox 
```

### Variable Name Matching

```bash
# List all variables starting with prefix
psh$ USER_NAME="Alice"
psh$ USER_AGE="25"
psh$ USER_CITY="NYC"
psh$ ADMIN_NAME="Bob"

psh$ echo ${!USER*}
USER_AGE USER_CITY USER_NAME

psh$ echo ${!USER@}
USER_AGE USER_CITY USER_NAME

# Useful for dynamic variable processing
psh$ for var in ${!USER*}; do
>     echo "$var = ${!var}"
> done
USER_AGE = 25
USER_CITY = NYC
USER_NAME = Alice
```

## 5.6 Local Variables in Functions

Local variables provide scope isolation within functions:

```bash
# Global vs local variables
psh$ counter=100

psh$ increment() {
>     local counter=0
>     counter=$((counter + 1))
>     echo "Local counter: $counter"
> }

psh$ increment
Local counter: 1
psh$ echo "Global counter: $counter"
Global counter: 100

# Local with initial value
psh$ process_file() {
>     local file="$1"
>     local -r max_size=1048576  # readonly local
>     local count=0
>     
>     echo "Processing $file (max size: $max_size)"
>     # ... processing logic ...
> }

# Locals are visible to nested functions
psh$ outer() {
>     local outer_var="outer"
>     
>     inner() {
>         echo "Inner sees: $outer_var"
>         local inner_var="inner"
>     }
>     
>     inner
>     echo "Outer cannot see: $inner_var"
> }

psh$ outer
Inner sees: outer
Outer cannot see: 

# Best practice: Always use local in functions
psh$ safe_function() {
>     local temp_file="/tmp/$$_temp"
>     local exit_code=0
>     local line
>     
>     while read -r line; do
>         echo "Processing: $line"
>     done < input.txt
>     
>     return $exit_code
> }
```

## Practical Examples

### Configuration File Parser

```bash
#!/usr/bin/env psh
# Parse configuration file with variable expansion

# Default configuration
DEFAULT_HOST="localhost"
DEFAULT_PORT="8080"
DEFAULT_DEBUG="false"

# Parse config file
parse_config() {
    local config_file="${1:-config.ini}"
    local section=""
    
    if [ ! -f "$config_file" ]; then
        echo "Warning: Config file not found, using defaults"
        return 1
    fi
    
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^[[:space:]]*# ]] && continue
        [[ -z $key ]] && continue
        
        # Handle sections
        if [[ $key =~ ^\[.*\]$ ]]; then
            section="${key//[\[\]]/}"
            continue
        fi
        
        # Trim whitespace
        key="${key%%[[:space:]]*}"
        value="${value##[[:space:]]*}"
        
        # Set variables with section prefix
        if [ -n "$section" ]; then
            declare -g "${section}_${key}=$value"
        else
            declare -g "$key=$value"
        fi
    done < "$config_file"
}

# Example config.ini:
# [server]
# host=192.168.1.100
# port=9090
# 
# [app]
# debug=true
# name=MyApp

# Usage
parse_config "config.ini"

# Access configuration
HOST="${server_host:-$DEFAULT_HOST}"
PORT="${server_port:-$DEFAULT_PORT}"
DEBUG="${app_debug:-$DEFAULT_DEBUG}"

echo "Starting server on $HOST:$PORT (debug=$DEBUG)"
```

### Dynamic Variable Generator

```bash
#!/usr/bin/env psh
# Generate variables dynamically

# Create numbered variables
create_items() {
    local count="$1"
    local prefix="${2:-item}"
    local i
    
    for ((i=1; i<=count; i++)); do
        declare -g "${prefix}_${i}=Value $i"
        declare -g "${prefix}_${i}_status=pending"
    done
}

# Process all variables with prefix
process_items() {
    local prefix="$1"
    local var value
    
    echo "Processing all ${prefix}_ variables:"
    for var in ${!prefix_*}; do
        value="${!var}"
        echo "  $var = $value"
        
        # Update status
        if [[ $var =~ _status$ ]]; then
            declare -g "$var=processed"
        fi
    done
}

# Example usage
create_items 3 "task"

echo "Initial state:"
for var in ${!task_*}; do
    echo "  $var = ${!var}"
done

echo
process_items "task"

echo
echo "Final state:"
for var in ${!task_*}; do
    echo "  $var = ${!var}"
done
```

### String Manipulation Utilities

```bash
#!/usr/bin/env psh
# Collection of string manipulation functions

# Trim whitespace
trim() {
    local var="$1"
    # Remove leading whitespace
    var="${var#"${var%%[![:space:]]*}"}"
    # Remove trailing whitespace
    var="${var%"${var##*[![:space:]]}"}"
    echo "$var"
}

# Join array elements
join() {
    local delimiter="$1"
    shift
    local first="$1"
    shift
    echo -n "$first"
    for item in "$@"; do
        echo -n "${delimiter}${item}"
    done
    echo
}

# Split string into array
split() {
    local string="$1"
    local delimiter="$2"
    local saved_ifs="$IFS"
    IFS="$delimiter"
    read -ra SPLIT_RESULT <<< "$string"
    IFS="$saved_ifs"
}

# URL encode
urlencode() {
    local string="$1"
    local length="${#string}"
    local encoded=""
    local i c
    
    for ((i=0; i<length; i++)); do
        c="${string:i:1}"
        case "$c" in
            [a-zA-Z0-9.~_-]) encoded+="$c" ;;
            *) encoded+=$(printf '%%%02X' "'$c") ;;
        esac
    done
    echo "$encoded"
}

# Examples
psh$ text="  hello world  "
psh$ trimmed=$(trim "$text")
psh$ echo "[$trimmed]"
[hello world]

psh$ join ":" apple banana cherry
apple:banana:cherry

psh$ split "one,two,three" ","
psh$ echo "${SPLIT_RESULT[@]}"
one two three

psh$ url=$(urlencode "hello world?foo=bar")
psh$ echo "$url"
hello%20world%3Ffoo%3Dbar
```

## Summary

Variables and parameters in PSH provide powerful ways to store and manipulate data:

1. **Basic variables** store values with simple assignment
2. **Environment variables** pass data to child processes
3. **Special variables** provide system and process information
4. **Parameter expansion** enables default values and string manipulation
5. **Advanced expansion** supports pattern matching, substitution, and case conversion
6. **Local variables** provide function scope isolation

Understanding these features is essential for effective shell scripting. Variables are the foundation for storing state, passing data between commands, and building complex scripts.

In the next chapter, we'll explore the various expansion mechanisms that make shell scripting so powerful.

---

[← Previous: Chapter 4 - Built-in Commands](04_builtin_commands.md) | [Next: Chapter 6 - Expansions →](06_expansions.md)