# Chapter 17: Differences from Bash

While PSH implements many shell features compatible with Bash, there are important differences due to its educational focus and Python implementation. Understanding these differences helps you write portable scripts and use PSH effectively.

## 17.1 Supported Features Overview

PSH v0.187.1 has near-complete compatibility with Bash for core shell programming. Most common Bash scripts run without modification. This section highlights what is fully supported before discussing the remaining gaps.

### Shell Options

PSH supports an extensive set of shell options matching Bash behavior:

```bash
# Core error-handling options
set -e              # Exit on error (errexit)
set -u              # Error on undefined variables (nounset)
set -x              # Print commands before execution (xtrace)
set -o pipefail     # Pipeline fails if any command fails

# Additional POSIX/Bash options
set -o allexport    # Export all variables on assignment
set -o braceexpand  # Enable brace expansion (on by default)
set -o noclobber    # Prevent overwriting files with >
set -o noglob       # Disable filename globbing
set -o noexec       # Read commands but do not execute
set -o notify       # Report background job status immediately
set -o verbose      # Print input lines as they are read
set -o ignoreeof    # Prevent Ctrl-D from exiting the shell
set -o monitor      # Enable job control
set -o posix        # Enable POSIX compliance mode

# Short-form combinations work
set -eu             # Enable errexit and nounset
set -eux            # Enable errexit, nounset, and xtrace

# Note: "set -euo pipefail" does NOT work as a single argument.
# The combined form treats 'o' as a short flag. Use instead:
set -eu; set -o pipefail
# Or:
set -e -u -o pipefail

# View all options
set -o              # Show all option settings
set +o              # Show settings as re-enterable commands
```

### Glob Options (shopt)

PSH provides several glob-related options via `shopt`:

```bash
# Available shopt options
shopt -s dotglob     # Include hidden files in glob expansion
shopt -s nullglob    # Non-matching globs expand to nothing
shopt -s globstar    # Enable ** recursive globbing
shopt -s nocaseglob  # Case-insensitive globbing

# The extglob option can be set but extended glob patterns
# are not yet parsed (see 17.2 below)
shopt -s extglob     # Can be set, but patterns like +(x) don't parse
```

### Arrays and Associative Arrays

```bash
# Indexed arrays
declare -a array=(one two three)
echo ${array[0]}         # First element
echo ${array[@]}         # All elements
echo ${#array[@]}        # Number of elements
fruits=(apple banana cherry)
fruits[3]="orange"       # Add element
fruits+=(grape)          # Append to array
echo ${fruits[@]:1:2}    # Slice from index 1, length 2
echo ${!fruits[@]}       # All indices

# Array element operations
files=(doc.txt img.txt data.txt)
echo ${files[@]/.txt/.bak}  # Replace in all elements
echo ${files[@]^^}          # Uppercase all elements

# Sparse arrays
unset fruits[2]
echo ${!fruits[@]}       # Shows remaining indices

# Associative arrays
declare -A colors=([red]="#FF0000" [green]="#00FF00")
colors[blue]="#0000FF"
echo ${colors[red]}      # Access by key
echo ${!colors[@]}       # All keys
echo ${colors[@]}        # All values
```

### Trap Command

```bash
# Signal handling
trap 'echo "Cleaning up..."' EXIT
trap 'echo "Interrupted"' INT TERM

# List current traps
trap -p
trap -p INT            # Show specific trap

# Reset traps to default
trap - EXIT INT
```

### Select Statement

```bash
select option in "Option 1" "Option 2" "Quit"; do
    case $option in
        "Option 1") echo "You chose 1" ;;
        "Option 2") echo "You chose 2" ;;
        "Quit") break ;;
        *) echo "Invalid selection" ;;
    esac
done
```

### History Expansion

```bash
# In interactive mode:
!!        # Previous command
!n        # Command n from history
!-n       # n commands ago
!string   # Most recent command starting with string
!?string? # Most recent command containing string
```

### Job Control

PSH provides full job control in interactive mode including `disown`:

```bash
# All standard job control
jobs           # List jobs
fg %1          # Bring job to foreground
bg %1          # Resume job in background
wait           # Wait for background jobs
kill %1        # Send signal to job
disown %1      # Remove job from job table
disown -h %1   # Mark job to not receive SIGHUP
disown -a      # Remove all jobs
```

