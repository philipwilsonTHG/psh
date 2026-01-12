"""
Command execution module for the PSH executor.

This module handles the execution of simple commands, including:
- Variable assignments
- Command expansion
- Builtin, function, and external command execution
- Redirection handling
"""

import os
import sys
import signal
from typing import List, Tuple, Optional, TYPE_CHECKING
from contextlib import contextmanager

from .strategies import (
    ExecutionStrategy,
    SpecialBuiltinExecutionStrategy,
    BuiltinExecutionStrategy,
    FunctionExecutionStrategy,
    AliasExecutionStrategy,
    ExternalExecutionStrategy
)
from ..core.assignment_utils import is_valid_assignment, extract_assignments, is_exported

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import SimpleCommand, Redirect
    from ..expansion.manager import ExpansionManager
    from ..io_redirect.manager import IOManager
    from ..job_control import JobManager
    from .context import ExecutionContext


class CommandExecutor:
    """
    Handles execution of simple commands.
    
    This class encapsulates all logic for executing SimpleCommand nodes,
    including variable assignments, expansions, and delegating to appropriate
    execution strategies.
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the command executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
        
        # Initialize execution strategies
        # Order matters: special builtins > functions > builtins > aliases > external (POSIX compliance)
        self.strategies = [
            SpecialBuiltinExecutionStrategy(),
            FunctionExecutionStrategy(),
            BuiltinExecutionStrategy(),
            AliasExecutionStrategy(),
            ExternalExecutionStrategy()
        ]
    
    def execute(self, node: 'SimpleCommand', context: 'ExecutionContext') -> int:
        """
        Execute a simple command and return exit status.
        
        Args:
            node: The SimpleCommand AST node to execute
            context: The current execution context
            
        Returns:
            Exit status code
        """
        try:
            # Handle array assignments first
            if node.array_assignments:
                for assignment in node.array_assignments:
                    self._handle_array_assignment(assignment)
            
            # Phase 1: Extract raw assignments (before expansion)
            raw_assignments = self._extract_assignments_raw(node)
            
            # Expand only the assignment values
            assignments = []
            for var, value in raw_assignments:
                expanded_value = self._expand_assignment_value(value)
                assignments.append((var, expanded_value))
            
            # Check if we have only assignments (no command)
            # Need to account for split assignments that consume multiple tokens
            tokens_consumed = 0
            for i, (var, value) in enumerate(raw_assignments):
                # Check if this was a split assignment
                if i < len(node.args) - 1:
                    arg = node.args[tokens_consumed]
                    arg_type = node.arg_types[tokens_consumed] if tokens_consumed < len(node.arg_types) else 'WORD'
                    next_arg_type = node.arg_types[tokens_consumed + 1] if tokens_consumed + 1 < len(node.arg_types) else 'WORD'
                    if (arg_type == 'WORD' and arg.endswith('=') and 
                        next_arg_type in ('PARAM_EXPANSION', 'COMMAND_SUB', 
                                         'COMMAND_SUB_BACKTICK', 'ARITH_EXPANSION',
                                         'VARIABLE')):
                        # This assignment consumed 2 tokens
                        tokens_consumed += 2
                    else:
                        # Normal assignment consumed 1 token
                        tokens_consumed += 1
                else:
                    # Last assignment
                    tokens_consumed += 1
            
            if assignments and tokens_consumed == len(node.args):
                # Pure assignment (no command)
                return self._handle_pure_assignments(node, assignments)
            
            # Apply assignments for this command
            saved_vars = self._apply_command_assignments(assignments)
            
            try:
                # Phase 2: Expand remaining arguments with assignments in effect
                # command_start_index needs to account for tokens consumed by assignments
                command_start_index = tokens_consumed
                if command_start_index >= len(node.args):
                    return 0
                
                # Create a sub-node for command arguments only
                from ..ast_nodes import SimpleCommand
                command_node = SimpleCommand(
                    args=node.args[command_start_index:],
                    arg_types=node.arg_types[command_start_index:] if command_start_index < len(node.arg_types) else [],
                    quote_types=node.quote_types[command_start_index:] if command_start_index < len(node.quote_types) else [],
                    redirects=node.redirects,
                    background=node.background
                )
                
                
                # Check for bypass mechanisms before expansion
                bypass_aliases = False
                bypass_functions = False
                if command_node.args and command_node.args[0].startswith('\\'):
                    bypass_aliases = True
                    bypass_functions = True
                    # Remove backslash from the first argument for expansion
                    modified_args = [command_node.args[0][1:]] + command_node.args[1:]
                    command_node = SimpleCommand(
                        args=modified_args,
                        arg_types=command_node.arg_types,
                        quote_types=command_node.quote_types,
                        redirects=command_node.redirects,
                        background=command_node.background
                    )
                
                # Now expand command arguments with assignments in place
                expanded_args = self._expand_arguments(command_node)
                
                if not expanded_args:
                    return 0
                
                cmd_name = expanded_args[0]
                cmd_args = expanded_args[1:]
                
                # Check for empty command after expansion
                if not cmd_name:
                    return 0
                
                
                # Handle xtrace option
                if self.state.options.get('xtrace'):
                    self._print_xtrace(cmd_name, cmd_args)
                
                # Special handling for exec builtin (needs access to redirections)
                if cmd_name == 'exec':
                    return self._handle_exec_builtin(node, expanded_args, assignments)
                
                # Execute the command using appropriate strategy
                return self._execute_with_strategy(
                    cmd_name, cmd_args, node, context, bypass_aliases, bypass_functions
                )
                
            finally:
                # Restore variables (unless exported)
                self._restore_command_assignments(saved_vars)
                
        except Exception as e:
            # Import these here to avoid circular imports
            from ..core.exceptions import LoopBreak, LoopContinue, ReadonlyVariableError, ExpansionError
            from ..builtins.function_support import FunctionReturn
            
            # Re-raise control flow exceptions
            if isinstance(e, (FunctionReturn, LoopBreak, LoopContinue, SystemExit)):
                raise
            
            # Handle other exceptions
            if isinstance(e, ReadonlyVariableError):
                print(f"psh: {e.name}: readonly variable", file=self.state.stderr)
                return 1
            
            if isinstance(e, ExpansionError):
                # Error message already printed by the expansion code
                # In script mode, we should exit the shell
                if self.shell.is_script_mode:
                    sys.exit(1)
                return 1
            
            print(f"psh: {e}", file=sys.stderr)
            return 1
    
    def _expand_arguments(self, node: 'SimpleCommand') -> List[str]:
        """Expand all arguments in a command."""
        return self.expansion_manager.expand_arguments(node)
    
    def _extract_assignments_raw(self, node: 'SimpleCommand') -> List[Tuple[str, str]]:
        """Extract assignments from raw arguments before expansion."""
        assignments = []
        i = 0
        
        while i < len(node.args):
            arg = node.args[i]
            arg_type = node.arg_types[i] if i < len(node.arg_types) else 'WORD'
            
            # Check if this is a WORD ending with = followed by an expansion
            if (arg_type == 'WORD' and arg.endswith('=') and 
                i + 1 < len(node.args) and 
                i + 1 < len(node.arg_types) and
                node.arg_types[i + 1] in ('PARAM_EXPANSION', 'COMMAND_SUB', 
                                         'COMMAND_SUB_BACKTICK', 'ARITH_EXPANSION',
                                         'VARIABLE')):
                # This is an assignment split across tokens
                var = arg[:-1]  # Remove the trailing =
                if self._is_valid_assignment(var + '=x'):  # Check if var name is valid
                    # The value is the next token
                    value = node.args[i + 1]
                    assignments.append((var, value))
                    i += 2  # Skip both tokens
                    continue
                else:
                    # Not a valid assignment, stop here
                    break
            elif arg_type in ('WORD', 'COMPOSITE', 'COMPOSITE_QUOTED'):
                if '=' in arg and self._is_valid_assignment(arg):
                    var, value = arg.split('=', 1)
                    assignments.append((var, value))
                    i += 1
                else:
                    # Stop at first non-assignment
                    break
            else:
                # Stop if we hit a non-WORD type
                break
        
        return assignments

    def _extract_assignments(self, args: List[str]) -> List[Tuple[str, str]]:
        """Extract variable assignments from beginning of arguments."""
        return extract_assignments(args)

    def _is_valid_assignment(self, arg: str) -> bool:
        """Check if argument is a valid variable assignment."""
        return is_valid_assignment(arg)
    
    def _handle_pure_assignments(self, node: 'SimpleCommand', 
                                assignments: List[Tuple[str, str]]) -> int:
        """Handle pure variable assignments (no command)."""
        # Apply redirections first
        with self._apply_redirections(node.redirects):
            # Handle xtrace for assignments
            if self.state.options.get('xtrace'):
                ps4 = self.state.get_variable('PS4', '+ ')
                for var, value in assignments:
                    trace_line = ps4 + f"{var}={value}\n"
                    self.state.stderr.write(trace_line)
                    self.state.stderr.flush()
            
            # Save the current exit code before expansions
            saved_exit_code = self.state.last_exit_code
            
            for var, value in assignments:
                # Apply all expansions to assignment values
                value = self._expand_assignment_value(value)
                try:
                    self.state.set_variable(var, value)
                except:
                    from ..core.exceptions import ReadonlyVariableError
                    print(f"psh: {var}: readonly variable", file=self.state.stderr)
                    return 1
            
            # Return current exit code (from any command substitutions)
            return self.state.last_exit_code
    
    def _apply_command_assignments(self, assignments: List[Tuple[str, str]]) -> dict:
        """Apply variable assignments for command execution.

        For command-prefixed assignments (FOO=bar cmd), we need to:
        1. Set the variable in shell state (for builtins/functions that use $VAR)
        2. Set the variable in shell.env (for external commands that use os.environ)

        Returns a dict with both state and env values for restoration.
        """
        saved_vars = {}

        for var, value in assignments:
            # Save both shell state and environment values
            saved_vars[var] = {
                'state': self.state.get_variable(var),
                'env': self.shell.env.get(var)  # May be None if not in env
            }
            # Apply all expansions to assignment values
            value = self._expand_assignment_value(value)
            try:
                self.state.set_variable(var, value)
                # Also set in shell.env for external commands
                self.shell.env[var] = value
            except:
                from ..core.exceptions import ReadonlyVariableError
                raise ReadonlyVariableError(var)

        return saved_vars
    
    def _restore_command_assignments(self, saved_vars: dict):
        """Restore variables after command execution.

        Restores both shell state and shell.env to their original values.
        Command-prefixed assignments (FOO=bar cmd) are always temporary,
        even for exported variables.
        """
        for var, saved in saved_vars.items():
            # Restore shell state variable
            old_state_value = saved['state']
            if old_state_value is None:
                self.state.unset_variable(var)
            else:
                self.state.set_variable(var, old_state_value)

            # Restore shell.env
            old_env_value = saved['env']
            if old_env_value is None:
                # Variable wasn't in env before, remove it
                if var in self.shell.env:
                    del self.shell.env[var]
            else:
                self.shell.env[var] = old_env_value
    
    def _is_exported(self, var_name: str) -> bool:
        """Check if a variable is exported."""
        return is_exported(var_name)
    
    def _expand_assignment_value(self, value: str) -> str:
        """Expand a value used in variable assignment."""
        # Handle all expansions in order, without word splitting
        
        # 1. Tilde expansion (only at start)
        if value.startswith('~'):
            value = self.expansion_manager.expand_tilde(value)
        
        # 2. Variable and command substitution expansion
        if '$' in value or '`' in value:
            # This complex expansion logic will use the expansion manager
            # For now, use a simplified version
            value = self.expansion_manager.expand_string_variables(value)
        
        return value
    
    def _print_xtrace(self, cmd_name: str, args: List[str]):
        """Print command trace if xtrace is enabled."""
        ps4 = self.state.get_variable('PS4', '+ ')
        trace_line = ps4 + ' '.join([cmd_name] + args) + '\n'
        self.state.stderr.write(trace_line)
        self.state.stderr.flush()
    
    def _execute_with_strategy(self, cmd_name: str, args: List[str],
                              node: 'SimpleCommand', context: 'ExecutionContext', 
                              bypass_aliases: bool = False, bypass_functions: bool = False) -> int:
        """Execute command using the appropriate strategy."""
        original_cmd_name = cmd_name
        
        # Note: The 'command' builtin handles its own bypass logic internally
        
        # Create strategy list based on bypass requirements
        strategies_to_exclude = []
        if bypass_aliases:
            strategies_to_exclude.append(AliasExecutionStrategy)
        if bypass_functions:
            strategies_to_exclude.append(FunctionExecutionStrategy)
            # Note: bypass_functions should NOT exclude special builtins
        
        if strategies_to_exclude:
            strategies_to_use = [
                strategy for strategy in self.strategies 
                if not any(isinstance(strategy, exc_type) for exc_type in strategies_to_exclude)
            ]
        else:
            strategies_to_use = self.strategies
        
        # Find the right strategy
        for strategy in strategies_to_use:
            if strategy.can_execute(cmd_name, self.shell):
                # Check if this is a builtin that needs special redirection handling
                if isinstance(strategy, (SpecialBuiltinExecutionStrategy, BuiltinExecutionStrategy)) and not context.in_pipeline:
                    return self._execute_builtin_with_redirections(
                        cmd_name, args, node, context, strategy
                    )
                else:
                    # Apply normal redirections for other commands or builtins in pipelines
                    with self._apply_redirections(node.redirects):
                        return strategy.execute(
                            cmd_name, args, self.shell, context,
                            node.redirects, node.background
                        )
        
        # Should never reach here as ExternalExecutionStrategy handles everything
        return 127
    
    def _execute_builtin_with_redirections(self, cmd_name: str, args: List[str],
                                          node: 'SimpleCommand', context: 'ExecutionContext',
                                          strategy: ExecutionStrategy) -> int:
        """Execute builtin with special redirection handling."""
        # DEBUG: Log builtin redirection setup
        if self.state.options.get('debug-exec'):
            print(f"DEBUG CommandExecutor: Setting up builtin redirections for '{cmd_name}'", 
                  file=sys.stderr)
            print(f"DEBUG CommandExecutor: Redirections: {[r.type for r in node.redirects]}", 
                  file=sys.stderr)
        
        # Builtins need special redirection handling
        stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = \
            self.io_manager.setup_builtin_redirections(node)
        try:
            # Update shell streams for builtins that might use them
            self.shell.stdout = sys.stdout
            self.shell.stderr = sys.stderr
            self.shell.stdin = sys.stdin
            
            # Execute builtin
            return strategy.execute(
                cmd_name, args, self.shell, context,
                node.redirects, node.background
            )
        finally:
            self.io_manager.restore_builtin_redirections(
                stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup
            )
            # Reset shell stream references
            # Preserve StringIO objects for test frameworks
            import io
            if not isinstance(self.shell.stdout, io.StringIO):
                self.shell.stdout = sys.stdout
            if not isinstance(self.shell.stderr, io.StringIO):
                self.shell.stderr = sys.stderr
            if not isinstance(self.shell.stdin, io.StringIO):
                self.shell.stdin = sys.stdin
    
    @contextmanager
    def _apply_redirections(self, redirects):
        """Context manager for applying and restoring redirections."""
        if not redirects:
            yield
            return
            
        saved_fds = self.io_manager.apply_redirections(redirects)
        try:
            yield
        finally:
            self.io_manager.restore_redirections(saved_fds)
    
    def _handle_array_assignment(self, assignment):
        """Handle array initialization or element assignment."""
        from ..ast_nodes import ArrayInitialization, ArrayElementAssignment
        from .array import ArrayOperationExecutor
        
        # Create array executor for this operation
        array_executor = ArrayOperationExecutor(self.shell)
        
        if isinstance(assignment, ArrayInitialization):
            return array_executor.execute_array_initialization(assignment)
        elif isinstance(assignment, ArrayElementAssignment):
            return array_executor.execute_array_element_assignment(assignment)
        else:
            return 0
    
    def _handle_exec_builtin(self, node: 'SimpleCommand', command_args: List[str], 
                            assignments: List[tuple]) -> int:
        """Handle exec builtin with access to redirections."""
        # Get the exec builtin for command execution
        exec_builtin = self.builtin_registry.get('exec')
        if not exec_builtin:
            print("psh: exec: builtin not found", file=sys.stderr)
            return 127
        
        # Remove 'exec' from command args
        args = command_args[1:] if command_args and command_args[0] == 'exec' else command_args
        
        if not args:
            # exec without command - apply redirections permanently
            # and make variable assignments permanent
            if assignments:
                # Make assignments permanent by exporting them
                for var, value in assignments:
                    self.state.set_variable(var, value)
                    # Also export to environment
                    self.shell.env[var] = value
                    import os
                    os.environ[var] = value
            
            if node.redirects:
                try:
                    self.io_manager.apply_permanent_redirections(node.redirects)
                    return 0
                except Exception as e:
                    print(f"psh: exec: {e}", file=sys.stderr)
                    return 1
            else:
                # No redirections, just succeed
                return 0
        else:
            # exec with command - use the builtin's execute method
            return exec_builtin.execute(['exec'] + args, self.shell)