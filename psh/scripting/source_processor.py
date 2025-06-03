"""Source file and command buffer processing."""
import sys
from typing import Optional
from .base import ScriptComponent
from ..tokenizer import tokenize
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
        
        while True:
            line = input_source.read_line()
            if line is None:  # EOF
                # Execute any remaining command in buffer
                if command_buffer.strip():
                    exit_code = self._execute_buffered_command(
                        command_buffer, input_source, command_start_line, add_to_history
                    )
                break
            
            # Skip empty lines when no command is being built
            if not command_buffer and not line.strip():
                continue
            
            # Skip comment lines when no command is being built
            if not command_buffer and line.strip().startswith('#'):
                continue
            
            # Handle line continuation (backslash at end)
            if line.endswith('\\'):
                # Remove the backslash and add to buffer
                if not command_buffer:
                    command_start_line = input_source.get_line_number()
                command_buffer += line[:-1] + ' '
                continue
            
            # Add current line to buffer
            if not command_buffer:
                command_start_line = input_source.get_line_number()
            # Add line to buffer with proper spacing
            if command_buffer and not command_buffer.endswith('\n'):
                command_buffer += '\n'
            command_buffer += line
            
            # Try to parse and execute the command
            if command_buffer.strip():
                # Check if command is complete by trying to parse it
                try:
                    tokens = tokenize(command_buffer)
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
        incomplete_patterns = [
            ("Expected DO", "got EOF"),
            ("Expected DONE", "got EOF"),
            ("Expected FI", "got EOF"),
            ("Expected THEN", "got EOF"),
            ("Expected IN", "got EOF"),
            ("Expected ESAC", "got EOF"),
            ("Expected '}' to end compound command", None),  # Function bodies
            ("Expected RPAREN", "got EOF"),
            ("Expected DOUBLE_RBRACKET", None),  # For incomplete [[ ]]
            ("Expected test operand", None),      # For [[ ... && at end
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
        
        try:
            tokens = tokenize(command_string)
            
            # Debug: Print tokens if requested
            if self.state.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                print(self.shell._format_tokens(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Expand aliases
            tokens = self.shell.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Debug: Print AST if requested
            if self.state.debug_ast:
                print("=== AST Debug Output ===", file=sys.stderr)
                print(self.shell._format_ast(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
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
                    # Break/continue outside of loops is an error
                    if "LoopBreak" in str(type(e)) or "LoopContinue" in str(type(e)):
                        stmt_name = "break" if "LoopBreak" in str(type(e)) else "continue"
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