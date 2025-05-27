#!/usr/bin/env python3
"""Version information for Python Shell (psh)."""

# Semantic versioning: MAJOR.MINOR.PATCH
__version__ = "0.2.0"

# Version history
VERSION_HISTORY = """
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