### Process Substitution

```bash
# Input process substitution
diff <(sort file1.txt) <(sort file2.txt)

# Output process substitution
echo "data" | tee >(grep pattern > matches.txt)
```

## 17.2 Unimplemented Features

The following Bash features are not available in PSH v0.187.1.

### Coprocesses

```bash
# NOT implemented
coproc { command; }           # Parse error
coproc NAME { command; }      # Parse error
```

### Extended Glob Patterns

```bash
# The shopt -s extglob option can be SET, but the extended
# glob patterns themselves are not parsed by PSH:
shopt -s extglob     # Succeeds (no error)
ls !(*.txt)          # Parse error - not supported
ls +(pattern)        # Parse error - not supported
ls ?(pattern)        # Parse error - not supported
ls *(pattern)        # Parse error - not supported
ls @(pattern)        # Parse error - not supported
```

### Programmable Completion

```bash
# The complete/compgen builtins do not exist
complete -F _my_func mycommand  # Command not found
compgen -W "words" -- prefix    # Command not found

# Basic tab completion for files, directories, and commands
# IS available in interactive mode
```

### BASH_REMATCH Capture Groups

```bash
# The =~ regex operator works for matching:
[[ "hello" =~ hel ]] && echo "matched"   # Works

# But BASH_REMATCH is NOT populated with capture groups:
[[ "hello123" =~ ([a-z]+)([0-9]+) ]]
echo ${BASH_REMATCH[1]}   # Empty (not captured)
```

### Missing Builtins

```bash
# These Bash builtins are not available:
let "x = 5 + 3"             # Use (( )) or $(( )) instead
mapfile lines < file.txt     # Use while read loop instead
readarray lines < file.txt   # Same as mapfile

# hash is not a builtin (falls through to external command)
type hash   # Shows external /usr/bin/hash
```

### Read Builtin Limitations

```bash
# The read builtin supports:
read var                # Basic reading
read -r var             # Raw mode (no backslash processing)
read -d ':' var         # Custom delimiter
read -p "prompt: " var  # Prompt (interactive only)

# These read options are not supported:
read -u 3 var           # Read from specific file descriptor
read -n 4 var           # Read exact number of characters
read -t 5 var           # Timeout
read -s var             # Silent mode (passwords)
```

### Other Missing Features

```bash
# wait -n (wait for any single job)
wait -n                 # Not supported

# time keyword (external /usr/bin/time works)
time echo hello         # Uses external time, not shell keyword

# BASH_SOURCE, BASH_LINENO, FUNCNAME arrays
echo ${BASH_SOURCE[0]}  # Not available
echo ${FUNCNAME[0]}     # Not available

# Variable name prefix matching is incomplete
echo ${!PATH*}          # Lists all variables, not just PATH-prefixed
```

## 17.3 Behavioral Differences

Some features work differently in PSH compared to Bash.

### Combined Short Option Parsing

```bash
# In Bash: set -euo pipefail works
# In PSH: -euo is parsed as three short flags (-e, -u, -o)
# and 'o' is not a valid short flag

# This fails in PSH:
set -euo pipefail       # Error: invalid option -o

# These work in PSH:
set -eu; set -o pipefail    # Separate statements
set -e -u -o pipefail       # Separate arguments
set -eu -o pipefail         # Mixed form
```

### Quote Handling

```bash
# Single quote handling follows POSIX rules:
echo 'It'"'"'s a test'  # Concatenate quoted strings
echo "It's a test"      # Use double quotes
echo 'It'\''s a test'   # End-quote, escaped quote, start-quote
```

### Variable Assignment

```bash
# PSH follows Bash rules for variable assignment:
VAR=value         # Correct - no spaces around =
VAR= value        # Sets VAR to empty, then runs "value" as command
VAR =value        # Tries to run "VAR" as command with arg "=value"
```

### Here Document Behavior

```bash
# Tab suppression with <<- works correctly:
cat <<-EOF
	This has a tab
	This too
EOF
# Output has leading tabs removed

# Quoted vs unquoted delimiter:
cat <<'EOF'      # No expansion
$HOME
EOF

cat <<EOF        # With expansion
$HOME
EOF
```

