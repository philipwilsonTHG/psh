# PSH Feature Roadmap

This document outlines potential features for future development of Python Shell (PSH), organized by priority and complexity.

## High-Priority Features

These features are essential for shell scripting compatibility and user productivity.

### 1. Array Variables
Arrays are fundamental for modern shell scripting and data manipulation.

**Indexed Arrays:**
```bash
# Declaration and initialization
arr=(one two three)
arr[3]="four"

# Access elements
echo ${arr[0]}        # First element
echo ${arr[@]}        # All elements
echo ${arr[*]}        # All elements as single string

# Array operations
echo ${#arr[@]}       # Number of elements
echo ${!arr[@]}       # Array indices
echo ${arr[@]:1:2}    # Slice from index 1, length 2
```

**Associative Arrays:**
```bash
# Declaration
declare -A map
typeset -A config

# Usage
map[key]="value"
config[host]="localhost"
config[port]="8080"

# Iteration
for key in "${!map[@]}"; do
    echo "$key: ${map[$key]}"
done
```

### 2. Trap Command for Signal Handling
Critical for robust scripts, cleanup operations, and debugging.

```bash
# Cleanup on exit
trap 'rm -f /tmp/tempfile.$$' EXIT

# Handle interrupts
trap 'echo "Interrupted!"; exit 1' INT TERM

# Debug command execution
trap 'echo "Executing: $BASH_COMMAND"' DEBUG

# Error handling
trap 'echo "Error on line $LINENO"' ERR

# Multiple signals
trap 'cleanup_function' EXIT INT TERM HUP

# Reset trap
trap - INT
```

### 3. Complete declare/typeset Functionality
Extend current implementation with variable attributes.

```bash
# Readonly variables
declare -r CONSTANT="immutable"
typeset -r VERSION="1.0"

# Integer variables
declare -i count=0
((count++))  # Arithmetic without $

# Export attribute
declare -x GLOBAL_VAR="exported"

# Nameref (reference to another variable)
declare -n ref=original_var
ref="new value"  # Updates original_var

# Combined attributes
declare -rx READONLY_EXPORT="constant"
declare -ai int_array=(1 2 3)

# Print attributes
declare -p VARNAME  # Show declaration
```

### 4. Here String Enhancement
Improve here string support with full expansion capabilities.

```bash
# Variable expansion
<<< "$variable"
<<< "${array[@]}"

# Command substitution
<<< "$(date)"
<<< "$(cat file.txt)"

# Arithmetic expansion
<<< "$((5 + 3))"

# Multiple expansions
<<< "User: $USER, Home: $HOME, Time: $(date +%T)"

# With commands
grep pattern <<< "$string"
while read line; do echo "$line"; done <<< "$multiline"
```

## Medium-Priority Features

Important features that enhance shell capabilities but aren't critical for basic usage.

### 5. Extended Globbing (extglob)
Advanced pattern matching beyond basic wildcards.

```bash
# Enable extended globbing
shopt -s extglob

# Patterns:
# ?(pattern) - Zero or one occurrence
ls ?(*.txt|*.log)

# *(pattern) - Zero or more occurrences
rm *(old|backup).*

# +(pattern) - One or more occurrences
echo +(digit|number)[0-9]

# @(pattern) - Exactly one occurrence
case $file in
    @(*.jpg|*.png|*.gif)) echo "Image file" ;;
esac

# !(pattern) - Anything except pattern
ls !(*.tmp|*.bak)

# Complex patterns
ls @(file|dir)@([0-9]|[a-z])
```

### 6. Process Substitution Enhancement
Improve existing implementation with better cleanup and broader support.

```bash
# Current support (enhance reliability)
diff <(sort file1) <(sort file2)
tee >(gzip > out.gz) >(wc -l)

# Needed improvements:
# - Automatic FIFO cleanup
# - Better error handling
# - Support in more contexts
# - Named FIFO management
```

### 7. Coprocesses
Bidirectional communication with background processes.

```bash
# Basic coprocess
coproc bc
echo "2+2" >&${COPROC[1]}
read result <&${COPROC[0]}

# Named coprocess
coproc CALC { bc -l; }
echo "scale=2; 22/7" >&${CALC[1]}
read pi <&${CALC[0]}

# Complex example
coproc SQLITE { sqlite3 database.db; }
echo "SELECT * FROM users;" >&${SQLITE[1]}
while read -u ${SQLITE[0]} line; do
    echo "Result: $line"
done
```

### 8. printf Builtin Enhancement
Full-featured printf implementation.

```bash
# Format specifiers
printf "%s\n" "string"
printf "%d\n" 42
printf "%x\n" 255
printf "%f\n" 3.14159
printf "%e\n" 1234.5

# Width and precision
printf "%10s\n" "right"
printf "%-10s\n" "left"
printf "%.2f\n" 3.14159
printf "%08d\n" 42

# Variable assignment
printf -v var "formatted %s" "string"

# Escape sequences
printf "\x41\x42\x43\n"  # ABC
printf "\u2665\n"        # ♥
printf "\033[31mRed\033[0m\n"

# Multiple arguments
printf "Name: %s, Age: %d\n" "Alice" 30 "Bob" 25
```

