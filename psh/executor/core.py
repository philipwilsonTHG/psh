"""
Executor visitor that executes AST nodes using the visitor pattern.

This visitor provides a clean architecture for command execution while
maintaining compatibility with the existing execution engine.
"""

import os
import sys
import subprocess
import signal
from typing import List, Tuple, Optional, Dict, Any, Union
from contextlib import contextmanager

from ..visitor.base import ASTVisitor
from .context import ExecutionContext
from .pipeline import PipelineContext, PipelineExecutor
from .command import CommandExecutor
from .control_flow import ControlFlowExecutor
from .array import ArrayOperationExecutor
from .function import FunctionOperationExecutor
from .subshell import SubshellExecutor
from ..ast_nodes import (
    # Core nodes
    ASTNode, TopLevel, StatementList, AndOrList, Pipeline,
    SimpleCommand, Redirect,
    
    # Control structures
    WhileLoop, ForLoop, CStyleForLoop, IfConditional, 
    CaseConditional, CaseItem, SelectLoop,
    BreakStatement, ContinueStatement,
    
    # Function nodes
    FunctionDef,
    
    # Arithmetic
    ArithmeticEvaluation,
    
    # Test commands
    EnhancedTestStatement,
    
    # Array operations
    ArrayInitialization, ArrayElementAssignment,
    
    # Other
    ProcessSubstitution, SubshellGroup, BraceGroup
)
from ..core.exceptions import LoopBreak, LoopContinue, UnboundVariableError, ReadonlyVariableError
from ..builtins.function_support import FunctionReturn
from ..job_control import JobState


