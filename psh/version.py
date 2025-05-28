#!/usr/bin/env python3
"""Version information for Python Shell (psh)."""

# Semantic versioning: MAJOR.MINOR.PATCH
__version__ = "0.12.0"

# Version history
VERSION_HISTORY = """
0.12.0 (2025-05-28) - Shebang support and advanced script execution
  - Full shebang support for multi-interpreter execution (#!/bin/bash, #!/usr/bin/env python3)
  - Enhanced binary file detection with multi-factor analysis
  - Improved script argument passing and state management
  - Production-quality script execution with proper fallback handling
  - Support for common shebang patterns and env-based interpreters
  - Comprehensive file signature recognition and encoding handling
  - Updated documentation and TODO.md reflecting 26 completed features

0.11.0 (2025-05-28) - Enhanced script execution
  - Enhanced source builtin with PATH search and argument support
  - Improved command line processing with -h, -V, and -- options
  - Line continuation support with backslash
  - Enhanced error messages with file and line number information
  - Script vs interactive mode distinction with appropriate signal handling
  - Unified input processing system for better consistency
  - Comprehensive help and usage examples
  - Better file validation and error handling

0.10.0 (2025-05-28) - Script file execution
  - Added script file execution support with `psh script.sh`
  - Implemented InputSource abstraction for flexible input handling
  - Added proper $0 variable handling for script names
  - Support script arguments as $1, $2, etc. via set_positional_params()
  - File validation with appropriate exit codes (126, 127)
  - Comment and empty line handling in scripts
  - Binary file detection and rejection
  - Enhanced -c flag to accept additional arguments
  - Comprehensive architecture documentation for future development

0.9.0 (2025-05-28) - Job control
  - Full job control implementation with process group management
  - Job suspension with Ctrl-Z (SIGTSTP handling)
  - Built-in commands: jobs, fg, bg for job management
  - Job specifications: %1, %+, %-, %string for referencing jobs
  - Background job completion notifications
  - Terminal control management between shell and jobs
  - Terminal mode preservation when switching jobs
  - SIGCHLD handler for tracking job state changes
  - Comprehensive test suite for job control features

0.8.0 (2025-05-28) - Shell functions
  - Added shell function definitions (POSIX name() {} and bash function name {})
  - Functions stored as AST nodes for proper execution
  - Function execution in current shell process (no fork)
  - Proper parameter isolation with positional parameters
  - Return builtin with exception-based control flow
  - Function management (declare -f, unset -f)
  - Functions work in pipelines and subshells
  - Comprehensive test suite with 32 passing tests

0.7.0 (2025-05-27) - Shell aliases
  - Added alias and unalias builtin commands
  - Implemented recursive alias expansion with loop prevention
  - Support for trailing space in aliases (enables next word expansion)
  - Position-aware expansion (only at command positions)
  - Proper handling of quoted alias definitions
  - Added comprehensive test suite for alias functionality

0.6.0 (2025-05-27) - Vi and Emacs key bindings
  - Added comprehensive vi and emacs key binding support
  - Emacs mode (default): Ctrl-A/E, Ctrl-K/U/W, Ctrl-Y, Alt-F/B, and more
  - Vi mode: normal/insert modes, hjkl movement, word motions, editing commands
  - Implemented reverse history search with Ctrl-R (works in both modes)
  - Added kill ring for cut/paste operations
  - Support mode switching via 'set -o vi/emacs' command
  - Added full documentation and test coverage for key bindings

0.5.0 (2025-05-27) - Tilde expansion
  - Added tilde expansion for home directories (~ and ~user)
  - Tilde expansion works in arguments, redirections, and variable assignments
  - Only expands unquoted tildes at the beginning of words
  - Added comprehensive test suite for tilde expansion
  - Note: Escaped tilde handling requires future architectural changes

0.4.0 (2025-05-27) - Here strings and bug fixes
  - Added here string support (<<<) for passing strings as stdin
  - Fixed command substitution to properly capture external command output
  - Fixed history builtin to show last 10 commands by default (bash behavior)
  - Fixed set builtin to support positional parameters ($1, $2, etc.)
  - Fixed multiple test suite issues for better reliability
  - Improved error handling for empty heredocs

0.3.0 (2025-01-27) - Conditional execution
  - Added && and || operators for conditional command execution
  - Implemented short-circuit evaluation
  - Fixed pipeline execution issues by removing cat builtin
  - Improved test suite reliability

0.2.0 (2025-01-23) - Tab completion and comments
  - Added interactive tab completion for files/directories
  - Added comment support (# at word boundaries)
  - Fixed prompt positioning issues in raw terminal mode
  - Fixed history navigation display
  - Added version builtin command

0.1.0 (2025-01-23) - Initial versioned release
  - Basic command execution
  - I/O redirection (<, >, >>, 2>, 2>>, 2>&1)
  - Pipelines
  - Background processes (&)
  - Command history
  - Built-in commands: cd, exit, pwd, echo, env, export, unset, source, history, set, cat
  - Variable expansion and special variables
  - Command substitution ($() and ``)
  - Wildcards/globbing (*, ?, [...])
  - Here documents (<< and <<-)
"""

def get_version():
    """Return the current version string."""
    return __version__

def get_version_info():
    """Return detailed version information."""
    return f"Python Shell (psh) version {__version__}"