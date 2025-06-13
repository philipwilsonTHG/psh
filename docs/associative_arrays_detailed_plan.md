# Detailed Implementation Plan: Associative Arrays in PSH

## Executive Summary

The `AssociativeArray` class and core infrastructure already exist in PSH v0.42.0. The main work required is enhancing the parser to handle string keys in array syntax and implementing proper type checking to distinguish between indexed and associative arrays.

**Chosen Approach**: We will implement a **"late binding" strategy** where the parser collects array keys as token sequences without evaluation, and the executor determines at runtime whether to evaluate them as arithmetic expressions (indexed arrays) or strings (associative arrays). This keeps the parser simple and maintains clean separation of concerns.

## Implementation Details

### Phase 1: Parser Enhancement (Priority: High)

#### 1.1 Modify Array Element Assignment Parsing

**File**: `psh/parser.py`

**Current Code** (line 1757):
```python
def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
    """Parse array element assignment: name[index]=value"""
    # Currently only handles arithmetic expressions as indices
```

**Changes Required**:
1. Add logic to determine array type (check if variable has ASSOC_ARRAY attribute)
2. Parse string keys for associative arrays
3. Handle quoted keys, variable expansions in keys

**New Implementation**:
```python
def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
    """Parse array element assignment: name[index_or_key]=value"""
    self.expect(TokenType.LBRACKET)
    
    # Check if this is an associative array
    is_associative = self._is_associative_array(name)
    
    if is_associative:
        # Parse as string key (may be quoted or contain variables)
        key = self._parse_array_key()
    else:
        # Parse as arithmetic expression (current behavior)
        key = self._parse_array_index()
    
    self.expect(TokenType.RBRACKET)
    # ... rest of the method

def _is_associative_array(self, name: str) -> bool:
    """Check if variable is declared as associative array"""
    # Look up variable in current scope
    # Check if it has ASSOC_ARRAY attribute
    # This requires access to shell state during parsing
    
def _parse_array_key(self) -> str:
    """Parse associative array key - can be quoted string, word, or variable"""
    key_parts = []
    
    while not self.check(TokenType.RBRACKET) and not self.at_end():
        token = self.peek()
        
        if token.type == TokenType.STRING:
            # Handle quoted keys: arr["key"] or arr['key']
            key_parts.append(('STRING', token.value, token.quote_type))
            self.advance()
        elif token.type == TokenType.VARIABLE:
            # Handle variable keys: arr[$key]
            key_parts.append(('VARIABLE', token.value))
            self.advance()
        elif token.type == TokenType.WORD:
            # Handle unquoted keys: arr[key]
            key_parts.append(('WORD', token.value))
            self.advance()
        else:
            raise self._error(f"Invalid token in array key: {token.type}")
    
    # Return composite key for later expansion
    return key_parts
```

#### 1.2 Enhance Array Access in Variable Expansion

**File**: `psh/expansion/variable.py`

**Current Code**:
- Already supports both `IndexedArray` and `AssociativeArray`
- Need to ensure string key parsing works

**Changes Required**:
1. Update `ArraySubscriptParser` to handle string keys
2. Ensure variable expansion in keys works properly

### Phase 2: Associative Array Initialization (Priority: High)

#### 2.1 Parse Initialization Syntax

**Pattern**: `declare -A arr=([key1]=val1 [key2]=val2)`

**New AST Node**:
```python
@dataclass
class AssociativeArrayInitialization(ASTNode):
    """Represents associative array initialization"""
    name: str
    pairs: List[Tuple[List[Tuple[str, str]], str]]  # (key_parts, value)
```

**Parser Changes**:
```python
def _parse_declare_args(self, args: List[str]):
    """Enhanced to handle associative array initialization"""
    # When we see pattern: name=([key]=value ...)
    if '=' in arg and arg.endswith(')') and '=(' in arg:
        name, rest = arg.split('=(', 1)
        pairs = self._parse_assoc_init_pairs(rest[:-1])
        # Create initialization node
```

### Phase 3: Execution Implementation (Priority: High)

#### 3.1 Update Command Executor

**File**: `psh/executor/command.py`

**Changes Required**:
1. Handle associative array element assignment
2. Implement initialization from declare