### Debug Option Runtime Behavior

```bash
# Command-line debug flags produce visible output:
psh --debug-ast -c 'echo hello'     # Shows AST tree
psh --debug-tokens -c 'echo hello'  # Shows token list

# Runtime set -o debug-* options can be set but
# some may not produce the same output format:
set -o debug-expansion   # Works - shows expansion trace
set -o debug-exec        # Works - shows execution trace
set -o debug-ast         # Can be set but may not produce output
set -o debug-tokens      # Can be set but may not produce output

# Use command-line flags for reliable debug output
```

### Recursion Depth

```bash
# PSH has limited recursion depth due to Python's call stack
# Deep recursion that works in Bash may fail in PSH:

factorial() {
    local n=$1
    if [ $n -le 1 ]; then
        echo 1
    else
        echo $((n * $(factorial $((n - 1)))))
    fi
}
factorial 1000  # May fail with stack overflow

# Workaround: Use iteration
factorial_iter() {
    local n=$1 result=1
    while [ $n -gt 1 ]; do
        result=$((result * n))
        n=$((n - 1))
    done
    echo $result
}
```

## 17.4 PSH-Specific Features

PSH includes features not found in Bash, designed for education and development.

### Debug Flags

```bash
# Command-line debug flags
psh --debug-ast script.sh           # Show parsed AST before execution
psh --debug-ast=tree script.sh      # Tree format (default)
psh --debug-ast=compact script.sh   # Compact format
psh --debug-ast=sexp script.sh      # S-expression format
psh --debug-ast=dot script.sh       # Graphviz DOT format
psh --debug-tokens script.sh        # Show tokenization
psh --debug-scopes script.sh        # Show variable scope operations
psh --debug-expansion script.sh     # Show expansion process
psh --debug-expansion-detail script.sh  # Detailed expansion steps
psh --debug-exec script.sh          # Show execution flow
psh --debug-exec-fork script.sh     # Show fork/exec details

# Runtime debug options (via set -o)
set -o debug-expansion    # Enable expansion tracing
set -o debug-exec         # Enable execution tracing
set -o debug-parser       # Enable parser tracing

# Custom PS4 for xtrace
PS4='[trace] '
set -x
echo hello               # Shows: [trace] echo hello
```

### Script Analysis Tools

```bash
# Validate script without executing
psh --validate script.sh    # Check for parse errors

# Format script
psh --format script.sh      # Pretty-print formatted script

# Lint analysis
psh --lint script.sh        # Check for common issues

# Security analysis
psh --security script.sh    # Check for security concerns

# Code metrics
psh --metrics script.sh     # Show complexity and statistics
```

### Parser Selection

```bash
# PSH includes two parsers for educational comparison:
psh --parser rd script.sh         # Recursive descent (default)
psh --parser combinator script.sh # Combinator parser (experimental)

# Switch at runtime (interactive mode):
parser-select combinator
parser-select rd
```

### Shell Version Detection

```bash
# PSH sets PSH_VERSION (not BASH_VERSION):
echo $PSH_VERSION    # Shows: 0.187.1

# Detect PSH:
if [ -n "$PSH_VERSION" ]; then
    echo "Running in PSH $PSH_VERSION"
fi
```

## 17.5 Feature Compatibility Reference

