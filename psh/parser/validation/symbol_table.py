"""Symbol table for tracking symbols during semantic analysis."""

from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field
from ...ast_nodes import FunctionDef


@dataclass
class FunctionInfo:
    """Information about a function."""
    definition: FunctionDef
    used: bool = False
    defined_at: int = 0


@dataclass
class VariableInfo:
    """Information about a variable."""
    name: str
    readonly: bool = False
    exported: bool = False
    defined_at: int = 0
    used: bool = False


class SymbolTable:
    """Track symbols during semantic analysis."""
    
    def __init__(self):
        # Function tracking
        self.functions: Dict[str, FunctionInfo] = {}
        
        # Variable tracking with scope support
        self.variable_scopes: List[Dict[str, VariableInfo]] = [{}]  # Start with global scope
        
        # Alias tracking
        self.aliases: Dict[str, str] = {}
        
        # Special variables that are always readonly
        self.builtin_readonly_vars: Set[str] = {
            'BASH_VERSION', 'BASH_VERSINFO', 'HOSTNAME', 'PPID', 'PWD',
            'RANDOM', 'SECONDS', 'SHELLOPTS', 'UID', 'EUID'
        }
        
        # Track loop and function context
        self.loop_depth: int = 0
        self.function_depth: int = 0
    
    def enter_scope(self):
        """Enter a new variable scope."""
        self.variable_scopes.append({})
    
    def exit_scope(self):
        """Exit the current variable scope."""
        if len(self.variable_scopes) > 1:
            self.variable_scopes.pop()
    
    def enter_function(self):
        """Enter function context."""
        self.function_depth += 1
        self.enter_scope()  # Functions create new scope
    
    def exit_function(self):
        """Exit function context."""
        if self.function_depth > 0:
            self.function_depth -= 1
            self.exit_scope()
    
    def enter_loop(self):
        """Enter loop context."""
        self.loop_depth += 1
    
    def exit_loop(self):
        """Exit loop context."""
        if self.loop_depth > 0:
            self.loop_depth -= 1
    
    def add_function(self, name: str, node: FunctionDef) -> None:
        """Add function to symbol table."""
        self.functions[name] = FunctionInfo(
            definition=node,
            defined_at=getattr(node, 'position', 0)
        )
    
    def has_function(self, name: str) -> bool:
        """Check if function exists."""
        return name in self.functions
    
    def use_function(self, name: str) -> None:
        """Mark function as used."""
        if name in self.functions:
            self.functions[name].used = True
    
    def add_variable(self, name: str, readonly: bool = False, exported: bool = False, position: int = 0) -> None:
        """Add variable to current scope."""
        current_scope = self.variable_scopes[-1]
        current_scope[name] = VariableInfo(
            name=name,
            readonly=readonly or name in self.builtin_readonly_vars,
            exported=exported,
            defined_at=position
        )
    
    def use_variable(self, name: str) -> None:
        """Mark variable as used."""
        # Search from current scope upward
        for scope in reversed(self.variable_scopes):
            if name in scope:
                scope[name].used = True
                return
    
    def get_variable(self, name: str) -> Optional[VariableInfo]:
        """Get variable info from any scope."""
        # Search from current scope upward
        for scope in reversed(self.variable_scopes):
            if name in scope:
                return scope[name]
        return None
    
    def is_variable_readonly(self, name: str) -> bool:
        """Check if variable is readonly."""
        var_info = self.get_variable(name)
        return var_info is not None and var_info.readonly
    
    def is_variable_in_current_scope(self, name: str) -> bool:
        """Check if variable exists in current scope."""
        current_scope = self.variable_scopes[-1]
        return name in current_scope
    
    def mark_variable_readonly(self, name: str) -> None:
        """Mark variable as readonly in current scope."""
        current_scope = self.variable_scopes[-1]
        if name in current_scope:
            current_scope[name].readonly = True
        else:
            # Add as readonly variable
            self.add_variable(name, readonly=True)
    
    def mark_variable_exported(self, name: str) -> None:
        """Mark variable as exported."""
        var_info = self.get_variable(name)
        if var_info:
            var_info.exported = True
        else:
            # Add as exported variable
            self.add_variable(name, exported=True)
    
    def add_alias(self, name: str, value: str) -> None:
        """Add alias definition."""
        self.aliases[name] = value
    
    def get_alias(self, name: str) -> Optional[str]:
        """Get alias value."""
        return self.aliases.get(name)
    
    def has_alias(self, name: str) -> bool:
        """Check if alias exists."""
        return name in self.aliases
    
    def get_unused_functions(self) -> List[FunctionInfo]:
        """Get list of unused functions."""
        return [info for info in self.functions.values() if not info.used]
    
    def get_unused_variables(self) -> List[VariableInfo]:
        """Get list of unused variables."""
        unused = []
        for scope in self.variable_scopes:
            for var_info in scope.values():
                if not var_info.used and not var_info.name.startswith('_'):
                    unused.append(var_info)
        return unused
    
    def in_loop_context(self) -> bool:
        """Check if currently in a loop."""
        return self.loop_depth > 0
    
    def in_function_context(self) -> bool:
        """Check if currently in a function."""
        return self.function_depth > 0