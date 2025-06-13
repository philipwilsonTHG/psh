# Process Substitution Architecture for psh

## Overview

Process substitution is a bash feature that allows treating the output of a command as a file. It comes in two forms:
- `<(command)` - Makes command output available as input (like a readable file)
- `>(command)` - Makes a writable file that sends data to command's stdin

Common use cases:
```bash
# Compare two directory listings
diff <(ls dir1) <(ls dir2)

# Split log output to multiple processors
tail -f app.log | tee >(grep ERROR > errors.log) >(grep WARN > warnings.log)

# Read from multiple sources
paste <(cut -f1 file1) <(cut -f2 file2)
```

## Current Architecture Analysis

### Strengths to Build On

1. **Command Substitution Infrastructure**
   - Already handles `$(...)` and backticks
   - Shows pattern for parsing nested commands
   - Has execution mechanism for subcommands

2. **Pipe and File Descriptor Management**
   - Robust fork/exec with pipes
   - File descriptor duplication (dup2)
   - Process group management
   - Child process tracking

3. **AST Design**
   - Clean separation of concerns
   - Easy to extend with new node types
   - Proper command expansion pipeline

4. **Heredoc Implementation**
   - Shows how to use pipes for dynamic content
   - Similar to process substitution needs

### Components to Modify

1. **Tokenizer** (`psh/tokenizer.py`)
   - Add recognition for `<(` and `>(`
   - Handle nested parentheses
   - Create new token types

2. **Parser** (`psh/parser.py`)
   - Parse process substitutions as word elements
   - Handle in argument lists and redirections

3. **AST Nodes** (`psh/ast_nodes.py`)
   - New node type for process substitution

4. **Executor** (`psh/shell.py`)
   - Implement process substitution execution
   - Manage file descriptors and child processes

## Detailed Design

### 1. Tokenizer Changes

Add new token types:
```python
class TokenType(Enum):
    # ... existing tokens ...
    PROCESS_SUB_IN = auto()   # <(...)
    PROCESS_SUB_OUT = auto()  # >(...)
```

Modify `read_word()` to recognize process substitution:
```python
def read_word(self):
    """Read a word token, handling process substitution."""
    # Check for process substitution
    if self.current_char == '<' and self.peek() == '(':
        return self.read_process_substitution('in')
    elif self.current_char == '>' and self.peek() == '(':
        return self.read_process_substitution('out')
    
    # ... existing word reading logic ...

def read_process_substitution(self, direction):
    """Read a process substitution <(...) or >(...)."""
    # Consume < or >
    self.advance()
    # Consume (
    self.advance()
    
    # Read until matching )
    paren_count = 1
    content = []
    
    while self.current_char is not None and paren_count > 0:
        if self.current_char == '(':
            paren_count += 1
        elif self.current_char == ')':
            paren_count -= 1
            if paren_count == 0:
                break
        content.append(self.current_char)
        self.advance()
    
    if paren_count != 0:
        raise TokenizerError("Unclosed process substitution")
    
    # Consume closing )
    self.advance()
    
    command = ''.join(content)
    token_type = TokenType.PROCESS_SUB_IN if direction == 'in' else TokenType.PROCESS_SUB_OUT
    return Token(token_type, f"{('<' if direction == 'in' else '>')}{command})")
```

### 2. AST Node Design

Add to `psh/ast_nodes.py`:
```python
@dataclass
class ProcessSubstitution:
    """Represents a process substitution <(...) or >(...)."""
    direction: str  # 'in' or 'out'
    command: str    # Command to execute
    
    def __str__(self):
        symbol = '<' if self.direction == 'in' else '>'
        return f"{symbol}({self.command})"
```

### 3. Parser Changes

