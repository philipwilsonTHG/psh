import os
import sys
import subprocess
import readline
import signal
import glob
import pwd
import stat
import fnmatch
import fcntl
from typing import List, Tuple
from .tokenizer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, Pipeline, CommandList, AndOrList, Redirect, TopLevel, FunctionDef, IfStatement, WhileStatement, ForStatement, BreakStatement, ContinueStatement, CaseStatement, CaseItem, CasePattern, ProcessSubstitution, EnhancedTestStatement, TestExpression, BinaryTestExpression, UnaryTestExpression, CompoundTestExpression, NegatedTestExpression
from .line_editor import LineEditor
from .multiline_handler import MultiLineInputHandler
from .version import get_version_info
from .aliases import AliasManager
from .functions import FunctionManager
from .job_control import JobManager, JobState
from .builtins import registry as builtin_registry
from .builtins.function_support import FunctionReturn

# Import from new core modules
from .core.exceptions import LoopBreak, LoopContinue
from .core.state import ShellState
from .utils.ast_formatter import ASTFormatter
from .utils.token_formatter import TokenFormatter
from .expansion.manager import ExpansionManager
from .io_redirect.manager import IOManager
from .executor.base import ExecutorManager
from .scripting.base import ScriptManager
from .interactive.base import InteractiveManager