```python
def _execute_array_assignment(self, node: ArrayElementAssignment):
    """Execute array element assignment"""
    # Get array from state
    var = self.state.get_variable_object(node.name)
    
    if var and var.value and isinstance(var.value, AssociativeArray):
        # Evaluate key as string (with expansions)
        key = self._evaluate_array_key(node.index)
        # Evaluate value
        value = self._evaluate_value(node.value, node.value_type)
        # Set in associative array
        var.value.set(key, value)
    else:
        # Indexed array - current behavior
        index = self._evaluate_arithmetic(node.index)
        # ... rest of current implementation

def _evaluate_array_key(self, key_parts):
    """Evaluate array key with expansions"""
    if isinstance(key_parts, str):
        # Old format - arithmetic expression
        return key_parts
    
    # New format - list of parts
    result = []
    for part_type, value, *extra in key_parts:
        if part_type == 'STRING':
            # Quoted string - may need expansion
            result.append(self._expand_string(value, extra[0] if extra else None))
        elif part_type == 'VARIABLE':
            # Variable expansion
            result.append(self.state.get_variable(value, ''))
        elif part_type == 'WORD':
            # Literal word
            result.append(value)
    
    return ''.join(result)
```

#### 3.2 Update Declare Builtin

**File**: `psh/builtins/function_support.py`

**Changes Required**:
1. Parse initialization syntax
2. Create and populate AssociativeArray

```python
# In declare builtin
if 'A' in self.attributes:
    # Create associative array
    if '=' in arg and arg.endswith(')'):
        # Parse initialization
        name, init_str = arg.split('=(', 1)
        array = AssociativeArray()
        # Parse pairs and populate
        self.state.set_variable_object(name, Variable(
            value=array,
            attributes=VarAttributes.ASSOC_ARRAY
        ))
```

### Phase 4: Type Safety and Error Handling (Priority: Medium)

#### 4.1 Add Type Checking

**Locations**: Parser and executor

**Checks Required**:
1. Prevent indexed operations on associative arrays
2. Prevent associative operations on indexed arrays
3. Require `declare -A` before use

```python
def _check_array_type(self, name: str, expected_type: str):
    """Ensure array is of expected type"""
    var = self.state.get_variable_object(name)
    if not var:
        if expected_type == 'associative':
            raise ShellError(f"{name}: must use declare -A before assignment")
        # Auto-create indexed array
        return
    
    if expected_type == 'associative':
        if not (var.attributes & VarAttributes.ASSOC_ARRAY):
            raise ShellError(f"{name}: not an associative array")
    else:
        if var.attributes & VarAttributes.ASSOC_ARRAY:
            raise ShellError(f"{name}: syntax error: invalid arithmetic operator")
```

### Phase 5: Testing (Priority: High)

#### 5.1 Test Categories

1. **Basic Operations**:
   - Declaration: `declare -A arr`
   - Assignment: `arr[key]=value`
   - Access: `${arr[key]}`
   - Unset: `unset arr[key]`

2. **Key Formats**:
   - Simple: `arr[simple]=value`
   - Quoted: `arr["with spaces"]=value`
   - Variables: `arr[$key]=value`
   - Compound: `arr[prefix$suffix]=value`

3. **Expansions**:
   - All values: `${arr[@]}`, `${arr[*]}`
   - All keys: `${!arr[@]}`
   - Count: `${#arr[@]}`
   - Element operations: `${arr[key]#prefix}`

4. **Edge Cases**:
   - Empty keys (if supported)
   - Special characters in keys
   - Very long keys
   - Unicode keys

5. **Error Cases**:
   - Use without declaration
   - Type mismatches
   - Invalid syntax

### Phase 6: Documentation (Priority: Low)

Update:
1. User guide chapter on arrays
2. Differences from bash (remove associative array limitation)
3. Examples and use cases
4. Quick reference

## Technical Challenges

### Challenge 1: Parser State Access

**Problem**: Parser needs to know if a variable is associative to parse keys correctly.

**Solutions**:
1. **Two-pass parsing**: First pass identifies declarations, second pass uses that info
2. **Late binding**: Parse generically, determine type during execution
3. **Parser state**: Give parser limited access to shell state

**Recommendation**: Use late binding - parse array keys as generic "key expressions" and evaluate during execution based on array type.

### Challenge 2: Ambiguous Syntax

**Problem**: `arr[2+2]` could be arithmetic or literal string.

**Solution**: Context-dependent parsing based on array type at execution time.

### Challenge 3: Key Evaluation Order

**Problem**: In `arr[$key$n]`, when do variables expand?

**Solution**: Follow bash behavior - expand during assignment/access execution.

## Chosen Implementation Strategy: Late Binding Approach

After analyzing the technical challenges, we will use a **late binding approach** that keeps the parser simple and maintains clean separation of concerns:

### Key Design Decisions