class ExecutorVisitor(ASTVisitor[int]):
    """
    Visitor that executes AST nodes and returns exit status.
    
    This visitor maintains compatibility with the existing execution
    engine while providing a cleaner architecture based on the visitor
    pattern.
    """
    
    def __init__(self, shell: 'Shell'):
        """
        Initialize executor with shell instance.
        
        Args:
            shell: The shell instance providing access to all components
        """
        super().__init__()  # Initialize method cache
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
        
        # Execution context - replaces scattered state variables
        self.context = ExecutionContext()
        
        # Command executor - handles simple command execution
        self.command_executor = CommandExecutor(shell)
        
        # Pipeline executor - handles pipeline execution
        self.pipeline_executor = PipelineExecutor(shell)
        
        # Control flow executor - handles control structures
        self.control_flow_executor = ControlFlowExecutor(shell)
        
        # Array operation executor - handles array operations
        self.array_executor = ArrayOperationExecutor(shell)
        
        # Function operation executor - handles function operations
        self.function_executor = FunctionOperationExecutor(shell)
        
        # Subshell executor - handles subshells and brace groups
        self.subshell_executor = SubshellExecutor(shell)
    
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
    
    # Top-level execution
    
    def visit_TopLevel(self, node: TopLevel) -> int:
        """Execute top-level statements."""
        exit_status = 0
        
        for item in node.items:
            try:
                exit_status = self.visit(item)
                # Update $? after each top-level item
                self.state.last_exit_code = exit_status
            except LoopBreak:
                # Break at top level is an error
                print("break: only meaningful in a `for' or `while' loop", file=sys.stderr)
                exit_status = 1
                self.state.last_exit_code = exit_status
            except LoopContinue:
                # Continue at top level is an error
                print("continue: only meaningful in a `for' or `while' loop", file=sys.stderr)
                exit_status = 1
                self.state.last_exit_code = exit_status
            except SystemExit:
                # Let exit propagate
                raise
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print()  # New line after ^C
                exit_status = 130
                self.state.last_exit_code = exit_status
        
        return exit_status
    
    def visit_StatementList(self, node: StatementList) -> int:
        """Execute a list of statements."""
        exit_status = 0
        
        for statement in node.statements:
            try:
                exit_status = self.visit(statement)
                # Update $? after each statement
                self.state.last_exit_code = exit_status
            except FunctionReturn:
                # Function return should propagate up
                raise
            except (LoopBreak, LoopContinue):
                # Re-raise if we're in a loop, otherwise it's an error
                if self.context.loop_depth > 0:
                    raise
                # Not in a loop - this was already reported by visit_BreakStatement/visit_ContinueStatement
                exit_status = 1
                self.state.last_exit_code = exit_status
                # Don't continue executing statements after break/continue error
                break
        
        return exit_status
    
    def visit_AndOrList(self, node: AndOrList) -> int:
        """Execute pipelines with && and || operators."""
        if not node.pipelines:
            return 0
        
        # Execute first pipeline
        exit_status = self.visit(node.pipelines[0])
        self.state.last_exit_code = exit_status
        
        # Process remaining pipelines based on operators
        for i, op in enumerate(node.operators):
            if op == '&&' and exit_status == 0:
                # Execute next pipeline only if previous succeeded
                exit_status = self.visit(node.pipelines[i + 1])
            elif op == '||' and exit_status != 0:
                # Execute next pipeline only if previous failed
                exit_status = self.visit(node.pipelines[i + 1])
            # Otherwise skip this pipeline
            
            self.state.last_exit_code = exit_status
        
        return exit_status
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        """Execute a pipeline of commands."""
        # Delegate to PipelineExecutor
        return self.pipeline_executor.execute(node, self.context, self)
    
    # Simple command execution
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        """Execute a simple command (builtin or external)."""
        # Delegate to CommandExecutor
        return self.command_executor.execute(node, self.context)
    
    # Control structures
    
    def visit_IfConditional(self, node: IfConditional) -> int:
        """Execute if/then/else statement."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_if(node, self.context, self)
    
    def visit_WhileLoop(self, node: WhileLoop) -> int:
        """Execute while loop."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_while(node, self.context, self)
    
    def visit_ForLoop(self, node: ForLoop) -> int:
        """Execute for loop."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_for(node, self.context, self)
    
    
    def visit_CaseConditional(self, node: CaseConditional) -> int:
        """Execute case statement."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_case(node, self.context, self)
    
    
    def visit_BreakStatement(self, node: BreakStatement) -> int:
        """Execute break statement."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_break(node, self.context)
    
    def visit_ContinueStatement(self, node: ContinueStatement) -> int:
        """Execute continue statement."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_continue(node, self.context)
    
    def visit_SubshellGroup(self, node: SubshellGroup) -> int:
        """Execute subshell group (...) in isolated environment."""
        # Delegate to SubshellExecutor
        return self.subshell_executor.execute_subshell(node, self.context, self)
    
    def visit_BraceGroup(self, node: BraceGroup) -> int:
        """Execute brace group {...} in current shell environment."""
        # Delegate to SubshellExecutor
        return self.subshell_executor.execute_brace_group(node, self.context, self)
    
    def visit_FunctionDef(self, node: FunctionDef) -> int:
        """Define a function."""
        # Delegate to FunctionOperationExecutor
        return self.function_executor.execute_function_def(node)
    
    # Helper methods
    
    def _expand_arguments(self, node: SimpleCommand) -> List[str]:
        """Expand all arguments in a command."""
        # Use expansion manager's expand_arguments method
        return self.expansion_manager.expand_arguments(node)
    
    def _extract_assignments(self, args: List[str]) -> List[Tuple[str, str]]:
        """Extract variable assignments from beginning of arguments."""
        assignments = []
        
        for arg in args:
            if '=' in arg and self._is_valid_assignment(arg):
                var, value = arg.split('=', 1)
                assignments.append((var, value))
            else:
                # Stop at first non-assignment
                break
        
        return assignments
    
    def _is_valid_assignment(self, arg: str) -> bool:
        """Check if argument is a valid variable assignment."""
        if '=' not in arg:
            return False
        
        var_name = arg.split('=', 1)[0]
        # Variable name must start with letter or underscore
        if not var_name or not (var_name[0].isalpha() or var_name[0] == '_'):
            return False
        
        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in var_name[1:])
    
    def _is_exported(self, var_name: str) -> bool:
        """Check if a variable is exported."""
        # This would check variable attributes when implemented
        return var_name in os.environ
    
    
    def _evaluate_arithmetic(self, expr: str) -> int:
        """Evaluate arithmetic expression."""
        # Use the shell's arithmetic evaluator
        from ..arithmetic import evaluate_arithmetic
        return evaluate_arithmetic(expr, self.shell)
    
    def _expand_assignment_value(self, value: str) -> str:
        """Expand a value used in variable assignment."""
        # Handle all expansions in order, without word splitting
        
        # 1. Tilde expansion (only at start)
        if value.startswith('~'):
            value = self.expansion_manager.expand_tilde(value)
        
        # 2. Variable expansion (including ${var} forms)
        if '$' in value:
            # We need to handle command substitution separately from variable expansion
            # to preserve the exact semantics
            result = []
            i = 0
            while i < len(value):
                if i < len(value) - 1 and value[i:i+2] == '$(':
                    # Find matching )
                    paren_count = 1
                    j = i + 2
                    while j < len(value) and paren_count > 0:
                        if value[j] == '(':
                            paren_count += 1
                        elif value[j] == ')':
                            paren_count -= 1
                        j += 1
                    if paren_count == 0:
                        # Found complete command substitution
                        cmd_sub = value[i:j]
                        output = self.expansion_manager.execute_command_substitution(cmd_sub)
                        result.append(output)
                        i = j
                        continue
                elif value[i] == '`':
                    # Find matching backtick
                    j = i + 1
                    while j < len(value) and value[j] != '`':
                        j += 1
                    if j < len(value):
                        # Found complete backtick command substitution
                        cmd_sub = value[i:j+1]
                        output = self.expansion_manager.execute_command_substitution(cmd_sub)
                        result.append(output)
                        i = j + 1
                        continue
                elif i < len(value) - 2 and value[i:i+3] == '$((': 
                    # Arithmetic expansion
                    # Find matching ))
                    paren_count = 2
                    j = i + 3
                    while j < len(value) and paren_count > 0:
                        if value[j] == '(':
                            paren_count += 1
                        elif value[j] == ')':
                            paren_count -= 1
                        j += 1
                    if paren_count == 0:
                        # Found complete arithmetic expression
                        arith_expr = value[i:j]
                        result.append(str(self.expansion_manager.execute_arithmetic_expansion(arith_expr)))
                        i = j
                        continue
                
                result.append(value[i])
                i += 1
            
            value = ''.join(result)
            
            # Now expand remaining variables
            value = self.expansion_manager.expand_string_variables(value)
        
        return value
    
    # Additional node type implementations
    
    def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> int:
        """Execute arithmetic command: ((expression))"""
        from ..arithmetic import evaluate_arithmetic
        
        try:
            # Apply redirections if any
            with self._apply_redirections(node.redirects):
                result = evaluate_arithmetic(node.expression, self.shell)
                # Bash behavior: exit 0 if expression is true (non-zero)
                # exit 1 if expression is false (zero)
                return 0 if result != 0 else 1
        except Exception as e:
            print(f"psh: ((: {e}", file=sys.stderr)
            return 1
    
    def visit_CStyleForLoop(self, node: CStyleForLoop) -> int:
        """Execute C-style for loop: for ((init; cond; update))"""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_c_style_for(node, self.context, self)
    
    def visit_SelectLoop(self, node: SelectLoop) -> int:
        """Execute select loop for interactive menu selection."""
        # Delegate to ControlFlowExecutor
        return self.control_flow_executor.execute_select(node, self.context, self)
    
    
    def visit_EnhancedTestStatement(self, node: EnhancedTestStatement) -> int:
        """Execute enhanced test: [[ expression ]]"""
        # Delegate to shell's existing implementation
        return self.shell.execute_enhanced_test_statement(node)
    
    # Array operations
    
    def visit_ArrayInitialization(self, node: ArrayInitialization) -> int:
        """Execute array initialization: arr=(a b c)"""
        # Delegate to ArrayOperationExecutor
        return self.array_executor.execute_array_initialization(node)
    
    def visit_ArrayElementAssignment(self, node: ArrayElementAssignment) -> int:
        """Execute array element assignment: arr[i]=value"""
        # Delegate to ArrayOperationExecutor
        return self.array_executor.execute_array_element_assignment(node)
    
    # Exec builtin implementation
    
    def _handle_exec_builtin(self, node: SimpleCommand, command_args: List[str], assignments: List[tuple]) -> int:
        """Handle exec builtin with access to redirections."""
        exec_args = command_args[1:]  # Remove 'exec' itself
        
        # Handle xtrace option
        if self.state.options.get('xtrace'):
            ps4 = self.state.get_variable('PS4', '+ ')
            trace_line = ps4 + ' '.join(command_args) + '\n'
            self.state.stderr.write(trace_line)
            self.state.stderr.flush()
        
        # Apply environment variable assignments permanently for exec
        for var, value in assignments:
            expanded_value = self._expand_assignment_value(value)
            self.state.set_variable(var, expanded_value)
            # Also set in environment for exec
            os.environ[var] = expanded_value
        
        try:
            if exec_args:
                # Mode 1: exec with command - replace the shell process
                return self._exec_with_command(node, exec_args)
            else:
                # Mode 2: exec without command - apply redirections permanently
                return self._exec_without_command(node)
                
        except OSError as e:
            if e.errno == 2:  # No such file or directory
                print(f"exec: {exec_args[0]}: command not found", file=sys.stderr)
                return 127
            elif e.errno == 13:  # Permission denied  
                print(f"exec: {exec_args[0]}: Permission denied", file=sys.stderr)
                return 126
            else:
                print(f"exec: {exec_args[0]}: {e}", file=sys.stderr)
                return 126
        except Exception as e:
            print(f"exec: {e}", file=sys.stderr)
            return 1
    
    def _exec_with_command(self, node: SimpleCommand, args: List[str]) -> int:
        """Handle exec with command - replace the shell process."""
        cmd_name = args[0]
        cmd_args = args
        
        # Apply redirections before exec
        if node.redirects:
            try:
                # Apply redirections permanently (don't restore them)
                self.io_manager.apply_permanent_redirections(node.redirects)
            except Exception as e:
                print(f"exec: {e}", file=sys.stderr)
                return 1
        
        # exec bypasses builtins and functions - look for external command in PATH
        command_path = self._find_command_in_path(cmd_name)
        if not command_path:
            print(f"exec: {cmd_name}: command not found", file=sys.stderr)
            return 127
        
        # Check if command is executable
        if not os.access(command_path, os.X_OK):
            print(f"exec: {cmd_name}: Permission denied", file=sys.stderr)
            return 126
        
        # Reset signal handlers to default
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGQUIT, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        
        # Replace the current process with the command
        try:
            os.execv(command_path, cmd_args)
        except OSError as e:
            # This should not return, but if it does, there was an error
            print(f"exec: {cmd_name}: {e}", file=sys.stderr)
            return 126
    
    def _exec_without_command(self, node: SimpleCommand) -> int:
        """Handle exec without command - apply redirections permanently."""
        if not node.redirects:
            # No redirections, just return success
            return 0
        
        try:
            # Apply redirections permanently (don't restore them)
            self.io_manager.apply_permanent_redirections(node.redirects)
            return 0
        except Exception as e:
            print(f"exec: {e}", file=sys.stderr)
            return 1
    
    def _find_command_in_path(self, cmd_name: str) -> str:
        """Find command in PATH, return full path or None."""
        # If command contains '/', it's a path
        if '/' in cmd_name:
            if os.path.isfile(cmd_name):
                return cmd_name
            return None
        
        # Search in PATH
        path_env = os.environ.get('PATH', '')
        for path_dir in path_env.split(':'):
            if not path_dir:
                continue
            full_path = os.path.join(path_dir, cmd_name)
            if os.path.isfile(full_path):
                return full_path
        
        return None
    
    # Fallback for unimplemented nodes
    
    def generic_visit(self, node: ASTNode) -> int:
        """Fallback for unimplemented node types."""
        node_name = type(node).__name__
        
        # Try to handle some common unimplemented nodes
        if node_name == "CommandList":
            # CommandList is likely an alias for StatementList
            return self.visit_StatementList(node)
        
        print(f"ExecutorVisitor: Unimplemented node type: {node_name}", 
              file=sys.stderr)
        return 1