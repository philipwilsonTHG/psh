# Select Statement Implementation Plan for PSH

## Overview

This document outlines the implementation plan for adding bash-compatible `select` statement support to PSH. The `select` statement creates interactive numbered menus from word lists and processes user selections in a loop.

## Syntax

```bash
select name in word_list; do
    commands
done
```

## Feature Requirements

### Core Functionality
1. Display numbered menu of options to stderr
2. Use PS3 prompt (default "#? ") for user input
3. Set variable to selected item (or empty if invalid)
4. Set REPLY variable to raw user input
5. Loop until explicit break or EOF (Ctrl+D)
6. Support I/O redirections on the loop

### Behavioral Requirements
- Menu formatting: Multi-column display for many items
- Input validation: Handle numeric, non-numeric, empty, and out-of-range inputs
- Signal handling: Clean exit on Ctrl+C
- Nested support: Work with break/continue levels
- Empty list: No menu display, immediate loop exit

## Implementation Steps

### Phase 1: Parser Support (2-3 hours)

#### 1.1 Token Types (`token_types.py`)
```python
# Add to TokenType enum
SELECT = auto()
```

#### 1.2 Lexer (`state_machine_lexer.py`)
```python
# Add to KEYWORDS dictionary
'select': TokenType.SELECT,
```

#### 1.3 AST Node (`ast_nodes.py`)
```python
@dataclass
class SelectStatement(Statement):
    """Represents a select statement."""
    variable: str
    items: List[Union[str, CommandSubstitution]]  # Words to expand
    body: StatementList
    redirects: List[Redirect] = field(default_factory=list)
```

#### 1.4 Parser Updates (`parser.py`)
```python
# Add to TokenGroups.CONTROL_KEYWORDS
TokenType.SELECT,

# In parse_control_structure()
elif self.current_token.type == TokenType.SELECT:
    return self.parse_select_statement()

# New method
def parse_select_statement(self):
    """Parse select statement: select name in words; do commands done"""
    self.expect(TokenType.SELECT)
    
    # Parse variable name
    if not self.current_token or self.current_token.type != TokenType.WORD:
        raise ParserError("Expected variable name after 'select'")
    variable = self.current_token.value
    self.advance()
    
    # Expect 'in'
    self.expect(TokenType.IN)
    
    # Parse word list (reuse existing method)
    items = self._parse_for_iterable()
    
    # Parse do block
    self.skip_separators()
    self.expect(TokenType.DO)
    body = self.parse_command_list(end_tokens={TokenType.DONE})
    self.expect(TokenType.DONE)
    
    # Parse optional redirections
    redirects = self.parse_redirections()
    
    return SelectStatement(
        variable=variable,
        items=items,
        body=body,
        redirects=redirects
    )
```

### Phase 2: Executor Implementation (4-5 hours)