| Feature | Bash | PSH | Notes |
|---------|------|-----|-------|
| **Basic Features** |
| Command execution | Yes | Yes | Full support |
| Pipelines | Yes | Yes | Full support |
| I/O redirection | Yes | Yes | All forms supported |
| Background jobs | Yes | Yes | Interactive only |
| Subshells | Yes | Yes | Full support |
| **Variables** |
| Simple variables | Yes | Yes | Full support |
| Arrays | Yes | Yes | Full support |
| Associative arrays | Yes | Yes | Full support |
| Local variables | Yes | Yes | Full support |
| Variable attributes | Yes | Yes | declare -i, -r, -x, etc. |
| **Expansions** |
| Parameter expansion | Yes | Yes | All features |
| Command substitution | Yes | Yes | Both $() and backticks |
| Arithmetic expansion | Yes | Yes | Full support |
| Brace expansion | Yes | Yes | Full support |
| Process substitution | Yes | Yes | Full support |
| Tilde expansion | Yes | Yes | Full support |
| Case modification | Yes | Yes | ${var^^}, ${var,,}, etc. |
| **Control Structures** |
| if/then/else/fi | Yes | Yes | Full support |
| while/until/do/done | Yes | Yes | Full support |
| for/do/done | Yes | Yes | Full support |
| C-style for loops | Yes | Yes | Full support |
| case/esac | Yes | Yes | Full support |
| select | Yes | Yes | Full support |
| Arithmetic commands (( )) | Yes | Yes | Full support |
| Control structures in pipelines | Yes | Yes | Full support |
| **Functions** |
| Function definition | Yes | Yes | Both syntaxes |
| Local variables | Yes | Yes | Full support |
| Return values | Yes | Yes | Full support |
| **Job Control** |
| jobs command | Yes | Yes | Interactive only |
| fg/bg commands | Yes | Yes | Interactive only |
| Job specifications | Yes | Yes | %1, %+, %-, %string |
| wait builtin | Yes | Yes | Full support |
| disown builtin | Yes | Yes | Full support |
| **Shell Options** |
| set -e (errexit) | Yes | Yes | Full support |
| set -u (nounset) | Yes | Yes | Full support |
| set -x (xtrace) | Yes | Yes | Full support |
| set -o pipefail | Yes | Yes | Full support |
| set -o noclobber | Yes | Yes | Full support |
| set -o allexport | Yes | Yes | Full support |
| set -o noglob | Yes | Yes | Full support |
| set -o verbose | Yes | Yes | Full support |
| **Signal Handling** |
| trap command | Yes | Yes | Full support |
| Signal handling | Yes | Yes | All standard signals |
| **Advanced Features** |
| History expansion | Yes | Yes | Full support |
| Here documents | Yes | Yes | Full support |
| Here strings | Yes | Yes | Full support |
| Enhanced test [[ ]] | Yes | Yes | Full support |
| Regex matching =~ | Yes | Partial | Matching works, BASH_REMATCH not populated |
| eval builtin | Yes | Yes | Full support |
| getopts builtin | Yes | Yes | Full support |
| printf builtin | Yes | Yes | Full support |
| pushd/popd/dirs | Yes | Yes | Full support |
| shopt options | Yes | Partial | dotglob, nullglob, globstar, nocaseglob |
| Coprocesses | Yes | No | Not implemented |
| Extended glob patterns | Yes | No | shopt can be set but patterns don't parse |
| Programmable completion | Yes | No | Basic tab completion only |
| let builtin | Yes | No | Use (( )) instead |
| mapfile/readarray | Yes | No | Use while read loop instead |
| BASH_REMATCH | Yes | No | =~ matches but groups not captured |
| wait -n | Yes | No | Not implemented |
| read -n / -t / -s / -u | Yes | No | Only -r, -d, -p supported |
| **PSH-Specific** |
| --debug-ast | No | Yes | Multiple output formats |
| --debug-tokens | No | Yes | PSH only |
| --debug-scopes | No | Yes | PSH only |
| --debug-expansion | No | Yes | PSH only |
| --validate | No | Yes | Syntax validation |
| --format | No | Yes | Script formatting |
| --lint | No | Yes | Lint analysis |
| --security | No | Yes | Security analysis |
| --metrics | No | Yes | Code metrics |

## 17.6 Writing Portable Scripts

When writing scripts that need to work in both PSH and Bash, follow these guidelines.

### Stick to Common Features

```bash
#!/bin/sh
# For maximum portability, use POSIX features:

# POSIX test command
if [ -f "$file" ]; then
    echo "File exists"
fi

# Standard arithmetic
result=$((a + b))

# For PSH+Bash portability, these features are safe:
# - [[ ]] enhanced test (but avoid =~ with capture groups)
# - (( )) arithmetic commands
# - Arrays and associative arrays
# - Process substitution <() and >()
# - Parameter expansion (all forms)
# - Brace expansion
# - Here documents and here strings
# - trap command
# - All control structures
```

### Detect the Shell

```bash
#!/bin/sh
# Detect which shell is running
if [ -n "$BASH_VERSION" ]; then
    echo "Running in Bash $BASH_VERSION"
elif [ -n "$PSH_VERSION" ]; then
    echo "Running in PSH $PSH_VERSION"
else
    echo "Unknown shell"
fi
```

