# POSIX Shell Specification Reference

This document outlines the key requirements from POSIX.1-2017 (IEEE Std 1003.1-2017) for shell implementations, focusing on areas relevant to PSH.

## 1. Shell Command Language (Section 2)

### 1.1 Shell Grammar

The POSIX shell grammar defines the following key constructs:

#### Commands
- Simple commands: `command [arguments...] [redirections...]`
- Pipelines: `command1 | command2 | ... | commandN`
- Lists: Commands separated by `;`, `&`, `&&`, or `||`
- Compound commands: `if`, `while`, `for`, `case`, etc.

#### Control Structures
- `if` command: `if list; then list; [elif list; then list;]... [else list;] fi`
- `while` loop: `while list; do list; done`
- `for` loop: `for name [in word...]; do list; done`
- `case` statement: `case word in [pattern [| pattern]...) list;;]... esac`

### 1.2 Quoting

POSIX defines three types of quoting:
- **Escape Character (Backslash)**: Preserves literal value of next character
- **Single Quotes**: Preserves literal value of all characters within quotes
- **Double Quotes**: Preserves literal value except for `$`, `` ` ``, `\`, and `!` (in some contexts)

### 1.3 Parameters and Variables

#### Special Parameters
- `$0`: Name of shell or shell script
- `$1`, `$2`, ..., `$9`: Positional parameters
- `$#`: Number of positional parameters
- `$@`: All positional parameters as separate words
- `$*`: All positional parameters as a single word
- `$?`: Exit status of most recent pipeline
- `$-`: Current option flags
- `$$`: Process ID of the shell
- `$!`: Process ID of most recent background command

#### Parameter Expansion
- `${parameter}`: Basic expansion
- `${parameter:-word}`: Use default value
- `${parameter:=word}`: Assign default value
- `${parameter:?word}`: Display error if null or unset
- `${parameter:+word}`: Use alternative value
- `${#parameter}`: String length
- `${parameter%word}`: Remove smallest suffix pattern
- `${parameter%%word}`: Remove largest suffix pattern
- `${parameter#word}`: Remove smallest prefix pattern
- `${parameter##word}`: Remove largest prefix pattern

### 1.4 Word Expansions

POSIX defines the order of word expansions:
1. Tilde expansion
2. Parameter expansion
3. Command substitution
4. Arithmetic expansion
5. Field splitting (IFS)
6. Pathname expansion (globbing)
7. Quote removal

### 1.5 Redirection

Standard redirections:
- `<`: Input redirection
- `>`: Output redirection
- `>>`: Append output
- `<<`: Here-document
- `<<-`: Here-document with tab stripping
- `<&`: Duplicate input file descriptor
- `>&`: Duplicate output file descriptor
- `<>`: Open for reading and writing

## 2. Required Built-in Utilities

### 2.1 Special Built-ins

These affect the shell execution environment and must be built-in:
- `break`: Exit from loop
- `colon (:)`: Null command
- `continue`: Continue loop
- `dot (.)`: Execute commands in current environment
- `eval`: Construct and execute command
- `exec`: Execute command or manipulate file descriptors
- `exit`: Exit shell
- `export`: Set export attribute
- `readonly`: Set readonly attribute
- `return`: Return from function
- `set`: Set/unset options and positional parameters
- `shift`: Shift positional parameters
- `trap`: Trap signals
- `unset`: Unset variables and functions

### 2.2 Regular Built-ins

These are typically built-in for efficiency:
- `alias`: Define command alias
- `bg`: Resume job in background
- `cd`: Change directory
- `command`: Execute simple command
- `false`: Return false value
- `fc`: Process command history
- `fg`: Resume job in foreground
- `getopts`: Parse options
- `hash`: Remember/report command locations
- `jobs`: Display jobs
- `kill`: Terminate or signal processes
- `pwd`: Print working directory
- `read`: Read line from input
- `true`: Return true value
- `umask`: Get/set file mode creation mask
- `unalias`: Remove alias
- `wait`: Wait for process completion

## 3. Exit Status

POSIX defines standard exit status values:
- `0`: Success
- `1-125`: Command-specific error codes
- `126`: Command found but not executable
- `127`: Command not found
- `128+n`: Command terminated by signal n

## 4. Shell Execution Environment

### 4.1 Environment Variables

Required environment variables:
- `HOME`: User's home directory
- `IFS`: Internal field separator (default: space, tab, newline)
- `PATH`: Command search path
- `PS1`: Primary prompt string
- `PS2`: Secondary prompt string
- `PS4`: Execution trace prompt
- `PWD`: Current working directory

### 4.2 Signal Handling

POSIX signal disposition:
- Signals ignored on entry to shell remain ignored
- Traps are reset to default in subshells
- SIGINT and SIGQUIT ignored for background commands
- SIGCHLD handling for job control

## 5. Pattern Matching

### 5.1 Pathname Expansion

- `*`: Matches any string, including null
- `?`: Matches any single character
- `[...]`: Matches any character in set
- `[!...]`: Matches any character not in set

### 5.2 Pattern Matching in Case Statements

Same as pathname expansion, but:
- No pathname expansion performed
- Patterns can contain `|` for alternatives

## 6. Arithmetic Expansion

POSIX arithmetic uses signed long integer arithmetic with these operators:
- `+`, `-`, `*`, `/`, `%`: Basic arithmetic
- `<<`, `>>`: Bit shifts
- `<`, `<=`, `>`, `>=`: Comparisons
- `==`, `!=`: Equality
- `&`, `|`, `^`: Bitwise operations
- `&&`, `||`: Logical operations
- `=`: Assignment
- `()`: Grouping

## 7. Key Differences from Bash

### Features NOT in POSIX:
- Arrays (neither indexed nor associative)
- `[[...]]` conditional command
- `((...))` arithmetic command
- Brace expansion (`{1..10}`, `{a,b,c}`)
- Process substitution (`<(...)`, `>(...)`)
- Extended globbing patterns
- `+=` assignment operator
- `local` keyword for functions
- Many parameter expansion features (case modification, substring operations)

### POSIX Requirements Often Missed:
- Proper handling of `-` as stdin/stdout in utilities
- Exact signal handling semantics
- Precise word splitting behavior
- Locale-aware operations
- Proper handling of unset vs null variables

## 8. Compliance Testing Approach

To test POSIX compliance:
1. Test each grammar construct
2. Verify built-in behavior matches specification
3. Check expansion order and results
4. Validate exit status handling
5. Ensure signal handling compliance
6. Test with minimal environment (no extensions)