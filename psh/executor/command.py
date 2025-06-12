"""Single command execution."""
import os
import sys
import signal
from typing import List, Optional
from ..ast_nodes import Command, SimpleCommand
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn
from ..job_control import JobState

class CommandExecutor(ExecutorComponent):
    """Executes single commands (builtins, functions, or external)."""
    
    def execute(self, command: SimpleCommand) -> int:
        """Execute a single command and return exit status."""
        # Handle array assignments first
        if command.array_assignments:
            exit_code = self._handle_array_assignments(command.array_assignments)
            if exit_code != 0:
                return exit_code
        
        # Preprocess here strings to expand variables
        for redirect in command.redirects:
            if redirect.type == '<<<':
                # Expand variables in here string content
                redirect.target = self.expansion_manager.expand_string_variables(redirect.target)
        
        # Expand arguments (variables, command substitutions, globs)
        args = self.expansion_manager.expand_arguments(command)
        
        if not args:
            # If we only had array assignments, that's fine
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
        
        # Trace command execution if xtrace is enabled
        if self.state.options.get('xtrace', False):
            from ..core.options import OptionHandler
            # Show the full command including assignments
            OptionHandler.print_xtrace(self.state, args)
        
        # If only assignments, handle them
        if not command_args:
            return self._handle_pure_assignments(assignments)
        
        # Execute with temporary variable assignments
        return self._execute_with_assignments(assignments, command_args, command)
    
    def _is_variable_assignment(self, args: List[str]) -> bool:
        """Check if command is a variable assignment."""
        if not args or '=' not in args[0] or args[0].startswith('='):
            return False
        
        # Check if all leading arguments are assignments
        for arg in args:
            if '=' not in arg:
                return False
        return True
    
    def _handle_pure_assignments(self, assignments: List[str]) -> int:
        """Handle pure variable assignments (no command)."""
        import re
        
        for assignment in assignments:
            var_name, var_value = assignment.split('=', 1)
            
            # Expand variables in the value first
            # Special case: Don't expand if this looks like a prompt string with escape sequences
            # This is a heuristic since we've lost quote information in COMPOSITE arguments
            is_likely_prompt = (var_name in ('PS1', 'PS2') and 
                              any(seq in var_value for seq in ['\\u', '\\h', '\\w', '\\t', '\\!', '\\#', '\\$']))
            
            if '$' in var_value and not is_likely_prompt:
                var_value = self.expansion_manager.expand_string_variables(var_value)
            
            # Expand arithmetic expansion in the value
            if '$((' in var_value and '))' in var_value:
                # Find and expand all arithmetic expansions using proper nesting
                import re
                result = []
                i = 0
                while i < len(var_value):
                    if var_value[i:i+3] == '$((':
                        # Find matching ))
                        paren_count = 2
                        j = i + 3
                        while j < len(var_value) and paren_count > 0:
                            if var_value[j] == '(':
                                paren_count += 1
                            elif var_value[j] == ')':
                                paren_count -= 1
                            j += 1
                        if paren_count == 0:
                            # Found complete arithmetic expression
                            arith_expr = var_value[i:j]
                            result.append(str(self.expansion_manager.execute_arithmetic_expansion(arith_expr)))
                            i = j
                            continue
                    result.append(var_value[i])
                    i += 1
                var_value = ''.join(result)
            
            # Expand tilde in the value
            if var_value.startswith('~'):
                var_value = self.expansion_manager.expand_tilde(var_value)
            
            self.state.set_variable(var_name, var_value)
        return 0
    
    def _handle_array_assignments(self, array_assignments: List) -> int:
        """Handle array assignments (initialization and element assignment)."""
        from ..ast_nodes import ArrayInitialization, ArrayElementAssignment
        from ..core.variables import Variable, IndexedArray, VarAttributes
        
        for assignment in array_assignments:
            if isinstance(assignment, ArrayInitialization):
                # Create a new indexed array
                array = IndexedArray()
                
                # Populate the array with elements
                for i, element in enumerate(assignment.elements):
                    # Expand variables in the element value
                    expanded_value = self.expansion_manager.expand_string_variables(element)
                    array.set(i, expanded_value)
                
                # Create a Variable with the array attribute
                var = Variable(
                    name=assignment.name,
                    value=array,
                    attributes=VarAttributes.ARRAY
                )
                
                # Store in the shell state using enhanced scope manager
                self.state.scope_manager.set_variable(assignment.name, array, attributes=VarAttributes.ARRAY)
                
            elif isinstance(assignment, ArrayElementAssignment):
                # Get the existing array or create a new one
                var = self.state.scope_manager.get_variable_object(assignment.name)
                
                if var is None or not isinstance(var.value, IndexedArray):
                    # Create a new array if it doesn't exist
                    array = IndexedArray()
                    var = Variable(
                        name=assignment.name,
                        value=array,
                        attributes=VarAttributes.ARRAY
                    )
                    self.state.scope_manager.set_variable(assignment.name, array, attributes=VarAttributes.ARRAY)
                else:
                    array = var.value
                
                # Evaluate the index (it might be an expression)
                try:
                    # Expand variables in the index
                    # Note: assignment.index might be 'i' or '$i' or '0' etc
                    if assignment.index.isdigit():
                        # Direct numeric index
                        expanded_index = assignment.index
                    elif assignment.index.startswith('$((') and assignment.index.endswith('))'):
                        # Arithmetic expansion
                        expanded_index = str(self.expansion_manager.execute_arithmetic_expansion(assignment.index))
                    elif assignment.index.startswith('$'):
                        # Variable with $ prefix
                        expanded_index = self.expansion_manager.expand_variable(assignment.index)
                    else:
                        # Variable name without $ prefix
                        expanded_index = self.expansion_manager.expand_variable('$' + assignment.index)
                    
                    # Check if it's an arithmetic expression
                    if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                        # Evaluate as arithmetic
                        from ..arithmetic import evaluate_arithmetic, ArithmeticError
                        try:
                            index = evaluate_arithmetic(expanded_index, self.shell)
                        except (ArithmeticError, Exception):
                            print(f"psh: {assignment.name}: bad array subscript", file=sys.stderr)
                            return 1
                    else:
                        # Try to convert to integer
                        index = int(expanded_index)
                except ValueError:
                    print(f"psh: {assignment.name}: bad array subscript", file=sys.stderr)
                    return 1
                
                # Expand variables in the value
                expanded_value = self.expansion_manager.expand_string_variables(assignment.value)
                
                # Set the array element
                try:
                    array.set(index, expanded_value)
                except ValueError as e:
                    print(f"psh: {assignment.name}: {e}", file=sys.stderr)
                    return 1
        
        return 0
    
    def _execute_with_assignments(self, assignments: List[str], command_args: List[str], 
                                  command: Command) -> int:
        """Execute command with temporary variable assignments."""
        import re
        
        # Save current values of variables that will be assigned
        saved_vars = {}
        for assignment in assignments:
            var_name = assignment.split('=', 1)[0]
            current_value = self.state.get_variable(var_name, None)
            if current_value is not None:
                saved_vars[var_name] = current_value
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
                def expand_arith(match):
                    return str(self.expansion_manager.execute_arithmetic_expansion(match.group(0)))
                var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
            # Expand tilde
            if var_value.startswith('~'):
                var_value = self.expansion_manager.expand_tilde(var_value)
            self.state.set_variable(var_name, var_value)
            # Also temporarily set in environment for external commands
            temp_env_vars[var_name] = var_value
        
        # Execute the command with temporary variables
        try:
            # Check for function call BEFORE builtin check
            func = self.function_manager.get_function(command_args[0])
            if func:
                result = self._execute_function(func, command_args, command)
            elif self.builtin_registry.has(command_args[0]) or command_args[0] in self.shell.builtins:
                # Execute builtin with command_args
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
                    # Variable didn't exist before, unset it
                    self.state.scope_manager.unset_variable(var_name)
                else:
                    self.state.set_variable(var_name, original_value)
        
        return result
    
    def _execute_function(self, func, args: List[str], command: Command) -> int:
        """Execute a shell function."""
        # Save current positional parameters
        saved_params = self.state.positional_params
        
        # Push new variable scope for the function
        self.state.scope_manager.push_scope(func.name)
        
        # Set up function environment
        self.state.positional_params = args[1:]  # args[0] is function name
        self.state.function_stack.append(func.name)
        
        # Apply redirections for the function call
        stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = self.io_manager.setup_builtin_redirections(command)
        
        try:
            # Execute function body
            exit_code = self.shell.execute_command_list(func.body)
            return exit_code
        except FunctionReturn as ret:
            return ret.exit_code
        finally:
            # Restore redirections
            self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup)
            # Pop variable scope (destroys local variables)
            self.state.scope_manager.pop_scope()
            # Restore environment
            self.state.function_stack.pop()
            self.state.positional_params = saved_params
    
    def _execute_builtin(self, args: List[str], command: Command) -> int:
        """Execute a builtin command."""
        # Check new registry first
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = self.io_manager.setup_builtin_redirections(command)
            try:
                # Update sys streams for builtins that might use them
                self.state.stdout = sys.stdout
                self.state.stderr = sys.stderr
                self.state.stdin = sys.stdin
                return builtin.execute(args, self.shell)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup)
        
        # Fall back to old builtins
        if args[0] in self.shell.builtins:
            stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = self.io_manager.setup_builtin_redirections(command)
            try:
                return self.shell.builtins[args[0]](args)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self.io_manager.restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup)
        
        # Not a builtin
        return -1
    
    def _execute_external(self, args: List[str], command: Command) -> int:
        """Execute an external command with proper redirection and process handling."""
        # Sync exported variables to environment before forking
        self.state.scope_manager.sync_exports_to_environment(self.state.env)
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        pid = os.fork()
        
        if pid == 0:  # Child process
            # Set flag to indicate we're in a forked child
            self.state._in_forked_child = True
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
                os.execvpe(args[0], args, self.state.env)
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
                self.state.last_bg_pid = pid
                return 0
            else:
                # Foreground job - give it terminal control
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                if original_pgid is not None:
                    self.state.foreground_pgid = pid
                    try:
                        os.tcsetpgrp(0, pid)
                    except:
                        pass
                
                # Wait for the job
                exit_status = self.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    self.state.foreground_pgid = None
                    self.job_manager.set_foreground_job(None)
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
                # Remove completed job
                if job.state == JobState.DONE:
                    self.job_manager.remove_job(job.job_id)
                
                return exit_status
    
    def execute_in_child(self, command: SimpleCommand):
        """Execute a command in a child process (after fork)"""
        # Handle array assignments first
        if command.array_assignments:
            exit_code = self._handle_array_assignments(command.array_assignments)
            if exit_code != 0:
                return exit_code
        
        # Expand arguments (reuse the same method as execute_command)
        args = self.expansion_manager.expand_arguments(command)
        
        if not args:
            return 0
        
        # Trace command execution if xtrace is enabled
        if self.state.options.get('xtrace', False):
            # Format the trace output with + prefix
            trace_output = '+ ' + ' '.join(args)
            print(trace_output, file=sys.stderr)
        
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
            saved_params = self.state.positional_params
            
            # Push new variable scope for the function
            self.state.scope_manager.push_scope(func.name)
            
            self.state.positional_params = args[1:]
            self.state.function_stack.append(func.name)
            
            try:
                exit_code = self.shell.execute_command_list(func.body)
                return exit_code
            except FunctionReturn as ret:
                return ret.exit_code
            finally:
                # Pop variable scope (destroys local variables)
                self.state.scope_manager.pop_scope()
                self.state.function_stack.pop()
                self.state.positional_params = saved_params
        
        # Check for built-in commands (new registry first, then old dict)
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            try:
                return builtin.execute(args, self.shell)
            except FunctionReturn:
                # Should not happen in child process
                print("return: can only `return' from a function or sourced script", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        elif args[0] in self.shell.builtins:
            try:
                return self.shell.builtins[args[0]](args)
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
            os.execvpe(args[0], args, self.state.env)
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1