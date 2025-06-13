# Arithmetic Command Syntax in Bash: ((expression))

## Overview

The arithmetic command `((expression))` is a compound command in bash that evaluates arithmetic expressions. It's different from arithmetic expansion `$((expression))` which returns the value of the expression. The arithmetic command returns an exit status based on the evaluation.

## Key Characteristics

1. **Exit Status**: Returns 0 (success) if the expression evaluates to non-zero, and 1 (failure) if it evaluates to zero
2. **Side Effects**: Can perform assignments and other operations that modify variables
3. **No Output**: Unlike `$((expr))`, it doesn't produce output - it's used for its side effects and exit status
4. **C-style Syntax**: Supports C-style operators and syntax

## Syntax Forms

### 1. Standalone Arithmetic Command
```bash
((expression))
```

### 2. In Conditional Statements
```bash
if ((expression)); then
    # commands
fi
```

### 3. Multiple Expressions
```bash
((expr1, expr2, expr3))  # Evaluates all, returns based on last
```

## Common Use Cases

### 1. Variable Assignment and Manipulation
```bash
# Assignment
((x = 5))
((y = x * 2))

# Increment/Decrement
((i++))      # Post-increment
((++i))      # Pre-increment
((i--))      # Post-decrement
((--i))      # Pre-decrement

# Compound assignments
((x += 5))   # x = x + 5
((x *= 2))   # x = x * 2
((x /= 3))   # x = x / 3
((x %= 4))   # x = x % 4
```

### 2. Conditional Testing
```bash
# Numeric comparisons
if ((x > 5)); then
    echo "x is greater than 5"
fi

if ((x == 10)); then
    echo "x equals 10"
fi

if ((x != 0)); then
    echo "x is not zero"
fi

# Multiple conditions
if ((x > 0 && x < 10)); then
    echo "x is between 0 and 10"
fi

if ((x < 0 || x > 100)); then
    echo "x is out of normal range"
fi
```

### 3. Loop Control
```bash
# C-style for loop (already implemented in psh)
for ((i=0; i<10; i++)); do
    echo $i
done

# While loop with arithmetic condition
i=0
while ((i < 10)); do
    echo $i
    ((i++))
done

# Until loop
i=10
until ((i == 0)); do
    echo $i
    ((i--))
done
```

### 4. Ternary Operator
```bash
((result = x > 5 ? 100 : 50))
# If x > 5, result = 100, else result = 50
```

### 5. Bitwise Operations
```bash
((flags = 0x0F))
((flags &= 0x03))   # Bitwise AND
((flags |= 0x10))   # Bitwise OR
((flags ^= 0x01))   # Bitwise XOR
((flags <<= 2))     # Left shift
((flags >>= 1))     # Right shift
```

## Operators Supported

### Arithmetic Operators
- `+` Addition
- `-` Subtraction
- `*` Multiplication
- `/` Division (integer)
- `%` Modulo (remainder)
- `**` Exponentiation

### Comparison Operators
- `<` Less than
- `>` Greater than
- `<=` Less than or equal
- `>=` Greater than or equal
- `==` Equal
- `!=` Not equal

### Logical Operators
- `&&` Logical AND
- `||` Logical OR
- `!` Logical NOT

### Bitwise Operators
- `&` Bitwise AND
- `|` Bitwise OR
- `^` Bitwise XOR
- `~` Bitwise NOT
- `<<` Left shift
- `>>` Right shift

### Assignment Operators
- `=` Assignment
- `+=`, `-=`, `*=`, `/=`, `%=` Compound assignments
- `&=`, `|=`, `^=`, `<<=`, `>>=` Bitwise compound assignments

## Examples to Try in Bash

```bash
# Example 1: Simple assignment and test
((x = 10))
echo $?  # 0 (success, because 10 is non-zero)

((x = 0))
echo $?  # 1 (failure, because 0 is zero)

# Example 2: Increment in a loop
i=0
while ((i < 5)); do
    echo "i = $i"
    ((i++))
done

# Example 3: Multiple expressions
((a=5, b=10, c=a+b))
echo "c = $c"  # c = 15

# Example 4: Conditional with arithmetic
x=7
if ((x % 2 == 1)); then
    echo "x is odd"
else
    echo "x is even"
fi

# Example 5: Complex expression
((x = 5))
((y = 3))
((result = (x > y) ? x*2 : y*2))
echo "result = $result"  # result = 10

# Example 6: Exit status in conditional execution
((5 > 3)) && echo "5 is greater than 3"
((2 > 5)) || echo "2 is not greater than 5"

# Example 7: Nested arithmetic in function
check_range() {
    local n=$1
    if ((n >= 0 && n <= 100)); then
        echo "$n is in range"
        return 0
    else
        echo "$n is out of range"
        return 1
    fi
}

check_range 50   # 50 is in range
check_range 150  # 150 is out of range
```

## Differences from Arithmetic Expansion

| Feature | `((expr))` Command | `$((expr))` Expansion |
|---------|-------------------|---------------------|
| Purpose | Execute arithmetic, return exit status | Evaluate and substitute result |
| Output | No output | Expands to the result |
| Usage | Standalone or in conditionals | Inside strings or assignments |
| Example | `((x++))` | `echo $((x+1))` |

## Implementation Notes for psh

To implement arithmetic command syntax in psh, the following components would need to be added:

1. **Parser Changes**: Recognize `((` as a special token that starts an arithmetic command
2. **AST Node**: Create an ArithmeticCommand node type
3. **Executor**: Implement arithmetic command execution that:
   - Evaluates the expression using the existing arithmetic evaluator
   - Returns exit code 0 if result is non-zero, 1 if zero
   - Handles variable assignments and side effects
4. **Integration**: Ensure it works in all contexts (standalone, if conditions, while/until loops)

## Testing the Feature

Once implemented, the 5 xfailed tests in test_c_style_for_loops.py should pass:
- `test_empty_condition`
- `test_empty_update`
- `test_all_empty`
- `test_break_in_c_style_for`
- `test_continue_in_c_style_for`

These tests use arithmetic commands in conditions like `if ((i >= 3)); then break; fi`.