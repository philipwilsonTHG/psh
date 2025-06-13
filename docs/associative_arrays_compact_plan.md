# Associative Arrays Implementation Plan (Compact)

## Status
- `AssociativeArray` class: ✅ Already implemented (v0.40.0)
- Variable attributes system: ✅ Already implemented
- Parser support for string keys: ❌ **Main work needed**
- Execution logic: ❌ Needs updates

## Chosen Approach: Late Binding
Parse array keys as token lists, evaluate at runtime based on array type.

## Implementation Tasks

### 1. Parser Changes (`psh/parser.py`)

```python
# Modify _parse_array_element_assignment()
def _parse_array_key_tokens(self) -> List[Token]:
    """Collect tokens between [ and ] without evaluation"""
    tokens = []
    while not self.check(TokenType.RBRACKET):
        if self.peek().type in VALID_KEY_TOKENS:
            tokens.append(self.peek())
            self.advance()
    return tokens

# Update AST node to store tokens instead of string
@dataclass
class ArrayElementAssignment:
    name: str
    index: List[Token]  # Changed from str
    value: str
    # ... rest unchanged
```

### 2. Executor Changes (`psh/executor/command.py`)

```python
def _execute_array_assignment(self, node):
    var = self.state.get_variable_object(node.name)
    
    # Determine array type and evaluate key accordingly
    if var and var.attributes & VarAttributes.ASSOC_ARRAY:
        key = self._tokens_to_string(node.index)  # String key
        array = var.value
    else:
        key = self._tokens_to_arithmetic(node.index)  # Numeric index
        array = var.value or self._create_indexed_array(node.name)
    
    array.set(key, self._evaluate_value(node.value))

def _tokens_to_string(self, tokens):
    """Concatenate tokens as string with expansions"""
    return ''.join(self._expand_token(t) for t in tokens)

def _tokens_to_arithmetic(self, tokens):
    """Join tokens and evaluate as arithmetic"""
    expr = ''.join(t.value for t in tokens)
    return self._evaluate_arithmetic(expr)
```

### 3. Declare Builtin Updates (`psh/builtins/function_support.py`)

```python
# Handle: declare -A arr=([key1]=val1 [key2]=val2)
if 'A' in flags and '=(' in arg:
    name, rest = arg.split('=(', 1)
    array = AssociativeArray()
    # Parse [key]=value pairs
    for pair in self._parse_assoc_pairs(rest.rstrip(')')):
        key, value = pair
        array.set(key, value)
    self.state.set_variable_object(name, Variable(
        value=array,
        attributes=VarAttributes.ASSOC_ARRAY
    ))
```

### 4. Variable Expansion Updates (`psh/expansion/variable.py`)

- `ArraySubscriptParser` already exists
- Update to handle token lists instead of strings
- Check array type during expansion

### 5. Test Cases

```bash
# Basic operations
declare -A colors
colors[red]="#FF0000"
colors["light blue"]="#ADD8E6"
echo ${colors[red]}
echo ${!colors[@]}

# Variable keys
key="red"
echo ${colors[$key]}

# Initialization
declare -A config=([host]=localhost [port]=8080)

# Error cases
unset arr
arr[key]=value  # Error: must declare -A first
```

## Timeline
- Parser changes: 4-6 hours
- Executor updates: 2-3 hours
- Declare builtin: 2-3 hours
- Testing: 3-4 hours
- **Total: 11-16 hours**

## Key Files to Modify
1. `psh/parser.py` - Array key parsing
2. `psh/ast_nodes.py` - Update ArrayElementAssignment
3. `psh/executor/command.py` - Array assignment execution
4. `psh/builtins/function_support.py` - Declare -A support
5. `psh/expansion/variable.py` - Array access in expansions

## Success Criteria
- All bash associative array syntax works
- No regression in indexed arrays
- Clear error messages
- 95%+ test coverage