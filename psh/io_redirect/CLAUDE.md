# I/O Redirection Subsystem

This document provides guidance for working with the PSH I/O redirection subsystem.

## Architecture Overview

The I/O subsystem handles all file descriptor redirections including file redirections, heredocs, here strings, and process substitutions.

```
IOManager (orchestrator)
     ↓
┌────┴─────┬──────────┬──────────┐
↓          ↓          ↓          ↓
File      Heredoc   Process    Context
Redirector Handler  SubHandler  Manager
```

## Key Files

| File | Purpose |
|------|---------|
| `manager.py` | `IOManager` - central orchestrator for all I/O operations |
| `file_redirect.py` | `FileRedirector` - file-based redirections (`<`, `>`, `>>`, etc.) |
| `heredoc.py` | `HeredocHandler` - here document processing (`<<`, `<<-`) |
| `process_sub.py` | `ProcessSubstitutionHandler` - process substitution (`<()`, `>()`) |

## Core Patterns

### 1. IOManager Orchestration

All I/O operations go through `IOManager`:

```python
class IOManager:
    def __init__(self, shell):
        self.file_redirector = FileRedirector(shell)
        self.heredoc_handler = HeredocHandler(shell)
        self.process_sub_handler = ProcessSubstitutionHandler(shell)
```

### 2. Context Manager for Temporary Redirections

```python
@contextmanager
def with_redirections(self, redirects: List[Redirect]):
    """Apply redirections temporarily, then restore."""
    saved_fds = self.apply_redirections(redirects)
    try:
        yield
    finally:
        self.restore_redirections(saved_fds)
```

### 3. File Descriptor Backup/Restore

```python
def apply_redirections(self, redirects) -> List[Tuple[int, int]]:
    """Apply redirections, returning (original_fd, saved_fd) pairs."""
    saved = []
    for redirect in redirects:
        # Backup original fd
        saved_fd = os.dup(redirect.fd)
        saved.append((redirect.fd, saved_fd))
        # Apply new redirection
        ...
    return saved

def restore_redirections(self, saved_fds):
    """Restore original file descriptors."""
    for original_fd, saved_fd in reversed(saved_fds):
        os.dup2(saved_fd, original_fd)
        os.close(saved_fd)
```

## Redirection Types

### Input Redirections

| Syntax | Type | Description |
|--------|------|-------------|
| `< file` | `<` | Read stdin from file |
| `<< DELIM` | `<<` | Here document |
| `<<- DELIM` | `<<-` | Here document (strip tabs) |
| `<<< string` | `<<<` | Here string |

### Output Redirections

| Syntax | Type | Description |
|--------|------|-------------|
| `> file` | `>` | Write stdout to file (truncate) |
| `>> file` | `>>` | Append stdout to file |
| `2> file` | `>` (fd=2) | Write stderr to file |
| `2>> file` | `>>` (fd=2) | Append stderr to file |

### File Descriptor Operations

| Syntax | Type | Description |
|--------|------|-------------|
| `2>&1` | `>&` | Redirect stderr to stdout |
| `>&2` | `>&` | Redirect stdout to stderr |
| `n>&m` | `>&` | Duplicate fd m to fd n |

### Process Substitution

| Syntax | Direction | Description |
|--------|-----------|-------------|
| `<(cmd)` | Input | Command output as input file |
| `>(cmd)` | Output | File that feeds command input |

## Redirection Flow

### For External Commands (Child Process)

```
1. Fork child process
2. In child: setup_child_redirections()
   - Open files with os.open()
   - Redirect with os.dup2()
   - Close original fds
3. Exec external command
4. Parent waits for child
```

### For Builtin Commands

```
1. setup_builtin_redirections()
   - Backup sys.stdin/stdout/stderr
   - Redirect Python file objects
   - Backup file descriptor 0 if needed
2. Execute builtin
3. restore_builtin_redirections()
   - Close redirected files
   - Restore original file objects
   - Restore fd 0 if backed up
```

## Common Tasks

### Adding a New Redirection Type