Modify `parse_word()` to handle process substitution:
```python
def parse_word(self):
    """Parse a word, which can be a simple word, variable, command sub, or process sub."""
    token = self.current_token
    
    if token.type == TokenType.WORD:
        self.advance()
        return ('WORD', token.value)
    elif token.type == TokenType.STRING:
        self.advance()
        return ('STRING', token.value)
    elif token.type == TokenType.VARIABLE:
        self.advance()
        return ('VARIABLE', token.value)
    elif token.type == TokenType.COMMAND_SUB:
        self.advance()
        return ('COMMAND_SUB', token.value)
    elif token.type == TokenType.PROCESS_SUB_IN:
        self.advance()
        return ('PROCESS_SUB', ProcessSubstitution('in', token.value[2:-1]))
    elif token.type == TokenType.PROCESS_SUB_OUT:
        self.advance()
        return ('PROCESS_SUB', ProcessSubstitution('out', token.value[2:-1]))
    else:
        self.error(f"Expected word, got {token.type}")
```

### 4. Execution Strategy

Process substitution needs to:
1. Fork a child process for each substitution
2. Set up pipes between parent and child
3. Replace the substitution with a file path (like `/dev/fd/N`)
4. Execute the main command with these file descriptors available

Add to `psh/shell.py`:

```python
def _setup_process_substitutions(self, command: Command) -> Tuple[List[int], List[str], List[int]]:
    """Set up process substitutions and return (fds, paths, child_pids)."""
    fds_to_keep = []
    substituted_args = []
    child_pids = []
    
    for i, arg in enumerate(command.args):
        arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
        
        if arg_type == 'PROCESS_SUB':
            proc_sub = arg  # This is a ProcessSubstitution object
            
            # Create pipe
            if proc_sub.direction == 'in':
                # For <(cmd), parent reads from pipe, child writes to it
                read_fd, write_fd = os.pipe()
                parent_fd = read_fd
                child_fd = write_fd
                child_stdio = (0, child_fd, 2)  # stdin, stdout, stderr
            else:
                # For >(cmd), parent writes to pipe, child reads from it
                read_fd, write_fd = os.pipe()
                parent_fd = write_fd
                child_fd = read_fd
                child_stdio = (child_fd, 1, 2)  # stdin, stdout, stderr
            
            # Fork child for process substitution
            pid = os.fork()
            if pid == 0:  # Child
                # Close parent's end of pipe
                os.close(parent_fd)
                
                # Set up child's stdio
                if child_stdio[0] != 0:
                    os.dup2(child_stdio[0], 0)
                if child_stdio[1] != 1:
                    os.dup2(child_stdio[1], 1)
                
                # Close the pipe fd we duplicated
                os.close(child_fd)
                
                # Execute the substitution command
                # Parse and execute the command string
                tokens = tokenize(proc_sub.command)
                ast = parse(tokens)
                temp_shell = Shell()
                temp_shell.env = self.env.copy()
                temp_shell.variables = self.variables.copy()
                exit_code = temp_shell.execute_command_list(ast)
                os._exit(exit_code)
            
            else:  # Parent
                # Close child's end of pipe
                os.close(child_fd)
                
                # Keep track of what we need to clean up
                fds_to_keep.append(parent_fd)
                child_pids.append(pid)
                
                # Create path for this fd
                # On Linux/macOS, we can use /dev/fd/N
                fd_path = f"/dev/fd/{parent_fd}"
                substituted_args.append(fd_path)
        else:
            # Not a process substitution, keep as-is
            substituted_args.append(arg)
    
    return fds_to_keep, substituted_args, child_pids

def _expand_arguments(self, command: Command) -> list:
    """Expand variables, command substitutions, process substitutions, tildes, and globs."""
    # First handle process substitutions
    if any(command.arg_types[i] == 'PROCESS_SUB' for i in range(len(command.arg_types))):
        fds, substituted_args, child_pids = self._setup_process_substitutions(command)
        
        # Store for cleanup
        self._process_sub_fds = fds
        self._process_sub_pids = child_pids
        
        # Update command args with substituted paths
        command.args = substituted_args
        # Update arg_types to treat substituted paths as words
        command.arg_types = ['WORD'] * len(substituted_args)
    
    # Continue with normal argument expansion
    # ... existing expansion code ...
```

