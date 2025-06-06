"""Control flow statement execution."""
import sys
from typing import List
from ..ast_nodes import (IfStatement, WhileStatement, ForStatement, 
                         CStyleForStatement, CaseStatement, SelectStatement,
                         BreakStatement, ContinueStatement, EnhancedTestStatement)
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
        elif isinstance(node, CStyleForStatement):
            return self.execute_c_style_for(node)
        elif isinstance(node, CaseStatement):
            return self.execute_case(node)
        elif isinstance(node, SelectStatement):
            return self.execute_select(node)
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
        # Trace if statement if xtrace is enabled
        if self.state.options.get('xtrace', False):
            print('+ if ...', file=sys.stderr)
        
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
        # Trace while statement if xtrace is enabled
        if self.state.options.get('xtrace', False):
            print('+ while ...', file=sys.stderr)
        
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
        # Trace for statement if xtrace is enabled
        if self.state.options.get('xtrace', False):
            print(f'+ for {node.variable} in ...', file=sys.stderr)
        
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
            loop_var = node.variable
            
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
    
    def execute_c_style_for(self, node: CStyleForStatement) -> int:
        """Execute C-style for loop: for ((init; condition; update))"""
        # Apply redirections if present
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            # Execute initialization expression
            if node.init_expr:
                self._evaluate_arithmetic(node.init_expr)
            
            last_status = 0
            
            while True:
                try:
                    # Check condition (empty means true, 0 means false)
                    if node.condition_expr:
                        result = self._evaluate_arithmetic(node.condition_expr)
                        if result == 0:
                            break
                    
                    # Execute body
                    last_status = self.shell.execute_command_list(node.body)
                    
                    # Execute update expression (except when breaking)
                    if node.update_expr:
                        self._evaluate_arithmetic(node.update_expr)
                        
                except LoopBreak as e:
                    if e.level > 1:
                        raise LoopBreak(e.level - 1)
                    break
                except LoopContinue as e:
                    if e.level > 1:
                        raise LoopContinue(e.level - 1)
                    # Execute update before continuing
                    if node.update_expr:
                        self._evaluate_arithmetic(node.update_expr)
                    continue
            
            return last_status
        finally:
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def _evaluate_arithmetic(self, expr: str) -> int:
        """Evaluate arithmetic expression using shell's arithmetic system."""
        from ..arithmetic import evaluate_arithmetic
        # Handle empty expressions
        if not expr or not expr.strip():
            return 1  # Empty expression is true in bash
        return evaluate_arithmetic(expr, self.shell)
    
    def execute_select(self, node: SelectStatement) -> int:
        """Execute a select statement."""
        # Set up redirections
        if node.redirects:
            saved_fds = self.io_manager.apply_redirections(node.redirects)
        else:
            saved_fds = None
        
        try:
            # Expand the word list
            expanded_items = []
            for item in node.items:
                # Handle each item based on its type (similar to for loop)
                expanded = self._expand_for_item(item)
                expanded_items.extend(expanded)
            
            # Empty list - exit immediately
            if not expanded_items:
                return 0
            
            # Main select loop
            return self._execute_select_loop(node.variable, expanded_items, node.body)
        finally:
            if saved_fds:
                self.io_manager.restore_redirections(saved_fds)
    
    def _execute_select_loop(self, variable: str, items: List[str], body) -> int:
        """Execute the select loop with menu display and input handling."""
        exit_code = 0
        
        # Get PS3 prompt (default "#? " if not set)
        ps3 = self.shell.state.get_variable("PS3", "#? ")
        
        try:
            while True:
                # Display menu to stderr
                self._display_select_menu(items)
                
                # Show prompt and read input
                try:
                    sys.stderr.write(ps3)
                    sys.stderr.flush()
                    
                    # Read input line
                    if hasattr(self.shell, 'stdin') and self.shell.stdin:
                        # Use shell's stdin if available (set by I/O redirection)
                        reply = self.shell.stdin.readline()
                    else:
                        # Use sys.stdin as fallback
                        if sys.stdin is None or sys.stdin.closed:
                            raise EOFError
                        try:
                            reply = sys.stdin.readline()
                        except (OSError, ValueError):
                            # Handle case where stdin is not available in test environment
                            raise EOFError
                    
                    if not reply:  # EOF
                        raise EOFError
                    reply = reply.rstrip('\n')
                except (EOFError, KeyboardInterrupt):
                    # Ctrl+D or Ctrl+C exits the loop
                    sys.stderr.write("\n")
                    break
                
                # Set REPLY variable
                self.shell.state.set_variable("REPLY", reply)
                
                # Process selection
                if reply.strip().isdigit():
                    choice = int(reply.strip())
                    if 1 <= choice <= len(items):
                        # Valid selection
                        selected = items[choice - 1]
                        self.shell.state.set_variable(variable, selected)
                    else:
                        # Out of range
                        self.shell.state.set_variable(variable, "")
                else:
                    # Non-numeric input
                    self.shell.state.set_variable(variable, "")
                
                # Execute loop body
                try:
                    exit_code = self.shell.execute_command_list(body)
                except LoopBreak as e:
                    if e.level <= 1:
                        break
                    else:
                        e.level -= 1
                        raise
                except LoopContinue as e:
                    if e.level <= 1:
                        continue
                    else:
                        e.level -= 1
                        raise
        
        except KeyboardInterrupt:
            sys.stderr.write("\n")
            exit_code = 130
        
        return exit_code
    
    def _display_select_menu(self, items: List[str]) -> None:
        """Display the select menu to stderr."""
        # Calculate layout
        num_items = len(items)
        if num_items <= 9:
            # Single column for small lists
            for i, item in enumerate(items, 1):
                sys.stderr.write(f"{i}) {item}\n")
        else:
            # Multi-column for larger lists
            columns = 2 if num_items <= 20 else 3
            rows = (num_items + columns - 1) // columns
            
            # Calculate column widths
            col_width = max(len(f"{i}) {items[i-1]}") for i in range(1, num_items + 1)) + 3
            
            for row in range(rows):
                for col in range(columns):
                    idx = row + col * rows
                    if idx < num_items:
                        entry = f"{idx + 1}) {items[idx]}"
                        sys.stderr.write(entry.ljust(col_width))
                sys.stderr.write("\n")