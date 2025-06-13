# Select Statement Implementation Analysis for PSH

## Overview

The `select` statement is a bash-specific control structure that presents a numbered menu to the user and reads their selection. It's particularly useful for creating interactive scripts with menu-driven interfaces.

## Bash Select Statement Behavior

### Syntax
```bash
select var in list; do
    commands
done
```

### Key Characteristics

1. **Menu Display**: Automatically generates a numbered menu from the word list
2. **Prompt**: Uses PS3 variable (defaults to "#? ") for the selection prompt
3. **User Input**: Reads user input into the REPLY variable
4. **Variable Assignment**: 
   - If user enters a valid number, sets `var` to the corresponding list item
   - If invalid or empty input, `var` is set to empty string
   - REPLY always contains the raw user input
5. **Loop Behavior**: Continues looping until explicitly broken with `break` or loop control
6. **Output**: Menu is printed to stderr, allowing stdout redirection

### Example Behavior
```bash
$ select fruit in apple banana cherry; do
>     echo "You selected: $fruit (REPLY=$REPLY)"
>     break
> done
1) apple
2) banana  
3) cherry
#? 2
You selected: banana (REPLY=2)
```

## Implementation Components Required

### 1. Token Types (token_types.py)
Add new token type:
```python
SELECT = auto()  # New keyword token
```

### 2. AST Node (ast_nodes.py)
Create new AST node:
```python
@dataclass
class SelectStatement(Statement):
    """Select menu statement."""
    variable: str                    # Variable to store selection
    items: List[str]                # List of menu items
    body: StatementList             # Commands to execute
    redirects: List[Redirect] = field(default_factory=list)
```

### 3. Parser (parser.py)
Add parsing logic:
- Recognize SELECT keyword in `parse_control_structure()`
- Implement `parse_select_statement()` method similar to `parse_for_statement()`
- Parse: `select WORD in word_list; do command_list done`

### 4. Executor (executor/control_flow.py)
Implement `execute_select()` method:
- Display numbered menu to stderr
- Read user input using PS3 prompt
- Set variable based on selection
- Set REPLY variable with raw input
- Loop until break

### 5. State Machine Lexer (state_machine_lexer.py)
Add 'select' to KEYWORDS set

### 6. Interactive Support
- Use existing PS3 variable support (or implement if missing)
- Leverage read builtin functionality for input

## Implementation Plan

### Phase 1: Parser Support
1. Add SELECT token type
2. Create SelectStatement AST node
3. Implement parser method
4. Add tests for parsing

### Phase 2: Executor Implementation
1. Implement menu display logic
2. Handle user input and validation
3. Implement loop control
4. Add PS3 support if needed

### Phase 3: Integration
1. Wire up control flow executor
2. Test with various scenarios
3. Handle edge cases (empty lists, redirections)

## Challenges and Considerations

### 1. Menu Display
- Must output to stderr to allow stdout redirection
- Format: "N) item" with proper alignment
- Handle long item names gracefully

### 2. Input Handling
- Need to handle both numeric and non-numeric input
- Empty input (just pressing Enter) should be handled
- EOF (Ctrl+D) should break the loop

### 3. Variable Scoping
- Loop variable should follow same scoping rules as for loops
- REPLY variable must be set in correct scope

### 4. Signal Handling
- Ctrl+C should interrupt select loop properly
- Need to restore terminal state if interrupted

### 5. Nested Select Statements
- Should work like nested loops
- Break/continue with levels should work

## Test Cases

### Basic Functionality
```bash
# Test 1: Basic selection
select item in a b c; do
    echo "Selected: $item"
    break
done

# Test 2: Invalid selection
select item in a b c; do
    if [ -z "$item" ]; then
        echo "Invalid: $REPLY"
    fi
    break
done

# Test 3: Custom PS3
PS3="Choose: "
select item in a b c; do
    echo "$item"
    break
done
```

### Advanced Features
```bash
# Test 4: Command substitution in list
select file in $(ls *.txt); do
    echo "Processing $file"
    break
done

# Test 5: Break levels
for i in 1 2; do
    select item in a b quit; do
        if [ "$item" = "quit" ]; then
            break 2
        fi
    done
done

# Test 6: Redirections
select item in a b c; do
    echo "$item"
    break
done > output.txt 2>&1
```

## Estimated Effort

- Parser implementation: 2-3 hours
- Executor implementation: 3-4 hours  
- Testing and edge cases: 2-3 hours
- Total: 7-10 hours

## Benefits

1. **User Experience**: Enables interactive menu-driven scripts
2. **Compatibility**: Increases bash compatibility for existing scripts
3. **Educational**: Good example of a control structure with I/O interaction
4. **Completeness**: Fills gap in control structure implementations

## Conclusion

The select statement is a well-scoped feature that would enhance PSH's interactive capabilities and bash compatibility. It follows similar patterns to existing control structures (especially for loops) but adds the unique aspect of user interaction. The implementation is straightforward and would provide significant value for interactive script development.