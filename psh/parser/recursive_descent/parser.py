"""
Main Parser class for PSH shell.

This module contains the main Parser class that orchestrates parsing by delegating
to specialized parser modules for different language constructs.
"""

import sys
from typing import List, Optional, Union, Tuple, Set

from ...token_types import Token, TokenType
from ...token_stream import TokenStream
from ...ast_nodes import (
    Command, SimpleCommand, CompoundCommand, Pipeline, CommandList, StatementList, AndOrList, Redirect, 
    FunctionDef, TopLevel, BreakStatement, ContinueStatement, 
    CaseItem, CasePattern, ProcessSubstitution, EnhancedTestStatement, 
    TestExpression, BinaryTestExpression, UnaryTestExpression, 
    CompoundTestExpression, NegatedTestExpression, Statement,
    # Unified types only
    ExecutionContext, UnifiedControlStructure, WhileLoop, ForLoop, CStyleForLoop,
    IfConditional, CaseConditional, SelectLoop, ArithmeticEvaluation,
    # Array assignments
    ArrayAssignment, ArrayInitialization, ArrayElementAssignment
)

from .base_context import ContextBaseParser
from .context import ParserContext
from .support.context_factory import ParserContextFactory
from .helpers import TokenGroups, ParseError, ErrorContext
from .support.error_collector import ErrorCollector, MultiErrorParseResult, ErrorRecoveryStrategy
from .parsers.statements import StatementParser
from .parsers.commands import CommandParser
from .parsers.control_structures import ControlStructureParser
from .parsers.tests import TestParser