## Nice-to-Have Features

Features that would enhance PSH but have lower priority.

### 9. Advanced Parameter Expansion Operators
Additional expansion operators for specialized use cases.

```bash
# Quote for reuse
echo ${var@Q}  # Properly quoted for shell input

# Expand escape sequences
echo ${var@E}  # Like echo -e

# Prompt expansion
PS1='${PWD@P} $ '  # Expand as prompt

# Pattern replacement with case modification
echo ${var@U}  # Uppercase
echo ${var@L}  # Lowercase
echo ${var@u}  # Capitalize first letter

# Transform operations
${parameter@operator}
```

### 10. Loadable Builtins
Dynamic extension mechanism.

```bash
# Enable builtin
enable -f /path/to/builtin.so builtin_name

# List loaded builtins
enable -p

# Disable builtin
enable -n builtin_name

# Example custom builtins:
# - JSON parsing
# - Database queries
# - Network operations
# - System-specific tools
```

### 11. Enhanced Debugging Features
Better debugging support for script development.

```bash
# Function trace
set -o functrace
set -T

# Redirect trace output
exec {BASH_XTRACEFD}> trace.log
set -x

# Caller builtin for stack traces
caller [n]  # Show call stack

# Debug trap improvements
trap 'echo "Line $LINENO: $BASH_COMMAND"' DEBUG

# Error context
set -E  # Inherit ERR trap

# Conditional debugging
[[ $DEBUG ]] && set -x
```

### 12. Shell Options (shopt)
Bash-compatible shell options.

```bash
# View options
shopt          # Show all
shopt -p       # Show as commands
shopt optname  # Check specific

# Useful options:
shopt -s cdspell       # Correct minor cd typos
shopt -s autocd        # cd when typing directory
shopt -s checkwinsize  # Update LINES/COLUMNS
shopt -s globstar      # ** recursive glob
shopt -s nocaseglob    # Case-insensitive globbing
shopt -s histappend    # Append to history
shopt -s checkjobs     # Check jobs before exit
shopt -s dirspell      # Correct directory spelling

# Disable option
shopt -u optname
```

## Performance & Architecture Improvements

### 13. Command Hashing
Cache command locations for performance.

```bash
# Hash table management
hash            # Show all cached commands
hash -r         # Clear cache
hash -p /path/to/cmd cmd  # Add to cache
hash -d cmd     # Remove from cache

# Automatic hashing
# - First execution: search PATH
# - Subsequent: use cache
# - Cache cleared on PATH change
```

### 14. Lazy Variable Expansion
Defer expansion for better performance.

- Expand variables only when accessed
- Reduce memory usage for large arrays
- Optimize parameter expansion chains
- Cache expansion results

### 15. Background Job Improvements
Enhanced job control features.

```bash
# Wait for any job
wait -n  # Return when any job completes

# Wait with timeout
wait -t 10 $!  # Timeout after 10 seconds

# Job completion notification
set -b  # Immediate notification

# Better job status
jobs -r  # Running jobs only
jobs -s  # Stopped jobs only

# Job control in scripts
set -m  # Enable job control
```

## Compatibility Features

### 16. POSIX Mode
Strict POSIX compliance for portability.

```bash
# Enable POSIX mode
set -o posix
psh --posix

# Differences in POSIX mode:
# - Word splitting behavior
# - Alias expansion rules
# - Function vs special builtin precedence
# - Signal handling
# - Variable expansion edge cases
```

### 17. Restricted Shell Mode
Security-focused limited shell.

```bash
# Start restricted shell
psh -r
set -r  # Cannot unset

# Restrictions:
# - No cd command
# - No setting PATH
# - No command names with /
# - No redirecting output
# - No exec builtin
# - No enabling/disabling builtins

# Use cases:
# - Limited user environments
# - Application shells
# - Captive portals
```

## Implementation Considerations

### Priority Criteria
1. **User demand** - Features frequently requested
2. **Compatibility** - Bash/POSIX compliance
3. **Complexity** - Implementation difficulty
4. **Dependencies** - Required architectural changes
5. **Testing** - Ability to thoroughly test

### Architectural Impact
- Arrays require variable system refactoring
- Trap needs signal handling improvements
- Extended features may need parser updates
- Performance features need profiling

### Testing Strategy
- Comprehensive test suite for each feature
- Compatibility tests against bash
- Performance benchmarks
- Edge case coverage

## Contributing

When implementing features:
1. Check existing patterns in codebase
2. Write tests first
3. Update documentation
4. Consider backwards compatibility
5. Follow PSH coding standards

---

This roadmap is a living document. Features may be added, removed, or reprioritized based on user feedback and project needs.