### Strict Mode Portability

```bash
# Bash strict mode:
set -euo pipefail       # Works in Bash

# PSH strict mode (use one of these forms):
set -eu; set -o pipefail     # Separate statements
set -e -u -o pipefail        # Separate arguments
set -eu -o pipefail          # Mixed form
```

## 17.7 Migration Guide

### From Bash to PSH

Most Bash scripts work without modification. Check for these issues:

```bash
# 1. Check for unsupported features
grep -E 'coproc|complete |compgen |mapfile|readarray' script.sh
grep -E '\blet\b' script.sh
grep -E 'read.*-[ntsu]' script.sh

# 2. Check for combined -euo pattern
grep 'set -euo' script.sh
# Replace with: set -eu -o pipefail

# 3. Check for BASH_REMATCH usage
grep 'BASH_REMATCH' script.sh
# Replace with alternative parsing

# 4. Check for extended glob patterns
grep -E '!\(|@\(|\+\(|\?\(|\*\(' script.sh
# Replace with standard globs or find/grep

# 5. Check for let command
grep '\blet\b' script.sh
# Replace: let "x=5+3" -> ((x=5+3))
```

### Script Compatibility Checklist

```bash
#!/usr/bin/env psh
# PSH v0.187.1 Compatibility Checklist

# Fully supported:
# - Variables, arrays, associative arrays
# - All control structures (if, while, for, case, select)
# - C-style for loops
# - Functions with local variables
# - Command substitution $() and backticks
# - Process substitution <() and >()
# - All I/O redirection forms
# - Parameter expansion (all bash forms)
# - Arithmetic expansion and commands
# - Job control (jobs, fg, bg, wait, disown)
# - Shell options (errexit, nounset, xtrace, pipefail, etc.)
# - History expansion (interactive mode)
# - eval, trap, getopts, printf
# - Subshells with variable isolation
# - Control structures in pipelines
# - Brace expansion, tilde expansion
# - Here documents and here strings
# - shopt: dotglob, nullglob, globstar, nocaseglob
# - pushd, popd, dirs

# Not supported:
# - Coprocesses (coproc)
# - Extended glob patterns (syntax not parsed)
# - Programmable completion (complete, compgen)
# - let builtin (use (( )) instead)
# - mapfile/readarray
# - BASH_REMATCH capture groups
# - read -n, -t, -s, -u options
# - wait -n
# - Very deep recursion (Python stack limits)
```

## 17.8 Design Philosophy

PSH is built with educational priorities:

```
1. Code clarity over performance
2. Educational value over feature completeness
3. Correct behavior over optimization
4. Helpful errors over terse messages
5. Built-in debugging over external tools
```

This means:
- Some rarely-used Bash features may never be implemented
- Error messages are more descriptive than Bash
- Built-in debugging tools (AST, token, expansion tracing) provide visibility into shell internals
- The Python implementation enables script analysis tools (lint, security, metrics) not available in Bash
- Performance is adequate for interactive use and scripting but not optimized for high-throughput workloads

## Summary

PSH v0.187.1 provides near-complete Bash compatibility for everyday shell programming:

1. **Comprehensive Feature Support**: Arrays, associative arrays, trap, wait, disown, all control structures, all expansions
2. **Full Shell Options**: errexit, nounset, xtrace, pipefail, noclobber, allexport, and many more
3. **Minimal Remaining Gaps**: Coprocesses, extended glob patterns, programmable completion, and a few read options
4. **Educational Tools**: Debug flags, script analysis, multiple parser implementations
5. **High Compatibility**: Most Bash scripts run without modification

Key differences to remember:
- Use `set -eu -o pipefail` instead of `set -euo pipefail`
- BASH_REMATCH capture groups are not populated
- Extended glob patterns are not parsed even when extglob is set
- `let`, `mapfile`, and `readarray` are not available
- Use `$PSH_VERSION` instead of `$BASH_VERSION` to detect PSH
- Deep recursion may hit Python stack limits

---

[Previous: Chapter 16 - Advanced Features](16_advanced_features.md) | [Next: Chapter 18 - Troubleshooting](18_troubleshooting.md)
