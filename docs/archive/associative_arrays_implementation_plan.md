# Associative Arrays Implementation Plan for PSH

## Overview

This document outlines the plan for implementing bash-compatible associative arrays in PSH. Most of the infrastructure already exists from v0.40.0, but parser enhancements are needed to handle string keys.

## Current State (v0.42.0)

### Already Implemented
1. **Core Classes**:
   - `AssociativeArray` class in `psh/core/variables.py`
   - `VarAttributes.ASSOC_ARRAY` flag
   - Basic `declare -A` support in builtin

2. **Variable System**:
   - Enhanced scope manager handles both array types
   - Variable expansion already checks for both `IndexedArray` and `AssociativeArray`
   - Special expansions (`@`, `*`, `#`, `!`) work with both array types

3. **Parser Infrastructure**:
   - Array element assignment: `arr[index]=value`
   - Array element access: `${arr[index]}`
   - Array initialization: `arr=(values...)`

### Missing Components
1. **Parser Support for String Keys**:
   - Currently only accepts numeric indices
   - Need to handle: `arr[key]=value`, `arr["key"]=value`, `arr[$var]=value`

2. **Associative Array Initialization**:
   - Need to parse: `declare -A arr=([key1]=val1 [key2]=val2)`
   - Current parser only handles positional initialization

3. **Key Evaluation**:
   - String keys should not undergo arithmetic evaluation
   - Variable expansion in keys: `arr[$key]=value`

## Bash Associative Array Behavior

### Declaration
```bash
declare -A assoc_array       # Must declare before use
declare -A colors=(          # Initialize at declaration
    [red]="#FF0000"
    [green]="#00FF00"
    [blue]="#0000FF"
)
```

### Key Syntax
```bash
# Various key formats
assoc[simple]=value
assoc["with spaces"]=value
assoc['single quoted']=value
assoc[$variable]=value
assoc[key$n]=value          # Variable in key
assoc[${var}suffix]=value   # Complex key
```

### Operations
```bash
# Access
echo ${assoc[key]}
echo ${assoc["key with spaces"]}

# All values/keys
echo ${assoc[@]}     # All values
echo ${!assoc[@]}    # All keys
echo ${#assoc[@]}    # Number of elements

# Check existence
[[ -v assoc[key] ]]  # True if key exists
[[ -n "${assoc[key]+set}" ]]  # Alternative

# Delete
unset assoc[key]
unset assoc          # Delete entire array
```

## Implementation Steps

### Phase 1: Parser Enhancement for String Keys

**File: `psh/parser.py`**

1. **Modify `_parse_array_element_assignment()`**:
   ```python
   def _parse_array_element_assignment(self, name):
       """Parse array element assignment: name[key]=value"""
       # Current: Only handles arithmetic expressions
       # Need: Handle both numeric and string keys
       
       if self.current_token.type == TokenType.LBRACKET:
           self.advance()  # Skip [
           
           # New logic to determine key type
           if self._is_associative_array(name):
               key = self._parse_array_key()  # String or variable
           else:
               key = self._parse_arithmetic_expression()  # Numeric
   ```

2. **Add `_parse_array_key()` method**:
   ```python
   def _parse_array_key(self):
       """Parse associative array key - can be string, variable, or compound"""
       # Handle quoted strings, unquoted words, variables
       # Return key as string for evaluation later
   ```

3. **Update `_parse_array_subscript()` in expansions**:
   - Similar changes for `${assoc[key]}` access

### Phase 2: Associative Array Initialization

**File: `psh/parser.py`**

1. **Enhance `declare` command parsing**:
   ```python
   # Handle: declare -A arr=([key1]=val1 [key2]=val2)
   def _parse_declare_array_init(self):
       """Parse associative array initialization"""
       # Recognize [key]=value pattern
       # Build initialization structure
   ```

2. **Create new AST node**:
   ```python
   @dataclass
   class AssociativeArrayInit(ASTNode):
       """Initialization: declare -A arr=([k1]=v1 [k2]=v2)"""
       name: str
       pairs: List[Tuple[str, str]]  # (key, value) pairs
   ```

### Phase 3: Execution Support

**File: `psh/executor/command.py`**

1. **Update array element assignment execution**:
   ```python
   def _execute_array_assignment(self, node):
       """Execute array element assignment"""
       # Determine if indexed or associative
       # For associative: evaluate key as string
       # For indexed: evaluate as arithmetic
   ```

2. **Handle initialization in declare**:
   ```python
   # In declare builtin
   if '-A' in flags and '=' in arg:
       # Parse associative array initialization
       # Create AssociativeArray with initial values
   ```

### Phase 4: Variable Expansion Updates

**File: `psh/expansion/variable.py`**

1. **Update `_expand_array_element()`**:
   - Already supports both array types
   - May need minor tweaks for edge cases

2. **Ensure key expansion works**:
   ```python
   # Handle ${assoc[$key]} where $key expands first
   ```

### Phase 5: Testing

**File: `tests/test_associative_arrays.py`**

Create comprehensive test suite covering:
1. Declaration and initialization
2. Various key formats (quoted, unquoted, with spaces)
3. Variable keys
4. All expansions (@, *, #, !)
5. Mixed operations
6. Error cases (undeclared arrays, missing keys)
7. Comparison with bash behavior

## Technical Considerations

### 1. Key Storage
- Keys are strings in `AssociativeArray._elements` dict
- Unicode keys should work naturally
- Empty string keys are valid

### 2. Key Evaluation Order
```bash
key="mykey"
assoc[$key]=value    # $key expands first, then used as key
assoc[\$key]=value   # Literal '$key' as key
```

### 3. Arithmetic Context
- In indexed arrays: `arr[2+2]` evaluates to `arr[4]`
- In associative arrays: `arr[2+2]` uses literal "2+2" as key

### 4. Type Checking
- Need to track array type via attributes
- Error if mixing indexed/associative operations

### 5. Backwards Compatibility
- Indexed arrays must continue working exactly as before
- Clear error messages for type mismatches

## Effort Estimate

1. **Parser Enhancement**: 2-3 hours
   - Modify array key parsing
   - Handle quoted/unquoted strings
   - Test various key formats

2. **Initialization Syntax**: 1-2 hours
   - Parse `([k]=v ...)` format
   - Integrate with declare builtin

3. **Execution Updates**: 1 hour
   - Route to correct array type
   - Handle key evaluation

4. **Testing**: 2-3 hours
   - Comprehensive test suite
   - Edge cases and error handling
   - Bash compatibility verification

**Total Estimate**: 6-9 hours of development

## Success Criteria

1. All bash associative array syntax works correctly
2. Clear error messages for invalid operations
3. No regression in indexed array functionality
4. Comprehensive test coverage (95%+)
5. Documentation updated
6. Examples demonstrating common use cases

## Example Use Cases

```bash
#!/usr/bin/env psh
# Associative array examples

# Color codes
declare -A colors=(
    [red]=$'\e[31m'
    [green]=$'\e[32m'
    [blue]=$'\e[34m'
    [reset]=$'\e[0m'
)

# Configuration
declare -A config
config[host]="localhost"
config[port]="8080"
config[debug]="true"

# Word frequency counter
declare -A words
while read -r word; do
    ((words[$word]++))
done < file.txt

# Print sorted by frequency
for word in "${!words[@]}"; do
    echo "${words[$word]} $word"
done | sort -rn
```

## Next Steps

1. Review this plan and get approval
2. Create feature branch `feature/associative-arrays`
3. Implement parser changes first (most complex part)
4. Add execution support
5. Create comprehensive tests
6. Update documentation
7. Submit PR for review