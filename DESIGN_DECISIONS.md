# Python Shell (psh) - Early Design Decisions

## 1. Parser Architecture
- **Tokenizer/Lexer**: How to break input into tokens (words, operators, etc.)
- **Parser Type**: Recursive descent vs. parser generator (e.g., PLY, pyparsing)
- **AST Structure**: How to represent parsed commands internally

## 2. Command Execution Model
- **Process Creation**: subprocess module vs. os.fork/exec
- **Built-in vs External**: Which commands to implement internally
- **Pipeline Implementation**: How to handle pipes between processes

## 3. Shell Grammar Support
- **Syntax Features**: Which bash/POSIX features to support initially
  - Basic command execution
  - Pipes (|)
  - Redirections (<, >, >>)
  - Background jobs (&)
  - Command substitution ($(...) or `...`)
  - Variable expansion
  - Wildcards/globbing
  - Quotes (single, double, escaping)

## 4. Environment and Variables
- **Variable Storage**: How to manage shell variables vs environment
- **Variable Expansion**: When and how to expand $VAR
- **Special Variables**: Support for $?, $!, $$, $0, $1, etc.

## 5. Job Control
- **Process Groups**: Whether to implement job control
- **Signal Handling**: How to handle Ctrl-C, Ctrl-Z
- **Background Jobs**: Managing & and jobs command

## 6. Interactive Features
- **Line Editing**: Use readline, prompt_toolkit, or custom
- **History**: Command history storage and recall
- **Tab Completion**: Whether and how to implement

## 7. Error Handling
- **Error Reporting**: How verbose/helpful error messages should be
- **Exit Codes**: Propagating command exit status
- **Shell Options**: set -e, set -u equivalents

## 8. Compatibility Level
- **POSIX Compliance**: How strictly to follow POSIX
- **Bash Extensions**: Which bash-specific features to include
- **Teaching Focus**: Simplifications for clarity vs completeness