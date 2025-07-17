"""Enhanced integration for existing command parser components."""

from typing import List, Optional, Union, Any
from ..token_types import Token, TokenType
from ..token_types import Token
from ..token_enhanced import TokenContext, SemanticType
from ..ast_nodes import SimpleCommand, Pipeline, ArrayAssignment
from .enhanced_base import EnhancedContextBaseParser, EnhancedParserConfig
from .commands import CommandParser


class EnhancedCommandParser(CommandParser):
    """Enhanced version of CommandParser that leverages enhanced token metadata."""
    
    def __init__(self, main_parser):
        """Initialize enhanced command parser."""
        super().__init__(main_parser)
        
        # Check if the main parser has enhanced capabilities
        self.enhanced_parser = isinstance(main_parser, EnhancedContextBaseParser)
        self.enhanced_config = getattr(main_parser, 'enhanced_config', None)
    
    def parse_command_enhanced(self) -> SimpleCommand:
        """Enhanced version of command parsing using token metadata."""
        if not self.enhanced_parser:
            # Fallback to original implementation
            return self.parse_command()
        
        command = SimpleCommand()
        
        # Use enhanced error detection from lexer
        if self._has_lexer_errors():
            self._handle_lexer_errors()
        
        # Enhanced assignment detection using token metadata
        self._parse_enhanced_assignments(command)
        
        # Enhanced command name parsing
        if not self._parse_enhanced_command_name(command):
            return command  # Assignment-only command
        
        # Enhanced argument and redirection parsing
        self._parse_enhanced_arguments_and_redirections(command)
        
        return command
    
    def _has_lexer_errors(self) -> bool:
        """Check if lexer detected any errors."""
        if hasattr(self.parser, 'lexer_errors'):
            return len(self.parser.lexer_errors) > 0
        return False
    
    def _handle_lexer_errors(self):
        """Handle errors detected by the lexer."""
        if not hasattr(self.parser, 'lexer_errors'):
            return
        
        for error in self.parser.lexer_errors:
            if error.error_type == 'UNCLOSED_QUOTE':
                self._suggest_quote_fix(error)
            elif error.error_type == 'UNCLOSED_EXPANSION':
                self._suggest_expansion_fix(error)
            elif error.error_type == 'UNMATCHED_BRACKET':
                self._suggest_bracket_fix(error)
    
    def _suggest_quote_fix(self, error):
        """Suggest fix for unclosed quote."""
        suggestion = f"Add closing {error.expected} quote"
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(f"Lexer: {error.message}. Suggestion: {suggestion}")
    
    def _suggest_expansion_fix(self, error):
        """Suggest fix for unclosed expansion."""
        suggestion = f"Add closing {error.expected}"
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(f"Lexer: {error.message}. Suggestion: {suggestion}")
    
    def _suggest_bracket_fix(self, error):
        """Suggest fix for unmatched bracket."""
        suggestion = f"Add matching {error.expected}"
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(f"Lexer: {error.message}. Suggestion: {suggestion}")
    
    def _parse_enhanced_assignments(self, command: SimpleCommand):
        """Parse assignments using enhanced token metadata."""
        while self._current_token_is_assignment():
            assignment_token = self._get_current_enhanced_token()
            
            if self.enhanced_config and self.enhanced_config.enable_context_validation:
                # Validate assignment is in correct context
                if TokenContext.COMMAND_POSITION not in assignment_token.metadata.contexts:
                    if hasattr(self.parser.ctx, 'add_warning'):
                        self.parser.ctx.add_warning(
                            f"Assignment '{assignment_token.value}' not in command position"
                        )
            
            # Extract assignment information from enhanced metadata
            assignment = self._extract_assignment_from_enhanced_token(assignment_token)
            
            if assignment.assignment_type == 'array':
                command.array_assignments.append(assignment)
            else:
                command.args.append(assignment_token.value)
                command.arg_types.append('ASSIGNMENT')
                command.quote_types.append(assignment_token.quote_type)
            
            self.parser.advance()
    
    def _current_token_is_assignment(self) -> bool:
        """Check if current token is an assignment using enhanced metadata."""
        token = self._get_current_enhanced_token()
        return token and token.is_assignment
    
    def _get_current_enhanced_token(self) -> Optional[Token]:
        """Get current token as enhanced token."""
        if hasattr(self.parser, 'peek_enhanced'):
            return self.parser.peek_enhanced()
        
        # Fallback: convert basic token to enhanced
        token = self.parser.peek()
        if token and not isinstance(token, Token):
            return Token.from_token(token)
        return token
    
    def _extract_assignment_from_enhanced_token(self, token: Token) -> ArrayAssignment:
        """Extract assignment from enhanced token metadata."""
        if hasattr(token, 'assignment_info'):
            info = token.assignment_info
            
            if info.get('type') == 'array':
                return ArrayAssignment(
                    name=info['variable'],
                    indices=[info.get('index', '0')],
                    values=[info['value']],
                    position=token.position
                )
        
        # Fallback to basic parsing
        return self._parse_assignment_basic(token)
    
    def _parse_assignment_basic(self, token: Token) -> ArrayAssignment:
        """Basic assignment parsing fallback."""
        value = token.value
        if '=' not in value:
            raise self.parser._error(f"Invalid assignment: {value}")
        
        parts = value.split('=', 1)
        variable = parts[0]
        assignment_value = parts[1] if len(parts) > 1 else ''
        
        # Check for array assignment
        if '[' in variable and variable.endswith(']'):
            bracket_pos = variable.find('[')
            array_name = variable[:bracket_pos]
            index = variable[bracket_pos+1:-1]
            return ArrayAssignment(
                name=array_name,
                indices=[index],
                values=[assignment_value],
                position=token.position
            )
        
        # Simple assignment - create as array assignment with index 0
        return ArrayAssignment(
            name=variable,
            indices=['0'],
            values=[assignment_value],
            position=token.position
        )
    
    def _parse_enhanced_command_name(self, command: SimpleCommand) -> bool:
        """Parse command name using enhanced token metadata."""
        if not self.parser.match_any([TokenType.WORD, TokenType.STRING]):
            return False  # No command name (assignment-only)
        
        command_token = self._get_current_enhanced_token()
        
        # Semantic validation
        if (self.enhanced_config and 
            self.enhanced_config.enable_semantic_validation and
            command_token):
            
            self._validate_command_semantics(command_token)
        
        # Add command name
        token = self.parser.advance()
        command.args.append(token.value)
        command.arg_types.append(token.type.name)
        command.quote_types.append(token.quote_type)
        
        return True
    
    def _validate_command_semantics(self, command_token: Token):
        """Validate command using semantic information."""
        if command_token.metadata.semantic_type == SemanticType.BUILTIN:
            # Known builtin - no validation needed
            return
        
        if command_token.metadata.semantic_type == SemanticType.KEYWORD:
            # Shell keyword - validate context
            if TokenContext.COMMAND_POSITION not in command_token.metadata.contexts:
                if hasattr(self.parser.ctx, 'add_warning'):
                    self.parser.ctx.add_warning(
                        f"Keyword '{command_token.value}' used as command"
                    )
            return
        
        # Check if command might not exist
        if not self._is_known_command(command_token.value):
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Command '{command_token.value}' not found - check spelling or PATH"
                )
    
    def _is_known_command(self, command: str) -> bool:
        """Check if command is known."""
        # Common Unix commands
        common_commands = {
            'echo', 'cat', 'ls', 'grep', 'sed', 'awk', 'sort', 'head', 'tail',
            'find', 'xargs', 'cut', 'tr', 'wc', 'uniq', 'tee', 'touch', 'rm',
            'cp', 'mv', 'mkdir', 'rmdir', 'chmod', 'chown', 'ln', 'pwd', 'cd',
            'ps', 'kill', 'jobs', 'fg', 'bg', 'nohup', 'which', 'whereis',
            'man', 'info', 'help', 'history', 'alias', 'unalias', 'export',
            'set', 'unset', 'env', 'printenv', 'source', 'exec', 'eval'
        }
        return command in common_commands
    
    def _parse_enhanced_arguments_and_redirections(self, command: SimpleCommand):
        """Parse arguments and redirections with enhanced features."""
        has_parsed_regular_args = len(command.args) > 1  # Already have command name
        
        while self._can_continue_parsing():
            current_token = self._get_current_enhanced_token()
            
            if self._is_redirection_token(current_token):
                redirect = self.parser.redirections.parse_redirect()
                command.redirects.append(redirect)
            
            elif current_token and current_token.is_redirect:
                # Enhanced redirection detection
                redirect = self._parse_enhanced_redirection(current_token)
                command.redirects.append(redirect)
            
            elif (not has_parsed_regular_args and 
                  self._current_token_is_assignment()):
                # Late assignment detection
                self._parse_enhanced_assignments(command)
            
            else:
                # Regular argument
                token = self.parser.advance()
                command.args.append(token.value)
                command.arg_types.append(token.type.name)
                command.quote_types.append(token.quote_type)
                has_parsed_regular_args = True
    
    def _can_continue_parsing(self) -> bool:
        """Check if we can continue parsing the command."""
        if self.parser.at_end():
            return False
        
        current = self.parser.peek()
        if not current:
            return False
        
        # Stop at command terminators
        terminators = {
            TokenType.SEMICOLON, TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR,
            TokenType.NEWLINE, TokenType.EOF, TokenType.RPAREN
        }
        
        return current.type not in terminators
    
    def _is_redirection_token(self, token: Optional[Token]) -> bool:
        """Check if token is a redirection."""
        if not token:
            return False
        
        redirection_types = {
            TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, TokenType.REDIRECT_APPEND,
            TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP,
            TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING
        }
        
        return token.type in redirection_types
    
    def _parse_enhanced_redirection(self, redirect_token: Token):
        """Parse redirection with enhanced validation."""
        # Use existing redirection parser but add enhanced validation
        redirect = self.parser.redirections.parse_redirect()
        
        # Enhanced validation
        if (self.enhanced_config and 
            self.enhanced_config.enable_semantic_validation):
            
            self._validate_redirection_semantics(redirect_token, redirect)
        
        return redirect
    
    def _validate_redirection_semantics(self, token: Token, redirect):
        """Validate redirection semantics."""
        # Check for common redirection issues
        if redirect.target == '/dev/null' and redirect.type in ['<']:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    "Reading from /dev/null (always empty)"
                )
        
        # Check for suspicious redirections
        if redirect.target.startswith('-'):
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Suspicious redirection target: {redirect.target}"
                )


def install_enhanced_command_parser(parser):
    """Install enhanced command parser into existing parser."""
    if hasattr(parser, 'commands'):
        # Replace the command parser with enhanced version
        enhanced_commands = EnhancedCommandParser(parser)
        
        # Add enhanced method while keeping original
        parser.commands.parse_command_enhanced = enhanced_commands.parse_command_enhanced
        parser.commands._enhanced_parser = enhanced_commands
        
        # Optionally replace the main parse_command method
        if hasattr(parser, 'enhanced_config') and parser.enhanced_config.use_enhanced_tokens:
            parser.commands.parse_command_original = parser.commands.parse_command
            parser.commands.parse_command = enhanced_commands.parse_command_enhanced


def create_enhanced_command_parser_integration(main_parser) -> EnhancedCommandParser:
    """Create enhanced command parser for integration."""
    return EnhancedCommandParser(main_parser)