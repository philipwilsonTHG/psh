# Bash Arithmetic Expansion Implementation Summary

## Overview
Bash supports arithmetic expansion through `$((...))` and the deprecated `$[...]` syntax. It evaluates integer arithmetic expressions using 64-bit signed integers.

## Syntax Forms
1. `$((...))` - Modern syntax (preferred)
2. `$[...]` - Old syntax (deprecated but still supported)
3. `((...))` - Arithmetic command (returns exit status based on result)
4. `let` builtin - Evaluates arithmetic expressions

## Supported Operators (by precedence, highest to lowest)

### 1. Postfix operators
- `var++` - Post-increment
- `var--` - Post-decrement

### 2. Unary operators
- `++var` - Pre-increment
- `--var` - Pre-decrement
- `-` - Unary minus
- `+` - Unary plus
- `!` - Logical NOT
- `~` - Bitwise NOT

### 3. Exponentiation
- `**` - Power (right-associative)

### 4. Multiplicative
- `*` - Multiplication
- `/` - Division (integer)
- `%` - Modulo

### 5. Additive
- `+` - Addition
- `-` - Subtraction

### 6. Shift
- `<<` - Left shift
- `>>` - Right shift

### 7. Relational
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal
- `>=` - Greater than or equal

### 8. Equality
- `==` - Equal
- `!=` - Not equal

### 9. Bitwise AND
- `&` - Bitwise AND

### 10. Bitwise XOR
- `^` - Bitwise XOR

### 11. Bitwise OR
- `|` - Bitwise OR

### 12. Logical AND
- `&&` - Logical AND

### 13. Logical OR
- `||` - Logical OR

### 14. Ternary
- `? :` - Conditional (right-associative)

### 15. Assignment (right-associative)
- `=` - Assignment
- `+=`, `-=`, `*=`, `/=`, `%=` - Compound assignment
- `<<=`, `>>=` - Shift assignment
- `&=`, `^=`, `|=` - Bitwise assignment

### 16. Comma
- `,` - Comma (evaluates left-to-right, returns rightmost)

## Variable Handling

1. **Variable References**: Variables can be referenced with or without `$`
   ```bash
   x=10
   $((x + 5))    # Valid
   $(($x + 5))   # Also valid
   ```

2. **Undefined Variables**: Treated as 0
3. **Empty Variables**: Treated as 0
4. **Non-numeric Variables**: Attempt to interpret as variable name (indirect reference)

## Special Features

### Base Conversion
- `base#number` - Convert from specified base (2-64)
- Examples:
  - `$((2#1010))` - Binary
  - `$((8#17))` - Octal
  - `$((16#FF))` - Hexadecimal
  - `$((36#ZZ))` - Base 36

### Integer Literals
- Decimal: `123`
- Octal: `0123` (leading zero)
- Hex: `0x7B` or `0X7B`

## Implementation Considerations

### Parser Requirements
1. **Tokenizer modifications**:
   - Recognize `$((` and `))` as special tokens
   - Handle operators within arithmetic context
   - Support base#number syntax

2. **Grammar rules**:
   ```
   arithmetic_expansion → '$((' arithmetic_expr '))'
   arithmetic_expr → ternary_expr
   ternary_expr → logical_or_expr ('?' ternary_expr ':' ternary_expr)?
   logical_or_expr → logical_and_expr ('||' logical_and_expr)*
   logical_and_expr → bitwise_or_expr ('&&' bitwise_or_expr)*
   bitwise_or_expr → bitwise_xor_expr ('|' bitwise_xor_expr)*
   bitwise_xor_expr → bitwise_and_expr ('^' bitwise_and_expr)*
   bitwise_and_expr → equality_expr ('&' equality_expr)*
   equality_expr → relational_expr (('==' | '!=') relational_expr)*
   relational_expr → shift_expr (('<' | '>' | '<=' | '>=') shift_expr)*
   shift_expr → additive_expr (('<<' | '>>') additive_expr)*
   additive_expr → multiplicative_expr (('+' | '-') multiplicative_expr)*
   multiplicative_expr → power_expr (('*' | '/' | '%') power_expr)*
   power_expr → unary_expr ('**' power_expr)?  // right-associative
   unary_expr → ('++' | '--' | '+' | '-' | '!' | '~')? postfix_expr
   postfix_expr → primary_expr ('++' | '--')?
   primary_expr → NUMBER | VARIABLE | '(' arithmetic_expr ')'
   ```

### Evaluator Requirements
1. **64-bit signed integer arithmetic**
2. **Overflow wraps around** (two's complement)
3. **Division by zero is an error**
4. **Variable lookup in arithmetic context**
5. **Support for assignment side effects**

### Error Handling
- Division by zero: Runtime error
- Invalid syntax: Parse error
- Invalid base: Runtime error
- Non-numeric variable in numeric context: Treated as variable name

### AST Node Types Needed
- `ArithmeticExpansion`
- `BinaryOp` (with operator type)
- `UnaryOp` (with operator type)
- `TernaryOp`
- `AssignmentOp`
- `VariableRef` (arithmetic context)
- `NumberLiteral` (with base support)

## Implementation Strategy

1. **Phase 1**: Basic arithmetic with `+`, `-`, `*`, `/`, `%` and parentheses
2. **Phase 2**: Add comparison and logical operators
3. **Phase 3**: Add bitwise operators and shifts
4. **Phase 4**: Add assignment operators and increment/decrement
5. **Phase 5**: Add ternary operator and comma operator
6. **Phase 6**: Add base conversion and special number formats

## Testing Considerations

1. **Precedence tests**: Ensure correct operator precedence
2. **Associativity tests**: Right-associative for `**`, `?:`, and assignments
3. **Edge cases**: Overflow, division by zero, empty expressions
4. **Variable substitution**: With/without `$`, undefined variables
5. **Nested expressions**: Arithmetic within arithmetic
6. **Integration**: Arithmetic in redirections, assignments, array indices