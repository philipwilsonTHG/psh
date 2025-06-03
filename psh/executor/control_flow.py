"""Control flow statement execution."""
from typing import List
from ..ast_nodes import (IfStatement, WhileStatement, ForStatement, 
                         CaseStatement, BreakStatement, ContinueStatement, EnhancedTestStatement)
from .base import ExecutorComponent
from ..core.exceptions import LoopBreak, LoopContinue

class ControlFlowExecutor(ExecutorComponent):
    """Executes control flow statements."""
    
    def execute(self, node) -> int:
        """Execute a control flow statement."""
        if isinstance(node, IfStatement):
            return self.execute_if(node)
        elif isinstance(node, WhileStatement):
            return self.execute_while(node)
        elif isinstance(node, ForStatement):
            return self.execute_for(node)
        elif isinstance(node, CaseStatement):
            return self.execute_case(node)
        elif isinstance(node, BreakStatement):
            raise LoopBreak(node.level)
        elif isinstance(node, ContinueStatement):
            raise LoopContinue(node.level)
        else:
            raise ValueError(f"Unknown control flow node: {type(node)}")
    
    def execute_enhanced_test(self, node: EnhancedTestStatement) -> int:
        """Execute enhanced test statement [[...]]."""
        return self.shell.execute_enhanced_test_statement(node)
    
    def execute_if(self, node: IfStatement) -> int:
        """Execute if/then/else statement."""
        # Apply redirections if present
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            # Execute condition
            condition_status = self.shell.execute_command_list(node.condition)
            
            if condition_status == 0:
                # Condition true, execute then part
                return self.shell.execute_command_list(node.then_part)
            
            # Check elif parts
            for elif_condition, elif_then in node.elif_parts:
                elif_status = self.shell.execute_command_list(elif_condition)
                if elif_status == 0:
                    return self.shell.execute_command_list(elif_then)
            
            # Execute else part if present
            if node.else_part:
                return self.shell.execute_command_list(node.else_part)
            
            return 0
        finally:
            # Restore file descriptors
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def execute_while(self, node: WhileStatement) -> int:
        """Execute while loop."""
        # Apply redirections if present
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            last_status = 0
            
            while True:
                try:
                    # Execute condition
                    condition_status = self.shell.execute_command_list(node.condition)
                    
                    if condition_status != 0:
                        # Condition false, exit loop
                        break
                    
                    # Execute body
                    last_status = self.shell.execute_command_list(node.body)
                    
                except LoopBreak as e:
                    if e.level > 1:
                        raise LoopBreak(e.level - 1)
                    break
                except LoopContinue as e:
                    if e.level > 1:
                        raise LoopContinue(e.level - 1)
                    continue
            
            return last_status
        finally:
            # Restore file descriptors
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def execute_for(self, node: ForStatement) -> int:
        """Execute for loop."""
        # Apply redirections if present
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            # Expand the word list
            expanded_items = []
            for item in node.iterable:
                # Handle each item based on its type
                expanded = self._expand_for_item(item)
                expanded_items.extend(expanded)
            
            last_status = 0
            
            # Save the current value of the loop variable (if it exists)
            loop_var = node.variable
            saved_value = self.state.variables.get(loop_var)
            
            try:
                for item in expanded_items:
                    try:
                        # Set loop variable
                        self.state.set_variable(loop_var, item)
                        
                        # Execute body
                        last_status = self.shell.execute_command_list(node.body)
                        
                    except LoopBreak as e:
                        if e.level > 1:
                            raise LoopBreak(e.level - 1)
                        break
                    except LoopContinue as e:
                        if e.level > 1:
                            raise LoopContinue(e.level - 1)
                        continue
            finally:
                # Restore the previous value of the loop variable
                if saved_value is not None:
                    self.state.variables[loop_var] = saved_value
                else:
                    # Variable didn't exist before, remove it
                    self.state.variables.pop(loop_var, None)
            
            return last_status
        finally:
            # Restore file descriptors
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def execute_case(self, node: CaseStatement) -> int:
        """Execute case statement."""
        # Apply redirections if present
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            # Expand the expression
            expanded_expr = self._expand_case_expr(node.expr)
            
            last_exit = 0
            fallthrough = False
            
            # Try each case item
            for item in node.items:
                # Check if expression matches any pattern in this item
                matched = fallthrough  # Start with fallthrough state
                
                if not fallthrough:
                    # Only check patterns if not falling through
                    if self._match_case_pattern(expanded_expr, item.patterns):
                        matched = True
                
                if matched:
                    # Execute commands for this case
                    if item.commands.statements:
                        last_exit = self.shell.execute_command_list(item.commands)
                    
                    # Handle terminator
                    if item.terminator == ';;':
                        # Standard terminator - stop after this case
                        break
                    elif item.terminator == ';&':
                        # Fallthrough to next case unconditionally
                        fallthrough = True
                    elif item.terminator == ';;&':
                        # Continue pattern matching (reset fallthrough)
                        fallthrough = False
                    else:
                        # Default to standard behavior
                        break
                else:
                    # Reset fallthrough if no match
                    fallthrough = False
            
            return last_exit
        finally:
            # Restore file descriptors
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def _expand_for_item(self, item):
        """Expand a for loop item."""
        # For now, delegate to shell's expansion logic
        # This will be properly implemented when we integrate
        if item == '$@':
            return self.state.positional_params
        elif item.startswith('$(') and item.endswith(')'):
            # Command substitution
            output = self.expansion_manager.execute_command_substitution(item)
            if output:
                return output.split()
            return []
        elif item.startswith('`') and item.endswith('`'):
            # Backtick command substitution
            output = self.expansion_manager.execute_command_substitution(item)
            if output:
                return output.split()
            return []
        else:
            # Expand variables and globs
            expanded = self.expansion_manager.expand_string_variables(item)
            # Handle glob patterns
            if any(c in expanded for c in ['*', '?', '[']):
                import glob
                matches = glob.glob(expanded)
                if matches:
                    return sorted(matches)
            return [expanded]
    
    def _expand_case_expr(self, expr):
        """Expand case expression."""
        return self.expansion_manager.expand_string_variables(expr)
    
    def _match_case_pattern(self, expr: str, patterns: List) -> bool:
        """Check if expression matches any of the patterns."""
        import fnmatch
        for pattern in patterns:
            pattern_str = self.expansion_manager.expand_string_variables(pattern.pattern)
            if fnmatch.fnmatch(expr, pattern_str):
                return True
        return False