### 5. Cleanup and Process Management

Add cleanup in command execution:
```python
def execute_command(self, command: Command):
    """Execute a single command."""
    try:
        # ... existing execution code ...
        
        # Execute the command
        result = self._execute_external(expanded_args, command)
        
    finally:
        # Clean up process substitutions
        if hasattr(self, '_process_sub_fds'):
            for fd in self._process_sub_fds:
                try:
                    os.close(fd)
                except:
                    pass
            del self._process_sub_fds
        
        if hasattr(self, '_process_sub_pids'):
            for pid in self._process_sub_pids:
                try:
                    os.waitpid(pid, 0)
                except:
                    pass
            del self._process_sub_pids
        
    return result
```

### 6. Alternative Implementation for Systems without /dev/fd

For systems that don't support `/dev/fd`, use named pipes (FIFOs):

```python
def _create_fifo_for_process_sub(self):
    """Create a named pipe for process substitution."""
    import tempfile
    
    # Create unique FIFO
    fifo_path = tempfile.mktemp(prefix='psh_procsub_')
    os.mkfifo(fifo_path)
    
    # Register for cleanup
    self._temp_fifos.append(fifo_path)
    
    return fifo_path
```

## Implementation Phases

### Phase 1: Basic Process Substitution
1. Implement tokenizer changes
2. Add AST node
3. Update parser
4. Basic execution with /dev/fd
5. Add tests for simple cases

### Phase 2: Robustness
1. Handle nested process substitutions
2. Proper error handling
3. Process cleanup and signal handling
4. FIFO fallback for systems without /dev/fd

### Phase 3: Integration
1. Test with pipelines
2. Test with redirections
3. Test with job control
4. Test multiple process substitutions

## Testing Strategy

Create comprehensive tests:
```python
# test_process_substitution.py

def test_simple_input_substitution():
    """Test basic <(cmd) substitution."""
    shell = Shell()
    # diff <(echo "hello") <(echo "world")
    result = shell.run_command('diff <(echo "hello") <(echo "world")')
    assert result != 0  # Files differ

def test_simple_output_substitution():
    """Test basic >(cmd) substitution."""
    shell = Shell()
    # echo "test" | tee >(cat > file1.txt)
    result = shell.run_command('echo "test" | tee >(cat > file1.txt)')
    assert result == 0

def test_multiple_substitutions():
    """Test multiple process substitutions."""
    shell = Shell()
    # paste <(seq 1 3) <(seq 4 6)
    result = shell.run_command('paste <(seq 1 3) <(seq 4 6)')
    assert result == 0

def test_nested_substitution():
    """Test nested process substitution."""
    shell = Shell()
    # cat <(echo "line1" | cat <(echo "nested"))
    result = shell.run_command('cat <(echo "line1" | cat <(echo "nested"))')
    assert result == 0
```

## Error Handling

1. **Syntax Errors**: Invalid process substitution syntax
2. **Execution Errors**: Command fails inside substitution
3. **Resource Errors**: Too many file descriptors
4. **Signal Handling**: Proper cleanup on interruption

## Compatibility Notes

1. **Platform Support**: Primary implementation uses `/dev/fd/N` (Linux, macOS)
2. **Fallback**: Named pipes for other systems
3. **Limitations**: Maximum number of file descriptors
4. **Differences from Bash**: Simplified implementation, same user-visible behavior

## Educational Value

Process substitution teaches:
1. Advanced file descriptor manipulation
2. Inter-process communication via pipes
3. Fork and process management
4. Dynamic file descriptor paths
5. Resource cleanup and error handling

This implementation maintains psh's educational clarity while adding a powerful shell feature.