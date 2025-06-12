# Scope Manager Migration Guide

This guide explains how to migrate from the existing ScopeManager to the EnhancedScopeManager with variable attributes support.

## Key Differences

### 1. Variable Storage
- **Old**: Variables stored as `Dict[str, str]` (simple string values)
- **New**: Variables stored as `Dict[str, Variable]` (objects with attributes)

### 2. Method Changes

#### get_variable()
- **Old behavior**: Returns string value or None
- **New behavior**: Still returns string value for backward compatibility
- **New method**: Use `get_variable_object()` to get the full Variable object

#### set_variable()
```python
# Old
scope_manager.set_variable("name", "value", local=False)

# New - with attributes
scope_manager.set_variable("name", "value", 
                          attributes=VarAttributes.READONLY | VarAttributes.EXPORT,
                          local=False)
```

#### create_local()
```python
# Old
scope_manager.create_local("name", "value")

# New - with attributes
scope_manager.create_local("name", "value", 
                          attributes=VarAttributes.NONE)
```

### 3. New Methods

#### get_variable_object()
Returns the full Variable object with attributes:
```python
var = scope_manager.get_variable_object("PATH")
if var and var.is_exported:
    print(f"{var.name} is exported with value: {var.value}")
```

#### all_variables_with_attributes()
Get all visible variables as Variable objects:
```python
for var in scope_manager.all_variables_with_attributes():
    if var.is_readonly:
        print(f"Readonly: {var.name}")
```

#### sync_exports_to_environment()
Sync exported variables to the environment:
```python
scope_manager.sync_exports_to_environment(os.environ)
```

#### apply_attribute() / remove_attribute()
Modify attributes of existing variables:
```python
# Make variable readonly
scope_manager.apply_attribute("CONFIG", VarAttributes.READONLY)

# Remove export attribute
scope_manager.remove_attribute("TEMP", VarAttributes.EXPORT)
```

## Migration Steps

### 1. Update Imports
```python
# Old
from psh.core import ScopeManager

# New
from psh.core import EnhancedScopeManager as ScopeManager
from psh.core import VarAttributes, Variable
```

### 2. Update Variable Setting
When setting variables that need attributes:
```python
# Setting a readonly exported variable
scope_manager.set_variable("VERSION", "1.0", 
                          attributes=VarAttributes.READONLY | VarAttributes.EXPORT)

# Setting an integer variable
scope_manager.set_variable("COUNT", "0",
                          attributes=VarAttributes.INTEGER)
```

### 3. Update Variable Access
For code that needs to check attributes:
```python
# Old - no attribute checking possible
value = scope_manager.get_variable("name")

# New - check attributes
var = scope_manager.get_variable_object("name")
if var:
    if var.is_readonly:
        # Handle readonly
    value = var.value
```

### 4. Handle Exceptions
New exception for readonly violations:
```python
from psh.core import ReadonlyVariableError

try:
    scope_manager.set_variable("CONST", "new_value")
except ReadonlyVariableError as e:
    print(f"Error: {e}")
```

## Array Support (Future)

The new system is designed to support arrays:

```python
# Create an indexed array
arr = IndexedArray()
arr.set(0, "first")
arr.set(1, "second")
scope_manager.set_variable("myarray", arr, 
                          attributes=VarAttributes.ARRAY)

# Create an associative array
map = AssociativeArray()
map.set("key1", "value1")
map.set("key2", "value2")
scope_manager.set_variable("mymap", map,
                          attributes=VarAttributes.ASSOC_ARRAY)
```

## Testing

Before full migration, you can test both implementations side by side:

```python
from psh.core import ScopeManager, EnhancedScopeManager

# Test with old
old_mgr = ScopeManager()
old_mgr.set_variable("test", "value")

# Test with new
new_mgr = EnhancedScopeManager()
new_mgr.set_variable("test", "value", attributes=VarAttributes.NONE)

# Results should be compatible for basic operations
assert old_mgr.get_variable("test") == new_mgr.get_variable("test")
```

## Gradual Migration

1. Start by updating the imports to use EnhancedScopeManager
2. Add `attributes=VarAttributes.NONE` to all set_variable calls
3. Gradually add proper attributes where needed
4. Update code to use get_variable_object() where attributes matter
5. Add array support when the parser is ready