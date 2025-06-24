"""Multi-line input handler for interactive mode.

This module provides multi-line command support for the interactive shell,
allowing users to naturally type control structures across multiple lines.
"""

from typing import Optional, List
from .lexer import tokenize
from .parser import parse, ParseError
from .line_editor import LineEditor
from .prompt import PromptExpander


class MultiLineInputHandler:
    """Handles multi-line command input for interactive mode."""
    
    def __init__(self, line_editor: LineEditor, shell):
        self.line_editor = line_editor
        self.shell = shell
        self.buffer: List[str] = []
        self.in_heredoc = False
        self.heredoc_delimiter = None
        self.heredoc_indent = False  # For <<- style
        self.prompt_expander = PromptExpander(shell)
    
    def read_command(self) -> Optional[str]:
        """Read a complete command, possibly spanning multiple lines."""
        self.buffer = []
        
        while True:
            # Determine prompt
            prompt = self._get_prompt()
            
            # Read one line
            line = self.line_editor.read_line(prompt)
            if line is None:  # EOF
                if self.buffer:
                    print("\npsh: syntax error: unexpected end of file")
                    self.reset()
                return None
            
            # Add line to buffer
            self.buffer.append(line)
            
            # Check if command is complete
            full_command = '\n'.join(self.buffer)
            if self._is_complete_command(full_command):
                self.reset()
                # Process line continuations before returning
                from .input_preprocessing import process_line_continuations
                return process_line_continuations(full_command)
    
    def reset(self):
        """Reset multi-line state."""
        self.buffer = []
        self.in_heredoc = False
        self.heredoc_delimiter = None
        self.heredoc_indent = False
    
    def _get_prompt(self) -> str:
        """Get the appropriate prompt based on current state."""
        if not self.buffer:
            # Primary prompt
            ps1 = self.shell.variables.get('PS1', '\\u@\\h:\\w\\$ ')
            return self.prompt_expander.expand_prompt(ps1)
        else:
            # Continuation prompt
            ps2 = self.shell.variables.get('PS2', '> ')
            return self.prompt_expander.expand_prompt(ps2)
    
    def _is_complete_command(self, command: str) -> bool:
        """Check if command is syntactically complete."""
        if not command.strip():
            return True
        
        # Check for explicit line continuation
        if self._has_line_continuation(command):
            return False
        
        # Check for active heredoc
        if self._has_unclosed_heredoc(command):
            return False
        
        # Check for operators at end of line that require continuation
        # But only if we're not inside [[ ]]
        stripped = command.strip()
        if stripped.endswith(('|', '||', '&&')):
            # Count [[ and ]] to see if we're inside
            double_lbracket_count = command.count('[[')
            double_rbracket_count = command.count(']]')
            if double_lbracket_count == double_rbracket_count:
                # Not inside [[ ]], so operators mean continuation
                return False
            # Inside [[ ]], let the parser decide
        
        
        # Try to tokenize and parse
        try:
            tokens = tokenize(command)
            if not tokens:
                return True
            
            # Check for incomplete expansions in tokens
            for token in tokens:
                if token.type == 'WORD':
                    # Check for unclosed expansions
                    if self._has_unclosed_expansion(token.value):
                        return False
            
            # Try parsing
            parse(tokens)
            return True
            
        except SyntaxError as e:
            # Unterminated string or other tokenization error
            if "Unclosed" in str(e) or "Unterminated" in str(e):
                return False
            # Other tokenization errors are complete but invalid
            return True
            
        except ParseError as e:
            # Check for incomplete constructs
            error_msg = str(e)
            incomplete_patterns = [
                # Updated patterns for human-readable error messages
                "Expected 'do'",
                "Expected 'done'", 
                "Expected 'fi'",
                "Expected 'else'",
                "Expected 'then'",
                "Expected 'esac'",
                "Expected 'in'",
                "Expected 'elif'",
                "Expected '{'",
                "Expected '}'",
                "Expected ')'",
                "Expected ']]'",
                "Expected '('",
                "Expected closing",
                "Unexpected EOF",
                "got end of input",
                "Expected pattern",  # For incomplete case statements
                "Expected test operand",
                # Old patterns for backward compatibility
                "Expected DO",
                "Expected DONE", 
                "Expected FI",
                "Expected ELSE",
                "Expected THEN",
                "Expected ESAC",
                "Expected DOUBLE_RBRACKET",
            ]
            
            for pattern in incomplete_patterns:
                if pattern in error_msg:
                    return False
            
            # Other parse errors mean command is complete but invalid
            return True
    
    def _has_line_continuation(self, command: str) -> bool:
        """Check if command ends with line continuation."""
        # Don't process empty strings
        if not command:
            return False
            
        lines = command.splitlines(keepends=True)
        if not lines:
            return False
        
        # Get the last line (including any trailing newline)
        last_line = lines[-1]
        
        # If there's a newline, check the content before it
        if last_line.endswith('\n'):
            content = last_line[:-1].rstrip()
        else:
            content = last_line.rstrip()
        
        if content.endswith('\\'):
            # Count preceding backslashes
            count = 0
            for i in range(len(content) - 2, -1, -1):
                if content[i] == '\\':
                    count += 1
                else:
                    break
            # Odd number of total backslashes means the last one is not escaped
            return (count % 2) == 0
        
        return False
    
    def _has_unclosed_heredoc(self, command: str) -> bool:
        """Check if command has an unclosed heredoc."""
        import re
        
        # Find all heredoc start markers (<<EOF, <<-EOF, << EOF, etc.)
        # Also handle escaped delimiters like << \EOF
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\\\s*)?(\w+)\2'
        
        lines = command.split('\n')
        heredoc_delimiters = []
        
        for line in lines:
            # Skip if line is inside a heredoc
            if any(d for d in heredoc_delimiters if not d['closed']):
                # Check if this line closes a heredoc
                for delimiter in heredoc_delimiters:
                    if not delimiter['closed']:
                        # For <<- style, strip leading tabs
                        check_line = line.lstrip('\t') if delimiter['strip_tabs'] else line
                        if check_line.rstrip() == delimiter['word']:
                            delimiter['closed'] = True
                            break
            else:
                # Look for new heredoc markers
                for match in re.finditer(heredoc_pattern, line):
                    strip_tabs = bool(match.group(1))  # '-' present
                    has_backslash = bool(match.group(3))  # Escaped delimiter
                    word = match.group(4)
                    heredoc_delimiters.append({
                        'word': word,
                        'strip_tabs': strip_tabs,
                        'closed': False,
                        'escaped': has_backslash
                    })
        
        # Check if any heredocs remain unclosed
        return any(d for d in heredoc_delimiters if not d['closed'])
    
    def _has_unclosed_expansion(self, text: str) -> bool:
        """Check if text contains unclosed expansions."""
        # Track open/close counts for each expansion type
        
        # Command substitution $()
        depth = 0
        i = 0
        while i < len(text):
            if i + 1 < len(text) and text[i:i+2] == '$(':
                depth += 1
                i += 2
            elif text[i] == ')' and depth > 0:
                depth -= 1
                i += 1
            else:
                i += 1
        if depth > 0:
            return True
        
        # Arithmetic expansion $(())
        i = 0
        while i < len(text):
            if i + 2 < len(text) and text[i:i+3] == '$((': 
                # Find the closing ))
                j = i + 3
                paren_count = 2
                while j < len(text) and paren_count > 0:
                    if text[j] == '(':
                        paren_count += 1
                    elif text[j] == ')':
                        paren_count -= 1
                    j += 1
                if paren_count > 0:
                    return True
                i = j
            else:
                i += 1
        
        # Brace expansion {...}
        brace_depth = 0
        in_brace_expansion = False
        i = 0
        while i < len(text):
            if text[i] == '{':
                # Check if this looks like a brace expansion
                # Look for comma or .. sequence
                j = i + 1
                while j < len(text) and text[j] not in '{}':
                    if text[j] == ',' or (j + 1 < len(text) and text[j:j+2] == '..'):
                        in_brace_expansion = True
                        break
                    j += 1
                if in_brace_expansion:
                    brace_depth += 1
                i += 1
            elif text[i] == '}' and brace_depth > 0:
                brace_depth -= 1
                if brace_depth == 0:
                    in_brace_expansion = False
                i += 1
            else:
                i += 1
        if brace_depth > 0:
            return True
        
        # Backtick command substitution
        backtick_count = text.count('`')
        if backtick_count % 2 != 0:
            return True
        
        return False