class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, debug_tokens=False, norc=False, rcfile=None):
        # Initialize state
        self.state = ShellState(args, script_name, debug_ast, 
                              debug_tokens, norc, rcfile)
        
        # Create backward compatibility properties
        self._setup_compatibility_properties()
        
        # Use new builtin registry for migrated builtins
        self.builtin_registry = builtin_registry
        
        # All builtins are now handled by the registry
        self.builtins = {}
        
        # Alias management
        self.alias_manager = AliasManager()
        
        # Function management
        self.function_manager = FunctionManager()
        
        # Job control
        self.job_manager = JobManager()
        
        # Expansion management
        self.expansion_manager = ExpansionManager(self)
        
        # I/O redirection management
        self.io_manager = IOManager(self)
        
        # Executor management
        self.executor_manager = ExecutorManager(self)
        
        # Script handling management
        self.script_manager = ScriptManager(self)
        
        # Interactive features management
        self.interactive_manager = InteractiveManager(self)
        
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
                   'io_manager', 'executor_manager', 'script_manager', 'interactive_manager'):
            super().__setattr__(name, value)
        elif hasattr(self, '_state_properties') and name in self._state_properties:
            setattr(self.state, name, value)
        else:
            super().__setattr__(name, value)
    
    
    
    
    def _handle_variable_assignment(self, args: list) -> int:
        """Handle variable assignment if present. Returns 0 if handled, -1 if not an assignment"""
        if not args or '=' not in args[0] or args[0].startswith('='):
            return -1
        
        # Check if all leading arguments are variable assignments
        assignments = []
        command_start = 0
        
        for i, arg in enumerate(args):
            if '=' in arg and not arg.startswith('='):
                # This looks like a variable assignment
                assignments.append(arg)
                command_start = i + 1
            else:
                # Not an assignment, this is where the command starts
                break
        
        if not assignments:
            return -1
        
        if command_start >= len(args):
            # Only assignments, no command
            for assignment in assignments:
                var_name, var_value = assignment.split('=', 1)
                # Expand variables in the value first
                if '$' in var_value:
                    var_value = self.expansion_manager.expand_string_variables(var_value)
                
                # Expand arithmetic expansion in the value
                if '$((' in var_value and '))' in var_value:
                    # Find and expand all arithmetic expansions
                    import re
                    def expand_arith(match):
                        return str(self.expansion_manager.execute_arithmetic_expansion(match.group(0)))
                    var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
                
                # Expand tilde in the value
                if var_value.startswith('~'):
                    var_value = self.expansion_manager.expand_tilde(var_value)
                self.variables[var_name] = var_value
            return 0
        else:
            # Assignments followed by command - not handled here
            return -1
    
    
    def _execute_builtin(self, args: list, command: Command) -> int:
        """Execute a built-in command with proper redirection handling"""
        # Check new registry first
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            stdin_backup, stdout_backup, stderr_backup = self.io_manager.setup_builtin_redirections(command)
            try:
                # Update sys streams for builtins that might use them
                self.stdout = sys.stdout
                self.stderr = sys.stderr
                self.stdin = sys.stdin
                return builtin.execute(args, self)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
        
        # Fall back to old builtins
        if args[0] in self.builtins:
            stdin_backup, stdout_backup, stderr_backup = self.io_manager.setup_builtin_redirections(command)
            try:
                return self.builtins[args[0]](args)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
        
        # Not a builtin
        return -1
    
    def _execute_external(self, args: list, command: Command) -> int:
        """Execute an external command with proper redirection and process handling"""
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        pid = os.fork()
        
        if pid == 0:  # Child process
            # Set flag to indicate we're in a forked child
            self._in_forked_child = True
            # Create new process group
            os.setpgid(0, 0)
            
            # Reset signal handlers to default
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)
            signal.signal(signal.SIGTTOU, signal.SIG_DFL)
            signal.signal(signal.SIGTTIN, signal.SIG_DFL)
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            
            # Set up redirections
            self.io_manager.setup_child_redirections(command)
            
            # Execute the command
            try:
                os.execvpe(args[0], args, self.env)
            except FileNotFoundError:
                print(f"{args[0]}: command not found", file=sys.stderr)
                os._exit(127)
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                os._exit(1)
        
        else:  # Parent process
            # Set child's process group
            try:
                os.setpgid(pid, pid)
            except:
                pass  # Race condition - child may have already done it
            
            # Create job for tracking
            job = self.job_manager.create_job(pid, ' '.join(args))
            job.add_process(pid, args[0])
            
            if command.background:
                # Background job
                job.foreground = False
                print(f"[{job.job_id}] {pid}")
                self.last_bg_pid = pid
                return 0
            else:
                # Foreground job - give it terminal control
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                if original_pgid is not None:
                    self.foreground_pgid = pid
                    try:
                        os.tcsetpgrp(0, pid)
                    except:
                        pass
                
                # Wait for the job
                exit_status = self.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    self.foreground_pgid = None
                    self.job_manager.set_foreground_job(None)
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
                # Remove completed job
                if job.state == JobState.DONE:
                    self.job_manager.remove_job(job.job_id)
                
                return exit_status
    
    def execute_command(self, command: Command):
        """Execute a single command"""
        # Preprocess here strings to expand variables
        for redirect in command.redirects:
            if redirect.type == '<<<':
                # Expand variables in here string content
                redirect.target = self.expansion_manager.expand_string_variables(redirect.target)
        
        # For now, keep the existing implementation but gradually move to executor
        # This allows us to test incrementally
        
        # Expand arguments (variables, command substitutions, globs)
        args = self.expansion_manager.expand_arguments(command)
        
        if not args:
            return 0
        
        # Separate variable assignments from command
        assignments = []
        command_args = []
        in_command = False
        
        for arg in args:
            if not in_command and '=' in arg and not arg.startswith('='):
                # This is a variable assignment
                assignments.append(arg)
            else:
                # This is part of the command
                in_command = True
                command_args.append(arg)
        
        # If only assignments, handle them
        if not command_args:
            for assignment in assignments:
                var_name, var_value = assignment.split('=', 1)
                # Expand variables in the value first
                if '$' in var_value:
                    var_value = self.expansion_manager.expand_string_variables(var_value)
                
                # Expand arithmetic expansion in the value
                if '$((' in var_value and '))' in var_value:
                    # Find and expand all arithmetic expansions
                    import re
                    def expand_arith(match):
                        return str(self.expansion_manager.execute_arithmetic_expansion(match.group(0)))
                    var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
                
                # Expand tilde in the value
                if var_value.startswith('~'):
                    var_value = self.expansion_manager.expand_tilde(var_value)
                self.variables[var_name] = var_value
            return 0
        
        # Save current values of variables that will be assigned
        saved_vars = {}
        for assignment in assignments:
            var_name = assignment.split('=', 1)[0]
            if var_name in self.variables:
                saved_vars[var_name] = self.variables[var_name]
            else:
                saved_vars[var_name] = None
        
        # Apply temporary assignments
        temp_env_vars = {}
        for assignment in assignments:
            var_name, var_value = assignment.split('=', 1)
            # Expand variables in the value
            if '$' in var_value:
                var_value = self.expansion_manager.expand_string_variables(var_value)
            # Expand arithmetic expansion
            if '$((' in var_value and '))' in var_value:
                import re
                def expand_arith(match):
                    return str(self.expansion_manager.execute_arithmetic_expansion(match.group(0)))
                var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
            # Expand tilde
            if var_value.startswith('~'):
                var_value = self.expansion_manager.expand_tilde(var_value)
            self.variables[var_name] = var_value
            # Also temporarily set in environment for external commands
            temp_env_vars[var_name] = var_value
        
        # Execute the command with temporary variables
        try:
            # Check for function call BEFORE builtin check
            func = self.function_manager.get_function(command_args[0])
            if func:
                result = self._execute_function(func, command_args, command)
            elif self.builtin_registry.has(command_args[0]) or command_args[0] in self.builtins:
                # Execute builtin with command_args instead of args
                result = self._execute_builtin(command_args, command)
            else:
                # External command
                result = self._execute_external(command_args, command)
        finally:
            # Clean up process substitutions
            self.io_manager.cleanup_process_substitutions()
            
            # Restore original variable values
            for var_name, original_value in saved_vars.items():
                if original_value is None:
                    self.variables.pop(var_name, None)
                else:
                    self.variables[var_name] = original_value
        
        return result
    
    def _setup_child_process(self, pgid, command_index, num_commands, pipes):
        """Set up a child process in a pipeline"""
        # Set process group - first child becomes group leader
        if pgid is None:
            pgid = os.getpid()
            os.setpgid(0, pgid)
        else:
            os.setpgid(0, pgid)
        
        # Reset signal handlers to default
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
        
        # Set up pipes
        if command_index > 0:  # Not first command - read from previous pipe
            os.dup2(pipes[command_index-1][0], 0)  # stdin = pipe_read
            
        if command_index < num_commands - 1:  # Not last command - write to next pipe
            os.dup2(pipes[command_index][1], 1)  # stdout = pipe_write
        
        # Close all pipe file descriptors
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        return pgid
    
    def _wait_for_pipeline(self, pids):
        """Wait for all processes in pipeline and return exit status of last"""
        last_status = 0
        for i, pid in enumerate(pids):
            try:
                _, status = os.waitpid(pid, 0)
                if i == len(pids) - 1:  # Last command
                    if os.WIFEXITED(status):
                        last_status = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        last_status = 128 + os.WTERMSIG(status)
                    else:
                        last_status = 1
            except OSError:
                # Child might have been killed by signal
                last_status = 1
        return last_status
    
    def _build_pipeline_string(self, pipeline: Pipeline) -> str:
        """Build a string representation of the pipeline for job display."""
        parts = []
        for command in pipeline.commands:
            cmd_str = ' '.join(command.args) if command.args else ''
            if command.background:
                cmd_str += ' &'
            parts.append(cmd_str)
        return ' | '.join(parts)
    
    def execute_pipeline(self, pipeline: Pipeline):
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            try:
                exit_status = self.execute_command(pipeline.commands[0])
                # Apply negation if needed
                if pipeline.negated:
                    exit_status = 0 if exit_status != 0 else 1
                return exit_status
            except FunctionReturn:
                # Propagate up
                raise
        
        # Build command string for job tracking
        command_string = self._build_pipeline_string(pipeline)
        
        # Execute pipeline using fork and pipe
        num_commands = len(pipeline.commands)
        pipes = []
        pids = []
        pgid = None
        job = None
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        # Create pipes for inter-process communication
        for i in range(num_commands - 1):
            pipe_read, pipe_write = os.pipe()
            pipes.append((pipe_read, pipe_write))
        
        # Fork and execute each command
        for i, command in enumerate(pipeline.commands):
            pid = os.fork()
            
            if pid == 0:  # Child process
                # Set flag to indicate we're in a forked child
                self._in_forked_child = True
                pgid = self._setup_child_process(pgid, i, num_commands, pipes)
                exit_code = self._execute_in_child(command)
                os._exit(exit_code)
            
            else:  # Parent process
                if pgid is None:
                    pgid = pid
                    os.setpgid(pid, pgid)
                else:
                    try:
                        os.setpgid(pid, pgid)
                    except:
                        pass  # Race condition - child may have already done it
                pids.append(pid)
        
        # Create job entry for tracking
        job = self.job_manager.create_job(pgid, command_string)
        for i, pid in enumerate(pids):
            cmd_str = ' '.join(pipeline.commands[i].args) if pipeline.commands[i].args else ''
            job.add_process(pid, cmd_str)
        
        # Give terminal control to the pipeline
        is_background = pipeline.commands[-1].background
        
        if not is_background:
            # Foreground job
            self.foreground_pgid = pgid
            job.foreground = True
            self.job_manager.set_foreground_job(job)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, pgid)
                except:
                    pass
        else:
            # Background job
            job.foreground = False
            print(f"[{job.job_id}] {job.pgid}")
        
        # Parent: Close all pipes
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        # Wait for all children and get exit status
        if not is_background:
            # Foreground job - wait for it
            last_status = self.job_manager.wait_for_job(job)
            
            # Restore terminal control
            self.foreground_pgid = None
            self.job_manager.set_foreground_job(None)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, original_pgid)
                except:
                    pass
            
            # Remove completed job
            if job.state == JobState.DONE:
                self.job_manager.remove_job(job.job_id)
        else:
            # Background job - don't wait
            last_status = 0
            self.last_bg_pid = pids[-1] if pids else None
        
        # Apply negation if needed
        if pipeline.negated:
            last_status = 0 if last_status != 0 else 1
        
        return last_status
    
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        try:
            for item in command_list.statements:
                if isinstance(item, BreakStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, ContinueStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, IfStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_if(item)
                elif isinstance(item, WhileStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_while(item)
                elif isinstance(item, ForStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_for(item)
                elif isinstance(item, CaseStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_case(item)
                elif isinstance(item, EnhancedTestStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_enhanced_test(item)
                elif isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        exit_code = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        exit_code = 1
                elif isinstance(item, AndOrList):
                    # Handle regular and_or_list
                    exit_code = self.executor_manager.statement_executor.execute_and_or_list(item)
                else:
                    print(f"psh: unknown statement type: {type(item).__name__}", file=sys.stderr)
                    exit_code = 1
                self.last_exit_code = exit_code
        except FunctionReturn:
            # Only catch FunctionReturn if we're in a function
            if self.function_stack:
                raise
            # Otherwise it's an error
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        except (LoopBreak, LoopContinue) as e:
            # Re-raise to be handled by enclosing loop
            raise
        return exit_code
    
    def execute_toplevel(self, toplevel: TopLevel):
        """Execute a top-level script/input containing functions and commands."""
        last_exit = 0
        
        try:
            for item in toplevel.items:
                if isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        last_exit = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        last_exit = 1
                elif isinstance(item, CommandList):
                    # Collect here documents if any
                    self.io_manager.collect_heredocs(item)
                    # Execute commands
                    last_exit = self.execute_command_list(item)
                elif isinstance(item, IfStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute if statement
                    last_exit = self.executor_manager.control_flow_executor.execute_if(item)
                elif isinstance(item, WhileStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute while statement
                    last_exit = self.executor_manager.control_flow_executor.execute_while(item)
                elif isinstance(item, ForStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute for statement
                    last_exit = self.executor_manager.control_flow_executor.execute_for(item)
                elif isinstance(item, CaseStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute case statement
                    last_exit = self.executor_manager.control_flow_executor.execute_case(item)
                elif isinstance(item, BreakStatement):
                    # Execute break statement (this will raise LoopBreak)
                    last_exit = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, ContinueStatement):
                    # Execute continue statement (this will raise LoopContinue)  
                    last_exit = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, EnhancedTestStatement):
                    # Execute enhanced test statement
                    last_exit = self.executor_manager.control_flow_executor.execute_enhanced_test(item)
        except (LoopBreak, LoopContinue) as e:
            # Break/continue outside of loops is an error
            stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
            print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
            last_exit = 1
        
        self.last_exit_code = last_exit
        return last_exit
    
    
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
            return self._to_int(left) == self._to_int(right)
        elif expr.operator == '-ne':
            return self._to_int(left) != self._to_int(right)
        elif expr.operator == '-lt':
            return self._to_int(left) < self._to_int(right)
        elif expr.operator == '-le':
            return self._to_int(left) <= self._to_int(right)
        elif expr.operator == '-gt':
            return self._to_int(left) > self._to_int(right)
        elif expr.operator == '-ge':
            return self._to_int(left) >= self._to_int(right)
        elif expr.operator == '-nt':
            # File newer than
            return self._file_newer_than(left, right)
        elif expr.operator == '-ot':
            # File older than
            return self._file_older_than(left, right)
        elif expr.operator == '-ef':
            # Files are the same
            return self._files_same(left, right)
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
    
    def _to_int(self, value: str) -> int:
        """Convert string to integer for numeric comparisons."""
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"integer expression expected: {value}")
    
    def _file_newer_than(self, file1: str, file2: str) -> bool:
        """Check if file1 is newer than file2."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return stat1.st_mtime > stat2.st_mtime
        except FileNotFoundError:
            return False
    
    def _file_older_than(self, file1: str, file2: str) -> bool:
        """Check if file1 is older than file2."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return stat1.st_mtime < stat2.st_mtime
        except FileNotFoundError:
            return False
    
    def _files_same(self, file1: str, file2: str) -> bool:
        """Check if two files are the same (same inode)."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return (stat1.st_dev == stat2.st_dev and 
                    stat1.st_ino == stat2.st_ino)
        except FileNotFoundError:
            return False
    
    def _execute_function(self, func, args: list, command: Command) -> int:
        """Execute a function with given arguments."""
        # Save current positional parameters
        saved_params = self.positional_params
        
        # Set up function environment
        self.positional_params = args[1:]  # args[0] is function name
        self.function_stack.append(func.name)
        
        # Apply redirections for the function call
        stdin_backup, stdout_backup, stderr_backup = self.io_manager.setup_builtin_redirections(command)
        
        try:
            # Execute function body
            exit_code = self.execute_command_list(func.body)
            return exit_code
        except FunctionReturn as ret:
            return ret.exit_code
        finally:
            # Restore redirections
            self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
            # Restore environment
            self.function_stack.pop()
            self.positional_params = saved_params
    
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
                from .utils.ast_formatter import ASTFormatter
                print(ASTFormatter.format(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
            # Add to history if requested (for interactive or testing)
            if add_to_history and command_string.strip():
                self.interactive_manager.history_manager.add_to_history(command_string.strip())
            
            # Increment command number for successful parse
            self.command_number += 1
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                try:
                    # Collect here documents if any
                    self.io_manager.collect_heredocs(ast)
                    exit_code = self.execute_command_list(ast)
                    return exit_code
                except (LoopBreak, LoopContinue) as e:
                    # Break/continue outside of loops is an error
                    stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
                    print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
                    return 1
        except ParseError as e:
            # Enhanced error message with location
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.last_exit_code = 1
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
    
    
    
    
    def _execute_in_child(self, command: Command):
        """Execute a command in a child process (after fork)"""
        # Expand arguments (reuse the same method as execute_command)
        args = self.expansion_manager.expand_arguments(command)
        
        if not args:
            return 0
        
        # Set up redirections
        try:
            self.io_manager.setup_child_redirections(command)
        except Exception as e:
            print(f"psh: {e}", file=sys.stderr)
            return 1
        
        # Check for function call BEFORE builtin check
        func = self.function_manager.get_function(args[0])
        if func:
            # Functions need special handling in child process
            # We can't use the normal _execute_function because it expects Command object
            # Save current positional parameters
            saved_params = self.positional_params
            self.positional_params = args[1:]
            self.function_stack.append(func.name)
            
            try:
                exit_code = self.execute_command_list(func.body)
                return exit_code
            except FunctionReturn as ret:
                return ret.exit_code
            finally:
                self.function_stack.pop()
                self.positional_params = saved_params
        
        # Check for built-in commands (new registry first, then old dict)
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            try:
                return builtin.execute(args, self)
            except FunctionReturn:
                # Should not happen in child process
                print("return: can only `return' from a function or sourced script", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        elif args[0] in self.builtins:
            try:
                return self.builtins[args[0]](args)
            except FunctionReturn:
                # Should not happen in child process
                print("return: can only `return' from a function or sourced script", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        
        # Execute external command
        try:
            # Execute with execvpe to pass environment
            os.execvpe(args[0], args, self.env)
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1
    
    
    
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