# Multi-line Commands and Prompt Customization Architecture

## Overview

This document outlines the architecture for implementing two related features in psh:
1. **Multi-line command support** in interactive mode
2. **Prompt customization** with PS0, PS1, and PS2 variables

These features will enable users to type complex control structures naturally across multiple lines and customize their shell prompts.

## Current State Analysis

### Existing Capabilities
- **Script mode** already supports multi-line commands with incomplete detection
- **Parser** can identify incomplete control structures via specific error messages
- **LineEditor** provides sophisticated single-line editing with vi/emacs modes
- **Variables** infrastructure exists for storing PS1/PS2/PS0

### Current Limitations
- Interactive mode reads only single lines
- No continuation prompt (PS2) when commands are incomplete
- Hardcoded prompt format with no customization
- No prompt expansion capabilities

## Proposed Architecture

### 1. Multi-line Input Handler

Create a new `MultiLineInputHandler` class that coordinates between LineEditor and the shell:

```python
class MultiLineInputHandler:
    def __init__(self, line_editor: LineEditor, shell: Shell):
        self.line_editor = line_editor
        self.shell = shell
        self.buffer = []
        self.in_heredoc = False
        self.heredoc_delimiter = None
        
    def read_command(self) -> Optional[str]:
        """Read a complete command, possibly spanning multiple lines."""
        self.buffer = []
        
        while True:
            # Determine which prompt to show
            if not self.buffer:
                prompt = self.shell.expand_prompt(self.shell.variables.get('PS1', 'psh$ '))
            else:
                prompt = self.shell.expand_prompt(self.shell.variables.get('PS2', '> '))
            
            # Read one line
            line = self.line_editor.read_line(prompt)
            if line is None:  # EOF
                if self.buffer:
                    # Incomplete command at EOF
                    print("\npsh: unexpected EOF while looking for matching `}'")
                    self.buffer = []
                return None
                
            self.buffer.append(line)
            
            # Check if command is complete
            full_command = '\n'.join(self.buffer)
            if self._is_complete_command(full_command):
                self.buffer = []
                return full_command
                
    def _is_complete_command(self, command: str) -> bool:
        """Check if command is syntactically complete."""
        # Reuse logic from shell._execute_from_source
        try:
            # Try to parse the command
            tokens = tokenize(command)
            parse(tokens)
            return True
        except ParseError as e:
            # Check if it's an incomplete construct
            error_msg = str(e)
            incomplete_patterns = [
                "Expected DO", "Expected DONE", "Expected FI",
                "Expected ELSE or FI", "Expected THEN", "Expected ESAC",
                "Unexpected EOF", "Unterminated string"
            ]
            for pattern in incomplete_patterns:
                if pattern in error_msg:
                    return False
            # Other parse errors mean the command is complete but invalid
            return True
```

### 2. Prompt Variables and Expansion

Add prompt variables to the shell and implement expansion:

```python
# In Shell.__init__
self.variables['PS1'] = '\\u@\\h:\\w$ '  # Default primary prompt
self.variables['PS2'] = '> '             # Default continuation prompt
self.variables['PS0'] = ''               # Executed before each command

# Prompt expansion method
def expand_prompt(self, prompt_string: str) -> str:
    """Expand prompt escape sequences."""
    if not prompt_string:
        return ''
        
    # Basic expansions
    expansions = {
        '\\u': pwd.getpwuid(os.getuid()).pw_name,  # username
        '\\h': socket.gethostname().split('.')[0],   # hostname (short)
        '\\H': socket.gethostname(),                  # hostname (full)
        '\\w': os.getcwd().replace(os.path.expanduser('~'), '~'),  # working directory
        '\\W': os.path.basename(os.getcwd()),        # basename of pwd
        '\\$': '#' if os.getuid() == 0 else '$',    # $ or # for root
        '\\n': '\n',                                  # newline
        '\\t': time.strftime('%H:%M:%S'),           # time
        '\\d': time.strftime('%a %b %d'),           # date
        '\\!': str(len(self.history) + 1),          # history number
        '\\#': str(self.command_number),             # command number
        '\\?': str(self.last_exit_code),            # exit status
    }
    
    result = prompt_string
    for escape, value in expansions.items():
        result = result.replace(escape, value)
        
    # Handle command substitution in prompts
    # $(command) or `command` in prompts
    result = self._expand_prompt_commands(result)
    
    return result
