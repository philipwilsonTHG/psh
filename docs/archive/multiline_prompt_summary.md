# Multi-line Commands and Prompt Customization - Summary

## Problem Statement

psh currently lacks two important interactive features:
1. **Multi-line commands**: Users cannot naturally type control structures across multiple lines
2. **Prompt customization**: No support for PS0/PS1/PS2 variables or prompt expansion

## Recommended Solution

### Core Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Interactive   │────▶│ MultiLineInputHandler│────▶│ LineEditor  │
│      Loop       │     │                      │     │             │
└─────────────────┘     │ • Manages state      │     │ • Single    │
                        │ • Detects incomplete │     │   line      │
                        │ • Switches prompts   │     │   input     │
                        │ • Buffers lines      │     │             │
                        └──────────────────────┘     └─────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Parser/Tokenizer   │
                        │                      │
                        │ • Already detects    │
                        │   incomplete cmds    │
                        └──────────────────────┘
```

### Key Design Decisions

1. **Reuse Existing Logic**: The parser already detects incomplete commands for script mode - reuse this for interactive mode

2. **Layer Above LineEditor**: Add MultiLineInputHandler as a coordination layer rather than modifying LineEditor

3. **Prompt Variables**: Store PS0/PS1/PS2 as shell variables with sensible defaults

4. **State Management**: Track multi-line state (buffer, heredoc, quotes) in the handler

### Implementation Approach

#### Phase 1: Basic Multi-line Support (1-2 days)
```python
# Simple working example
psh$ if [ -f file.txt ]; then
> echo "File exists"
> fi
```
- Implement MultiLineInputHandler
- Detect incomplete commands
- Show PS2 for continuation
- Handle basic control structures

#### Phase 2: Prompt Customization (1-2 days)
```python
# Customizable prompts
psh$ PS1='[\u@\h \W]$ '
[user@host psh]$ PS2='... '
[user@host psh]$ for i in 1 2 3; do
... echo $i
... done
```
- Add PS0/PS1/PS2 variables
- Implement prompt expansion (\u, \h, \w, etc.)
- Support time/date/exit status

#### Phase 3: Advanced Features (Optional)
- Command substitution in prompts
- ANSI colors in prompts  
- Width-aware formatting
- Custom prompt functions

### Special Cases to Handle

1. **Heredocs**
   ```bash
   cat << EOF
   > line 1
   > line 2
   > EOF
   ```

2. **Line Continuation**
   ```bash
   echo "long line" \
   > "continued here"
   ```

3. **Unterminated Quotes**
   ```bash
   echo "multi
   > line
   > string"
   ```

### Benefits

1. **Natural Usage**: Users can type complex commands as they would in bash
2. **Visual Feedback**: PS2 clearly indicates more input is needed
3. **Customization**: Users can personalize their prompt
4. **Educational**: Shows how shells handle multi-line input

### Minimal Viable Implementation

```python
class MultiLineInputHandler:
    def read_command(self):
        buffer = []
        while True:
            # Show PS1 or PS2
            prompt = self.get_prompt(buffer)
            line = self.line_editor.read_line(prompt)
            
            if line is None:  # EOF
                return None
                
            buffer.append(line)
            
            # Check if complete
            command = '\n'.join(buffer)
            if self.is_complete(command):
                return command
    
    def is_complete(self, command):
        try:
            parse(tokenize(command))
            return True
        except ParseError as e:
            # Check for "Expected X" errors
            if "Expected" in str(e):
                return False
            return True  # Other errors = complete
```

### Testing Strategy

1. **Unit tests**: Incomplete detection for all constructs
2. **Integration tests**: Multi-line entry scenarios  
3. **UX tests**: Natural feel, clear feedback

### Risk Mitigation

- **Backward compatibility**: Single-line commands work identically
- **Graceful degradation**: Ctrl-C cancels multi-line input
- **Clear errors**: Helpful messages for syntax errors

## Conclusion

This architecture provides multi-line command support and prompt customization with minimal changes to existing code. By reusing the parser's incomplete detection and layering above LineEditor, we can deliver these features incrementally while maintaining psh's educational clarity.