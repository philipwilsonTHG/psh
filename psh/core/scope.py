"""Variable scope management for function-local variables."""

from typing import Dict, Optional, List, Any


class VariableScope:
    """Represents a single variable scope (function-local or global)."""
    
    def __init__(self, parent: Optional['VariableScope'] = None, name: Optional[str] = None):
        self.variables: Dict[str, str] = {}
        self.parent = parent
        self.name = name or 'anonymous'
        
    def __repr__(self):
        return f"VariableScope(name={self.name}, vars={list(self.variables.keys())})"


class ScopeManager:
    """Manages the stack of variable scopes for local variable support."""
    
    def __init__(self):
        self.global_scope = VariableScope(name='global')
        self.scope_stack: List[VariableScope] = [self.global_scope]
        self._debug = False
        
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
        """Resolve variable through scope chain."""
        # Search from innermost to outermost scope
        for scope in reversed(self.scope_stack):
            if name in scope.variables:
                self._debug_print(f"Variable lookup: {name} found in scope '{scope.name}' = {scope.variables[name]}")
                return scope.variables[name]
        
        self._debug_print(f"Variable lookup: {name} not found in any scope")
        return default
    
    def set_variable(self, name: str, value: str, local: bool = False):
        """Set variable in appropriate scope.
        
        Args:
            name: Variable name
            value: Variable value
            local: If True, set in current scope. If False and in function,
                   check if variable exists in current scope first
        """
        if local or len(self.scope_stack) == 1:
            # Set in current scope (global or explicitly local)
            self.current_scope.variables[name] = value
            self._debug_print(f"Setting variable in scope '{self.current_scope.name}': {name} = {value}")
        else:
            # In a function, not explicitly local
            # Check if variable exists in current scope (was declared local)
            if name in self.current_scope.variables:
                # Update existing local variable
                self.current_scope.variables[name] = value
                self._debug_print(f"Updating local variable in scope '{self.current_scope.name}': {name} = {value}")
            else:
                # Set in global scope (bash behavior for non-local assignments)
                self.global_scope.variables[name] = value
                self._debug_print(f"Setting variable in global scope: {name} = {value}")
    
    def create_local(self, name: str, value: Optional[str] = None):
        """Create a local variable in the current scope.
        
        This is what the 'local' builtin uses.
        """
        if not self.is_in_function():
            raise RuntimeError("local: can only be used in a function")
        
        if value is not None:
            self.current_scope.variables[name] = value
            self._debug_print(f"Creating local variable: {name} = {value}")
        else:
            # Create unset local variable (shadows global but has no value)
            self.current_scope.variables[name] = ""
            self._debug_print(f"Creating unset local variable: {name}")
    
    def unset_variable(self, name: str):
        """Unset a variable in the appropriate scope."""
        # Check current scope first
        if name in self.current_scope.variables:
            del self.current_scope.variables[name]
            self._debug_print(f"Unsetting variable in scope '{self.current_scope.name}': {name}")
            return
        
        # If not in current scope and we're in a function, check global
        if len(self.scope_stack) > 1 and name in self.global_scope.variables:
            del self.global_scope.variables[name]
            self._debug_print(f"Unsetting variable in global scope: {name}")
    
    @property
    def current_scope(self) -> VariableScope:
        """Get the current (innermost) scope."""
        return self.scope_stack[-1]
    
    def is_in_function(self) -> bool:
        """Check if we're currently in a function scope."""
        return len(self.scope_stack) > 1
    
    def get_all_variables(self) -> Dict[str, str]:
        """Get all variables visible in current scope (for debugging/listing)."""
        # Start with global variables
        all_vars = self.global_scope.variables.copy()
        
        # Override with variables from each scope (oldest to newest)
        for scope in self.scope_stack[1:]:  # Skip global scope
            all_vars.update(scope.variables)
        
        return all_vars
    
    def has_variable(self, name: str) -> bool:
        """Check if a variable exists in any scope."""
        for scope in reversed(self.scope_stack):
            if name in scope.variables:
                return True
        return False