1. **Generic Key Parsing**: 
   - Parse array subscripts as lists of tokens without evaluation
   - Store key components (strings, variables, words) without interpreting them
   - No need for parser to access shell state

2. **Runtime Type Detection**: 
   - Determine array type during execution, not parsing
   - Check variable attributes at the point of use
   - Handle undeclared arrays appropriately

3. **Context-Aware Evaluation**: 
   - For associative arrays: Evaluate keys as strings with expansions
   - For indexed arrays: Evaluate keys as arithmetic expressions
   - Same syntax, different evaluation based on array type

### Implementation Details

#### Parser Changes (Simplified)

```python
def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
    """Parse array element assignment: name[key]=value"""
    self.expect(TokenType.LBRACKET)
    
    # Parse key as generic token sequence
    key_tokens = self._parse_array_key_tokens()
    
    self.expect(TokenType.RBRACKET)
    # ... rest remains the same
    
    return ArrayElementAssignment(
        name=name,
        index=key_tokens,  # Store as token list, not string
        value=value,
        # ...
    )

def _parse_array_key_tokens(self) -> List[Token]:
    """Parse array key as list of tokens for later evaluation"""
    tokens = []
    
    while not self.check(TokenType.RBRACKET) and not self.at_end():
        token = self.peek()
        
        # Accept any valid key token
        if token.type in (TokenType.WORD, TokenType.STRING, 
                         TokenType.VARIABLE, TokenType.PLUS, 
                         TokenType.MINUS, TokenType.STAR, 
                         TokenType.SLASH, TokenType.NUMBER):
            tokens.append(token)
            self.advance()
        else:
            raise self._error(f"Invalid token in array key: {token.type}")
    
    return tokens
```

#### Executor Changes

```python
def _execute_array_assignment(self, node: ArrayElementAssignment):
    """Execute array element assignment with type detection"""
    # Get or create array
    var = self.state.get_variable_object(node.name)
    
    # Determine array type
    if var and var.attributes & VarAttributes.ASSOC_ARRAY:
        # Associative array - evaluate key as string
        key = self._evaluate_key_as_string(node.index)
        array = var.value
    elif var and isinstance(var.value, IndexedArray):
        # Indexed array - evaluate key as arithmetic
        key = self._evaluate_key_as_arithmetic(node.index)
        array = var.value
    else:
        # Auto-create indexed array (bash behavior)
        key = self._evaluate_key_as_arithmetic(node.index)
        array = self._create_indexed_array(node.name)
    
    # Set value
    value = self._evaluate_value(node.value, node.value_type)
    array.set(key, value)

def _evaluate_key_as_string(self, tokens: List[Token]) -> str:
    """Evaluate tokens as string key for associative array"""
    result = []
    for token in tokens:
        if token.type == TokenType.STRING:
            # Expand variables in strings if needed
            result.append(self._expand_string(token.value, token.quote_type))
        elif token.type == TokenType.VARIABLE:
            # Expand variable
            result.append(self.state.get_variable(token.value[1:], ''))
        elif token.type == TokenType.WORD:
            # Literal text
            result.append(token.value)
        else:
            # Other tokens used literally
            result.append(token.value)
    return ''.join(result)

def _evaluate_key_as_arithmetic(self, tokens: List[Token]) -> int:
    """Evaluate tokens as arithmetic expression for indexed array"""
    # Reconstruct expression and evaluate
    expr = ''.join(token.value for token in tokens)
    return self._evaluate_arithmetic(expr)
```

### Advantages of This Approach

1. **Simplicity**: Parser remains stateless and simple
2. **Flexibility**: Same parsing code handles both array types
3. **Compatibility**: Matches bash behavior exactly
4. **Maintainability**: Clear separation between parsing and evaluation
5. **Extensibility**: Easy to add new key evaluation strategies

### Migration Path

1. Update AST nodes to store token lists instead of strings for keys
2. Modify parser to collect tokens without evaluation
3. Update executor to evaluate based on array type
4. Ensure backward compatibility with existing indexed arrays

## Timeline Estimate

1. **Week 1**: Parser changes and basic execution (8-10 hours)
2. **Week 2**: Complete implementation and testing (6-8 hours)
3. **Week 3**: Edge cases, documentation, and polish (4-6 hours)

Total: 18-24 hours over 3 weeks

## Success Metrics

1. All bash test cases pass
2. No regression in indexed arrays
3. Clear error messages
4. Performance comparable to indexed arrays
5. 95%+ test coverage

## Next Steps

1. Create feature branch
2. Implement generic key parsing
3. Add execution logic
4. Write comprehensive tests
5. Update documentation
6. Submit for review