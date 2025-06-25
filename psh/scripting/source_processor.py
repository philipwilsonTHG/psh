"""Source file and command buffer processing."""
import sys
from typing import Optional
from .base import ScriptComponent
from ..lexer import tokenize
from ..parser import parse, ParseError
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
            if line is None:  # EOF
                # Execute any remaining command in buffer
                if command_buffer.strip():
                    exit_code = self._execute_buffered_command(
                        command_buffer, input_source, command_start_line, add_to_history
                    )
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
                
                # Apply history expansion for completeness testing
                if hasattr(self.shell, 'history_expander'):
                    expanded_test = self.shell.history_expander.expand_history(test_command)
                    if expanded_test is not None:
                        test_command = expanded_test
                
                # Check if command is complete by trying to parse it
                try:
                    tokens = tokenize(test_command)
                    # Try parsing to see if command is complete
                    parse(tokens)
                    # If parsing succeeds, execute the command
                    exit_code = self._execute_buffered_command(
                        command_buffer.rstrip('\n'), input_source, command_start_line, add_to_history
                    )
                    # Reset buffer for next command
                    command_buffer = ""
                    command_start_line = 0
                except ParseError as e:
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
                        exit_code = 1
                        self.state.last_exit_code = 1
        
        return exit_code
    
    def _is_incomplete_command(self, parse_error: ParseError) -> bool:
        """Check if a parse error indicates an incomplete command."""
        error_msg = str(parse_error)
        
        # Updated patterns to match the new human-readable error messages
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
                    # History expansion failed
                    self.state.last_exit_code = 1
                    return 1
                command_string = expanded_command
            
            tokens = tokenize(command_string)
            
            # Debug: Print tokens if requested
            if self.state.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                from ..utils.token_formatter import TokenFormatter
                print(TokenFormatter.format(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Expand aliases
            tokens = self.shell.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Debug: Print AST if requested
            if self.state.debug_ast:
                print("=== AST Debug Output ===", file=sys.stderr)
                from ..visitor import DebugASTVisitor
                debug_visitor = DebugASTVisitor()
                print(debug_visitor.visit(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
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
            if add_to_history and command_string.strip():
                self.shell.interactive_manager.history_manager.add_to_history(command_string.strip())
            
            # Increment command number for successful parse
            self.state.command_number += 1
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.shell.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                try:
                    # Collect here documents if any
                    self.shell.io_manager.collect_heredocs(ast)
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
            # Enhanced error message with location
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
        except Exception as e:
            # Enhanced error message with location  
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: unexpected error: {e}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