class ContextWrapper:
    """Wrapper providing context manager support for ParserContext.

    This provides backward compatibility for code that uses:
        with parser.context:
            parser.context.in_arithmetic = True
            ...
    """

    def __init__(self, ctx: ParserContext):
        self._ctx = ctx
        self._saved_states = []

    # Forward attribute access to ctx
    def __getattr__(self, name):
        return getattr(self._ctx, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._ctx, name, value)

    def push_context(self, context: str) -> None:
        """Push a parsing context onto the stack."""
        self._ctx.enter_scope(context)

    def pop_context(self) -> Optional[str]:
        """Pop a parsing context from the stack."""
        return self._ctx.exit_scope()

    def __enter__(self):
        """Save current state for context manager."""
        saved = {
            'in_test_expr': self._ctx.in_test_expr,
            'in_arithmetic': self._ctx.in_arithmetic,
            'in_case_pattern': self._ctx.in_case_pattern,
            'in_function_body': self._ctx.in_function_body,
            'in_command_substitution': self._ctx.in_command_substitution,
        }
        self._saved_states.append(saved)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous state."""
        if self._saved_states:
            saved = self._saved_states.pop()
            for key, value in saved.items():
                setattr(self._ctx, key, value)
        return False


from .parsers.arithmetic import ArithmeticParser
from .parsers.redirections import RedirectionParser
from .parsers.arrays import ArrayParser
from .parsers.functions import FunctionParser
from .support.utils import ParserUtils
from ..config import ParserConfig, ParsingMode, ErrorHandlingMode
from ..validation import SemanticAnalyzer, ValidationPipeline, ValidationReport, Issue, Severity


class Parser(ContextBaseParser):
    """Main parser class that orchestrates parsing by delegating to specialized parsers."""
    
    def __init__(self, tokens: List[Token],
                 source_text: Optional[str] = None, collect_errors: bool = False,
                 config: Optional[ParserConfig] = None, ctx: Optional[ParserContext] = None):
        # Create or use provided context
        if ctx is not None:
            # Use provided context directly
            super().__init__(ctx)
        else:
            # Configuration (create default if not provided)
            config = config or ParserConfig()
            
            # Override config with explicit parameters
            if collect_errors:
                config.collect_errors = True
                config.error_handling = ErrorHandlingMode.COLLECT
            
            # Create context
            ctx = ParserContextFactory.create(
                tokens=tokens,
                config=config,
                source_text=source_text
            )
            super().__init__(ctx)
        
        # Legacy attributes for backward compatibility
        self.config = self.ctx.config
        self.source_text = self.ctx.source_text
        self.source_lines = self.ctx.source_lines

        # Error collection support - use config settings
        if self.ctx.config.collect_errors:
            self.error_collector = ErrorCollector(max_errors=self.ctx.config.max_errors)
        else:
            self.error_collector = None
        
        # Context wrapper for backward compatibility
        self._context_wrapper = ContextWrapper(self.ctx)

        # Initialize specialized parsers
        self.statements = StatementParser(self)
        self.commands = CommandParser(self)
        self.control_structures = ControlStructureParser(self)
        self.tests = TestParser(self)
        self.arithmetic = ArithmeticParser(self)
        self.redirections = RedirectionParser(self)
        self.arrays = ArrayParser(self)
        self.functions = FunctionParser(self)
        self.utils = ParserUtils(self)
    
    @property
    def context(self) -> ContextWrapper:
        """Legacy context wrapper for backward compatibility."""
        return self._context_wrapper

    def _error(self, message: str, token: Optional[Token] = None) -> ParseError:
        """Create a ParseError with context."""
        # Delegate to the context-based error method
        return self.error(message, token)
    
    # === Configuration-Based Methods ===
    # These delegate to ContextBaseParser methods
    
    # is_feature_enabled, should_allow, require_feature, check_posix_compliance 
    # are inherited from ContextBaseParser
    
    def should_collect_errors(self) -> bool:
        """Check if errors should be collected rather than thrown immediately."""
        return super().should_collect_errors()
    
    def should_attempt_recovery(self) -> bool:
        """Check if error recovery should be attempted."""
        return super().should_attempt_recovery()
    
    def add_error_with_recovery(self, error: ParseError) -> bool:
        """Add error and determine if parsing should continue."""
        if self.error_collector:
            self.error_collector.add_error(error)
            return self.error_collector.should_continue()
        else:
            # Delegate to context-based error handling
            return self.add_error(error)
    
    def create_configured_parser(self, tokens: List[Token], **overrides) -> 'Parser':
        """Create a new parser with the same configuration."""
        # Create context with same config
        ctx = ParserContextFactory.create(
            tokens=tokens,
            config=self.ctx.config,
            source_text=self.ctx.source_text
        )
        
        # Apply any overrides to the context
        for key, value in overrides.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
            elif hasattr(ctx.config, key):
                setattr(ctx.config, key, value)
        
        return Parser(tokens=[], ctx=ctx)
    
    @classmethod
    def from_context(cls, ctx: ParserContext) -> 'Parser':
        """Create parser from existing context."""
        return cls(tokens=[], ctx=ctx)
    
    @classmethod
    def create_with_config(cls, tokens: List[Token], config: ParserConfig, 
                          source_text: Optional[str] = None) -> 'Parser':
        """Create parser with specific configuration."""
        ctx = ParserContextFactory.create(tokens, config, source_text)
        return cls.from_context(ctx)
    
    # === Legacy Compatibility Properties ===
    
    @property
    def tokens(self) -> List[Token]:
        """Legacy access to tokens."""
        return self.ctx.tokens
    
    @property  
    def current(self) -> int:
        """Legacy access to current position."""
        return self.ctx.current
    
    @current.setter
    def current(self, value: int):
        """Legacy setter for current position."""
        self.ctx.current = value
    
    # === Legacy Method Delegation ===
    
    def consume_if_match(self, *token_types):
        """Legacy method - consume token if it matches any of the given types."""
        return self.consume_if(*token_types)
    
    def match_any(self, token_set):
        """Legacy method - check if current token is in the given set."""
        return super().match_any(token_set)
    
    def save_position(self) -> int:
        """Legacy method - save current parser position."""
        return self.ctx.current
    
    def restore_position(self, position: int):
        """Legacy method - restore parser to saved position."""
        self.ctx.current = position
    
    def peek_ahead(self, n: int = 1):
        """Legacy method - look ahead n tokens without consuming."""
        return self.peek(n)
    
    def expect_with_recovery(self, token_type, recovery_hint=None):
        """Legacy method with recovery hint."""
        try:
            return self.expect(token_type)
        except Exception as e:
            if recovery_hint:
                print(f"Recovery hint: {recovery_hint}")
            raise
    
    def expect_one_of(self, *token_types):
        """Legacy method - expect one of several token types."""
        from ...token_types import TokenType
        token = self.peek()
        if token.type not in token_types:
            expected = [str(tt).replace('TokenType.', '').lower() for tt in token_types]
            error = self.error(f"Expected one of {expected}, got {token.type}")
            self.add_error(error)
        return self.advance()
    
    def panic_mode_recovery(self, sync_tokens):
        """Legacy method for panic mode recovery."""
        self.synchronize(sync_tokens)
    
    def with_error_recovery(self, sync_tokens):
        """Legacy method for error recovery context manager."""
        class ErrorRecoveryContext:
            def __init__(self, parser):
                self.parser = parser
                self.sync_tokens = sync_tokens
                self.old_recovery = False
                
            def __enter__(self):
                self.old_recovery = self.parser.ctx.error_recovery_mode
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.parser.ctx.error_recovery_mode = self.old_recovery
                return False

        return ErrorRecoveryContext(self)

    # === AST Validation ===
    
    def parse_and_validate(self) -> Tuple[Optional[Union[CommandList, TopLevel]], ValidationReport]:
        """Parse and validate AST, returning both AST and validation report."""
        # Parse first
        ast = None
        try:
            ast = self.parse()
        except ParseError as e:
            # If parsing fails, return the error in the validation report
            report = ValidationReport()
            report.add_issue(Issue(
                message=str(e.message),
                position=getattr(e.error_context, 'position', 0),
                severity=Severity.ERROR,
                rule_name="parse"
            ))
            return None, report
        
        # If AST was created and validation is enabled, validate it
        if ast and getattr(self.config, 'enable_validation', False):
            return ast, self.validate_ast(ast)
        
        # Return AST with empty validation report
        return ast, ValidationReport()
    
    def validate_ast(self, ast: Union[CommandList, TopLevel]) -> ValidationReport:
        """Validate an AST and return validation report."""
        if not ast:
            return ValidationReport()
        
        # Combine semantic analysis and validation rules
        report = ValidationReport()
        
        # Semantic analysis
        if getattr(self.config, 'enable_semantic_analysis', True):
            analyzer = SemanticAnalyzer()
            errors, warnings = analyzer.analyze(ast)
            report.add_errors(errors)
            report.add_warnings(warnings)
        
        # Validation rules
        if getattr(self.config, 'enable_validation_rules', True):
            pipeline = ValidationPipeline()
            rule_report = pipeline.validate(ast)
            report.add_issues(rule_report.issues)
        
        return report
    
    def enable_validation(self, enable_semantic: bool = True, enable_rules: bool = True):
        """Enable AST validation features."""
        # Add validation options to config (these don't exist yet, so we'll add them dynamically)
        self.config.enable_validation = True
        self.config.enable_semantic_analysis = enable_semantic
        self.config.enable_validation_rules = enable_rules
    
    def disable_validation(self):
        """Disable AST validation features."""
        self.config.enable_validation = False
    
    # === Top-Level Parsing ===
    
    def parse(self) -> Union[CommandList, TopLevel]:
        """Parse input, returning TopLevel if needed, CommandList for simple cases."""
        # Start profiling if enabled
        if self.ctx.profiler:
            self.ctx.profiler.start_parsing()
        
        try:
            top_level = TopLevel()
            self.skip_newlines()
            
            while not self.at_end():
                item = self._parse_top_level_item()
                if item:
                    top_level.items.append(item)
                self.skip_separators()

            return self._simplify_result(top_level)
        finally:
            # End profiling if enabled
            if self.ctx.profiler:
                self.ctx.profiler.end_parsing()
    
    def parse_with_error_collection(self) -> MultiErrorParseResult:
        """Parse input collecting multiple errors instead of stopping on first error.
        
        Returns:
            MultiErrorParseResult containing AST and any errors encountered
        """
        if not self.error_collector:
            # Enable error collection if not already enabled
            self.error_collector = ErrorCollector()
        
        # Ensure error collection is enabled in context
        old_collect_errors = self.ctx.config.collect_errors
        self.ctx.config.collect_errors = True
        
        try:
            ast = self.parse()
            
            # Collect errors from context into error collector
            for error in self.ctx.errors:
                if error not in self.error_collector.errors:
                    self.error_collector.add_error(error)
            
            # If we have errors but still got an AST, it's a partial success
            if self.ctx.errors:
                return MultiErrorParseResult(ast, self.error_collector.errors)
            else:
                return MultiErrorParseResult(ast, self.error_collector.errors)
                
        except ParseError as e:
            self.error_collector.add_error(e)
            # Try to recover and continue parsing
            if self.error_collector.should_continue():
                ast = self._parse_with_recovery()
            else:
                ast = None
            return MultiErrorParseResult(ast, self.error_collector.errors)
        finally:
            # Restore original error collection setting
            self.ctx.config.collect_errors = old_collect_errors
    
    def _parse_with_recovery(self) -> Optional[Union[CommandList, TopLevel]]:
        """Continue parsing after error with recovery strategies."""
        top_level = TopLevel()
        
        while not self.at_end() and self.error_collector.should_continue():
            try:
                # Try to find next statement
                if not ErrorRecoveryStrategy.find_next_statement(self):
                    break
                
                # Try to parse next item
                item = self._parse_top_level_item_with_recovery()
                if item:
                    top_level.items.append(item)
                    
            except ParseError as e:
                self.error_collector.add_error(e)
                # Skip to next recovery point
                ErrorRecoveryStrategy.skip_to_statement_end(self)
                
            self.skip_separators()
        
        return self._simplify_result(top_level) if top_level.items else None
    
    def _parse_top_level_item_with_recovery(self):
        """Parse top level item with error recovery."""
        try:
            return self._parse_top_level_item()
        except ParseError as e:
            # Add error but try to recover
            self.error_collector.add_error(e)
            
            # Try different recovery strategies
            if self._try_statement_recovery():
                return self._parse_top_level_item()
            else:
                # Skip this item and continue
                ErrorRecoveryStrategy.skip_to_statement_end(self)
                return None
    
    def _try_statement_recovery(self) -> bool:
        """Try to recover at statement level.
        
        Returns:
            True if recovery successful, False otherwise
        """
        # Look for common missing tokens and try to insert them
        current = self.peek()
        
        # Try to recover from missing semicolon
        if current.type in {TokenType.THEN, TokenType.DO}:
            # Assume missing semicolon, continue parsing
            return True
        
        # Try to recover from missing closing tokens
        if current.type in {TokenType.FI, TokenType.DONE, TokenType.ESAC}:
            # Assume we're at the end of a block, continue
            return True
        
        return False
    
    def parse_with_heredocs(self, heredoc_map: dict) -> Union[CommandList, TopLevel]:
        """Parse tokens with heredoc content."""
        # Store heredoc map for legacy compatibility
        self.heredoc_map = heredoc_map
        
        # Populate context with heredoc information
        for key, content in heredoc_map.items():
            # Extract delimiter from key (format: "heredoc_N_delimiter")
            parts = key.split('_')
            if len(parts) >= 3:
                delimiter = '_'.join(parts[2:])
                ctx_key = self.ctx.register_heredoc(delimiter)
                # Add content lines
                for line in content.splitlines():
                    self.ctx.add_heredoc_line(ctx_key, line)
                self.ctx.close_heredoc(ctx_key)
        
        ast = self.parse()
        # Populate heredoc content in the AST
        self.utils.populate_heredoc_content(ast, heredoc_map)
        return ast
    
    def _parse_top_level_item(self) -> Optional[Statement]:
        """Parse a single top-level item."""
        if self.functions.is_function_def():
            return self.functions.parse_function_def()
        elif self.match_any(TokenGroups.CONTROL_KEYWORDS):
            # Check if control structure is part of a pipeline
            control_struct = self.control_structures.parse_control_structure_neutral()
            
            # Check if followed by pipe or logical operators
            if self.match(TokenType.PIPE):
                # Parse as pipeline with control structure as first component
                return self.commands.parse_pipeline_with_initial_component(control_struct)
            elif self.match(TokenType.AND_AND, TokenType.OR_OR):
                # Create pipeline with control structure and wrap in and_or_list
                control_struct.execution_context = ExecutionContext.STATEMENT
                pipeline = Pipeline()
                pipeline.commands.append(control_struct)
                
                and_or_list = AndOrList()
                and_or_list.pipelines.append(pipeline)
                
                # Parse the rest of the and_or_list
                while self.match(TokenType.AND_AND, TokenType.OR_OR):
                    operator = self.advance()
                    and_or_list.operators.append(operator.value)
                    self.skip_newlines()
                    pipeline = self.commands.parse_pipeline()
                    and_or_list.pipelines.append(pipeline)
                
                return and_or_list
            else:
                # Set as statement context and return
                control_struct.execution_context = ExecutionContext.STATEMENT
                return control_struct
        else:
            # Parse commands until we hit a function or control structure
            cmd_list = self.statements.parse_command_list_until_top_level()
            return cmd_list if cmd_list.statements else None
    
    def _simplify_result(self, top_level: TopLevel) -> Union[CommandList, TopLevel]:
        """Simplify result for backward compatibility when possible."""
        if not top_level.items:
            return CommandList()
        elif len(top_level.items) == 1:
            item = top_level.items[0]
            if isinstance(item, CommandList):
                return item
            elif isinstance(item, (BreakStatement, ContinueStatement)):
                # Convert to CommandList for compatibility
                cmd_list = CommandList()
                cmd_list.statements.append(item)
                return cmd_list
            else:
                # Other single items return TopLevel
                return top_level
        else:
            return top_level
    
    # === Delegation Methods ===
    # These methods delegate to specialized parsers for backward compatibility
    
    def parse_statement(self) -> Optional[Statement]:
        """Parse a statement."""
        return self.statements.parse_statement()
    
    def parse_command_list(self) -> CommandList:
        """Parse a command list."""
        return self.statements.parse_command_list()
    
    def parse_and_or_list(self) -> Union[AndOrList, BreakStatement, ContinueStatement]:
        """Parse an and/or list."""
        return self.statements.parse_and_or_list()
    
    def parse_pipeline(self) -> Pipeline:
        """Parse a pipeline."""
        return self.commands.parse_pipeline()
    
    def parse_command(self) -> SimpleCommand:
        """Parse a command."""
        return self.commands.parse_command()
    
    def parse_composite_argument(self) -> Tuple[str, str, Optional[str]]:
        """Parse a composite argument."""
        return self.commands.parse_composite_argument()
    
    # ===== Additional delegation methods for backward compatibility =====
    
    def parse_test_expression(self):
        """Delegate to test parser.""" 
        return self.tests.parse_test_expression()
    
    def _parse_arithmetic_expression_until_double_rparen(self):
        """Delegate to arithmetic parser."""
        return self.arithmetic._parse_arithmetic_expression_until_double_rparen()
    
    def _parse_case_pattern(self):
        """Delegate to control structures parser."""
        return self.control_structures._parse_case_pattern()
    
    def parse_command_list_until(self, *args):
        """Delegate to statements parser."""
        return self.statements.parse_command_list_until(*args)
    
    def parse_if_statement(self) -> IfConditional:
        """Parse an if statement."""
        return self.control_structures.parse_if_statement()
    
    def parse_while_statement(self) -> WhileLoop:
        """Parse a while statement."""
        return self.control_structures.parse_while_statement()
    
    def parse_for_statement(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse a for statement."""
        return self.control_structures.parse_for_statement()
    
    def parse_case_statement(self) -> CaseConditional:
        """Parse a case statement."""
        return self.control_structures.parse_case_statement()
    
    def parse_select_statement(self) -> SelectLoop:
        """Parse a select statement."""
        return self.control_structures.parse_select_statement()
    
    def parse_break_statement(self) -> BreakStatement:
        """Parse a break statement."""
        return self.control_structures.parse_break_statement()
    
    def parse_continue_statement(self) -> ContinueStatement:
        """Parse a continue statement."""
        return self.control_structures.parse_continue_statement()
    
    def parse_enhanced_test_statement(self) -> EnhancedTestStatement:
        """Parse an enhanced test statement ([[ ... ]])."""
        # Check if enhanced conditionals are allowed
        if not self.should_allow('bash_conditionals'):
            self.check_posix_compliance('[[ ]] enhanced test syntax', '[ ] test command')
        
        return self.tests.parse_enhanced_test_statement()
    
    def parse_arithmetic_command(self) -> ArithmeticEvaluation:
        """Parse an arithmetic command ((...)). """
        # Check if arithmetic is enabled
        self.require_feature('arithmetic', 'Arithmetic evaluation is disabled')
        
        # Check POSIX compliance for (( )) syntax
        if not self.should_allow('bash_arithmetic'):
            self.check_posix_compliance('(( )) arithmetic syntax', 'expr command')
        
        return self.arithmetic.parse_arithmetic_command()
    
    def parse_function_def(self) -> FunctionDef:
        """Parse a function definition."""
        # Check if functions are enabled
        self.require_feature('functions', 'Function definitions are disabled')
        
        return self.functions.parse_function_def()
    
    def parse_redirects(self) -> List[Redirect]:
        """Parse redirections."""
        return self.redirections.parse_redirects()
    
    def parse_redirect(self) -> Redirect:
        """Parse a single redirection."""
        return self.redirections.parse_redirect()