#### 2.1 Control Flow Executor (`executor/control_flow.py`)
```python
# In execute() method
elif isinstance(node, SelectStatement):
    return self.execute_select(node)

# New method
def execute_select(self, node: SelectStatement) -> int:
    """Execute a select statement."""
    # Set up redirections
    with self.shell.io_manager.setup_redirects(node.redirects):
        # Expand the word list
        expanded_items = []
        for item in node.items:
            expanded = self.shell.expansion_manager.expand_value(item)
            if isinstance(expanded, list):
                expanded_items.extend(expanded)
            else:
                expanded_items.append(expanded)
        
        # Empty list - exit immediately
        if not expanded_items:
            return 0
        
        # Main select loop
        return self._execute_select_loop(node.variable, expanded_items, node.body)

def _execute_select_loop(self, variable: str, items: List[str], body: StatementList) -> int:
    """Execute the select loop with menu display and input handling."""
    exit_code = 0
    
    # Get PS3 prompt (add PS3 support if not present)
    ps3 = self.shell.state.get_variable("PS3", "#? ")
    
    try:
        while True:
            # Display menu to stderr
            self._display_select_menu(items)
            
            # Show prompt and read input
            try:
                sys.stderr.write(ps3)
                sys.stderr.flush()
                reply = input()
            except (EOFError, KeyboardInterrupt):
                # Ctrl+D or Ctrl+C exits the loop
                sys.stderr.write("\n")
                break
            
            # Set REPLY variable
            self.shell.state.set_variable("REPLY", reply)
            
            # Process selection
            if reply.strip().isdigit():
                choice = int(reply.strip())
                if 1 <= choice <= len(items):
                    # Valid selection
                    selected = items[choice - 1]
                    self.shell.state.set_variable(variable, selected)
                else:
                    # Out of range
                    self.shell.state.set_variable(variable, "")
            else:
                # Non-numeric input
                self.shell.state.set_variable(variable, "")
            
            # Execute loop body
            try:
                exit_code = self.shell.executor_manager.execute(body)
            except LoopBreak as e:
                if e.level <= 1:
                    break
                else:
                    e.level -= 1
                    raise
            except LoopContinue as e:
                if e.level <= 1:
                    continue
                else:
                    e.level -= 1
                    raise
    
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        exit_code = 130
    
    return exit_code

def _display_select_menu(self, items: List[str]) -> None:
    """Display the select menu to stderr."""
    # Calculate layout
    num_items = len(items)
    if num_items <= 9:
        # Single column for small lists
        for i, item in enumerate(items, 1):
            sys.stderr.write(f"{i}) {item}\n")
    else:
        # Multi-column for larger lists
        columns = 2 if num_items <= 20 else 3
        rows = (num_items + columns - 1) // columns
        
        # Calculate column widths
        col_width = max(len(f"{i}) {items[i-1]}") for i in range(1, num_items + 1)) + 3
        
        for row in range(rows):
            for col in range(columns):
                idx = row + col * rows
                if idx < num_items:
                    entry = f"{idx + 1}) {items[idx]}"
                    sys.stderr.write(entry.ljust(col_width))
            sys.stderr.write("\n")
```

#### 2.2 PS3 Variable Support

Add PS3 to the shell's default variables if not already present. This might require updates to:
- Initial variable setup in `ShellState`
- Documentation of special variables

### Phase 3: Testing (2-3 hours)

#### 3.1 Test File (`tests/test_select_statement.py`)
```python
import pytest
from tests.helpers.shell_factory import create_shell

class TestSelectStatement:
    def test_basic_select(self, shell):
        """Test basic select functionality."""
        # Test with numeric input
        script = '''
        echo "1" | select fruit in apple banana cherry; do
            echo "Selected: $fruit"
            echo "Reply: $REPLY"
            break
        done
        '''
        result = shell.run_command(script)
        assert "Selected: apple" in result.output
        assert "Reply: 1" in result.output
    
    def test_invalid_selection(self, shell):
        """Test invalid numeric and non-numeric selections."""
        script = '''
        printf "10\\nhello\\n2\\n" | select x in a b c; do
            echo "x='$x' REPLY='$REPLY'"
            [[ -z "$x" && "$REPLY" == "10" ]] && continue
            [[ -z "$x" && "$REPLY" == "hello" ]] && continue
            [[ "$x" == "b" && "$REPLY" == "2" ]] && break
        done
        '''
        result = shell.run_command(script)
        assert "x='' REPLY='10'" in result.output
        assert "x='' REPLY='hello'" in result.output
        assert "x='b' REPLY='2'" in result.output
    
    def test_empty_list(self, shell):
        """Test select with empty word list."""
        result = shell.run_command('select x in; do echo "Should not run"; done')
        assert "Should not run" not in result.output
        assert result.exit_code == 0
    
    def test_ps3_prompt(self, shell):
        """Test custom PS3 prompt."""
        script = '''
        PS3="Choose wisely: "
        echo "1" | select x in a b c; do break; done 2>&1 | grep -q "Choose wisely:"
        '''
        result = shell.run_command(script)
        assert result.exit_code == 0
    
    def test_break_continue(self, shell):
        """Test break and continue in select loops."""
        script = '''
        printf "1\\n2\\n3\\n" | select num in one two three; do
            case $num in
                one) echo "First"; continue;;
                two) echo "Second"; continue;;
                three) echo "Third"; break;;
            esac
        done
        '''
        result = shell.run_command(script)
        assert "First" in result.output
        assert "Second" in result.output
        assert "Third" in result.output
    
    def test_nested_select(self, shell):
        """Test nested select statements."""
        script = '''
        echo "1" | select outer in A B; do
            echo "1" | select inner in X Y; do
                echo "Outer: $outer, Inner: $inner"
                break 2
            done
        done
        '''
        result = shell.run_command(script)
        assert "Outer: A, Inner: X" in result.output
    
    def test_io_redirection(self, shell):
        """Test that select menu goes to stderr while body output goes to stdout."""
        script = '''
        echo "1" | select x in option1 option2; do
            echo "Selected: $x"
            break
        done 2>/dev/null
        '''
        result = shell.run_command(script)
        assert "Selected: option1" in result.output
        # Menu should not appear in stdout since stderr was redirected
        assert "1) option1" not in result.output
    
    def test_command_substitution_in_list(self, shell):
        """Test select with command substitution in word list."""
        script = '''
        echo "2" | select file in $(echo "file1 file2 file3"); do
            echo "Chosen: $file"
            break
        done
        '''
        result = shell.run_command(script)
        assert "Chosen: file2" in result.output
    
    def test_eof_handling(self, shell):
        """Test EOF (Ctrl+D) handling."""
        # Simulate EOF by not providing any input
        script = '''
        select x in a b c; do
            echo "Should not execute"
        done < /dev/null
        echo "After select"
        '''
        result = shell.run_command(script)
        assert "Should not execute" not in result.output
        assert "After select" in result.output
```