```

### 3. Enhanced Interactive Loop

Modify the interactive loop to use the multi-line handler:

```python
def interactive_loop(self):
    """Run the interactive command loop with multi-line support."""
    # Initialize multi-line handler
    multi_line_handler = MultiLineInputHandler(self.line_editor, self)
    self.command_number = 0
    
    while True:
        try:
            # Execute PS0 if set
            ps0 = self.variables.get('PS0', '')
            if ps0:
                self.run_command(ps0, add_to_history=False)
            
            # Read complete command (possibly multi-line)
            command = multi_line_handler.read_command()
            if command is None:  # EOF
                print("exit")
                break
                
            # Skip empty commands
            if not command.strip():
                continue
                
            # Update command number
            self.command_number += 1
            
            # Execute the command
            self.last_exit_code = self.run_command(command)
            
        except KeyboardInterrupt:
            # Ctrl-C: Cancel current multi-line input
            multi_line_handler.reset()
            print("^C")
            self.last_exit_code = 130
```

### 4. Special Cases

#### Heredocs
Need special handling for heredoc detection and termination:

```python
def _detect_heredoc(self, line: str) -> Optional[str]:
    """Detect if line contains a heredoc and return delimiter."""
    # Look for << or <<- followed by delimiter
    heredoc_match = re.search(r'<<-?\s*([\'"]?)(\w+)\1', line)
    if heredoc_match:
        return heredoc_match.group(2)
    return None
```

#### Quoted Strings
Multi-line strings need careful handling:
- Detect unterminated quotes
- Track quote state across lines
- Handle escaped quotes

#### Line Continuation
Support explicit line continuation with backslash:
```bash
echo "This is a very long line that \
continues on the next line"
```

### 5. Implementation Phases

#### Phase 1: Basic Multi-line Support
1. Implement MultiLineInputHandler
2. Reuse incomplete detection from script mode
3. Add basic PS2 support
4. Handle simple control structures

#### Phase 2: Prompt Customization
1. Add PS1/PS2/PS0 variables
2. Implement basic prompt expansion
3. Support common escape sequences
4. Add time/date expansions

#### Phase 3: Advanced Features
1. Command substitution in prompts
2. ANSI color codes in prompts
3. Conditional prompt elements
4. Width-aware prompt formatting

## Example Usage

### Multi-line Control Structures
```bash
psh$ if [ -f ~/.bashrc ]; then
> echo "Found bashrc"
> source ~/.bashrc
> fi
Found bashrc
psh$ 
```

### Custom Prompts
```bash
psh$ PS1='[\u@\h \W]\$ '
[user@hostname psh]$ PS1='\t \w\n\$ '
14:23:45 ~/projects/psh
$ PS2='... '
$ for i in 1 2 3; do
... echo $i
... done
1
2
3
```

### Heredocs
```bash
psh$ cat << EOF
> This is line 1
> This is line 2
> EOF
This is line 1
This is line 2
psh$
```

## Technical Considerations

### 1. State Management
- Multi-line handler must track state between lines
- Reset state on Ctrl-C or completed command
- Preserve state across history navigation

### 2. Error Recovery
- Graceful handling of incomplete commands at EOF
- Clear error messages for syntax errors
- Ability to cancel multi-line input

### 3. History Integration
- Store multi-line commands as single history entries
- Display multi-line commands properly in history
- Handle history navigation during multi-line input

### 4. Performance
- Minimal overhead for single-line commands
- Efficient prompt expansion
- Quick incomplete detection

### 5. Compatibility
- Maintain backward compatibility
- Support existing features (tab completion, key bindings)
- Work with all existing command types

## Testing Strategy

### Unit Tests
1. Test incomplete detection for all control structures
2. Test prompt expansion with all escape sequences
3. Test multi-line string handling
4. Test heredoc detection and processing

### Integration Tests
1. Interactive control structure entry
2. Prompt customization scenarios
3. Edge cases (nested structures, mixed quotes)
4. Signal handling during multi-line input

### User Experience Tests
1. Natural feel for multi-line entry
2. Clear visual feedback (PS2 prompt)
3. Intuitive cancellation (Ctrl-C)
4. Consistent behavior across modes

## Alternatives Considered

### 1. Modify LineEditor Directly
- Pros: More integrated solution
- Cons: Complicates LineEditor, harder to test
- Decision: Keep LineEditor simple, add coordination layer

### 2. Use readline's Multi-line Support
- Pros: Battle-tested implementation
- Cons: Less control, harder to customize
- Decision: Build on existing LineEditor for consistency

### 3. Separate Multi-line Mode
- Pros: Clear separation of concerns
- Cons: Confusing UX, mode switching
- Decision: Seamless multi-line support

## Conclusion

The proposed architecture leverages psh's existing capabilities while adding minimal complexity. By reusing the incomplete detection logic from script mode and building a coordination layer above LineEditor, we can provide a natural multi-line editing experience with customizable prompts.

The phased approach allows for incremental implementation and testing, with basic functionality available quickly and advanced features added over time.