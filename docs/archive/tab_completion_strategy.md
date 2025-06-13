# Tab Completion Strategy for psh

## Overview
Tab completion is a critical usability feature for any shell. This document outlines a strategy for implementing file/directory completion in psh.

## Implementation Strategy

### 1. Terminal Setup
- **Raw Mode**: Put terminal in raw mode to capture individual keystrokes
- **termios**: Use Python's termios module to manage terminal settings
- **Restore on Exit**: Ensure terminal settings are restored on exit/error

### 2. Input Handling Architecture
Replace simple input() with a custom line editor:
```python
class LineEditor:
    def __init__(self):
        self.buffer = []
        self.cursor_pos = 0
        self.history = []
        self.completion_state = None
    
    def read_line(self) -> str:
        # Handle each keystroke
        # Return complete line on Enter
```

### 3. Tab Detection and Processing
```python
def handle_keystroke(self, char):
    if char == '\t':  # Tab key
        self.handle_tab_completion()
    elif char == '\n':  # Enter
        return self.get_line()
    elif char == '\x7f':  # Backspace
        self.handle_backspace()
    # ... other special keys
```

### 4. Completion Logic
```python
def handle_tab_completion(self):
    # 1. Extract current word at cursor
    current_word = self.get_current_word()
    
    # 2. Determine completion context
    if self.is_first_word():
        # Complete commands (later feature)
        candidates = self.get_command_completions(current_word)
    else:
        # Complete files/directories
        candidates = self.get_path_completions(current_word)
    
    # 3. Apply completion
    if len(candidates) == 1:
        self.complete_word(candidates[0])
    elif len(candidates) > 1:
        # Show options or cycle through them
        self.show_completions(candidates)
```

### 5. Path Completion Implementation
```python
def get_path_completions(self, partial_path: str) -> List[str]:
    # Handle different cases:
    # 1. Absolute paths (/usr/...)
    # 2. Relative paths (./foo/...)
    # 3. Home directory (~/....)
    # 4. Plain filenames
    
    if '/' in partial_path:
        dirname, basename = os.path.split(partial_path)
        search_dir = dirname or '.'
    else:
        search_dir = '.'
        basename = partial_path
    
    # Get matching entries
    try:
        entries = os.listdir(search_dir)
        matches = [e for e in entries if e.startswith(basename)]
        
        # Add / suffix for directories
        results = []
        for match in matches:
            full_path = os.path.join(search_dir, match)
            if os.path.isdir(full_path):
                results.append(match + '/')
            else:
                results.append(match)
        
        return sorted(results)
    except OSError:
        return []
```

### 6. Common Prefix Extraction
When multiple matches exist, complete to the longest common prefix:
```python
def find_common_prefix(candidates: List[str]) -> str:
    if not candidates:
        return ""
    
    # Use os.path.commonprefix or implement manually
    prefix = candidates[0]
    for candidate in candidates[1:]:
        while not candidate.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                break
    return prefix
```

### 7. Display Options
When multiple completions exist:
```python
def show_completions(self, candidates: List[str]):
    if len(candidates) > self.MAX_DISPLAY:
        print(f"\nDisplay all {len(candidates)} possibilities? (y/n)")
        if self.get_confirmation():
            self.display_in_columns(candidates)
    else:
        self.display_in_columns(candidates)
    
    # Redraw current line
    self.redraw_line()
```

### 8. Edge Cases to Handle
1. **Quoted Paths**: Handle completion within quotes
   ```bash
   $ cat "my fi<TAB>  # Should complete to "my file.txt"
   ```

2. **Escaped Spaces**: Handle backslash-escaped spaces
   ```bash
   $ cat my\ fi<TAB>  # Should complete to my\ file.txt
   ```

3. **Special Characters**: Properly escape special chars in completions
   ```bash
   $ cat file<TAB>  # If "file&name" exists, complete to file\&name
   ```

4. **Hidden Files**: Decide whether to include dot files
   - Include if partial path starts with '.'
   - Otherwise exclude

5. **Symbolic Links**: Show link targets or treat as files/dirs?

### 9. Integration Points

1. **Tokenizer Integration**: 
   - Need to understand where we are in the command line
   - Reuse tokenizer logic to identify current token

2. **Parser Context**:
   - Know if we're completing a command vs argument
   - Handle redirect targets differently

3. **Variable Expansion**:
   - Complete after $ for variables (future feature)
   - Handle ${VA<TAB> → ${VAR}

### 10. Testing Strategy

1. **Unit Tests**:
   - Test path completion logic
   - Test common prefix finding
   - Test escape handling

2. **Integration Tests**:
   - Test with actual filesystem
   - Test interactive behavior (using pty)

3. **Manual Testing Scenarios**:
   - Empty directory
   - Directory with many files
   - Files with spaces/special chars
   - Nested directories
   - Permission-denied directories

## Implementation Phases

### Phase 1: Basic Infrastructure
1. Implement LineEditor class
2. Add raw mode terminal handling
3. Basic keystroke processing
4. Line editing (insert, delete, cursor movement)

### Phase 2: Simple Completion
1. Tab detection
2. Current word extraction
3. Basic file/directory completion
4. Single match completion

### Phase 3: Advanced Features
1. Multiple match handling
2. Common prefix completion
3. Completion display
4. Quoted path handling

### Phase 4: Polish
1. Escape character handling
2. Performance optimization
3. Configurable behavior
4. Command completion (bonus)

## Code Structure

```
tab_completion.py
├── class TerminalManager    # Terminal mode handling
├── class LineEditor         # Main line editing logic
├── class CompletionEngine   # Completion logic
└── class DisplayFormatter   # Formatting completion output
```

## Example Usage

```python
# In simple_shell.py
def main():
    if sys.stdin.isatty():
        # Interactive mode with completion
        line_editor = LineEditor()
        while True:
            try:
                line = line_editor.read_line()
                if line is None:  # EOF
                    break
                execute_line(line)
            except KeyboardInterrupt:
                print("^C")
                continue
    else:
        # Non-interactive mode
        for line in sys.stdin:
            execute_line(line.strip())
```

## Dependencies
- `termios` (Unix/Linux/macOS)
- `tty` (for raw mode)
- Consider `readline` library as alternative (but less educational)

## Platform Considerations
- Primary target: Unix-like systems (Linux, macOS)
- Windows would require different approach (msvcrt or windows-curses)