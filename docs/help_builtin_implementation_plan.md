# Plan: Implement Help Builtin for PSH

## Overview
Implement a `help` builtin for PSH that provides documentation for shell builtin commands, similar to bash's help command.

## Features to Implement

### 1. Basic Help Command
- `help` - List all available builtin commands with brief descriptions
- `help <builtin>` - Show detailed help for a specific builtin
- Support pattern matching: `help echo*` shows help for all builtins starting with "echo"

### 2. Command Options
- `-d` - Show short descriptions for each builtin (one line per builtin)
- `-s` - Show only usage synopsis for matching patterns
- `-m` - Display help in pseudo-manpage format

### 3. Help Text Structure
Each builtin should provide:
- **Synopsis**: Command syntax with options
- **Description**: Brief overview of what the command does
- **Options**: Detailed list of command-line options
- **Exit Status**: Return codes and their meanings
- **Examples** (optional): Usage examples

## Implementation Plan

### Step 1: Create Help Builtin Class
Create `psh/builtins/help_command.py`:
- Implement `HelpBuiltin` class
- Parse command-line options (-d, -s, -m)
- Handle pattern matching for builtin names
- Format output based on selected display mode

### Step 2: Enhance Builtin Base Class
Update `psh/builtins/base.py`:
- Add optional properties for structured help:
  - `synopsis`: Brief command syntax
  - `description`: One-line description
  - `detailed_help`: Full help text (current `help` property)
- Maintain backward compatibility with existing `help` property

### Step 3: Update Existing Builtins
For each existing builtin, enhance the help text to include:
- Proper synopsis format
- Brief description for `-d` option
- Structured help text with sections

### Step 4: Output Formatting
Implement different display modes:
- **Default**: Show list of builtins with usage lines
- **-d mode**: One builtin per line with description
- **-s mode**: Just the synopsis line
- **-m mode**: Manpage-style formatting with sections

### Step 5: Pattern Matching
- Support glob patterns (*, ?, [])
- Case-insensitive matching option
- Show all matches for patterns

### Step 6: Testing
Create comprehensive tests:
- Test all display modes
- Test pattern matching
- Test error cases (invalid options, no matches)
- Verify output formatting

## Example Output

```bash
# Default help
psh$ help
PSH Shell Builtins
Type 'help name' to find out more about the function 'name'.

:           - Null command that returns success
alias       - Define or display aliases
bg          - Resume jobs in the background
cd          - Change the current directory
echo        - Display text
...

# Specific builtin
psh$ help echo
echo: echo [-neE] [arg ...]
    Display arguments separated by spaces, followed by a newline.
    
    Options:
      -n    Do not output the trailing newline
      -e    Enable interpretation of backslash escapes
      -E    Disable interpretation of backslash escapes (default)
    
    Exit Status:
      Returns success unless a write error occurs.

# Short description mode
psh$ help -d echo
echo - Display text

# Synopsis only
psh$ help -s echo
echo: echo [-neE] [arg ...]
```

## Files to Create/Modify

1. **Create**: `psh/builtins/help_command.py` - The help builtin implementation
2. **Modify**: `psh/builtins/base.py` - Add structured help properties
3. **Modify**: All existing builtin files - Enhance help text
4. **Create**: `tests/test_help_builtin.py` - Comprehensive tests
5. **Update**: User documentation to mention the help builtin

## Benefits

- Improves discoverability of PSH features
- Provides consistent documentation format
- Matches bash behavior for familiarity
- Enhances the educational value of PSH
- Makes PSH more self-documenting

## Implementation Details

### Help Text Format
The help text should follow this structure:

```
NAME: synopsis
    Brief description
    
    Detailed description paragraph(s)
    
    Options:
      -x    Description of option x
      -y    Description of option y
    
    Arguments:
      ARG   Description of argument
    
    Examples:
      command -x arg    # Example description
    
    Exit Status:
      Returns 0 on success, non-zero on failure.
      
    See Also:
      Related commands or topics
```

### Pattern Matching Implementation
Use Python's `fnmatch` module for glob pattern matching:
- `*` matches any characters
- `?` matches single character  
- `[seq]` matches any character in seq
- `[!seq]` matches any character not in seq

### Display Modes

#### Default Mode
Shows a formatted list of all builtins with brief descriptions, similar to bash's help output.

#### Description Mode (-d)
One line per builtin:
```
builtin_name - brief description
```

#### Synopsis Mode (-s)
Just the synopsis line:
```
builtin_name: usage syntax
```

#### Manpage Mode (-m)
Full manpage-style formatting with sections like NAME, SYNOPSIS, DESCRIPTION, OPTIONS, etc.

### Error Handling
- Invalid options: Show usage and return 2
- No matching builtins: Show error message and return 1
- Success: Return 0

### Integration with Shell
The help builtin will:
- Access the builtin registry to get all registered builtins
- Call methods on each builtin to get help information
- Format and display the help text according to options