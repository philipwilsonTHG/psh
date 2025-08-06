"""Main parser integration for the modular parser combinator implementation.

This module integrates all the parser combinator modules into a cohesive
parser that implements the AbstractShellParser interface.
"""

from typing import List, Optional, Union, Dict, Any, Tuple
from ...ast_nodes import TopLevel, CommandList, StatementList, ASTNode
from ...token_types import Token
from ..abstract_parser import (
    AbstractShellParser, ParserCharacteristics, ParserType,
    ParseMetrics, ParseError
)
from ..config import ParserConfig

# Import all parser modules
from .core import Parser, ParseResult, ForwardParser
from .tokens import TokenParsers, create_token_parsers
from .expansions import ExpansionParsers, create_expansion_parsers
from .commands import CommandParsers, create_command_parsers
from .control_structures import ControlStructureParsers, create_control_structure_parsers
from .special_commands import SpecialCommandParsers, create_special_command_parsers
from .heredoc_processor import HeredocProcessor, create_heredoc_processor


class ParserCombinatorShellParser(AbstractShellParser):
    """Modular parser combinator implementation.
    
    This parser demonstrates functional parsing through composable combinators.
    It breaks down complex shell syntax into small, reusable parsing functions
    that can be combined to handle the full shell grammar.
    """
    
    def __init__(self, config: Optional[ParserConfig] = None,
                 heredoc_contents: Optional[Dict[str, str]] = None):
        """Initialize the parser combinator.
        
        Args:
            config: Parser configuration
            heredoc_contents: Optional map of heredoc keys to their content
        """
        super().__init__()
        
        self.config = config or ParserConfig()
        self.heredoc_contents = heredoc_contents or {}
        
        # Initialize all parser modules
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Initialize all parser modules and wire them together."""
        # Create token parsers
        self.tokens = create_token_parsers()
        
        # Create expansion parsers
        self.expansions = create_expansion_parsers(self.config)
        
        # Create command parsers with dependencies
        self.commands = create_command_parsers(
            config=self.config,
            token_parsers=self.tokens,
            expansion_parsers=self.expansions
        )
        
        # Create control structure parsers
        self.control = create_control_structure_parsers(
            config=self.config,
            token_parsers=self.tokens,
            command_parsers=self.commands
        )
        
        # Create special command parsers
        self.special = create_special_command_parsers(
            config=self.config,
            token_parsers=self.tokens,
            command_parsers=self.commands
        )
        
        # Create heredoc processor
        self.heredoc_processor = create_heredoc_processor()
        
        # Wire circular dependencies
        self._wire_dependencies()
        
        # Build the complete parser after dependencies are wired
        self._build_complete_parser()
    
    def _wire_dependencies(self):
        """Wire circular dependencies between modules.
        
        Some parser modules have circular dependencies (e.g., commands
        can contain control structures which contain commands). This
        method resolves these dependencies after all modules are created.
        """
        # Wire command parsers in dependent modules - this triggers
        # initialization of parsers that depend on commands
        self.control.set_command_parsers(self.commands)
        self.special.set_command_parsers(self.commands)
        
        # Wire forward declarations in commands module if needed
        if hasattr(self.commands, 'set_control_parsers'):
            self.commands.set_control_parsers(self.control)
        
        if hasattr(self.commands, 'set_special_parsers'):
            self.commands.set_special_parsers(self.special)
    
    def _build_complete_parser(self):
        """Build the complete top-level parser."""
        # First check if control structures have been initialized
        if not hasattr(self.control, 'control_structure') or self.control.control_structure is None:
            # Control structures haven't been initialized yet, use simple commands only
            self.command = self.commands.and_or_list
        else:
            # Combine all command types
            self.command = (
                # Try control structures first (most specific)
                self.control.control_structure
                # Then special commands
                .or_else(self.special.special_command)
                # Then and-or lists (which include pipelines and simple commands)
                .or_else(self.commands.and_or_list)
            )
        
        # Update command parsers with the complete command parser
        if hasattr(self.commands, 'set_command_parser'):
            self.commands.set_command_parser(self.command)
        
        # Build top-level parser (statement list)
        self.top_level = self.commands.statement_list
    
    def parse(self, tokens: List[Token]) -> Union[TopLevel, CommandList]:
        """Parse a list of tokens into an AST.
        
        Args:
            tokens: List of tokens from the lexer
            
        Returns:
            The root AST node (either TopLevel or CommandList)
            
        Raises:
            ParseError: If parsing fails
        """
        # Reset metrics
        self.reset_metrics()
        
        # Skip leading whitespace/newlines
        start_pos = 0
        while start_pos < len(tokens) and tokens[start_pos].type.name in ['WHITESPACE', 'NEWLINE']:
            start_pos += 1
        
        # Empty input
        if start_pos >= len(tokens):
            return TopLevel(items=[])
        
        # Parse the tokens
        result = self.top_level.parse(tokens, start_pos)
        
        if not result.success:
            # Try to provide a helpful error message
            error_msg = result.error or "Failed to parse input"
            if result.position < len(tokens):
                error_token = tokens[result.position]
                error_msg = f"{error_msg} at position {result.position}: {error_token.type.name} '{error_token.value}'"
            raise ParseError(error_msg, position=result.position)
        
        # Get the parsed AST
        ast = result.value
        
        # Ensure we consumed all tokens (allowing trailing whitespace/newlines)
        pos = result.position
        while pos < len(tokens) and tokens[pos].type.name in ['WHITESPACE', 'NEWLINE']:
            pos += 1
        
        if pos < len(tokens):
            # We didn't consume all tokens
            remaining_token = tokens[pos]
            raise ParseError(
                f"Unexpected token after valid input: {remaining_token.type.name} '{remaining_token.value}'",
                position=pos,
                token=remaining_token
            )
        
        # Populate heredoc content if needed
        if self.heredoc_contents:
            self.heredoc_processor.populate_heredocs(ast, self.heredoc_contents)
        
        # Wrap in TopLevel if needed
        if isinstance(ast, CommandList):
            # Convert CommandList to TopLevel by putting statements as items
            return TopLevel(items=ast.statements)
        elif isinstance(ast, StatementList):
            # Convert StatementList to TopLevel
            return TopLevel(items=ast.statements)
        elif isinstance(ast, TopLevel):
            return ast
        else:
            # Single statement - wrap it
            return TopLevel(items=[ast])
    
    def parse_with_heredocs(self, tokens: List[Token], 
                           heredoc_contents: Dict[str, str]) -> Union[TopLevel, CommandList]:
        """Parse tokens with heredoc content support.
        
        This method performs a two-pass parse:
        1. Parse the token stream into an AST
        2. Populate heredoc content in AST nodes
        
        Args:
            tokens: List of tokens from the lexer
            heredoc_contents: Map of heredoc keys to their content
            
        Returns:
            Parsed AST with heredoc content populated
        """
        # Store heredoc contents
        self.heredoc_contents = heredoc_contents
        
        # Parse normally (which will populate heredocs)
        return self.parse(tokens)
    
    def parse_partial(self, tokens: List[Token]) -> Tuple[Optional[ASTNode], int]:
        """Parse as much as possible from the token stream.
        
        Args:
            tokens: List of tokens from the lexer
            
        Returns:
            Tuple of (AST node or None, position where parsing stopped)
        """
        # Skip leading whitespace/newlines
        start_pos = 0
        while start_pos < len(tokens) and tokens[start_pos].type.name in ['WHITESPACE', 'NEWLINE']:
            start_pos += 1
        
        # Empty input
        if start_pos >= len(tokens):
            return None, start_pos
        
        # Try to parse
        result = self.top_level.parse(tokens, start_pos)
        
        if result.success:
            # Populate heredocs if needed
            if self.heredoc_contents:
                self.heredoc_processor.populate_heredocs(result.value, self.heredoc_contents)
            return result.value, result.position
        
        # Try to parse a single statement
        stmt_result = self.commands.statement.parse(tokens, start_pos)
        if stmt_result.success:
            if self.heredoc_contents:
                self.heredoc_processor.populate_heredocs(stmt_result.value, self.heredoc_contents)
            return stmt_result.value, stmt_result.position
        
        # Try to parse a single command
        cmd_result = self.command.parse(tokens, start_pos)
        if cmd_result.success:
            if self.heredoc_contents:
                self.heredoc_processor.populate_heredocs(cmd_result.value, self.heredoc_contents)
            return cmd_result.value, cmd_result.position
        
        # Nothing could be parsed
        return None, start_pos
    
    def can_parse(self, tokens: List[Token]) -> bool:
        """Check if the tokens can be parsed without actually parsing.
        
        Args:
            tokens: List of tokens to check
            
        Returns:
            True if the tokens appear to be parseable
        """
        try:
            # Skip leading whitespace/newlines
            start_pos = 0
            while start_pos < len(tokens) and tokens[start_pos].type.name in ['WHITESPACE', 'NEWLINE']:
                start_pos += 1
            
            # Empty input is valid
            if start_pos >= len(tokens):
                return True
            
            # Try to parse
            result = self.top_level.parse(tokens, start_pos)
            
            if not result.success:
                return False
            
            # Check if we consumed all tokens (allowing trailing whitespace)
            pos = result.position
            while pos < len(tokens) and tokens[pos].type.name in ['WHITESPACE', 'NEWLINE']:
                pos += 1
            
            return pos == len(tokens)
        except Exception:
            return False
    
    def get_name(self) -> str:
        """Return the parser implementation name.
        
        Returns:
            A unique identifier for this parser implementation
        """
        return "parser_combinator"
    
    def get_description(self) -> str:
        """Return a human-readable description of the parser.
        
        Returns:
            A description suitable for educational display
        """
        return (
            "Modular functional parser built from composable combinators. "
            "Demonstrates how complex parsers can be built by combining "
            "simple parsing primitives using functional composition. "
            "Features a clean separation of concerns with dedicated modules "
            "for tokens, expansions, commands, control structures, and "
            "special syntax."
        )
    
    def get_characteristics(self) -> ParserCharacteristics:
        """Return the characteristics of this parser implementation.
        
        Returns:
            ParserCharacteristics object describing the parser
        """
        return ParserCharacteristics(
            parser_type=ParserType.PARSER_COMBINATOR,
            complexity="medium",
            error_recovery=False,
            backtracking=True,
            memoization=False,
            left_recursion=False,
            ambiguity_handling="first",
            incremental=False,
            streaming=False,
            hand_coded=True,
            generated=False,
            functional=True
        )
    
    def get_configuration_options(self) -> Dict[str, Any]:
        """Return available configuration options for this parser.
        
        Returns:
            Dictionary of option names to their descriptions
        """
        return {
            'build_word_ast_nodes': 'Build detailed Word AST nodes with expansion info',
            'parsing_mode': 'Parsing mode (strict_posix, bash_compat, permissive)',
            'enable_process_substitution': 'Enable <(cmd) and >(cmd) syntax',
            'enable_arrays': 'Enable array syntax',
            'enable_arithmetic': 'Enable arithmetic evaluation',
            'allow_bash_conditionals': 'Allow [[ ]] enhanced test syntax',
            'allow_empty_commands': 'Allow empty command lists'
        }
    
    def configure(self, **options):
        """Configure the parser with implementation-specific options.
        
        Args:
            **options: Implementation-specific configuration options
        """
        # Update configuration
        for key, value in options.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Reinitialize modules with new config
        self._initialize_modules()
        self._build_complete_parser()
    
    def explain_parse(self, tokens: List[Token]) -> str:
        """Provide an educational explanation of how parsing works.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Multi-line string explaining the parsing process
        """
        return """
