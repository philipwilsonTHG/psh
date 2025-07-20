import os
import sys
from typing import List, Tuple
from .lexer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, SimpleCommand, Pipeline, StatementList, AndOrList, TopLevel, FunctionDef, BreakStatement, ContinueStatement, EnhancedTestStatement, TestExpression, BinaryTestExpression, UnaryTestExpression, CompoundTestExpression, NegatedTestExpression, WhileLoop, ForLoop, CStyleForLoop, IfConditional, CaseConditional, SelectLoop, ArithmeticEvaluation, SubshellGroup
from .aliases import AliasManager
from .functions import FunctionManager
from .job_control import JobManager, JobState
from .builtins import registry as builtin_registry
from .builtins.function_support import FunctionReturn

# Import from new core modules
from .core.exceptions import LoopBreak, LoopContinue, UnboundVariableError
from .core.state import ShellState
from .utils.token_formatter import TokenFormatter
from .expansion.manager import ExpansionManager
from .io_redirect.manager import IOManager
# Legacy executor removed - using visitor pattern exclusively
from .scripting.base import ScriptManager
from .interactive.base import InteractiveManager

class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, debug_tokens=False, debug_scopes=False, 
                 debug_expansion=False, debug_expansion_detail=False, debug_exec=False, debug_exec_fork=False,
                 norc=False, rcfile=None, validate_only=False, format_only=False, metrics_only=False,
                 security_only=False, lint_only=False, parent_shell=None, ast_format=None, enhanced_lexer=None):
        # Initialize state
        self.state = ShellState(args, script_name, debug_ast, 
                              debug_tokens, debug_scopes, debug_expansion, debug_expansion_detail,
                              debug_exec, debug_exec_fork, norc, rcfile)
        
        # Store validation and visitor modes
        self.validate_only = validate_only
        self.format_only = format_only
        self.metrics_only = metrics_only
        self.security_only = security_only
        self.lint_only = lint_only
        self.ast_format = ast_format
        
        # Visitor executor is now the only executor
        # Remove this option from state as well
        if 'visitor-executor' in self.state.options:
            del self.state.options['visitor-executor']
        
        # Set shell reference in scope manager for arithmetic evaluation
        self.state.scope_manager.set_shell(self)
        
        # Create backward compatibility properties
        self._setup_compatibility_properties()
        
        # Use new builtin registry for migrated builtins
        self.builtin_registry = builtin_registry
        
        # All builtins are now handled by the registry
        self.builtins = {}
        
        # Initialize basic managers first
        self.alias_manager = AliasManager()
        self.function_manager = FunctionManager()
        self.job_manager = JobManager()
        
        # Connect job manager to shell state for option checking
        self.job_manager.set_shell_state(self.state)
        
        # Inherit from parent shell if provided - MUST be done before creating other managers
        if parent_shell:
            self.env = parent_shell.env.copy()
            # Copy global variables from parent's scope manager
            for name, var in parent_shell.state.scope_manager.global_scope.variables.items():
                # Copy the entire Variable object to preserve attributes
                self.state.scope_manager.global_scope.variables[name] = var.copy()
            # Copy all scopes to inherit local variables and their attributes
            for scope in parent_shell.state.scope_manager.scope_stack[1:]:  # Skip global, already copied
                new_scope = scope.copy()
                self.state.scope_manager.scope_stack.append(new_scope)
            self.function_manager = parent_shell.function_manager.copy()
            # Copy positional parameters for subshells
            self.state.positional_params = parent_shell.state.positional_params.copy()
            # Sync all exported variables (including local exports) to environment
            self.state.scope_manager.sync_exports_to_environment(self.env)
            # Note: We don't copy aliases or jobs - those are shell-specific
        
        # Now create managers that need references to the shell
        # These will get the correct function_manager reference
        self.expansion_manager = ExpansionManager(self)
        self.io_manager = IOManager(self)
        # Legacy executor removed - using visitor pattern exclusively
        self.script_manager = ScriptManager(self)
        self.interactive_manager = InteractiveManager(self)
        
        # Initialize history expander
        from .history_expansion import HistoryExpander
        self.history_expander = HistoryExpander(self)
        
        # Initialize parser strategy
        from .parser.parser_registry import ParserStrategy
        self.parser_strategy = ParserStrategy("default")
        
        # Initialize trap manager
        from .core.trap_manager import TrapManager
        self.trap_manager = TrapManager(self)
        
        # Initialize parser integration (enhanced features now standard)
        if enhanced_lexer is not False:  # None or True means auto-detect/enable
            try:
                from .shell_parser import install_parser_integration
                install_parser_integration(self)
            except ImportError:
                # Parser integration not available, continue without it
                pass
        
        # Initialize stream references (used by builtins)
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stdin = sys.stdin
        
        # Load history
        self.interactive_manager.load_history()
        
        # Load RC file for interactive shells
        # Allow force_interactive for testing purposes
        is_interactive = getattr(self, '_force_interactive', sys.stdin.isatty())
        
        # Set emacs mode based on interactive status (bash behavior)
        # Interactive: emacs on (for line editing), Non-interactive: emacs off
        self.state.options['emacs'] = is_interactive and not self.is_script_mode
        
        if not self.is_script_mode and is_interactive and not self.norc:
            self._load_rc_file()
    
    def _setup_compatibility_properties(self):
        """Set up properties for backward compatibility."""
        # These will be removed in later phases
        self._state_properties = [
            'env', 'variables', 'positional_params', 'script_name',
            'is_script_mode', 'debug_ast', 'debug_tokens', 'norc', 'rcfile',
            'last_exit_code', 'last_bg_pid', 'foreground_pgid', 'command_number',
            'history', 'history_file', 'max_history_size', 'history_index',
            'current_line', 'edit_mode', 'function_stack', '_in_forked_child',
            'stdout', 'stderr', 'stdin'
        ]
    
    def __getattr__(self, name):
        """Delegate attribute access to state for compatibility."""
        if hasattr(self.state, name):
            return getattr(self.state, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Delegate attribute setting to state for compatibility."""
        if name in ('state', '_state_properties', 'builtin_registry', 'builtins', 
                   'alias_manager', 'function_manager', 'job_manager', 'expansion_manager',
                   'io_manager', 'executor_manager', 'script_manager', 'interactive_manager',
                   'history_expander'):
            super().__setattr__(name, value)
        elif hasattr(self, '_state_properties') and name in self._state_properties:
            setattr(self.state, name, value)
        else:
            super().__setattr__(name, value)
    
    
    
    
    # Legacy execute_command and execute_pipeline methods removed
    # All execution now goes through the visitor pattern
    
    def execute_command_list(self, command_list: StatementList):
        """Execute a command list"""
        from .executor import ExecutorVisitor
        executor = ExecutorVisitor(self)
        return executor.visit(command_list)
    
    def execute_toplevel(self, toplevel: TopLevel):
        """Execute a top-level script/input containing functions and commands."""
        from .executor import ExecutorVisitor
        executor = ExecutorVisitor(self)
        return executor.visit(toplevel)
    
    def execute(self, ast):
        """Execute an AST node - for backward compatibility with tests."""
        from .ast_nodes import TopLevel
        if isinstance(ast, TopLevel):
            return self.execute_toplevel(ast)
        else:
            # Wrap in TopLevel if needed
            toplevel = TopLevel([ast])
            return self.execute_toplevel(toplevel)
    
    
    def execute_enhanced_test_statement(self, test_stmt: EnhancedTestStatement) -> int:
        """Execute an enhanced test statement [[...]]."""
        # Apply redirections if present
        if test_stmt.redirects:
            saved_fds = self.io_manager.apply_redirections(test_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            result = self._evaluate_test_expression(test_stmt.expression)
            # DEBUG
            # print(f"DEBUG: Enhanced test result={result}, returning {0 if result else 1}", file=sys.stderr)
            return 0 if result else 1
        except Exception as e:
            print(f"psh: [[: {e}", file=sys.stderr)
            return 2  # Syntax error
        finally:
            # Restore file descriptors
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def _evaluate_test_expression(self, expr: TestExpression) -> bool:
        """Evaluate a test expression to boolean."""
        if isinstance(expr, BinaryTestExpression):
            return self._evaluate_binary_test(expr)
        elif isinstance(expr, UnaryTestExpression):
            return self._evaluate_unary_test(expr)
        elif isinstance(expr, CompoundTestExpression):
            return self._evaluate_compound_test(expr)
        elif isinstance(expr, NegatedTestExpression):
            return not self._evaluate_test_expression(expr.expression)
        else:
            raise ValueError(f"Unknown test expression type: {type(expr).__name__}")
    
    def _evaluate_binary_test(self, expr: BinaryTestExpression) -> bool:
        """Evaluate binary test expression."""
        # Expand variables in operands
        left = self.expansion_manager.expand_string_variables(expr.left)
        right = self.expansion_manager.expand_string_variables(expr.right)
        
        # Process escape sequences for pattern matching
        left = self._process_escape_sequences(left)
        right = self._process_escape_sequences(right)
        
        # Handle different operators
        if expr.operator == '=':
            return left == right
        elif expr.operator == '==':
            # Shell pattern matching (not string equality)
            # If the right operand was quoted, treat it as literal string
            right_quote_type = getattr(expr, 'right_quote_type', None)
            if right_quote_type:
                # Quoted pattern should be treated literally
                return left == right
            else:
                # Unquoted pattern should be treated as glob pattern
                import fnmatch
                return fnmatch.fnmatch(left, right)
        elif expr.operator == '!=':
            # Shell pattern non-matching
            # If the right operand was quoted, treat it as literal string
            right_quote_type = getattr(expr, 'right_quote_type', None)
            if right_quote_type:
                # Quoted pattern should be treated literally
                return left != right
            else:
                # Unquoted pattern should be treated as glob pattern
                import fnmatch
                return not fnmatch.fnmatch(left, right)
        elif expr.operator == '<':
            # Lexicographic comparison
            return left < right
        elif expr.operator == '>':
            # Lexicographic comparison
            return left > right
        elif expr.operator == '=~':
            # Regex matching
            import re
            try:
                pattern = re.compile(right)
                return bool(pattern.search(left))
            except re.error as e:
                raise ValueError(f"invalid regex: {e}")
        elif expr.operator == '-eq':
            from .utils.file_tests import to_int
            return to_int(left) == to_int(right)
        elif expr.operator == '-ne':
            from .utils.file_tests import to_int
            return to_int(left) != to_int(right)
        elif expr.operator == '-lt':
            from .utils.file_tests import to_int
            return to_int(left) < to_int(right)
        elif expr.operator == '-le':
            from .utils.file_tests import to_int
            return to_int(left) <= to_int(right)
        elif expr.operator == '-gt':
            from .utils.file_tests import to_int
            return to_int(left) > to_int(right)
        elif expr.operator == '-ge':
            from .utils.file_tests import to_int
            return to_int(left) >= to_int(right)
        elif expr.operator == '-nt':
            # File newer than
            from .utils.file_tests import file_newer_than
            return file_newer_than(left, right)
        elif expr.operator == '-ot':
            # File older than
            from .utils.file_tests import file_older_than
            return file_older_than(left, right)
        elif expr.operator == '-ef':
            # Files are the same
            from .utils.file_tests import files_same
            return files_same(left, right)
        else:
            raise ValueError(f"unknown binary operator: {expr.operator}")
    
    def _process_escape_sequences(self, text: str) -> str:
        """Process escape sequences in text for pattern matching."""
        if not text or '\\' not in text:
            return text
        
        from .lexer.pure_helpers import handle_escape_sequence
        
        result = []
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                # Process escape sequence
                escaped_char, new_pos = handle_escape_sequence(text, i, quote_context=None)
                result.append(escaped_char)
                i = new_pos
            else:
                result.append(text[i])
                i += 1
        
        return ''.join(result)
    
    def _evaluate_unary_test(self, expr: UnaryTestExpression) -> bool:
        """Evaluate unary test expression."""
        # Handle -v operator specially since it needs shell state
        if expr.operator == '-v':
            # Check if variable is set (including array elements)
            operand = expr.operand  # Don't expand for -v, we want the variable name
            return self._is_variable_set(operand)
        
        # Expand variables in operand for other operators
        operand = self.expansion_manager.expand_string_variables(expr.operand)
        
        # Import test command's unary operators
        from .builtins.test_command import TestBuiltin
        test_cmd = TestBuiltin()
        
        # Reuse the existing unary operator implementation
        # Note: _evaluate_unary returns 0 for true, 1 for false (shell convention)
        # We need to convert to boolean
        result = test_cmd._evaluate_unary(expr.operator, operand)
        return result == 0
    
    def _evaluate_compound_test(self, expr: CompoundTestExpression) -> bool:
        """Evaluate compound test expression with && or ||."""
        left_result = self._evaluate_test_expression(expr.left)
        
        if expr.operator == '&&':
            # Short-circuit AND
            if not left_result:
                return False
            return self._evaluate_test_expression(expr.right)
        elif expr.operator == '||':
            # Short-circuit OR
            if left_result:
                return True
            return self._evaluate_test_expression(expr.right)
        else:
            raise ValueError(f"unknown compound operator: {expr.operator}")
    
    def _is_variable_set(self, var_ref: str) -> bool:
        """Check if a variable is set, including array element syntax.
        
        Supports:
        - var: check if variable is set
        - array[key]: check if array element exists
        """
        # Check for array element syntax: var[key]
        if '[' in var_ref and var_ref.endswith(']'):
            var_name = var_ref[:var_ref.index('[')]
            key_expr = var_ref[var_ref.index('[') + 1:-1]
            
            # Expand the key expression
            key = self.expansion_manager.expand_string_variables(key_expr)
            
            # Get the array variable
            var_obj = self.state.scope_manager.get_variable_object(var_name)
            if not var_obj:
                return False
                
            # Check if it's an array and if the key exists
            from .core.variables import IndexedArray, AssociativeArray
            if isinstance(var_obj.value, AssociativeArray):
                return key in var_obj.value._elements
            elif isinstance(var_obj.value, IndexedArray):
                try:
                    index = int(key)
                    return index in var_obj.value._elements
                except ValueError:
                    return False
            else:
                # Not an array, so array[key] syntax doesn't apply
                return False
        else:
            # Simple variable check
            var_obj = self.state.scope_manager.get_variable_object(var_ref)
            return var_obj is not None
    
    
    
    def set_positional_params(self, params):
        """Set positional parameters ($1, $2, etc.)."""
        self.positional_params = params.copy() if params else []
    
    
    def run_script(self, script_path: str, script_args: list = None) -> int:
        """Execute a script file with optional arguments."""
        return self.script_manager.run_script(script_path, script_args)
    
    
    def _execute_buffered_command(self, command_string: str, input_source, start_line: int, add_to_history: bool) -> int:
        """Execute a buffered command with enhanced error reporting."""
        # Skip empty commands and comments
        if not command_string.strip() or command_string.strip().startswith('#'):
            return 0
        
        try:
            # Use strict=False for interactive mode, strict=True for script mode
            strict_mode = self.state.is_script_mode
            tokens = tokenize(command_string, strict=strict_mode)
            
            # Debug: Print tokens if requested
            if self.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                from .utils.token_formatter import TokenFormatter
                print(TokenFormatter.format(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Note: Alias expansion now happens during execution phase for proper precedence
            
            # Parse using the selected parser implementation
            ast = self.parser_strategy.parse(tokens)
            
            # Debug: Print AST if requested
            if self.debug_ast:
                self._print_ast_debug(ast)
            
            # Validation mode - analyze AST without executing
            if self.validate_only:
                from .visitor import EnhancedValidatorVisitor
                validator = EnhancedValidatorVisitor()
                validator.visit(ast)
                
                # Print validation results
                print(validator.get_summary())
                
                # Return exit code based on errors
                error_count = sum(1 for i in validator.issues 
                                if i.severity.value == 'error')
                return 1 if error_count > 0 else 0
            
            # Format mode - format AST and print
            if self.format_only:
                from .visitor import FormatterVisitor
                formatter = FormatterVisitor()
                formatted_code = formatter.visit(ast)
                print(formatted_code)
                return 0
            
            # Metrics mode - analyze AST and print metrics
            if self.metrics_only:
                from .visitor import MetricsVisitor
                metrics = MetricsVisitor()
                metrics.visit(ast)
                print(metrics.get_summary())
                return 0
            
            # Security mode - analyze AST for security issues
            if self.security_only:
                from .visitor import SecurityVisitor
                security = SecurityVisitor()
                security.visit(ast)
                print(security.get_summary())
                
                # Return exit code based on security issues
                issue_count = len(security.issues)
                return 1 if issue_count > 0 else 0
            
            # Lint mode - analyze AST for style and best practices
            if self.lint_only:
                from .visitor import LinterVisitor
                linter = LinterVisitor()
                linter.visit(ast)
                print(linter.get_summary())
                
                # Return exit code based on lint issues
                issue_count = len(linter.issues)
                return 1 if issue_count > 0 else 0
            
            # Add to history if requested (for interactive or testing)
            # Don't add history expansion commands to history
            if add_to_history and command_string.strip():
                import re
                history_pattern = r'(?:^|\s)!(?:!|[0-9]+|-[0-9]+|[a-zA-Z][a-zA-Z0-9]*|\?[^?]*\?)(?:\s|$)'
                if not re.search(history_pattern, command_string):
                    self.interactive_manager.history_manager.add_to_history(command_string.strip())
            
            # Increment command number for successful parse
            self.command_number += 1
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.execute_toplevel(ast)
            else:
                # Backward compatibility - StatementList
                try:
                    # Collect here documents if any
                    self.io_manager.collect_heredocs(ast)
                    exit_code = self.execute_command_list(ast)
                    return exit_code
                except (LoopBreak, LoopContinue) as e:
                    # Break/continue outside of loops is an error
                    stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
                    print(f"{stmt_name}: only meaningful in a `for', `while', or `select' loop", file=sys.stderr)
                    return 1
        except ParseError as e:
            # Check if error already has context, otherwise add location
            if e.error_context and e.error_context.source_line:
                # Error already has full context, just print it
                print(f"psh: {str(e)}", file=sys.stderr)
            else:
                # Add location prefix to error
                location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
                print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.last_exit_code = 2  # Bash uses exit code 2 for syntax errors
            return 2
        except UnboundVariableError as e:
            # Handle nounset errors
            print(str(e), file=sys.stderr)
            self.last_exit_code = 1
            if self.is_script_mode:
                sys.exit(1)
            return 1
        except Exception as e:
            # Enhanced error message with location  
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: unexpected error: {e}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
    
    def _handle_visitor_mode_for_command(self, command: str) -> int:
        """Handle visitor modes for -c commands."""
        # Parse the command to get AST
        try:
            from .lexer import tokenize
            from .parser import parse
            
            tokens = tokenize(command)
            ast = parse(tokens)
            
            return self._apply_visitor_mode(ast)
        except Exception as e:
            print(f"Error parsing command: {e}", file=sys.stderr)
            return 1
    
    def _handle_visitor_mode_for_script(self, script_path: str) -> int:
        """Handle visitor modes for script files."""
        try:
            # Read and parse the script file
            with open(script_path, 'r') as f:
                content = f.read()
            
            from .lexer import tokenize
            from .parser import parse
            
            tokens = tokenize(content)
            ast = parse(tokens)
            
            return self._apply_visitor_mode(ast)
        except FileNotFoundError:
            print(f"psh: {script_path}: No such file or directory", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error processing script: {e}", file=sys.stderr)
            return 1
    
    def _apply_visitor_mode(self, ast) -> int:
        """Apply the appropriate visitor mode to the AST."""
        if self.validate_only:
            from .visitor import EnhancedValidatorVisitor
            validator = EnhancedValidatorVisitor()
            validator.visit(ast)
            print(validator.get_summary())
            error_count = sum(1 for i in validator.issues if i.severity.value == 'error')
            return 1 if error_count > 0 else 0
        
        if self.format_only:
            from .visitor import FormatterVisitor
            formatter = FormatterVisitor()
            formatted_code = formatter.visit(ast)
            print(formatted_code)
            return 0
        
        if self.metrics_only:
            from .visitor import MetricsVisitor
            metrics = MetricsVisitor()
            metrics.visit(ast)
            print(metrics.get_summary())
            return 0
        
        if self.security_only:
            from .visitor import SecurityVisitor
            security = SecurityVisitor()
            security.visit(ast)
            print(security.get_summary())
            issue_count = len(security.issues)
            return 1 if issue_count > 0 else 0
        
        if self.lint_only:
            from .visitor import LinterVisitor
            linter = LinterVisitor()
            linter.visit(ast)
            print(linter.get_summary())
            issue_count = len(linter.issues)
            return 1 if issue_count > 0 else 0
        
        return 0
    
    def run_command(self, command_string: str, add_to_history=True):
        """Execute a command string using the unified input system."""
        from .input_sources import StringInput
        
        # Use the unified execution system for consistency
        input_source = StringInput(command_string, "<command>")
        return self.script_manager.execute_from_source(input_source, add_to_history)
    
    def interactive_loop(self):
        """Run the interactive shell loop."""
        return self.interactive_manager.run_interactive_loop()
    
    # Built-in commands have been moved to the builtins module
    
    
    
    
    
    def _load_rc_file(self):
        """Load ~/.pshrc or alternative RC file if it exists."""
        # Determine which RC file to load
        if self.rcfile:
            rc_file = os.path.expanduser(self.rcfile)
        else:
            rc_file = os.path.expanduser("~/.pshrc")
        
        # Check if file exists and is readable
        if os.path.isfile(rc_file) and os.access(rc_file, os.R_OK):
            # Check security before loading
            if not self._is_safe_rc_file(rc_file):
                print(f"psh: warning: {rc_file} has unsafe permissions, skipping", file=sys.stderr)
                return
            
            try:
                # Store current $0
                old_script_name = self.variables.get('0', self.script_name)
                self.variables['0'] = rc_file
                
                # Source the file without adding to history
                from .input_sources import FileInput
                with FileInput(rc_file) as input_source:
                    self.script_manager.execute_from_source(input_source, add_to_history=False)
                
                # Restore $0
                self.variables['0'] = old_script_name
                
            except Exception as e:
                # Print warning but continue shell startup
                print(f"psh: warning: error loading {rc_file}: {e}", file=sys.stderr)
    
    def _is_safe_rc_file(self, filepath):
        """Check if RC file has safe permissions."""
        try:
            stat_info = os.stat(filepath)
            # Check if file is owned by user or root
            if stat_info.st_uid not in (os.getuid(), 0):
                return False
            # Check if file is world-writable
            if stat_info.st_mode & 0o002:
                return False
            return True
        except OSError:
            return False
    
    
    
    
    
    
    
    # Compatibility methods for tests (Phase 7 temporary)
    def _add_to_history(self, command: str) -> None:
        """Add command to history (compatibility wrapper)."""
        self.interactive_manager.history_manager.add_to_history(command)
    
    def _load_history(self) -> None:
        """Load history from file (compatibility wrapper)."""
        self.interactive_manager.history_manager.load_from_file()
    
    def _save_history(self) -> None:
        """Save history to file (compatibility wrapper)."""
        self.interactive_manager.history_manager.save_to_file()
    
    @property
    def _handle_sigint(self):
        """Get signal handler (compatibility wrapper)."""
        return self.interactive_manager.signal_manager._handle_sigint
    
    @property
    def _handle_sigchld(self):
        """Get signal handler (compatibility wrapper)."""
        return self.interactive_manager.signal_manager._handle_sigchld
    
    def create_parser(self, tokens, source_text=None, **parser_options):
        """Create a parser with configuration based on shell options.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            **parser_options: Additional parser options to override
            
        Returns:
            Configured Parser instance
        """
        from .parser import ParserFactory
        
        # Build shell options dictionary from current state
        shell_options = {
            'posix': self.state.options.get('posix', False),
            'bash_compat': not self.state.options.get('posix', False),
            'collect_errors': self.state.options.get('collect_errors', False),
            'debug_parser': self.state.options.get('debug-parser', False),
            
            # Feature toggles based on shell options
            'enable_aliases': not self.state.options.get('no_aliases', False),
            'enable_functions': not self.state.options.get('no_functions', False),
            'enable_arithmetic': not self.state.options.get('no_arithmetic', False),
        }
        
        # Add any additional parser-specific options
        shell_options.update(parser_options)
        
        return ParserFactory.create_shell_parser(
            tokens, 
            source_text=source_text, 
            shell_options=shell_options
        )
    
    def _print_ast_debug(self, ast) -> None:
        """Print AST debug output in the requested format."""
        # Check for format from command line, then from PSH_AST_FORMAT variable, then default
        format_type = self.ast_format
        if not format_type:
            format_type = self.state.scope_manager.get_variable('PSH_AST_FORMAT') or 'tree'
        
        print("=== AST Debug Output ===", file=sys.stderr)
        
        try:
            if format_type == 'pretty':
                from .parser.visualization import ASTPrettyPrinter
                formatter = ASTPrettyPrinter(
                    indent_size=2,
                    show_positions=True,
                    compact_mode=False
                )
                output = formatter.visit(ast)
                print(output, file=sys.stderr)
                
            elif format_type == 'tree':
                from .parser.visualization import AsciiTreeRenderer
                output = AsciiTreeRenderer.render(
                    ast,
                    show_positions=True,
                    compact_mode=False
                )
                print(output, file=sys.stderr)
                
            elif format_type == 'compact':
                from .parser.visualization import CompactAsciiTreeRenderer
                output = CompactAsciiTreeRenderer.render(ast)
                print(output, file=sys.stderr)
                
            elif format_type == 'dot':
                from .parser.visualization import ASTDotGenerator
                generator = ASTDotGenerator(
                    show_positions=True,
                    color_by_type=True
                )
                output = generator.to_dot(ast)
                print(output, file=sys.stderr)
                print("\n# Save to file and visualize with:", file=sys.stderr)
                print("# dot -Tpng output.dot -o ast.png", file=sys.stderr)
                print("# xdg-open ast.png", file=sys.stderr)
                
            elif format_type == 'sexp':
                from .parser.visualization.sexp_renderer import SExpressionRenderer
                output = SExpressionRenderer.render(
                    ast,
                    compact_mode=False,
                    max_width=80,
                    show_positions=True
                )
                print(output, file=sys.stderr)
                
            else:  # default - use tree format as the new default
                from .parser.visualization import AsciiTreeRenderer
                output = AsciiTreeRenderer.render(ast, show_positions=False, compact_mode=False)
                print(output, file=sys.stderr)
                
        except Exception as e:
            # Fallback to default format if new formatters fail
            print(f"Warning: AST formatting failed ({e}), using default format", file=sys.stderr)
            from .visitor import DebugASTVisitor
            debug_visitor = DebugASTVisitor()
            output = debug_visitor.visit(ast)
            print(output, file=sys.stderr)
        
        print("======================", file=sys.stderr)
