# Implementation Plan: POSIX `set` Builtin Options for PSH

## Phase 1: Simple Options (Low Complexity)

### 1.1 `-f` (noglob) - Disable Pathname Expansion

**Files to modify**:
- `psh/expansion/manager.py` - Add check in `expand_glob()`
- `psh/core/state.py` - Add 'noglob' to options dict
- `psh/builtins/environment.py` - Add 'f' to short_to_long mapping

**Implementation**:
```python
# In ExpansionManager.expand_glob()
def expand_glob(self, pattern: str) -> List[str]:
    """Expand glob patterns."""
    # Check if noglob is set
    if self.shell.state.options.get('noglob', False):
        return [pattern]  # Return pattern unchanged
    
    # Existing glob expansion code...
```

**Tests needed**:
- Test that `*` doesn't expand when `-f` is set
- Test that other expansions still work
- Test toggling the option on/off

### 1.2 `-v` (verbose) - Echo Input Lines

**Files to modify**:
- `psh/shell.py` - Add verbose output in command processing
- `psh/interactive/manager.py` - Add verbose output for interactive input
- `psh/scripting/manager.py` - Add verbose output for script lines

**Implementation**:
```python
# In shell's run_command or process_input
if self.state.options.get('verbose', False):
    print(input_line, file=sys.stderr)
```

### 1.3 `-n` (noexec) - Read but Don't Execute

**Files to modify**:
- `psh/executor/executor_visitor.py` - Add execution check
- `psh/shell.py` - Skip execution when noexec is set

**Implementation**:
```python
# In ExecutorVisitor
def visit_SimpleCommand(self, node):
    if self.shell.state.options.get('noexec', False):
        return 0  # Don't execute, just return success
    # Normal execution...
```

## Phase 2: Safety Features

### 2.1 `-C` (noclobber) - Prevent File Overwriting

**Files to modify**:
- `psh/io_redirect/redirect_manager.py` - Add existence check
- `psh/io_redirect/output_redirect_handler.py` - Implement noclobber logic
- `psh/parser.py` - Support `>|` operator

**Implementation**:
```python
# In OutputRedirectHandler
def handle(self, redirect, shell):
    if redirect.redirect_type == 'OUTPUT' and shell.state.options.get('noclobber', False):
        # Check if file exists
        if os.path.exists(redirect.target):
            raise RedirectionError(f"cannot overwrite existing file: {redirect.target}")
    
    # For >| operator, bypass noclobber check
    if redirect.redirect_type == 'OUTPUT_CLOBBER':
        # Force overwrite regardless of noclobber
```

**New token/operator needed**:
- Add `OUTPUT_CLOBBER` token type for `>|`
- Update lexer to recognize `>|` as a single token

### 2.2 `-o ignoreeof` - Prevent EOF Exit

**Files to modify**:
- `psh/interactive/manager.py` - Handle EOF in interactive mode
- `psh/shell.py` - Add EOF counter

**Implementation**:
```python
# In InteractiveManager
def handle_eof(self):
    if self.shell.state.options.get('ignoreeof', False):
        print("Use 'exit' to leave the shell", file=sys.stderr)
        return False  # Don't exit
    return True  # Normal EOF behavior
```

## Phase 3: Environment Integration

### 3.1 `-a` (allexport) - Auto-export Variables

**Files to modify**:
- `psh/core/scope.py` - Add export flag on assignment
- `psh/executor/executor_visitor.py` - Handle assignment export

**Implementation**:
```python
# In set_variable
def set_variable(self, name: str, value: str):
    # Normal variable setting...
    
    # If allexport is on, also export
    if self.shell.state.options.get('allexport', False):
        os.environ[name] = value
        # Mark variable as exported in our tracking
```

## Phase 4: Job Control Enhancements

### 4.1 `-b` (notify) - Async Job Notifications

**Files to modify**:
- `psh/job_control.py` - Add async notification
- `psh/shell.py` - Check for completed jobs before prompt

**Implementation**:
```python
# In Shell before displaying prompt
def check_completed_jobs(self):
    if self.state.options.get('notify', False):
        for job in self.job_manager.get_completed_jobs():
            self._print_job_status(job)
```

### 4.2 `-m` (monitor) - Job Control Mode

**Files to modify**:
- `psh/job_control.py` - Ensure process group creation
- Already mostly implemented in PSH

## Phase 5: Advanced Features

### 5.1 `-h` (hashcmds) - Command Hashing

**Files to create**:
- `psh/core/command_cache.py` - Command location cache

**Implementation**:
```python
class CommandCache:
    def __init__(self):
        self.cache = {}  # command -> path
    
    def get(self, command: str) -> Optional[str]:
        if command in self.cache:
            path = self.cache[command]
            if os.path.exists(path):
                return path
            else:
                del self.cache[command]
        return None
    
    def set(self, command: str, path: str):
        self.cache[command] = path
```

### 5.2 `-o nolog` - Skip Function History

**Files to modify**:
- `psh/shell.py` - Check nolog in history recording

## Testing Strategy

### Unit Tests
For each option, create tests in `tests/test_set_builtin_options.py`:

```python
def test_noglob_option():
    """Test that -f disables pathname expansion."""
    shell = Shell()
    
    # Create test files
    shell.run_command("touch test1.txt test2.txt")
    
    # Without -f
    result = shell.run_command("echo *.txt")
    assert "test1.txt test2.txt" in result
    
    # With -f
    shell.run_command("set -f")
    result = shell.run_command("echo *.txt")
    assert result.strip() == "*.txt"
```

### Integration Tests
Test option combinations and interactions:

```python
def test_option_combinations():
    """Test multiple options together."""
    shell = Shell()
    
    # Set multiple options
    shell.run_command("set -fCn")
    
    # Verify all are set
    assert shell.state.options['noglob'] == True
    assert shell.state.options['noclobber'] == True
    assert shell.state.options['noexec'] == True
```

### Bash Comparison Tests
Compare behavior with bash:

```python
def test_noclobber_bash_comparison():
    """Compare noclobber behavior with bash."""
    # Test both PSH and bash behavior
    # Ensure they match
```

## Implementation Order

1. **Week 1**: Simple options (-f, -v, -n)
   - These are straightforward and provide immediate value
   - Good for understanding the option system

2. **Week 2**: Safety features (-C, -o ignoreeof)
   - Important for production use
   - Moderate complexity

3. **Week 3**: Environment integration (-a)
   - Useful for scripts
   - Requires careful variable handling

4. **Week 4**: Job control (-b, -m)
   - Enhances existing job control
   - Builds on current infrastructure

5. **Week 5**: Advanced features (-h, -o nolog)
   - Performance optimizations
   - Lower priority

## Special Considerations

### $- Variable
Need to implement the special parameter that shows current single-letter options:

```python
# In parameter expansion
elif var == '-':
    return self.get_option_string()
```

### Option Persistence
- Options should persist across subshells where appropriate
- Some options (like -m) may have different defaults for interactive vs non-interactive shells

### Error Handling
- Invalid option combinations should be detected
- Clear error messages for unsupported options

### Documentation
- Update help text for set builtin
- Add examples for each option
- Document option interactions

## Success Criteria

1. All POSIX-required options are implemented
2. Options behave identically to bash/POSIX specification
3. 100% test coverage for option handling
4. No regressions in existing functionality
5. Clear documentation and examples
6. Performance impact is minimal

## Future Enhancements

After basic implementation:
1. Option profiles (common option combinations)
2. Option introspection commands
3. Per-script option defaults
4. Option change notifications