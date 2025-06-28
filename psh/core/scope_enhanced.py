"""Enhanced variable scope management with attribute support."""

from typing import Dict, Optional, List, Any, Union
from .variables import Variable, VarAttributes, ReadonlyVariableError, IndexedArray, AssociativeArray
from .exceptions import UnboundVariableError
import re
import os
import time
import random


class VariableScope:
    """Represents a single variable scope with attribute-aware variables."""
    
    def __init__(self, parent: Optional['VariableScope'] = None, name: Optional[str] = None):
        self.variables: Dict[str, Variable] = {}
        self.parent = parent
        self.name = name or 'anonymous'
        
    def __repr__(self):
        return f"VariableScope(name={self.name}, vars={list(self.variables.keys())})"


class EnhancedScopeManager:
    """Enhanced scope manager with variable attributes support."""
    
    def __init__(self):
        self.global_scope = VariableScope(name='global')
        self.scope_stack: List[VariableScope] = [self.global_scope]
        self._debug = False
        self._shell = None  # Reference to shell for arithmetic evaluation
        
        # Special variable state
        self._shell_start_time = time.time()
        self._current_line_number = 1
        
    def set_shell(self, shell):
        """Set reference to shell instance for arithmetic evaluation."""
        self._shell = shell
    
    def enable_debug(self, enabled: bool = True):
        """Enable or disable debug output for scope operations."""
        self._debug = enabled
        
    def _debug_print(self, message: str):
        """Print debug message if debugging is enabled."""
        if self._debug:
            import sys
            print(f"[SCOPE] {message}", file=sys.stderr)
    
    def push_scope(self, name: Optional[str] = None) -> VariableScope:
        """Create new scope for function entry."""
        new_scope = VariableScope(parent=self.current_scope, name=name)
        self.scope_stack.append(new_scope)
        self._debug_print(f"Pushing scope for function: {name or 'anonymous'}")
        return new_scope
        
    def pop_scope(self) -> Optional[VariableScope]:
        """Remove scope on function exit."""
        if len(self.scope_stack) > 1:
            scope = self.scope_stack.pop()
            if scope.variables:
                var_names = ', '.join(scope.variables.keys())
                self._debug_print(f"Popping scope: {scope.name} (destroying variables: {var_names})")
            else:
                self._debug_print(f"Popping scope: {scope.name} (no variables)")
            return scope
        else:
            raise RuntimeError("Cannot pop global scope")
    
    def get_variable(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get variable value as string (backward compatibility).
        
        Returns the string value of the variable or default if not found.
        """
        var = self.get_variable_object(name)
        if var:
            return var.as_string()
        return default
    
    def get_variable_object(self, name: str) -> Optional[Variable]:
        """Get the full Variable object through scope chain."""
        # Check for special variables first
        special_var = self._get_special_variable(name)
        if special_var is not None:
            return special_var
            
        # Search from innermost to outermost scope
        for scope in reversed(self.scope_stack):
            if name in scope.variables:
                var = scope.variables[name]
                # Skip unset variables (tombstones)
                if var.is_unset:
                    self._debug_print(f"Variable lookup: {name} found unset tombstone in scope '{scope.name}', skipping")
                    return None
                self._debug_print(f"Variable lookup: {name} found in scope '{scope.name}' = {var.value}")
                return var
        
        self._debug_print(f"Variable lookup: {name} not found in any scope")
        return None
    
    def set_variable(self, name: str, value: Any, 
                     attributes: VarAttributes = VarAttributes.NONE,
                     local: bool = False):
        """Set variable with attributes in appropriate scope.
        
        Args:
            name: Variable name
            value: Variable value
            attributes: Variable attributes to apply
            local: If True, set in current scope. If False and in function,
                   check if variable exists in current scope first
        """
        # Check if variable exists
        existing = self.get_variable_object(name)
        if existing and existing.is_readonly:
            raise ReadonlyVariableError(name)
        
        # If updating existing variable, merge its attributes with new ones
        if existing and not attributes:
            # Use existing attributes when no new attributes specified
            attributes = existing.attributes
        elif existing and attributes:
            # Merge attributes when both exist
            attributes = existing.attributes | attributes
        
        # Apply attribute transformations
        transformed_value = self._apply_attributes(value, attributes)
        
        # Determine target scope
        if local or len(self.scope_stack) == 1:
            # Set in current scope (global or explicitly local)
            target_scope = self.current_scope
            scope_name = target_scope.name
        else:
            # In a function, not explicitly local
            # Search for existing variable in scope chain (bash behavior)
            target_scope = None
            for scope in reversed(self.scope_stack):
                if name in scope.variables:
                    target_scope = scope
                    scope_name = scope.name
                    break
            
            if target_scope is None:
                # Variable doesn't exist anywhere, create in global scope
                target_scope = self.global_scope
                scope_name = "global"
        
        # Create or update variable
        if name in target_scope.variables:
            # Update existing variable, preserving some attributes
            var = target_scope.variables[name]
            if var.is_readonly:
                raise ReadonlyVariableError(name)
            
            # Merge attributes (some attributes like EXPORT are additive)
            new_attributes = var.attributes | attributes
            var.value = transformed_value  # Use the already-transformed value
            var.attributes = new_attributes
            self._debug_print(f"Updating variable in scope '{scope_name}': {name} = {var.value}")
        else:
            # Create new variable
            var = Variable(name=name, value=transformed_value, attributes=attributes)
            target_scope.variables[name] = var
            self._debug_print(f"Setting variable in scope '{scope_name}': {name} = {var.value}")
    
    def create_local(self, name: str, value: Optional[Any] = None,
                     attributes: VarAttributes = VarAttributes.NONE):
        """Create a local variable in the current scope.
        
        This is what the 'local' builtin uses.
        """
        if not self.is_in_function():
            raise RuntimeError("local: can only be used in a function")
        
        # Check if variable exists in outer scope and is readonly
        for scope in self.scope_stack[:-1]:  # Check all but current
            if name in scope.variables and scope.variables[name].is_readonly:
                raise ReadonlyVariableError(name)
        
        if value is not None:
            transformed_value = self._apply_attributes(value, attributes)
            var = Variable(name=name, value=transformed_value, attributes=attributes)
            self.current_scope.variables[name] = var
            self._debug_print(f"Creating local variable: {name} = {transformed_value}")
        else:
            # Create unset local variable (shadows global but has no value)
            var = Variable(name=name, value="", attributes=attributes)
            self.current_scope.variables[name] = var
            self._debug_print(f"Creating unset local variable: {name}")
    
    def unset_variable(self, name: str):
        """Unset a variable in the appropriate scope."""
        # Check current scope first
        if name in self.current_scope.variables:
            var = self.current_scope.variables[name]
            if var.is_readonly:
                raise ReadonlyVariableError(name)
            del self.current_scope.variables[name]
            self._debug_print(f"Unsetting variable in scope '{self.current_scope.name}': {name}")
            
            # If we're in a function scope, create an unset tombstone
            # to prevent fallback to parent scopes
            if len(self.scope_stack) > 1:
                unset_var = Variable(name=name, value="", attributes=VarAttributes.UNSET)
                self.current_scope.variables[name] = unset_var
                self._debug_print(f"Creating unset tombstone for {name} in scope '{self.current_scope.name}'")
            return
        
        # If not in current scope and we're in a function, check parent scopes
        if len(self.scope_stack) > 1:
            # Search for the variable in parent scopes
            for scope in reversed(self.scope_stack[:-1]):  # Skip current scope
                if name in scope.variables:
                    var = scope.variables[name]
                    if var.is_readonly:
                        raise ReadonlyVariableError(name)
                    del scope.variables[name]
                    self._debug_print(f"Unsetting variable in parent scope '{scope.name}': {name}")
                    
                    # Create unset tombstone in current scope
                    unset_var = Variable(name=name, value="", attributes=VarAttributes.UNSET)
                    self.current_scope.variables[name] = unset_var
                    self._debug_print(f"Creating unset tombstone for {name} in current scope")
                    return
        
        # Check global scope as fallback
        if name in self.global_scope.variables:
            var = self.global_scope.variables[name]
            if var.is_readonly:
                raise ReadonlyVariableError(name)
            del self.global_scope.variables[name]
            self._debug_print(f"Unsetting variable in global scope: {name}")
    
    def _apply_attributes(self, value: Any, attributes: VarAttributes) -> Any:
        """Apply attribute transformations to value."""
        # Don't transform arrays
        if isinstance(value, (IndexedArray, AssociativeArray)):
            return value
        
        # Convert to string for transformations
        str_value = str(value) if value is not None else ""
        
        if attributes & VarAttributes.UPPERCASE:
            return str_value.upper()
        elif attributes & VarAttributes.LOWERCASE:
            return str_value.lower()
        elif attributes & VarAttributes.INTEGER:
            # Evaluate arithmetic expressions for integer variables
            if str_value.strip():
                try:
                    # Simple integer evaluation (would need full arithmetic evaluator)
                    # For now, just try to convert or evaluate simple expressions
                    result = self._evaluate_integer(str_value)
                    return str(result)  # Store as string, but evaluated as integer
                except Exception as e:
                    return "0"
            return "0"
        
        return str_value
    
    def _evaluate_integer(self, expr: str) -> int:
        """Evaluate integer expressions using the shell's arithmetic evaluator."""
        # Remove whitespace
        expr = expr.strip()
        
        # Always use the shell's arithmetic evaluator if available
        # This properly handles octal (010), hex (0x10), and arithmetic expressions
        if hasattr(self, '_shell') and self._shell:
            from ..arithmetic import evaluate_arithmetic
            try:
                # Evaluate the expression using the helper function
                result = evaluate_arithmetic(expr, self._shell)
                return result
            except Exception:
                # If evaluation fails, return 0
                return 0
        
        # Fallback when no shell context: try to use the arithmetic tokenizer
        # to handle octal and hex properly
        try:
            from ..arithmetic import ArithTokenizer, ArithParser, ArithmeticEvaluator
            
            # Create a minimal evaluator without shell context
            class MinimalShell:
                def __init__(self, scope_manager):
                    self.state = type('State', (), {'get_variable': lambda _, name, default='0': scope_manager.get_variable(name, default)})()
            
            tokenizer = ArithTokenizer(expr)
            tokens = tokenizer.tokenize()
            parser = ArithParser(tokens)
            ast = parser.parse()
            
            # Use minimal evaluator
            minimal_shell = MinimalShell(self)
            evaluator = ArithmeticEvaluator(minimal_shell)
            return evaluator.evaluate(ast)
            
        except Exception:
            # Last resort: simple conversion, but this loses octal support
            try:
                return int(expr)
            except ValueError:
                return 0
    
    @property
    def current_scope(self) -> VariableScope:
        """Get the current (innermost) scope."""
        return self.scope_stack[-1]
    
    def _get_special_variable(self, name: str) -> Optional[Variable]:
        """Handle special shell variables that are computed dynamically."""
        if name == 'LINENO':
            # Return current line number (simplified implementation)
            return Variable(name='LINENO', value=str(self._current_line_number))
        elif name == 'SECONDS':
            # Return seconds since shell start
            elapsed = int(time.time() - self._shell_start_time)
            return Variable(name='SECONDS', value=str(elapsed))
        elif name == 'RANDOM':
            # Return random number between 0 and 32767 (bash compatible)
            return Variable(name='RANDOM', value=str(random.randint(0, 32767)))
        elif name == 'FUNCNAME':
            # Return current function name if in function
            if self._shell and hasattr(self._shell, 'state') and self._shell.state.function_stack:
                func_name = self._shell.state.function_stack[-1]
                return Variable(name='FUNCNAME', value=func_name)
            else:
                # Not in a function, return empty string (bash behavior)
                return Variable(name='FUNCNAME', value='')
        
        return None
    
    def set_current_line_number(self, line_number: int):
        """Update the current line number for LINENO variable."""
        self._current_line_number = line_number
    
    def is_in_function(self) -> bool:
        """Check if we're currently in a function scope."""
        return len(self.scope_stack) > 1
    
    def get_all_variables(self) -> Dict[str, str]:
        """Get all variables visible in current scope as strings (backward compat)."""
        result = {}
        
        # Start with global variables
        for name, var in self.global_scope.variables.items():
            result[name] = var.as_string()
        
        # Override with variables from each scope (oldest to newest)
        for scope in self.scope_stack[1:]:  # Skip global scope
            for name, var in scope.variables.items():
                result[name] = var.as_string()
        
        return result
    
    def all_variables_with_attributes(self) -> List[Variable]:
        """Get all visible variables as Variable objects."""
        # Use dict to handle shadowing correctly
        all_vars: Dict[str, Variable] = {}
        
        # Start with global variables
        for name, var in self.global_scope.variables.items():
            all_vars[name] = var
        
        # Override with variables from each scope
        for scope in self.scope_stack[1:]:
            for name, var in scope.variables.items():
                all_vars[name] = var
        
        return list(all_vars.values())
    
    def has_variable(self, name: str) -> bool:
        """Check if a variable exists in any scope."""
        for scope in reversed(self.scope_stack):
            if name in scope.variables:
                return True
        return False
    
    def get_variable_with_attributes(self, name: str) -> Optional[Variable]:
        """Get variable with all its attributes (alias for get_variable_object)."""
        return self.get_variable_object(name)
    
    def sync_exports_to_environment(self, env: Dict[str, str]):
        """Sync variables with EXPORT attribute to environment."""
        # First, get all shell variables
        all_shell_vars = set()
        for scope in self.scope_stack:
            all_shell_vars.update(scope.variables.keys())
        
        # Remove from environment any variables that exist in shell but aren't exported
        for var_name in list(env.keys()):
            if var_name in all_shell_vars:
                var = self.get_variable_object(var_name)
                if var and not var.is_exported:
                    del env[var_name]
        
        # Collect all exported variables
        exported_vars = {}
        
        # Start with global scope
        for name, var in self.global_scope.variables.items():
            if var.is_exported and not var.is_array:
                exported_vars[name] = var.as_string()
        
        # Override with function scopes
        for scope in self.scope_stack[1:]:
            for name, var in scope.variables.items():
                if var.is_exported and not var.is_array:
                    exported_vars[name] = var.as_string()
        
        # Update environment
        env.update(exported_vars)
    
    def apply_attribute(self, name: str, attributes: VarAttributes):
        """Apply additional attributes to an existing variable."""
        var = self.get_variable_object(name)
        if var:
            # Check readonly before modifying attributes
            if var.is_readonly and attributes != VarAttributes.READONLY:
                raise ReadonlyVariableError(name)
            
            # Handle mutually exclusive attributes
            new_attributes = var.attributes
            
            # If setting lowercase, remove uppercase
            if attributes & VarAttributes.LOWERCASE:
                new_attributes &= ~VarAttributes.UPPERCASE
            # If setting uppercase, remove lowercase
            if attributes & VarAttributes.UPPERCASE:
                new_attributes &= ~VarAttributes.LOWERCASE
            
            # Apply new attributes
            new_attributes |= attributes
            var.attributes = new_attributes
            
            # Re-apply transformations if needed
            if attributes & (VarAttributes.UPPERCASE | VarAttributes.LOWERCASE | VarAttributes.INTEGER):
                var.value = self._apply_attributes(var.value, var.attributes)
    
    def remove_attribute(self, name: str, attributes: VarAttributes):
        """Remove attributes from an existing variable."""
        var = self.get_variable_object(name)
        if var:
            # Cannot remove readonly attribute
            if attributes & VarAttributes.READONLY and var.is_readonly:
                raise ReadonlyVariableError(name)
            
            # Remove specified attributes
            var.attributes &= ~attributes
            
            # If removing export, ensure it's removed from environment
            if attributes & VarAttributes.EXPORT:
                # The variable is no longer exported, so it won't be synced to env
                # in the next sync_exports_to_environment call
                pass