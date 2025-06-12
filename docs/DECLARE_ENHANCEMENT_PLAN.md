# PSH Declare Enhancement Implementation Plan

This document outlines the plan to implement high-priority `declare` builtin features in PSH, including arrays, associative arrays, readonly variables, export attribute, and print functionality.

## Overview

The implementation will be done in phases to ensure each feature is properly integrated with PSH's architecture. Arrays require the most significant changes as they affect the variable storage system.

## Phase 1: Variable Attribute System

Before implementing specific declare options, we need to enhance the variable system to support attributes.

### 1.1 Variable Storage Enhancement

**Current State:**
- Variables stored as simple key-value pairs in dictionaries
- No attribute tracking

**Required Changes:**

```python
# psh/core/variables.py (new file)
from dataclasses import dataclass
from enum import Flag, auto
from typing import Any, Dict, List, Optional, Union

class VarAttributes(Flag):
    """Variable attributes that can be combined."""
    NONE = 0
    READONLY = auto()    # -r
    EXPORT = auto()      # -x
    INTEGER = auto()     # -i
    LOWERCASE = auto()   # -l
    UPPERCASE = auto()   # -u
    ARRAY = auto()       # -a
    ASSOC_ARRAY = auto() # -A
    NAMEREF = auto()     # -n
    TRACE = auto()       # -t (functions)
    
@dataclass
class Variable:
    """Enhanced variable with attributes and value."""
    name: str
    value: Any  # Can be str, list, dict, int
    attributes: VarAttributes = VarAttributes.NONE
    
    @property
    def is_array(self) -> bool:
        return bool(self.attributes & (VarAttributes.ARRAY | VarAttributes.ASSOC_ARRAY))
    
    @property
    def is_readonly(self) -> bool:
        return bool(self.attributes & VarAttributes.READONLY)
    
    @property
    def is_exported(self) -> bool:
        return bool(self.attributes & VarAttributes.EXPORT)
```

### 1.2 Scope Manager Updates

```python
# Updates to psh/core/scope_manager.py

class Scope:
    def __init__(self):
        # Change from Dict[str, str] to Dict[str, Variable]
        self.variables: Dict[str, Variable] = {}
    
    def set_variable(self, name: str, value: Any, 
                     attributes: VarAttributes = VarAttributes.NONE) -> None:
        """Set variable with attributes."""
        if name in self.variables:
            var = self.variables[name]
            if var.is_readonly:
                raise ReadonlyVariableError(f"Cannot modify readonly variable: {name}")
            # Preserve existing attributes unless explicitly changing
            var.value = self._apply_attributes(value, var.attributes | attributes)
        else:
            self.variables[name] = Variable(
                name=name,
                value=self._apply_attributes(value, attributes),
                attributes=attributes
            )
    
    def _apply_attributes(self, value: Any, attributes: VarAttributes) -> Any:
        """Apply attribute transformations to value."""
        if attributes & VarAttributes.UPPERCASE:
            return str(value).upper()
        elif attributes & VarAttributes.LOWERCASE:
            return str(value).lower()
        elif attributes & VarAttributes.INTEGER:
            # Evaluate arithmetic expressions
            if isinstance(value, str):
                try:
                    return self._evaluate_arithmetic(value)
                except:
                    return 0
            return int(value)
        return value
```

## Phase 2: Array Implementation

### 2.1 Indexed Arrays (-a)

**Data Structure:**
```python
class IndexedArray:
    """Indexed array implementation."""
    def __init__(self):
        self._elements: Dict[int, str] = {}
        self._max_index = -1
    
    def set(self, index: int, value: str):
        self._elements[index] = value
        self._max_index = max(self._max_index, index)
    
    def get(self, index: int) -> Optional[str]:
        return self._elements.get(index)
    
    def all_elements(self) -> List[str]:
        """Get all elements in order."""
        result = []
        for i in range(self._max_index + 1):
            if i in self._elements:
                result.append(self._elements[i])
        return result
    
    def indices(self) -> List[int]:
        """Get all defined indices."""
        return sorted(self._elements.keys())
    
    def length(self) -> int:
        """Number of elements."""
        return len(self._elements)
```

### 2.2 Associative Arrays (-A)