=== Modular Parser Combinator Parsing ===

This parser uses a modular architecture with specialized modules:

1. TOKEN PARSERS - Recognize basic tokens:
   - Keywords (if, then, while, etc.)
   - Operators (|, &, ;, etc.)
   - Delimiters and separators

2. EXPANSION PARSERS - Handle shell expansions:
   - Variable expansion ($var, ${var})
   - Command substitution $(cmd) and `cmd`
   - Arithmetic expansion $((expr))
   - Parameter expansion ${var:-default}

3. COMMAND PARSERS - Parse command structures:
   - Simple commands (cmd arg1 arg2)
   - Pipelines (cmd1 | cmd2)
   - And-or lists (cmd1 && cmd2 || cmd3)
   - Redirections (< file, > file, 2>&1)

4. CONTROL STRUCTURE PARSERS - Handle control flow:
   - If/elif/else conditionals
   - While/for loops
   - Case statements
   - Function definitions

5. SPECIAL COMMAND PARSERS - Parse special syntax:
   - Arithmetic commands ((expr))
   - Enhanced tests [[ condition ]]
   - Array operations
   - Process substitution <(cmd)

6. HEREDOC PROCESSOR - Post-processing phase:
   - Populates heredoc content in redirect nodes
   - Traverses AST after main parsing

The parser works by:
1. Starting with the top-level statement list parser
2. Trying control structures first (most specific)
3. Then special commands
4. Finally regular commands
5. Each parser can recursively call others
6. Results are composed into a complete AST

Key advantages:
- Modular and maintainable
- Clear separation of concerns
- Reusable parser components
- Easy to extend with new features
- Functional programming style
"""


# Convenience functions

def create_parser_combinator_shell_parser(
    config: Optional[ParserConfig] = None,
    heredoc_contents: Optional[Dict[str, str]] = None
) -> ParserCombinatorShellParser:
    """Create and return a ParserCombinatorShellParser instance.
    
    Args:
        config: Optional parser configuration
        heredoc_contents: Optional heredoc content map
        
    Returns:
        Initialized ParserCombinatorShellParser object
    """
    return ParserCombinatorShellParser(config, heredoc_contents)