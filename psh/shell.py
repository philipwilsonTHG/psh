import os
import sys
from typing import List, Tuple
from .state_machine_lexer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, SimpleCommand, Pipeline, StatementList, AndOrList, TopLevel, FunctionDef, BreakStatement, ContinueStatement, EnhancedTestStatement, TestExpression, BinaryTestExpression, UnaryTestExpression, CompoundTestExpression, NegatedTestExpression, WhileLoop, ForLoop, CStyleForLoop, IfConditional, CaseConditional, SelectLoop, ArithmeticEvaluation
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
from .executor.base import ExecutorManager
from .scripting.base import ScriptManager
from .interactive.base import InteractiveManager

class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, debug_tokens=False, debug_scopes=False, 
                 debug_expansion=False, debug_expansion_detail=False, debug_exec=False, debug_exec_fork=False,
                 norc=False, rcfile=None, validate_only=False, use_visitor_executor=True, parent_shell=None):
        # Initialize state
        self.state = ShellState(args, script_name, debug_ast, 
                              debug_tokens, debug_scopes, debug_expansion, debug_expansion_detail,
                              debug_exec, debug_exec_fork, norc, rcfile)
        
        # Store validation mode
        self.validate_only = validate_only
        
        # Store executor mode - visitor executor is now the default
        # Priority order:
        # 1. Environment variable PSH_USE_VISITOR_EXECUTOR
        # 2. Explicit parameter (use_visitor_executor)
        # 3. Default from state options
        env_override = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower()
        if env_override in ('0', 'false', 'no'):
            self.use_visitor_executor = False
        elif env_override in ('1', 'true', 'yes'):
            self.use_visitor_executor = True
        else:
            # Use parameter if provided, otherwise use state default
            self.use_visitor_executor = use_visitor_executor
        
        # Update state options to match
        self.state.options['visitor-executor'] = self.use_visitor_executor
        
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
        
        # Inherit from parent shell if provided - MUST be done before creating other managers
        if parent_shell:
            self.env = parent_shell.env.copy()
            # Copy global variables from parent's scope manager
            for name, var in parent_shell.state.scope_manager.global_scope.variables.items():
                # Copy the entire Variable object to preserve attributes
                self.state.scope_manager.global_scope.variables[name] = var.copy()
            self.function_manager = parent_shell.function_manager.copy()
            # Note: We don't copy aliases or jobs - those are shell-specific
        
        # Now create managers that need references to the shell
        # These will get the correct function_manager reference
        self.expansion_manager = ExpansionManager(self)
        self.io_manager = IOManager(self)
        self.executor_manager = ExecutorManager(self)
        self.script_manager = ScriptManager(self)
        self.interactive_manager = InteractiveManager(self)
        
        # Initialize history expander
        from .history_expansion import HistoryExpander
        self.history_expander = HistoryExpander(self)
        
        # Load history
        self.interactive_manager.load_history()
        
        # Load RC file for interactive shells
        # Allow force_interactive for testing purposes
        is_interactive = getattr(self, '_force_interactive', sys.stdin.isatty())
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
    
    
    
    
    def execute_command(self, command: SimpleCommand):
        """Execute a single command"""
        # Delegate to the CommandExecutor
        return self.executor_manager.command_executor.execute(command)
    
    
    def execute_pipeline(self, pipeline: Pipeline):
        """Execute a pipeline"""
        # Delegate to the PipelineExecutor
        return self.executor_manager.pipeline_executor.execute(pipeline)
    
    
    def execute_command_list(self, command_list: StatementList):
        """Execute a command list"""
        # Use visitor executor by default
        if self.use_visitor_executor:
            from .visitor.executor_visitor import ExecutorVisitor
            executor = ExecutorVisitor(self)
            return executor.visit(command_list)
        
        # Otherwise use legacy executor
        return self.executor_manager.statement_executor.execute_command_list(command_list)
    
    def execute_toplevel(self, toplevel: TopLevel):
        """Execute a top-level script/input containing functions and commands."""
        # Use visitor executor by default
        if self.use_visitor_executor:
            from .visitor.executor_visitor import ExecutorVisitor
            executor = ExecutorVisitor(self)
            return executor.visit(toplevel)
        
        # Otherwise use legacy executor
        return self.executor_manager.statement_executor.execute_toplevel(toplevel)
    
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
        
        # Handle different operators
        if expr.operator == '=':
            return left == right
        elif expr.operator == '==':
            return left == right
        elif expr.operator == '!=':
            return left != right
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
    
    def _evaluate_unary_test(self, expr: UnaryTestExpression) -> bool:
        """Evaluate unary test expression."""
        # Expand variables in operand
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
            tokens = tokenize(command_string)
            
            # Debug: Print tokens if requested
            if self.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                from .utils.token_formatter import TokenFormatter
                print(TokenFormatter.format(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Expand aliases
            tokens = self.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Debug: Print AST if requested
            if self.debug_ast:
                print("=== AST Debug Output ===", file=sys.stderr)
                from .visitor import DebugASTVisitor
                debug_visitor = DebugASTVisitor()
                print(debug_visitor.visit(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
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
            
            # Add to history if requested (for interactive or testing)
            if add_to_history and command_string.strip():
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
            # Enhanced error message with location
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
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