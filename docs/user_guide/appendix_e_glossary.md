# Appendix E: Glossary of Terms

This glossary provides definitions for common shell scripting terms and concepts used throughout the PSH User's Guide. Terms are organized alphabetically for easy reference.

## A

**Alias**  
A user-defined shortcut for a command or series of commands. Created with the `alias` command.  
Example: `alias ll='ls -la'`

**Argument**  
A value passed to a command or function. Also called a parameter.  
Example: In `ls -l /home`, `-l` and `/home` are arguments.

**Arithmetic Expansion**  
The process of evaluating mathematical expressions within `$((...))`.  
Example: `echo $((2 + 3))` outputs `5`

**Arithmetic Command**  
A command that evaluates arithmetic expressions using `((...))` syntax.  
Example: `((x++))` increments the variable x.

**Array**
A variable that can hold multiple values indexed by number (indexed arrays) or string (associative arrays declared with `declare -A`).

**ASCII**  
American Standard Code for Information Interchange. A character encoding standard.

**Assignment**  
Setting a value to a variable using the `=` operator.  
Example: `name="John"`

## B

**Background Process**  
A process that runs without blocking the shell prompt, started with `&`.  
Example: `long_command &`

**Backslash**  
The `\` character used for escaping special characters or line continuation.

**Backtick**  
The `` ` `` character used for command substitution (legacy syntax).  
Example: `` echo `date` ``

**Bash**  
Bourne Again Shell, the shell that PSH aims to be compatible with.

**Binary**  
An executable file containing machine code, as opposed to a script.

**Blank**  
A space or tab character.

**Brace Expansion**  
Generating multiple strings from a pattern using `{}`.  
Example: `echo {a,b,c}` outputs `a b c`

**Builtin**  
A command implemented within the shell itself, not as an external program.  
Examples: `cd`, `echo`, `export`

## C

**Case Statement**  
A control structure for pattern matching using `case...esac`.  
Example: `case $var in pattern) commands ;; esac`

**Character Class**  
A set of characters within square brackets for pattern matching.  
Example: `[a-z]` matches any lowercase letter.

**Child Process**  
A process created by another process (the parent).

**Command**  
An instruction to the shell to perform an action.

**Command Line**  
The text interface where users type commands.

**Command Substitution**  
Replacing a command with its output using `$(...)` or backticks.  
Example: `today=$(date)`

**Comment**  
Text ignored by the shell, starting with `#`.  
Example: `# This is a comment`

**Conditional**  
A statement that executes code based on a condition.  
Example: `if [ -f file ]; then ... fi`

**Control Character**  
A non-printing character that controls text processing (e.g., newline, tab).

**Control Structure**  
Language constructs for controlling program flow (if, while, for, case).

**Current Directory**  
The directory where the shell is currently operating, shown by `pwd`.

## D

**Delimiter**  
A character that separates values or fields.  
Example: `:` in PATH entries.

**Directory**  
A file system container for files and other directories (folder).

**Double Quotes**  
Quotes `"..."` that allow variable expansion but prevent word splitting.  
Example: `echo "$variable"`

## E

**Environment**  
The set of variables and values available to processes.

**Environment Variable**  
A variable exported to child processes.  
Example: `export PATH=/usr/bin:$PATH`