**Data Structure:**
```python
class AssociativeArray:
    """Associative array (hash/dictionary) implementation."""
    def __init__(self):
        self._elements: Dict[str, str] = {}
    
    def set(self, key: str, value: str):
        self._elements[key] = value
    
    def get(self, key: str) -> Optional[str]:
        return self._elements.get(key)
    
    def all_elements(self) -> List[str]:
        """Get all values."""
        return list(self._elements.values())
    
    def keys(self) -> List[str]:
        """Get all keys."""
        return list(self._elements.keys())
    
    def items(self) -> List[Tuple[str, str]]:
        """Get key-value pairs."""
        return list(self._elements.items())
    
    def length(self) -> int:
        """Number of elements."""
        return len(self._elements)
```

### 2.3 Array Assignment Syntax

**Parser Updates Required:**

```python
# New AST nodes in psh/ast_nodes.py
@dataclass
class ArrayAssignment(ASTNode):
    """Array assignment: arr=(one two three) or arr[0]=value"""
    name: str
    index: Optional[Union[int, str]] = None  # None for full array
    values: Optional[List[str]] = None       # For arr=(...)
    value: Optional[str] = None              # For arr[i]=value

@dataclass
class ArrayExpansion(ASTNode):
    """Array expansion: ${arr[@]} or ${arr[0]}"""
    name: str
    index: Optional[Union[int, str, Literal['@', '*']]] = None
    operation: Optional[str] = None  # For ${#arr[@]}, ${!arr[@]}
```

**Tokenizer Updates:**
- Recognize `=(` as array initialization token
- Handle `[` and `]` in variable contexts

**Parser Updates:**
- Parse `name=(values...)` syntax
- Parse `name[subscript]=value` syntax
- Handle array expansions in variable expansion

### 2.4 Array Expansion

**Expansion Manager Updates:**

```python
def expand_array(self, node: ArrayExpansion) -> List[str]:
    """Expand array references."""
    var = self.get_variable(node.name)
    
    if not var or not var.is_array:
        return [""]
    
    array = var.value
    
    # ${arr[@]} or ${arr[*]}
    if node.index in ('@', '*'):
        if node.operation == '#':  # ${#arr[@]}
            return [str(array.length())]
        elif node.operation == '!':  # ${!arr[@]}
            if isinstance(array, IndexedArray):
                return [str(i) for i in array.indices()]
            else:  # AssociativeArray
                return array.keys()
        else:
            return array.all_elements()
    
    # ${arr[index]}
    elif node.index is not None:
        value = array.get(node.index)
        return [value] if value is not None else [""]
    
    # ${arr} - first element for indexed, error for associative
    else:
        if isinstance(array, IndexedArray):
            value = array.get(0)
            return [value] if value is not None else [""]
        else:
            raise ExpansionError("Must specify key for associative array")
```

## Phase 3: Declare Builtin Enhancement

### 3.1 Option Parsing

```python
class DeclareBuiltin(Builtin):
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse options
        options = DeclareOptions()
        positional = []
        i = 1
        
        while i < len(args):
            arg = args[i]
            if arg.startswith('-') and len(arg) > 1:
                for flag in arg[1:]:
                    if flag == 'a':
                        options.array = True
                    elif flag == 'A':
                        options.assoc_array = True
                    elif flag == 'r':
                        options.readonly = True
                    elif flag == 'x':
                        options.export = True
                    elif flag == 'i':
                        options.integer = True
                    elif flag == 'l':
                        options.lowercase = True
                    elif flag == 'u':
                        options.uppercase = True
                    elif flag == 'p':
                        options.print = True
                    elif flag == 'f':
                        options.functions = True
                    elif flag == 'F':
                        options.function_names = True
                    else:
                        self.error(f"invalid option: -{flag}", shell)
                        return 1
            elif arg.startswith('+') and len(arg) > 1:
                # Handle attribute removal
                for flag in arg[1:]:
                    if flag == 'x':
                        options.remove_export = True
                    # ... etc
            else:
                positional.append(arg)
            i += 1
        
        # Validate exclusive options
        if options.array and options.assoc_array:
            self.error("cannot use -a and -A together", shell)
            return 1
        
        # Execute based on options
        if options.print:
            return self._print_variables(options, positional, shell)
        elif options.functions or options.function_names:
            return self._handle_functions(options, positional, shell)
        else:
            return self._declare_variables(options, positional, shell)
```

### 3.2 Variable Declaration

