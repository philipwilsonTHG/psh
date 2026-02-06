"""Source file and command buffer processing."""
import sys
from typing import Optional
from .base import ScriptComponent
from ..lexer import tokenize, LexerError
from ..parser import parse, parse_with_heredocs, ParseError
from ..ast_nodes import TopLevel


class SourceProcessor(ScriptComponent):
    """Processes input from various sources (files, strings, stdin)."""
    
    def execute(self, input_source, add_to_history: bool = True) -> int:
        """Execute from an input source."""
        return self.execute_from_source(input_source, add_to_history)
    
    def execute_from_source(self, input_source, add_to_history: bool = True) -> int:
        """Execute commands from an input source with enhanced processing."""
        exit_code = 0
        command_buffer = ""
        command_start_line = 0
        
        # For validation mode, collect all issues across the entire script
        if self.shell.validate_only:
            from ..visitor import EnhancedValidatorVisitor
            self.validation_visitor = EnhancedValidatorVisitor()
        else:
            self.validation_visitor = None
        
        while True:
            line = input_source.read_line()
            if self.state.options.get('debug-exec', False):
                print(f"DEBUG source_processor: read line: {repr(line)}", file=sys.stderr)
            if line is None:  # EOF
                # Execute any remaining command in buffer
                if command_buffer.strip():
                    exit_code = self._execute_buffered_command(
                        command_buffer, input_source, command_start_line, add_to_history
                    )
                    # In non-interactive mode with errexit, exit on error
                    if exit_code != 0 and not input_source.is_interactive() and self.state.options.get('errexit', False):
                        if self.state.options.get('debug-exec', False):
                            print(f"DEBUG: Exiting due to errexit with code {exit_code}", file=sys.stderr)
                        return exit_code
                # In validation mode, show final summary at end
                if self.validation_visitor:
                    print(self.validation_visitor.get_summary())
                    # Return exit code based on errors
                    error_count = sum(1 for i in self.validation_visitor.issues 
                                    if i.severity.value == 'error')
                    exit_code = 1 if error_count > 0 else 0
                break
            
            # Skip empty lines when no command is being built
            if not command_buffer and not line.strip():
                continue
            
            # Skip comment lines when no command is being built
            if not command_buffer and line.strip().startswith('#'):
                continue
            
            # Note: Line continuation handling is now done in preprocessing
            
            # Add current line to buffer
            if not command_buffer:
                command_start_line = input_source.get_line_number()
            # Add line to buffer with proper spacing
            if command_buffer and not command_buffer.endswith('\n'):
                command_buffer += '\n'
            command_buffer += line
            
            # Try to parse and execute the command
            if command_buffer.strip():
                # Process line continuations and history expansion before testing completeness
                test_command = command_buffer
                from ..input_preprocessing import process_line_continuations
                test_command = process_line_continuations(test_command)
                
                # Apply history expansion for completeness testing (don't print)
                if hasattr(self.shell, 'history_expander'):
                    expanded_test = self.shell.history_expander.expand_history(test_command, print_expansion=False)
                    if expanded_test is not None:
                        test_command = expanded_test
                
                # Check for unclosed heredocs and collect content if needed
                # Use the shell's method which properly handles arithmetic expressions
                if self.shell._contains_heredoc(test_command) and self._has_unclosed_heredoc(test_command):
                    # Continue reading lines to complete heredocs
                    command_buffer = self._collect_heredoc_content(command_buffer, input_source)
                    if command_buffer is None:  # EOF while reading heredoc
                        break
                    # Re-process the complete command
                    test_command = command_buffer
                    test_command = process_line_continuations(test_command)
                    if hasattr(self.shell, 'history_expander'):
                        expanded_test = self.shell.history_expander.expand_history(test_command, print_expansion=False)
                        if expanded_test is not None:
                            test_command = expanded_test
                
                # Check if command contains history expansion - if so, treat as complete
                import re
                history_pattern = r'(?:^|\s)!(?:!|[0-9]+|-[0-9]+|[a-zA-Z][a-zA-Z0-9]*|\?[^?]*\?)(?:\s|$)'
                if re.search(history_pattern, test_command):
                    # Skip parse testing for history expansions - let execution handle them
                    exit_code = self._execute_buffered_command(
                        command_buffer.rstrip('\n'), input_source, command_start_line, add_to_history
                    )
                    # Reset buffer for next command
                    command_buffer = ""
                    command_start_line = 0
                    # In non-interactive mode with errexit, exit on error
                    if exit_code != 0 and not input_source.is_interactive() and self.state.options.get('errexit', False):
                        if self.state.options.get('debug-exec', False):
                            print(f"DEBUG: Exiting due to errexit with code {exit_code}", file=sys.stderr)
                        return exit_code
                else:
                    # Check if command is complete by trying to parse it
                    try:
                        tokens = tokenize(test_command, shell_options=self.state.options)
                        # Try parsing to see if command is complete
                        from ..parser import Parser
                        parser = Parser(tokens, source_text=test_command)
                        parser.parse()
                        # If parsing succeeds, execute the command
                        exit_code = self._execute_buffered_command(
                            command_buffer.rstrip('\n'), input_source, command_start_line, add_to_history
                        )
                        # Reset buffer for next command
                        command_buffer = ""
                        command_start_line = 0
                        # In non-interactive mode with errexit, exit on error
                        if exit_code != 0 and not input_source.is_interactive() and self.state.options.get('errexit', False):
                            if self.state.options.get('debug-exec', False):
                                print(f"DEBUG: Exiting due to errexit with code {exit_code}", file=sys.stderr)
                            return exit_code
                    except (ParseError, LexerError, SyntaxError) as e:
                        # Check if this is an incomplete command
                        if self._is_incomplete_command(e):
                            # Command is incomplete, continue reading
                            continue
                        else:
                            # It's a real parse error, report it and reset
                            filename = input_source.get_name() if hasattr(input_source, 'get_name') else 'stdin'
                            print(f"{filename}:{command_start_line}: {e}", file=sys.stderr)
                            command_buffer = ""
                            command_start_line = 0
                            exit_code = 2  # Bash uses exit code 2 for syntax errors
                            self.state.last_exit_code = 2
                            
                            # In non-interactive mode, exit immediately on parse errors
                            if not input_source.is_interactive():
                                return exit_code
        
        return exit_code
    
    def _is_incomplete_command(self, error) -> bool:
        """Check if a parse or lexer error indicates an incomplete command."""
        error_msg = str(error)
        
        # Handle lexer errors from incomplete constructs
        lexer_incomplete_patterns = [
            "Unclosed parenthesis",
            "Unclosed double parentheses", 
            "Unclosed arithmetic expansion",
            "Unclosed brace",
            "Unclosed quote",
            "Unclosed single quote",
            "Unclosed double quote",
            "Unclosed \" quote at position",
            "Unclosed ' quote at position"
        ]
        
        for pattern in lexer_incomplete_patterns:
            if pattern in error_msg:
                return True
        
        # Handle parser errors - updated patterns to match the new human-readable error messages
        incomplete_patterns = [
            # Control structure keywords
            ("Expected 'do'", "got end of input"),
            ("Expected 'done'", "got end of input"),
            ("Expected 'fi'", "got end of input"),
            ("Expected 'then'", "got end of input"),
            ("Expected 'in'", "got end of input"),
            ("Expected 'esac'", "got end of input"),
            ("Expected 'else'", "got end of input"),
            ("Expected 'elif'", "got end of input"),
            
            # Function and compound commands
            ("Expected '{'", "got end of input"),
            ("Expected '}'", "got end of input"),
            ("Expected '}' to end compound command", None),
            
            # Parentheses and brackets
            ("Expected ')'", "got end of input"),
            ("Expected ']]'", "got end of input"),
            ("Expected '('", "got end of input"),
            ("Expected '[['", "got end of input"),
            
            # Test expressions
            ("Expected test operand", "got end of input"),
            ("Expected test operand", None),
            
            # Redirections
            ("Expected delimiter after here document", "got end of input"),
            ("Expected string after here string", "got end of input"),
            
            # Commands
            ("Expected command", "got end of input"),
            
            # Case patterns
            ("Expected pattern in case statement", "got end of input"),
            ("Expected pattern in case statement", None),  # When no "got" part
            
            # New TokenType-based patterns from ParserContext (case sensitive)
            ("Expected TokenType.DO", "got TokenType.EOF"),
            ("Expected TokenType.DONE", "got TokenType.EOF"),
            ("Expected TokenType.FI", "got TokenType.EOF"),
            ("Expected TokenType.THEN", "got TokenType.EOF"),
            ("Expected TokenType.IN", "got TokenType.EOF"),
            ("Expected TokenType.ESAC", "got TokenType.EOF"),
            ("Expected TokenType.RPAREN", "got TokenType.EOF"),
            ("Expected TokenType.DOUBLE_RBRACKET", "got TokenType.EOF"),
            ("Expected TokenType.LBRACE", "got TokenType.EOF"),
            ("Expected TokenType.RBRACE", "got TokenType.EOF"),
            ("Expected TokenType.LPAREN", "got TokenType.EOF"),
            ("Expected TokenType.ELSE", "got TokenType.EOF"),
            ("Expected TokenType.ELIF", "got TokenType.EOF"),
            
            # Lowercase variants (in case error messages are normalized)
            ("expected tokentype.do", "got tokentype.eof"),
            ("expected tokentype.done", "got tokentype.eof"),
            ("expected tokentype.fi", "got tokentype.eof"),
            ("expected tokentype.then", "got tokentype.eof"),
            ("expected tokentype.in", "got tokentype.eof"),
            ("expected tokentype.esac", "got tokentype.eof"),
            ("expected tokentype.rparen", "got tokentype.eof"),
            ("expected tokentype.double_rbracket", "got tokentype.eof"),
            ("expected tokentype.lbrace", "got tokentype.eof"),
            ("expected tokentype.rbrace", "got tokentype.eof"),
            ("expected tokentype.lparen", "got tokentype.eof"),
            ("expected tokentype.else", "got tokentype.eof"),
            ("expected tokentype.elif", "got tokentype.eof"),
            
            # Old patterns for backward compatibility (in case some weren't updated)
            ("Expected DO", "got EOF"),
            ("Expected DONE", "got EOF"),
            ("Expected FI", "got EOF"),
            ("Expected THEN", "got EOF"),
            ("Expected IN", "got EOF"),
            ("Expected ESAC", "got EOF"),
            ("Expected RPAREN", "got EOF"),
            ("Expected DOUBLE_RBRACKET", None),
        ]
        
        for expected, got in incomplete_patterns:
            if expected in error_msg:
                if got is None or got in error_msg:
                    return True
        
        return False
    
    def _execute_buffered_command(self, command_string: str, input_source, 
                                  start_line: int, add_to_history: bool) -> int:
        """Execute a buffered command with enhanced error reporting."""
        # Skip empty commands and comments
        if not command_string.strip() or command_string.strip().startswith('#'):
            return 0
        
        # Update LINENO special variable with current line number
        if start_line > 0:
            self.shell.state.scope_manager.set_current_line_number(start_line)
        
        # Verbose mode: echo input lines as they are read
        if self.state.options.get('verbose', False):
            # Echo the command to stderr before execution
            print(command_string, file=sys.stderr)
        
        try:
            # Process line continuations first
            from ..input_preprocessing import process_line_continuations
            command_string = process_line_continuations(command_string)
            
            # Perform history expansion before tokenization
            if hasattr(self.shell, 'history_expander'):
                expanded_command = self.shell.history_expander.expand_history(command_string)
                if expanded_command is None:
                    # History expansion failed - this is the proper error path
                    self.state.last_exit_code = 1
                    return 1
                command_string = expanded_command
            
            tokens = tokenize(command_string, shell_options=self.state.options)

            # Debug: Print tokens if requested
            if self.state.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                from ..utils.token_formatter import TokenFormatter
                print(TokenFormatter.format(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Note: Alias expansion now happens during execution phase for proper precedence
            
            # Check if command contains heredocs and parse accordingly
            if self.shell._contains_heredoc(command_string):
                # Use the new lexer with heredoc support
                from ..lexer import tokenize_with_heredocs
                tokens, heredoc_map = tokenize_with_heredocs(command_string, strict=self.state.options.get('posix', False),
                                                              shell_options=self.state.options)
                # Parse with heredoc map
                from ..parser import parse_with_heredocs
                ast = parse_with_heredocs(tokens, heredoc_map)
            else:
                # Parse with source text for better error messages and shell configuration
                parser = self.shell.create_parser(tokens, source_text=command_string)
                ast = parser.parse()
            
            # Debug: Print AST if requested
            if self.state.debug_ast:
                self.shell._print_ast_debug(ast)
            
            # Validation mode - analyze AST without executing
            if self.shell.validate_only:
                # Use the shared validator instance
                if self.validation_visitor:
                    self.validation_visitor.visit(ast)
                else:
                    # Fallback for single command validation
                    from ..visitor import EnhancedValidatorVisitor
                    validator = EnhancedValidatorVisitor()
                    validator.visit(ast)
                    print(validator.get_summary())
                    error_count = sum(1 for i in validator.issues 
                                    if i.severity.value == 'error')
                    return 1 if error_count > 0 else 0
                
                # Don't execute in validation mode
                return 0
            
            # NoExec mode - parse and validate but don't execute
            if self.state.options.get('noexec', False):
                # Successfully parsed, so syntax is valid
                return 0
            
            # Add to history if requested (for interactive or testing)
            # Don't add history expansion commands to history
            if add_to_history and command_string.strip():
                import re
                history_pattern = r'(?:^|\s)!(?:!|[0-9]+|-[0-9]+|[a-zA-Z][a-zA-Z0-9]*|\?[^?]*\?)(?:\s|$)'
                if not re.search(history_pattern, command_string):
                    self.shell.interactive_manager.history_manager.add_to_history(command_string.strip())
            
            # Increment command number for successful parse
            self.state.command_number += 1
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.shell.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                try:
                    # Heredoc content is now pre-populated during parsing
                    exit_code = self.shell.execute_command_list(ast)
                    return exit_code
                except Exception as e:
                    # Import the exceptions properly
                    from ..core.exceptions import LoopBreak, LoopContinue
                    if isinstance(e, (LoopBreak, LoopContinue)):
                        # Break/continue outside of loops is an error
                        stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
                        print(f"{stmt_name}: only meaningful in a `for' or `while' loop", 
                              file=sys.stderr)
                        return 1
                    raise
        except ParseError as e:
            # Check if error already has context, otherwise add location
            if e.error_context and e.error_context.source_line:
                # Error already has full context, just print it
                print(f"psh: {str(e)}", file=sys.stderr)
            else:
                # Add location prefix to error
                location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
                print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.state.last_exit_code = 2  # Bash uses exit code 2 for syntax errors
            return 2
        except Exception as e:
            # Enhanced error message with location  
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: unexpected error: {e}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
    
    def _has_unclosed_heredoc(self, command: str) -> bool:
        """Check if command has an unclosed heredoc."""
        import re
        
        # Find all heredoc start markers (<<EOF, <<-EOF, << EOF, etc.)
        # But exclude << inside arithmetic expressions, command substitutions, etc.
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
                # Look for new heredoc markers, but exclude ones inside expansions
                potential_matches = list(re.finditer(heredoc_pattern, line))
                for match in potential_matches:
                    # Check if this << is inside an arithmetic expression or command substitution
                    start_pos = match.start()
                    if self._is_inside_expansion(line, start_pos):
                        continue  # Skip this match
                    
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
    
    def _collect_heredoc_content(self, command_buffer: str, input_source) -> Optional[str]:
        """Collect heredoc content from input source until all delimiters are satisfied."""
        import re
        
        # Extract heredoc information from current command
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\\\s*)?(\w+)\2'
        lines = command_buffer.split('\n')
        heredoc_delimiters = []
        
        # Find all heredoc start markers in the current command
        for line in lines:
            for match in re.finditer(heredoc_pattern, line):
                strip_tabs = bool(match.group(1))  # '-' present
                quoted = bool(match.group(2))      # Delimiter is quoted
                has_backslash = bool(match.group(3))  # Escaped delimiter
                word = match.group(4)
                heredoc_delimiters.append({
                    'word': word,
                    'strip_tabs': strip_tabs,
                    'quoted': quoted,
                    'closed': False,
                    'escaped': has_backslash
                })
        
        # If no heredocs found, return current buffer
        if not heredoc_delimiters:
            return command_buffer
        
        # Continue reading lines until all heredocs are closed
        result_buffer = command_buffer
        
        while True:
            # Check if all heredocs are closed
            if all(d['closed'] for d in heredoc_delimiters):
                break
            
            # Read next line
            line = input_source.read_line()
            if line is None:  # EOF
                return None
            
            # Add line to buffer
            if not result_buffer.endswith('\n'):
                result_buffer += '\n'
            result_buffer += line
            
            # Check if this line closes any open heredocs
            for delimiter in heredoc_delimiters:
                if not delimiter['closed']:
                    # For <<- style, strip leading tabs from delimiter check
                    check_line = line.lstrip('\t') if delimiter['strip_tabs'] else line
                    if check_line.rstrip() == delimiter['word']:
                        delimiter['closed'] = True
                        break
        
        return result_buffer
    
    def _is_inside_expansion(self, line: str, position: int) -> bool:
        """Check if the position is inside an arithmetic expression or command substitution."""
        # Check for arithmetic expressions $((..))
        arith_start = -1
        paren_depth = 0
        i = 0
        while i < len(line):
            if i + 2 < len(line) and line[i:i+3] == '$((': 
                if i <= position:
                    arith_start = i
                    paren_depth = 2
                    i += 3
                    continue
                else:
                    break
            elif line[i] == '(' and arith_start >= 0:
                paren_depth += 1
            elif line[i] == ')' and arith_start >= 0:
                paren_depth -= 1
                if paren_depth == 0:
                    # End of arithmetic expression
                    if arith_start <= position <= i:
                        return True
                    arith_start = -1
            i += 1
        
        # Check for command substitution $(..)
        cmd_sub_start = -1
        paren_depth = 0
        i = 0
        while i < len(line):
            if i + 1 < len(line) and line[i:i+2] == '$(':
                if i <= position:
                    cmd_sub_start = i
                    paren_depth = 1
                    i += 2
                    continue
                else:
                    break
            elif line[i] == '(' and cmd_sub_start >= 0:
                paren_depth += 1
            elif line[i] == ')' and cmd_sub_start >= 0:
                paren_depth -= 1
                if paren_depth == 0:
                    # End of command substitution
                    if cmd_sub_start <= position <= i:
                        return True
                    cmd_sub_start = -1
            i += 1
        
        # Check for backtick command substitution
        backtick_start = -1
        i = 0
        while i < len(line):
            if line[i] == '`':
                if backtick_start == -1:
                    if i <= position:
                        backtick_start = i
                else:
                    # End of backtick substitution
                    if backtick_start <= position <= i:
                        return True
                    backtick_start = -1
            i += 1
        
        return False
    
    def _extract_heredoc_content(self, command_text: str) -> dict:
        """Extract heredoc content from complete command text and return a mapping."""
        import re
        
        heredoc_map = {}
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\\\s*)?(\w+)\2'
        lines = command_text.split('\n')
        
        # Track delimiters and their content
        current_heredocs = []  # Stack of active heredocs
        line_idx = 0
        
        while line_idx < len(lines):
            line = lines[line_idx]
            
            # Check if this line closes any active heredocs
            if current_heredocs:
                for i in range(len(current_heredocs) - 1, -1, -1):  # Check in reverse order (LIFO)
                    delimiter_info = current_heredocs[i]
                    # For <<- style, strip leading tabs from delimiter check
                    check_line = line.lstrip('\t') if delimiter_info['strip_tabs'] else line
                    if check_line.rstrip() == delimiter_info['word']:
                        # Found closing delimiter
                        delimiter_info['end_line'] = line_idx
                        # Extract content between start and end
                        content_lines = lines[delimiter_info['start_line'] + 1:line_idx]
                        if delimiter_info['strip_tabs']:
                            # Strip leading tabs from content for <<-
                            content_lines = [l.lstrip('\t') for l in content_lines]
                        content = '\n'.join(content_lines)
                        if content_lines:  # Add final newline if there was content
                            content += '\n'
                        heredoc_map[delimiter_info['delimiter']] = {
                            'content': content,
                            'quoted': delimiter_info['quoted'],
                            'strip_tabs': delimiter_info['strip_tabs'],
                            'delimiter': delimiter_info['delimiter']
                        }
                        current_heredocs.pop(i)
                        break
            
            # Look for new heredoc markers in this line
            potential_matches = list(re.finditer(heredoc_pattern, line))
            for match in potential_matches:
                # Check if this << is inside an arithmetic expression or command substitution
                start_pos = match.start()
                if self._is_inside_expansion(line, start_pos):
                    continue  # Skip this match
                
                strip_tabs = bool(match.group(1))  # '-' present
                quoted = bool(match.group(2))      # Delimiter is quoted
                has_backslash = bool(match.group(3))  # Escaped delimiter
                word = match.group(4)
                
                current_heredocs.append({
                    'word': word,
                    'delimiter': word,  # Keep original for mapping
                    'strip_tabs': strip_tabs,
                    'quoted': quoted,
                    'start_line': line_idx,
                    'escaped': has_backslash
                })
            
            line_idx += 1
        
        return heredoc_map
    
    def _remove_heredoc_content_from_command(self, command_text: str) -> str:
        """Remove heredoc content lines from command text, leaving only the shell commands."""
        import re
        
        heredoc_pattern = r'<<(-?)\s*([\'"]?)(\\\s*)?(\w+)\2'
        lines = command_text.split('\n')
        result_lines = []
        
        # Track delimiters and skip their content
        current_heredocs = []
        line_idx = 0
        
        while line_idx < len(lines):
            line = lines[line_idx]
            skip_line = False
            
            # Check if this line closes any active heredocs
            if current_heredocs:
                for i in range(len(current_heredocs) - 1, -1, -1):
                    delimiter_info = current_heredocs[i]
                    # For <<- style, strip leading tabs from delimiter check
                    check_line = line.lstrip('\t') if delimiter_info['strip_tabs'] else line
                    if check_line.rstrip() == delimiter_info['word']:
                        # Found closing delimiter - skip this line and close heredoc
                        current_heredocs.pop(i)
                        skip_line = True
                        break
                
                # If we're inside a heredoc and this isn't a closing delimiter, skip content
                if current_heredocs and not skip_line:
                    skip_line = True
            
            # Look for new heredoc markers in this line
            if not skip_line:
                potential_matches = list(re.finditer(heredoc_pattern, line))
                for match in potential_matches:
                    # Check if this << is inside an arithmetic expression or command substitution
                    start_pos = match.start()
                    if self._is_inside_expansion(line, start_pos):
                        continue  # Skip this match
                    
                    strip_tabs = bool(match.group(1))
                    word = match.group(4)
                    current_heredocs.append({
                        'word': word,
                        'strip_tabs': strip_tabs
                    })
                # Keep this line since it contains the command with heredoc redirect
                result_lines.append(line)
            
            line_idx += 1
        
        return '\n'.join(result_lines)