**Escape Character**  
A backslash `\` used to remove special meaning from the next character.  
Example: `echo \$5` outputs `$5`

**Escape Sequence**  
A sequence of characters representing a special character.  
Example: `\n` for newline, `\t` for tab.

**Execute Permission**  
File permission allowing a file to be run as a program.

**Exit Status**  
A number (0-255) returned by a command indicating success (0) or failure (non-zero).

**Expansion**  
The process of replacing special patterns with their values (variable, command, arithmetic, etc.).

**Export**  
Making a shell variable available to child processes.  
Example: `export VAR=value`

## F

**Field**  
A unit of data separated by delimiters.

**File Descriptor**  
A number representing an open file. 0=stdin, 1=stdout, 2=stderr.

**File Test**  
An operator that checks file attributes.  
Example: `-f` tests if a file exists and is regular.

**Filter**  
A program that reads from stdin and writes to stdout.

**Foreground Process**  
A process that has control of the terminal.

**Fork**  
Creating a new process that is a copy of the current process.

**Function**  
A named group of commands that can be called like a command.  
Example: `greet() { echo "Hello $1"; }`

## G

**Glob**  
A pattern using wildcards for filename matching.  
Example: `*.txt` matches all .txt files.

**Globbing**  
The process of expanding glob patterns to matching filenames.

**Group**  
A collection of users; also, grouped commands in parentheses or braces.

## H

**Here Document**  
A method of providing multi-line input to a command using `<<`.  
Example: `cat <<EOF ... EOF`

**Here String**  
Providing a string as stdin using `<<<`.  
Example: `grep pattern <<< "search in this string"`

**History**  
The list of previously executed commands.

**Home Directory**  
A user's personal directory, represented by `~`.

## I

**Init File**  
A script run when the shell starts (e.g., .pshrc).

**Input**  
Data provided to a command or script.

**Interactive Shell**  
A shell session where users type commands at a prompt.

**Internal Field Separator (IFS)**  
Characters used to split words (default: space, tab, newline).

**Interpreter**  
A program that executes scripts (PSH is a shell interpreter).

## J

**Job**  
A pipeline or command running in the shell.

**Job Control**  
Managing running processes (suspend, resume, background, foreground).

**Job ID**  
A number assigned to a background job, referenced with `%`.

## K

**Kernel**  
The core of the operating system that manages resources.

**Keyword**  
Reserved words with special meaning (if, then, while, for, etc.).

## L

**Line Continuation**  
Using backslash at line end to continue a command on the next line.

**Local Variable**  
A variable visible only within a function.  
Example: `local var=value`

**Login Shell**  
The first shell started when a user logs in.

**Loop**  
A control structure that repeats commands (for, while, until).

## M

**Metacharacter**  
A character with special meaning to the shell (*, ?, $, etc.).

**Modifier**  
A flag that changes command behavior.  
Example: `-l` in `ls -l`

## N

**Newline**  
The character that ends a line (ASCII 10, \n).

**Non-interactive Shell**  
A shell running a script without user interaction.

**Null**  
Empty or zero value; the null character is ASCII 0.

## O

**Operator**  
A symbol that performs an operation (arithmetic, comparison, logical).

**Option**  
A command-line argument that modifies behavior, usually starting with `-`.

**Output**  
Data produced by a command.

## P

**Parameter**  
A variable, positional parameter, or special parameter.

**Parameter Expansion**  
Accessing and manipulating variable values using `${...}`.  
Example: `${var:-default}`

**Parent Process**  
The process that created another process.

**PATH**  
Environment variable containing directories to search for commands.

**Pattern**  
A template for matching strings or filenames.

**Permission**  
File attributes controlling read, write, and execute access.

**Pipe**  
The `|` operator connecting command output to another command's input.  
Example: `ls | grep txt`

**Pipeline**  
A series of commands connected by pipes.

**Positional Parameter**  
Arguments to a script or function ($1, $2, etc.).

**Process**  
A running instance of a program.

**Process ID (PID)**  
A unique number identifying a running process.

**Process Substitution**  
Using command output as a file with `<(...)` or `>(...)`.  
Example: `diff <(sort file1) <(sort file2)`

**Prompt**  
The text displayed when the shell waits for input (PS1, PS2).

## Q

**Quote**  
Characters (' or ") used to group text and control expansion.

**Quoting**  
Using quotes to control how the shell interprets text.

## R

**Recursion**  
A function calling itself; limited depth in PSH.

**Redirect**  
Changing where a command reads input or writes output.  
Example: `command > file`

**Regular Expression (Regex)**  
A pattern for matching text, used with `=~` operator.

**Return Value**  
The exit status of a command or function.

**Root**  
The superuser account; also, the top directory `/`.

## S

**Script**  
A text file containing shell commands.

**Shebang**  
The `#!` at the start of a script specifying the interpreter.  
Example: `#!/usr/bin/env psh`