```python
def _declare_variables(self, options: DeclareOptions, 
                       args: List[str], shell: 'Shell') -> int:
    """Handle variable declarations."""
    
    # Build attributes from options
    attributes = VarAttributes.NONE
    if options.readonly:
        attributes |= VarAttributes.READONLY
    if options.export:
        attributes |= VarAttributes.EXPORT
    if options.integer:
        attributes |= VarAttributes.INTEGER
    if options.lowercase:
        attributes |= VarAttributes.LOWERCASE
    if options.uppercase:
        attributes |= VarAttributes.UPPERCASE
    if options.array:
        attributes |= VarAttributes.ARRAY
    if options.assoc_array:
        attributes |= VarAttributes.ASSOC_ARRAY
    
    # Process each argument
    for arg in args:
        if '=' in arg:
            # Variable assignment
            name, value = arg.split('=', 1)
            
            # Handle array syntax
            if options.array and value.startswith('('):
                # Parse array initialization
                array_values = self._parse_array_init(value)
                array = IndexedArray()
                for i, val in enumerate(array_values):
                    array.set(i, val)
                shell.state.set_variable(name, array, attributes)
            
            elif options.assoc_array and value.startswith('('):
                # Parse associative array
                assoc_values = self._parse_assoc_array_init(value)
                array = AssociativeArray()
                for key, val in assoc_values:
                    array.set(key, val)
                shell.state.set_variable(name, array, attributes)
            
            else:
                # Regular variable
                shell.state.set_variable(name, value, attributes)
        else:
            # Just declaring with attributes, no assignment
            if options.array:
                shell.state.set_variable(arg, IndexedArray(), attributes)
            elif options.assoc_array:
                shell.state.set_variable(arg, AssociativeArray(), attributes)
            else:
                # Apply attributes to existing variable
                var = shell.state.get_variable(arg)
                if var:
                    var.attributes |= attributes
```

### 3.3 Print Functionality (-p)

```python
def _print_variables(self, options: DeclareOptions, 
                     names: List[str], shell: 'Shell') -> int:
    """Print variables with attributes."""
    stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
    
    # Get variables to print
    if names:
        # Specific variables
        for name in names:
            var = shell.state.get_variable_with_attributes(name)
            if var:
                self._print_declaration(var, stdout)
            else:
                self.error(f"{name}: not found", shell)
                return 1
    else:
        # All variables
        for var in shell.state.all_variables_with_attributes():
            if self._matches_filter(var, options):
                self._print_declaration(var, stdout)
    
    return 0

def _print_declaration(self, var: Variable, file):
    """Print variable declaration in reusable format."""
    # Build declare command
    flags = []
    if var.attributes & VarAttributes.ARRAY:
        flags.append('a')
    if var.attributes & VarAttributes.ASSOC_ARRAY:
        flags.append('A')
    if var.attributes & VarAttributes.READONLY:
        flags.append('r')
    if var.attributes & VarAttributes.EXPORT:
        flags.append('x')
    if var.attributes & VarAttributes.INTEGER:
        flags.append('i')
    if var.attributes & VarAttributes.LOWERCASE:
        flags.append('l')
    if var.attributes & VarAttributes.UPPERCASE:
        flags.append('u')
    
    flag_str = f"-{''.join(flags)}" if flags else "--"
    
    # Format value
    if isinstance(var.value, IndexedArray):
        # declare -a name=([0]="val" [1]="val")
        elements = []
        for idx in var.value.indices():
            val = var.value.get(idx)
            elements.append(f'[{idx}]="{self._escape_value(val)}"')
        value_str = f"=({' '.join(elements)})"
    
    elif isinstance(var.value, AssociativeArray):
        # declare -A name=([key]="val" [key2]="val2")
        elements = []
        for key, val in sorted(var.value.items()):
            elements.append(f'[{key}]="{self._escape_value(val)}"')
        value_str = f"=({' '.join(elements)})"
    
    else:
        # Regular variable
        value_str = f'="{self._escape_value(str(var.value))}"'
    
    print(f"declare {flag_str} {var.name}{value_str}", file=file)
```

## Phase 4: Export Integration

### 4.1 Export Builtin Updates

```python
# Updates to psh/builtins/environment.py

class ExportBuiltin(Builtin):
    def execute(self, args: List[str], shell: 'Shell') -> int:
        if len(args) == 1:
            # Show exported variables using declare -p format
            for var in shell.state.all_variables_with_attributes():
                if var.is_exported:
                    self._print_export(var, shell.stdout)
        else:
            # Export variables
            for arg in args[1:]:
                if '=' in arg:
                    name, value = arg.split('=', 1)
                    # Set variable with export attribute
                    shell.state.set_variable(
                        name, value, 
                        VarAttributes.EXPORT
                    )
                else:
                    # Export existing variable
                    var = shell.state.get_variable_with_attributes(arg)
                    if var:
                        var.attributes |= VarAttributes.EXPORT
                        # Sync to environment
                        shell.env[var.name] = str(var.value)
                    else:
                        # Variable doesn't exist, create it
                        shell.state.set_variable(
                            arg, "", 
                            VarAttributes.EXPORT
                        )
        return 0
```