### Phase 4: Integration and Documentation (1 hour)

#### 4.1 Update Documentation
- Add select statement to user guide (`docs/user_guide/11_control_structures.md`)
- Update README.md feature list
- Add examples to `examples/` directory

#### 4.2 Example Script (`examples/select_demo.sh`)
```bash
#!/usr/bin/env psh

# Basic select menu
echo "=== Basic Fruit Selection ==="
select fruit in apple banana cherry quit; do
    case $fruit in
        apple|banana|cherry)
            echo "You selected: $fruit"
            ;;
        quit)
            echo "Goodbye!"
            break
            ;;
        *)
            echo "Invalid option: $REPLY"
            ;;
    esac
done

# Custom PS3 prompt
echo -e "\n=== File Operations Menu ==="
PS3="Enter your choice (1-4): "
select operation in "List files" "Show date" "Print working directory" "Exit"; do
    case $operation in
        "List files")
            ls -la
            ;;
        "Show date")
            date
            ;;
        "Print working directory")
            pwd
            ;;
        "Exit")
            break
            ;;
        *)
            echo "Please select a valid option (1-4)"
            ;;
    esac
done

# Dynamic menu from command output
echo -e "\n=== Select a Shell Script ==="
select script in *.sh "None"; do
    if [[ "$script" == "None" ]]; then
        echo "No script selected"
        break
    elif [[ -n "$script" ]]; then
        echo "You selected: $script"
        echo "First line: $(head -n1 "$script")"
        break
    else
        echo "Invalid selection: $REPLY"
    fi
done
```

## Testing Strategy

1. **Unit Tests**: Test parser recognition and AST generation
2. **Integration Tests**: Test full select execution with various inputs
3. **Edge Cases**:
   - Empty word lists
   - Very long word lists (test multi-column formatting)
   - Special characters in menu items
   - Nested select statements
   - Signal handling (Ctrl+C, Ctrl+D)
   - I/O redirection combinations

## Success Criteria

1. All test cases pass
2. Bash compatibility for common use cases
3. Proper PS3 prompt support
4. Clean menu formatting
5. Correct variable setting behavior
6. Proper break/continue support
7. Signal handling matches bash behavior

## Estimated Timeline

- Phase 1 (Parser): 2-3 hours
- Phase 2 (Executor): 4-5 hours  
- Phase 3 (Testing): 2-3 hours
- Phase 4 (Integration): 1 hour
- **Total: 9-12 hours**

## Future Enhancements

1. LINES/COLUMNS environment variable support for menu layout
2. Configurable column layout algorithm
3. Color support for menu items (if terminal supports it)
4. Extended select syntax (select-case combination)

## Notes

- The select statement fits well within PSH's existing control structure framework
- Reuses existing patterns from for loops and while loops
- Main complexity is in menu formatting and input handling
- PS3 variable support may require minor shell state updates