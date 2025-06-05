# Appendix A: Quick Reference Card

This quick reference provides a concise overview of PSH syntax, commands, and features. Keep it handy for quick lookups while working in PSH.

## Command Line Options

```bash
psh [options] [script] [arguments]

Options:
  -c COMMAND         Execute command string
  -i                 Force interactive mode
  --norc             Skip ~/.pshrc file
  --rcfile FILE      Use alternate RC file
  --debug-ast        Show parsed AST
  --debug-tokens     Show tokenization
  --debug-scopes     Show variable scopes
  --version          Show version
  --help             Show help
```

## Basic Syntax

### Command Execution
```bash
command [args]                # Run command
command1; command2           # Sequential execution
command1 && command2         # Run command2 if command1 succeeds
command1 || command2         # Run command2 if command1 fails
command &                    # Run in background
command1 | command2          # Pipeline
```

### Variables
```bash
VAR=value                    # Set variable
export VAR=value            # Export to environment
unset VAR                   # Remove variable
readonly VAR=value          # Read-only variable
local VAR=value             # Function-local variable

$VAR or ${VAR}              # Variable expansion
${VAR:-default}             # Use default if unset
${VAR:=default}             # Set and use default if unset
${VAR:?error}               # Error if unset
${VAR:+alternate}           # Use alternate if set
```

### Special Variables
```bash
$0          # Script/shell name
$1..$9      # Positional parameters
${10}       # Positional parameter 10+
$#          # Number of parameters
$@          # All parameters (array)
$*          # All parameters (string)
$$          # Process ID
$!          # Last background PID
$?          # Last exit status
$-          # Shell options
```

### Parameter Expansion
```bash
${#VAR}                     # Length of variable
${VAR:offset}               # Substring from offset
${VAR:offset:length}        # Substring with length
${VAR#pattern}              # Remove shortest prefix
${VAR##pattern}             # Remove longest prefix
${VAR%pattern}              # Remove shortest suffix
${VAR%%pattern}             # Remove longest suffix
${VAR/pattern/string}       # Replace first match
${VAR//pattern/string}      # Replace all matches
${VAR^}                     # First char uppercase
${VAR^^}                    # All uppercase
${VAR,}                     # First char lowercase
${VAR,,}                    # All lowercase
${!prefix*}                 # Variable names with prefix
```

## Expansions

### Command Substitution
```bash
$(command)                  # Preferred form
`command`                   # Legacy form
```

### Arithmetic Expansion
```bash
$((expression))             # Arithmetic result
((expression))              # Arithmetic command
```

### Brace Expansion
```bash
{a,b,c}                     # Expands to: a b c
{1..10}                     # Expands to: 1 2 3 4 5 6 7 8 9 10
{a..z}                      # Expands to: a b c ... z
file{1,2,3}.txt             # Expands to: file1.txt file2.txt file3.txt
```

### Tilde Expansion
```bash
~                           # Home directory
~/file                      # File in home directory
~user                       # User's home directory
```

### Process Substitution
```bash
<(command)                  # Treat output as file
>(command)                  # Treat input as file
```

## Quoting

```bash
'string'                    # Single quotes - no expansion
"string"                    # Double quotes - allows $, `, \
$'string'                   # ANSI-C quoting (limited support)
\c                          # Escape character
```

## I/O Redirection

```bash
< file                      # Input from file
> file                      # Output to file (overwrite)
>> file                     # Output to file (append)
2> file                     # Stderr to file
2>&1                        # Stderr to stdout
&> file                     # All output to file
<< EOF                      # Here document
<<- EOF                     # Here document (strip tabs)
<<< "string"                # Here string
```

## Control Structures

### Conditionals
```bash
if condition; then
    commands
elif condition; then
    commands
else
    commands
fi

case expression in
    pattern1) commands ;;
    pattern2|pattern3) commands ;;
    *) default commands ;;
esac
```

### Loops
```bash
while condition; do
    commands
done

until condition; do
    commands
done

for var in list; do
    commands
done

for ((init; condition; update)); do
    commands
done
```

### Loop Control
```bash
break [n]                   # Exit n levels of loops
continue [n]                # Skip to next iteration
```

## Functions

```bash
# POSIX syntax
name() {
    commands
    return [n]
}

# Bash syntax
function name {
    commands
    return [n]
}

# Call function
name [arguments]