### 4.2 Environment Synchronization

```python
# In scope manager
def sync_exports_to_environment(self, env: Dict[str, str]):
    """Sync exported variables to environment."""
    for var in self.all_variables():
        if var.is_exported:
            # Only export non-array values
            if not var.is_array:
                env[var.name] = str(var.value)
```

## Phase 5: Testing Strategy

### 5.1 Unit Tests

```python
# tests/test_declare_builtin.py
class TestDeclareBuiltin:
    def test_readonly_variable(self, shell):
        shell.run_command('declare -r CONST=value')
        # Should fail
        result = shell.run_command('CONST=new')
        assert result != 0
        assert shell.state.get_variable('CONST') == 'value'
    
    def test_integer_arithmetic(self, shell):
        shell.run_command('declare -i num')
        shell.run_command('num="5+5"')
        assert shell.state.get_variable('num') == 10
    
    def test_array_declaration(self, shell):
        shell.run_command('declare -a arr=(one two three)')
        assert shell.run_command('echo ${arr[0]}') == 'one'
        assert shell.run_command('echo ${#arr[@]}') == '3'
    
    def test_associative_array(self, shell):
        shell.run_command('declare -A map')
        shell.run_command('map[key]="value"')
        shell.run_command('map[another]="test"')
        assert shell.run_command('echo ${map[key]}') == 'value'
    
    def test_print_declarations(self, shell):
        shell.run_command('declare -ix NUM=42')
        output = capture_output(shell.run_command, 'declare -p NUM')
        assert output == 'declare -ix NUM="42"'
```

### 5.2 Integration Tests

```python
# tests/test_arrays_integration.py
class TestArraysIntegration:
    def test_array_in_loop(self, shell):
        shell.run_command('arr=(apple banana cherry)')
        shell.run_command('for fruit in "${arr[@]}"; do echo $fruit; done')
        # Verify output
    
    def test_array_slicing(self, shell):
        shell.run_command('arr=(1 2 3 4 5)')
        output = shell.run_command('echo "${arr[@]:1:3}"')
        assert output == '2 3 4'
    
    def test_array_with_functions(self, shell):
        shell.run_command('''
        process_array() {
            local -a arr=("$@")
            echo "Array has ${#arr[@]} elements"
        }
        process_array one two three
        ''')
```

## Implementation Timeline

### Week 1-2: Variable Attribute System
- Implement Variable class and attributes
- Update scope manager
- Add attribute enforcement (readonly, case conversion)
- Basic declare -r, -l, -u, -i support

### Week 3-4: Array Infrastructure  
- Implement IndexedArray and AssociativeArray classes
- Update parser for array syntax
- Basic array assignment and expansion
- declare -a and -A support

### Week 5-6: Full Array Support
- Array subscript assignment (arr[i]=value)
- Array expansions (${arr[@]}, ${#arr[@]}, ${!arr[@]})
- Array slicing ${arr[@]:start:length}
- Integration with for loops

### Week 7: Export and Print
- declare -x integration
- declare -p implementation
- export builtin updates
- Comprehensive testing

### Week 8: Polish and Edge Cases
- Combination flags (declare -arix)
- Attribute removal (declare +x)
- Error handling improvements
- Documentation updates

## Success Criteria

1. All high-priority declare options implemented (-a, -A, -r, -x, -p)
2. Arrays work in all contexts (loops, functions, expansions)
3. Backwards compatibility maintained
4. Comprehensive test coverage (>90%)
5. Documentation updated
6. Performance acceptable (benchmark against bash)

## Risks and Mitigations

1. **Parser Complexity**: Array syntax adds significant parser complexity
   - Mitigation: Incremental parser updates with extensive testing

2. **Performance Impact**: Attribute checking on every variable access
   - Mitigation: Optimize hot paths, cache attribute checks

3. **Backwards Compatibility**: Existing scripts must continue working
   - Mitigation: Careful testing, gradual rollout

4. **Scope Interactions**: Arrays and local variables interaction
   - Mitigation: Clear scope rules, match bash behavior

This plan provides a structured approach to implementing these critical features while maintaining PSH's stability and educational clarity.