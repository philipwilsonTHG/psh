"""
Control flow execution support for the PSH executor.

This module handles execution of control structures including:
- If/elif/else conditionals
- While loops
- For loops (standard and C-style)
- Case statements
- Select loops
- Break and continue statements
"""

import os
import sys
import re
import glob
import fnmatch
from typing import List, Optional, TYPE_CHECKING
from contextlib import contextmanager

from ..core.exceptions import LoopBreak, LoopContinue, ReadonlyVariableError
from ..arithmetic import evaluate_arithmetic

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import (
        IfConditional, WhileLoop, ForLoop, CStyleForLoop,
        CaseConditional, SelectLoop, BreakStatement, ContinueStatement,
        Redirect
    )
    from .context import ExecutionContext
    from psh.visitor.base import ASTVisitor


class ControlFlowExecutor:
    """
    Handles execution of control flow structures.
    
    This class encapsulates all logic for executing control structures
    including conditionals, loops, and flow control statements.
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the control flow executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
    
    @contextmanager
    def _apply_redirections(self, redirects: List['Redirect']):
        """Context manager for applying and restoring redirections."""
        if not redirects:
            yield
            return
            
        saved_fds = self.io_manager.apply_redirections(redirects)
        try:
            yield
        finally:
            self.io_manager.restore_redirections(saved_fds)
    
    def execute_if(self, node: 'IfConditional', context: 'ExecutionContext',
                   visitor: 'ASTVisitor[int]') -> int:
        """
        Execute if/then/else statement.
        
        Args:
            node: The IfConditional AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        # Apply redirections to entire if statement
        with self._apply_redirections(node.redirects):
            # Temporarily disable pipeline context for commands inside control structure
            old_pipeline = context.in_pipeline
            context.in_pipeline = False
            try:
                # Evaluate main condition
                condition_status = visitor.visit(node.condition)
                
                if condition_status == 0:
                    return visitor.visit(node.then_part)
                
                # Check elif conditions
                for elif_condition, elif_then in node.elif_parts:
                    elif_status = visitor.visit(elif_condition)
                    if elif_status == 0:
                        return visitor.visit(elif_then)
                
                # Execute else part if present
                if node.else_part:
                    return visitor.visit(node.else_part)
                
                return 0
            finally:
                context.in_pipeline = old_pipeline
    
    def execute_while(self, node: 'WhileLoop', context: 'ExecutionContext',
                      visitor: 'ASTVisitor[int]') -> int:
        """
        Execute while loop.
        
        Args:
            node: The WhileLoop AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        exit_status = 0
        context.loop_depth += 1
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            # Temporarily disable pipeline context for commands inside control structure
            old_pipeline = context.in_pipeline
            context.in_pipeline = False
            try:
                while True:
                    # Evaluate condition
                    condition_status = visitor.visit(node.condition)
                    if condition_status != 0:
                        break
                    
                    # Execute body
                    try:
                        exit_status = visitor.visit(node.body)
                    except LoopContinue as lc:
                        if lc.level > 1:
                            raise LoopContinue(lc.level - 1)
                        continue
                    except LoopBreak as lb:
                        if lb.level > 1:
                            raise LoopBreak(lb.level - 1)
                        break
                        
            finally:
                context.in_pipeline = old_pipeline
        
        context.loop_depth -= 1
        return exit_status
    
    def execute_for(self, node: 'ForLoop', context: 'ExecutionContext',
                    visitor: 'ASTVisitor[int]') -> int:
        """
        Execute for loop.
        
        Args:
            node: The ForLoop AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        exit_status = 0
        context.loop_depth += 1
        
        # Expand items - handle all types of expansion, respecting quote types
        expanded_items = self._expand_for_loop_items(node)
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            # Temporarily disable pipeline context for commands inside control structure
            old_pipeline = context.in_pipeline
            context.in_pipeline = False
            try:
                for item in expanded_items:
                    # Set loop variable
                    try:
                        self.state.set_variable(node.variable, item)
                    except ReadonlyVariableError as e:
                        print(f"psh: {node.variable}: readonly variable", file=self.state.stderr)
                        return 1
                    
                    # Execute body
                    try:
                        exit_status = visitor.visit(node.body)
                    except LoopContinue as lc:
                        if lc.level > 1:
                            raise LoopContinue(lc.level - 1)
                        continue
                    except LoopBreak as lb:
                        if lb.level > 1:
                            raise LoopBreak(lb.level - 1)
                        break
                        
            finally:
                context.in_pipeline = old_pipeline
        
        context.loop_depth -= 1
        return exit_status
    
    def execute_c_style_for(self, node: 'CStyleForLoop', context: 'ExecutionContext',
                            visitor: 'ASTVisitor[int]') -> int:
        """
        Execute C-style for loop: for ((init; cond; update))
        
        Args:
            node: The CStyleForLoop AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        exit_status = 0
        context.loop_depth += 1
        
        # Evaluate init expression
        if node.init_expr:
            try:
                evaluate_arithmetic(node.init_expr, self.shell)
            except Exception as e:
                print(f"psh: ((: {e}", file=sys.stderr)
                context.loop_depth -= 1
                return 1
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            try:
                while True:
                    # Evaluate condition
                    if node.condition_expr:
                        try:
                            result = evaluate_arithmetic(node.condition_expr, self.shell)
                            if result == 0:  # Zero means false
                                break
                        except Exception as e:
                            print(f"psh: ((: {e}", file=sys.stderr)
                            exit_status = 1
                            break
                    
                    # Execute body
                    try:
                        exit_status = visitor.visit(node.body)
                    except LoopContinue as lc:
                        if lc.level > 1:
                            raise LoopContinue(lc.level - 1)
                    except LoopBreak as lb:
                        if lb.level > 1:
                            raise LoopBreak(lb.level - 1)
                        break
                    
                    # Evaluate update expression
                    if node.update_expr:
                        try:
                            evaluate_arithmetic(node.update_expr, self.shell)
                        except Exception as e:
                            print(f"psh: ((: {e}", file=sys.stderr)
                            exit_status = 1
                            break
                            
            finally:
                context.loop_depth -= 1
        
        return exit_status
    
    def execute_case(self, node: 'CaseConditional', context: 'ExecutionContext',
                     visitor: 'ASTVisitor[int]') -> int:
        """
        Execute case statement.
        
        Args:
            node: The CaseConditional AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        # Expand the expression
        expr = node.expr
        if '$' in expr:
            expr = self.expansion_manager.expand_string_variables(expr)
        
        # Apply redirections
        with self._apply_redirections(node.redirects):
            # Temporarily disable pipeline context for commands inside control structure
            old_pipeline = context.in_pipeline
            context.in_pipeline = False
            try:
                # Try each case item
                for case_item in node.items:
                    # Check if any pattern matches
                    for pattern_obj in case_item.patterns:
                        # Expand pattern
                        pattern_str = pattern_obj.pattern
                        expanded_pattern = pattern_str
                        if '$' in pattern_str:
                            expanded_pattern = self.expansion_manager.expand_string_variables(pattern_str)
                        
                        # Convert bash-style escape sequences for fnmatch
                        fnmatch_pattern = self._convert_case_pattern_for_fnmatch(expanded_pattern)
                        
                        if fnmatch.fnmatch(expr, fnmatch_pattern):
                            # Execute the commands for this case
                            exit_status = visitor.visit(case_item.commands)
                            
                            # Handle terminator
                            if case_item.terminator == ';;':
                                # Normal termination
                                return exit_status
                            elif case_item.terminator == ';&':
                                # Fall through to next case
                                break
                            elif case_item.terminator == ';;&':
                                # Continue testing patterns
                                continue
                            
                            return exit_status
                
                # No pattern matched
                return 0
            finally:
                context.in_pipeline = old_pipeline
    
    def execute_select(self, node: 'SelectLoop', context: 'ExecutionContext',
                       visitor: 'ASTVisitor[int]') -> int:
        """
        Execute select loop for interactive menu selection.
        
        Args:
            node: The SelectLoop AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        exit_status = 0
        context.loop_depth += 1
        
        # Expand items - handle all types of expansion, respecting quote types
        expanded_items = self._expand_select_items(node)
        
        # Empty list - exit immediately
        if not expanded_items:
            context.loop_depth -= 1
            return 0
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            try:
                # Get PS3 prompt (default "#? " if not set)
                ps3 = self.state.get_variable("PS3", "#? ")
                
                while True:
                    # Display menu to stderr
                    self._display_select_menu(expanded_items)
                    
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
                    self.state.set_variable("REPLY", reply)
                    
                    # Process selection
                    if reply.strip().isdigit():
                        choice = int(reply.strip())
                        if 1 <= choice <= len(expanded_items):
                            # Valid selection
                            selected = expanded_items[choice - 1]
                            self.state.set_variable(node.variable, selected)
                        else:
                            # Out of range
                            self.state.set_variable(node.variable, "")
                    else:
                        # Non-numeric input
                        self.state.set_variable(node.variable, "")
                    
                    # Execute loop body
                    try:
                        exit_status = visitor.visit(node.body)
                    except LoopContinue as lc:
                        if lc.level > 1:
                            raise LoopContinue(lc.level - 1)
                        continue
                    except LoopBreak as lb:
                        if lb.level > 1:
                            raise LoopBreak(lb.level - 1)
                        break
            except KeyboardInterrupt:
                sys.stderr.write("\n")
                exit_status = 130
            finally:
                context.loop_depth -= 1
        
        return exit_status
    
    def execute_break(self, node: 'BreakStatement', context: 'ExecutionContext') -> int:
        """
        Execute break statement.
        
        Args:
            node: The BreakStatement AST node
            context: Current execution context
            
        Returns:
            Never returns normally, always raises LoopBreak
        """
        if context.loop_depth == 0:
            print("break: only meaningful in a `for' or `while' loop", file=self.shell.stderr)
            # Raise exception even outside loop so StatementList stops executing
            raise LoopBreak(node.level)
        raise LoopBreak(node.level)
    
    def execute_continue(self, node: 'ContinueStatement', context: 'ExecutionContext') -> int:
        """
        Execute continue statement.
        
        Args:
            node: The ContinueStatement AST node
            context: Current execution context
            
        Returns:
            Never returns normally, always raises LoopContinue
        """
        if context.loop_depth == 0:
            print("continue: only meaningful in a `for' or `while' loop", file=self.shell.stderr)
            # Raise exception even outside loop so StatementList stops executing
            raise LoopContinue(node.level)
        raise LoopContinue(node.level)
    
    # Helper methods
    
    def _expand_for_loop_items(self, node: 'ForLoop') -> List[str]:
        """Expand items for a for loop, handling all expansion types."""
        expanded_items = []
        quote_types = getattr(node, 'item_quote_types', [None] * len(node.items))
        
        for i, item in enumerate(node.items):
            quote_type = quote_types[i] if i < len(quote_types) else None
            
            # Check if this is an array expansion
            if '$' in item and self.expansion_manager.variable_expander.is_array_expansion(item):
                # Expand array to list of items
                array_items = self.expansion_manager.variable_expander.expand_array_to_list(item)
                expanded_items.extend(array_items)
            else:
                # Perform full expansion on the item
                expanded_items.extend(self._expand_single_item(item, quote_type))
        
        return expanded_items
    
    def _expand_select_items(self, node: 'SelectLoop') -> List[str]:
        """Expand items for a select loop, handling all expansion types."""
        expanded_items = []
        quote_types = getattr(node, 'item_quote_types', [None] * len(node.items))
        
        for i, item in enumerate(node.items):
            quote_type = quote_types[i] if i < len(quote_types) else None
            
            # Check if this is an array expansion
            if '$' in item and self.expansion_manager.variable_expander.is_array_expansion(item):
                # Expand array to list of items
                array_items = self.expansion_manager.variable_expander.expand_array_to_list(item)
                expanded_items.extend(array_items)
            else:
                # Perform full expansion on the item
                expanded_items.extend(self._expand_single_item(item, quote_type))
        
        return expanded_items
    
    def _expand_single_item(self, item: str, quote_type: Optional[str]) -> List[str]:
        """Expand a single item based on its type and quote context."""
        # Determine the type of the item (check arithmetic first since it starts with $()
        if item.startswith('$((') and item.endswith('))'):
            # Arithmetic expansion
            result = self.expansion_manager.execute_arithmetic_expansion(item)
            # Arithmetic expansion always produces a single value
            return [str(result)]
        elif item.startswith('$(') and item.endswith(')'):
            # Command substitution
            output = self.expansion_manager.execute_command_substitution(item)
            # For quoted command substitution, don't word split
            if quote_type == '"':
                return [output if output else ""]
            else:
                # Split on whitespace for word splitting
                return output.split() if output else []
        elif item.startswith('`') and item.endswith('`'):
            # Backtick command substitution
            output = self.expansion_manager.execute_command_substitution(item)
            # For quoted command substitution, don't word split
            if quote_type == '"':
                return [output if output else ""]
            else:
                # Split on whitespace for word splitting
                return output.split() if output else []
        elif '$' in item:
            # Variable expansion
            expanded = self.expansion_manager.expand_string_variables(item)
            
            if quote_type == '"':
                # Double-quoted: no word splitting, no glob expansion
                return [expanded if expanded else ""]
            elif quote_type == "'":
                # Single-quoted: no expansion at all (but shouldn't happen here since we have $)
                return [item]
            else:
                # Unquoted: word splitting and glob expansion
                return self._word_split_and_glob(expanded)
        else:
            # No special expansion needed
            if quote_type in ['"', "'"]:
                # Quoted: no glob expansion
                return [item]
            else:
                # Unquoted: try glob expansion
                matches = glob.glob(item)
                return sorted(matches) if matches else [item]
    
    def _word_split_and_glob(self, text: str) -> List[str]:
        """Perform word splitting and glob expansion on text."""
        # Get IFS for field splitting
        ifs = self.state.get_variable('IFS', ' \t\n')
        if ifs:
            # Create regex pattern from IFS characters
            ifs_pattern = '[' + re.escape(ifs) + ']+'
            words = re.split(ifs_pattern, text.strip()) if text.strip() else []
        else:
            # No IFS means no field splitting
            words = [text] if text else []
        
        # Handle glob expansion on each word
        result = []
        for word in words:
            if word:  # Skip empty words
                matches = glob.glob(word)
                if matches:
                    result.extend(sorted(matches))
                else:
                    result.append(word)
        
        return result
    
    def _convert_case_pattern_for_fnmatch(self, pattern: str) -> str:
        """Convert bash-style case pattern escapes to fnmatch format.
        
        In bash case patterns:
        - \\[ means literal [, not character class
        - \\] means literal ], not character class  
        - \\* means literal *, not wildcard
        - \\? means literal ?, not single char wildcard
        
        Note: The tokenizer strips backslashes, so we need to detect patterns that
        were likely escaped and restore the literal meaning.
        """
        result = []
        i = 0
        while i < len(pattern):
            if pattern[i] == '\\' and i + 1 < len(pattern):
                next_char = pattern[i + 1]
                if next_char in '[]*?':
                    # Escape these special characters for fnmatch
                    result.append('[' + next_char + ']')
                    i += 2
                else:
                    # Other backslash sequences, keep as-is
                    result.append(pattern[i])
                    i += 1
            else:
                result.append(pattern[i])
                i += 1
        
        # Handle cases where tokenizer stripped escape sequences
        # Pattern like [*] likely came from \[*\] (literal brackets)
        # Check for suspicious character classes that contain wildcards
        converted_pattern = ''.join(result)
        
        # If pattern looks like [*] or [?] or [*...] with wildcards inside brackets,
        # it's likely meant to be literal brackets since wildcards in character
        # classes don't make sense
        if re.match(r'^\[[*?].*\]$', converted_pattern):
            # This looks like escaped brackets that got tokenized - treat as literal
            # Convert [*] to [[][*][]]  (literal [ followed by * followed by literal ])
            bracket_content = converted_pattern[1:-1]  # Remove outer []
            literal_pattern = '[[]' + bracket_content + '[]]'
            return literal_pattern
        
        return converted_pattern
    
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