1. Add to `file_redirect.py`:
```python
def apply_redirections(self, redirects):
    for redirect in redirects:
        if redirect.type == 'NEW_TYPE':
            self._handle_new_type(redirect)
```

2. Handle in `setup_child_redirections()` in `manager.py`

3. Handle in `setup_builtin_redirections()` if applicable

4. Add tests in `tests/unit/io/` or `tests/integration/`

### Handling noclobber Option

```python
if redirect.type == '>':
    if self.state.options.get('noclobber', False):
        if os.path.exists(target):
            raise OSError(f"cannot overwrite existing file: {target}")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
```

## Key Implementation Details

### Heredoc Processing

```python
# Quoted delimiter: no expansion
<<'EOF'     # heredoc_quoted = True
<<"EOF"     # heredoc_quoted = True

# Unquoted delimiter: expand variables
<<EOF       # heredoc_quoted = False

# In handler:
if not heredoc_quoted:
    content = shell.expansion_manager.expand_string_variables(content)
```

### Here String

```python
# <<< creates pipe, writes string + newline
r, w = os.pipe()
content = expanded_content + '\n'
os.write(w, content.encode())
os.close(w)
os.dup2(r, 0)  # stdin
os.close(r)
```

### Process Substitution

```python
# <(cmd) creates:
# 1. Pipe
# 2. Fork child to run cmd
# 3. Return /dev/fd/N path

read_fd, write_fd = os.pipe()
pid = os.fork()
if pid == 0:  # Child
    os.close(read_fd)
    os.dup2(write_fd, 1)  # stdout to pipe
    # Execute command
    os._exit(exit_code)
else:  # Parent
    os.close(write_fd)
    return f"/dev/fd/{read_fd}"
```

### Variable Expansion in Targets

```python
target = redirect.target

# Expand variables (respecting quotes)
if redirect.quote_type != "'":
    target = shell.expansion_manager.expand_string_variables(target)

# Expand tilde
if target.startswith('~'):
    target = shell.expansion_manager.expand_tilde(target)
```

## Testing

```bash
# Run I/O unit tests
python -m pytest tests/unit/io/ -v

# Run redirection integration tests
python -m pytest tests/integration/redirections/ -v

# Debug redirections
python -m psh --debug-exec -c "echo hello > /tmp/test.txt"
```

## Common Pitfalls

1. **File Descriptor Leaks**: Always close duplicated fds after use.

2. **Backup Order**: Backup fds before any redirections; restore in reverse order.

3. **Builtin vs External**: Builtins use Python file objects; external commands use raw fds.

4. **Heredoc Expansion**: Remember: quoted delimiter = no expansion.

5. **Pipe Cleanup**: Close unused pipe ends in both parent and child.

6. **noclobber Check**: Must check before opening file, not after.

7. **Process Substitution PIDs**: Must wait for child processes to prevent zombies.

## Debug Options

```bash
python -m psh --debug-exec -c "cat < input.txt > output.txt"
```

Output example:
```
DEBUG IOManager: setup_builtin_redirections called
DEBUG IOManager: Redirects: [('<', 'input.txt', None), ('>', 'output.txt', None)]
DEBUG IOManager: Redirected stdout to file 'output.txt'
```

## Integration Points

### With Executor (`psh/executor/`)

- Called during command execution for all redirections
- `ProcessLauncher` calls `setup_child_redirections()` after fork
- Builtins use `setup_builtin_redirections()` / `restore_builtin_redirections()`

### With Expansion (`psh/expansion/`)

- Redirect targets expanded via `expansion_manager.expand_string_variables()`
- Tilde expanded via `expansion_manager.expand_tilde()`
- Heredoc content expanded based on delimiter quoting

### With Shell State (`psh/core/state.py`)

- `noclobber` option checked for `>` redirections
- Debug options control output

### With Parser (`psh/parser/`)

- `Redirect` AST nodes created with type, target, fd, heredoc_content
- `heredoc_quoted` attribute indicates if delimiter was quoted