# Function builtins
local var=value             # Local variable
return [n]                  # Return with status
```

## Test Operators

### File Tests
```bash
-e file     # Exists
-f file     # Regular file
-d file     # Directory
-L file     # Symbolic link
-r file     # Readable
-w file     # Writable
-x file     # Executable
-s file     # Size > 0
-S file     # Socket
-p file     # Named pipe
-b file     # Block device
-c file     # Character device
-g file     # Setgid
-u file     # Setuid
-k file     # Sticky bit
-O file     # Owned by user
-G file     # Owned by group
file1 -nt file2  # file1 newer than file2
file1 -ot file2  # file1 older than file2
file1 -ef file2  # Same file
```

### String Tests
```bash
-z string   # Empty string
-n string   # Non-empty string
s1 = s2     # Strings equal
s1 != s2    # Strings not equal
s1 < s2     # s1 sorts before s2 (in [[)
s1 > s2     # s1 sorts after s2 (in [[)
```

### Numeric Tests
```bash
n1 -eq n2   # Equal
n1 -ne n2   # Not equal
n1 -lt n2   # Less than
n1 -le n2   # Less than or equal
n1 -gt n2   # Greater than
n1 -ge n2   # Greater than or equal
```

### Test Commands
```bash
[ expression ]              # Test command
[[ expression ]]            # Enhanced test
[[ string =~ regex ]]       # Regex match
```

## Built-in Commands

### Core
```bash
:           # Null command
.           # Source script (same as source)
exit [n]    # Exit shell
return [n]  # Return from function
true        # Return success
false       # Return failure
```

### Variables & Environment
```bash
export      # Export variables
unset       # Remove variables
readonly    # Make variables read-only
local       # Create local variables
env         # Show environment
set         # Set options/positional parameters
declare     # Declare variables (limited)
```

### Directory Navigation
```bash
cd [dir]    # Change directory
pwd         # Print working directory
pushd       # Push directory (not implemented)
popd        # Pop directory (not implemented)
dirs        # Show directory stack (not implemented)
```

### I/O
```bash
echo        # Print arguments
printf      # Formatted output (limited)
read        # Read input
```

### Job Control
```bash
jobs        # List jobs
fg [job]    # Foreground job
bg [job]    # Background job
wait [pid]  # Wait for process
kill        # Send signal
```

### Other
```bash
alias       # Define aliases
unalias     # Remove aliases
type        # Show command type
command     # Run command
builtin     # Run builtin
history     # Show command history
source      # Execute script in current shell
test        # Evaluate expression
[           # Evaluate expression
```

## Job Control

```bash
command &                   # Run in background
jobs                        # List jobs
fg [%job]                   # Bring to foreground
bg [%job]                   # Resume in background
kill %job                   # Kill job
Ctrl-Z                      # Suspend current job
Ctrl-C                      # Interrupt current job

Job specifications:
%n          # Job number n
%+, %%      # Current job
%-          # Previous job
%string     # Job beginning with string
```

## Prompt Customization

```bash
PS1         # Primary prompt
PS2         # Continuation prompt

Prompt escapes:
\u          # Username
\h          # Hostname (short)
\H          # Hostname (full)
\w          # Working directory
\W          # Directory basename
\t          # Time 24h HH:MM:SS
\T          # Time 12h HH:MM:SS
\@          # Time 12h am/pm
\A          # Time 24h HH:MM
\d          # Date
\n          # Newline
\$          # $ or # (root)
\!          # History number
\#          # Command number
\[...\]     # Non-printing sequence
```

## Arithmetic Operators

```bash
# Basic operators
+  -  *  /  %              # Add, subtract, multiply, divide, modulo
**                         # Exponentiation

# Assignment operators
=  +=  -=  *=  /=  %=      # Assign, add-assign, etc.

# Increment/decrement
++ --                      # Pre/post increment/decrement

# Comparison operators
<  <=  >  >=  ==  !=       # Comparisons

# Logical operators
&&  ||  !                  # AND, OR, NOT

# Bitwise operators
&  |  ^  ~  <<  >>         # AND, OR, XOR, NOT, left shift, right shift

# Ternary operator
condition ? true_val : false_val
```

## Pattern Matching

```bash
# Glob patterns
*           # Match any string
?           # Match any character
[abc]       # Match a, b, or c
[!abc]      # Match any except a, b, c
[a-z]       # Match range
[[:class:]] # Match character class

# Character classes
[:alnum:]   # Alphanumeric
[:alpha:]   # Alphabetic
[:digit:]   # Digits
[:lower:]   # Lowercase
[:upper:]   # Uppercase
[:space:]   # Whitespace
```

## Shell Options

```bash
set -o option              # Enable option
set +o option              # Disable option
set -o                     # Show all options

PSH-specific options:
debug-ast                  # Show parsed AST
debug-tokens               # Show tokenization
emacs                      # Emacs editing mode
vi                         # Vi editing mode
```

## Common Key Bindings

### Emacs Mode (default)
```bash
Ctrl-A      # Beginning of line
Ctrl-E      # End of line
Ctrl-F      # Forward char
Ctrl-B      # Backward char
Alt-F       # Forward word
Alt-B       # Backward word
Ctrl-D      # Delete char
Ctrl-K      # Kill to end
Ctrl-U      # Kill line
Ctrl-W      # Kill word backward
Ctrl-Y      # Yank
Ctrl-L      # Clear screen
Ctrl-R      # Reverse search
Ctrl-P      # Previous history
Ctrl-N      # Next history
```

### Vi Mode
```bash
ESC         # Normal mode
i           # Insert mode
h j k l     # Movement
w b         # Word movement
0 $         # Line start/end
x           # Delete char
dd          # Delete line
yy          # Yank line
p           # Paste
/           # Search forward
?           # Search backward
```

## Exit Status

```bash
0           # Success
1-125       # General errors
126         # Command not executable
127         # Command not found
128+n       # Terminated by signal n
130         # Terminated by Ctrl-C (SIGINT)
142         # Timeout (read -t)
```

---

[← Previous: Chapter 18 - Troubleshooting](18_troubleshooting.md) | [Next: Appendix B - Example Scripts →](appendix_b_example_scripts.md)