**Shell**  
A command-line interpreter (PSH is a shell).

**Shell Variable**  
A variable available only in the current shell.

**Signal**  
A message to a process (SIGINT, SIGTERM, etc.).

**Single Quotes**  
Quotes `'...'` that preserve literal values.  
Example: `echo '$VAR'` outputs `$VAR`

**Source**  
Executing commands from a file in the current shell.  
Example: `source script.sh` or `. script.sh`

**Special Parameter**  
Built-in variables like `$?`, `$$`, `$!`, `$#`, `$@`, `$*`.

**Standard Error (stderr)**  
Output stream for error messages (file descriptor 2).

**Standard Input (stdin)**  
Input stream for commands (file descriptor 0).

**Standard Output (stdout)**  
Output stream for normal output (file descriptor 1).

**Statement**  
A complete command or control structure.

**String**  
A sequence of characters.

**Subshell**  
A child shell process created with `()` or command substitution.

**Substitution**  
Replacing a pattern with a value (variable, command, etc.).

**Syntax**  
The rules for constructing valid shell commands.

## T

**Tab Completion**  
Pressing Tab to auto-complete commands or filenames.

**Terminal**  
The interface for interacting with the shell.

**Test**  
Evaluating a condition; the `test` command or `[` builtin.

**Tilde Expansion**  
Replacing `~` with the home directory path.

**Token**  
A basic unit of shell syntax (word, operator, etc.).

**Trap**
Catching and handling signals using the `trap` builtin.
Example: `trap 'rm -f $tmpfile' EXIT`

## U

**Unary Operator**  
An operator that takes one operand.  
Example: `-f file` (file exists test).

**Unicode**  
A standard for encoding text characters from all languages.

**Unix**  
The operating system family that includes Linux and macOS.

**Unset**  
Removing a variable or function.  
Example: `unset variable`

**User**  
An account on the system.

## V

**Variable**  
A named storage location for data.  
Example: `name="value"`

**Variable Expansion**  
Replacing `$variable` or `${variable}` with its value.

## W

**Whitespace**  
Space, tab, or newline characters.

**Wildcard**  
Characters (*, ?, [...]) representing multiple possible matches.

**Word**  
A sequence of characters treated as a unit by the shell.

**Word Splitting**  
Breaking a string into words based on IFS characters.

**Working Directory**  
The current directory; same as current directory.

## X

**Execute**  
Running a command or script.

**Exit**  
Terminating a shell or script with `exit` command.

## Y

**Yank** *(In editors)*  
Paste previously cut or copied text.

## Z

**Zero**  
The number 0; also, successful exit status.

**Zombie Process**  
A terminated process whose parent hasn't collected its exit status.

---

## Common Abbreviations

- **CLI** - Command Line Interface
- **EOF** - End of File
- **FIFO** - First In, First Out
- **FQDN** - Fully Qualified Domain Name
- **GNU** - GNU's Not Unix
- **GUI** - Graphical User Interface
- **I/O** - Input/Output
- **IPC** - Inter-Process Communication
- **LIFO** - Last In, First Out
- **POSIX** - Portable Operating System Interface
- **REPL** - Read-Eval-Print Loop
- **TTY** - Teletypewriter (terminal)
- **UID** - User IDentifier
- **UTC** - Coordinated Universal Time

## See Also

- [Appendix A: Quick Reference Card](appendix_a_quick_reference.md) - Command syntax reference
- [Appendix C: Regular Expression Reference](appendix_c_regex_reference.md) - Pattern matching guide
- [Chapter 1: Introduction](01_introduction.md) - Overview of shell concepts