# Script Execution Architecture for psh

## Current Architecture Analysis

### Entry Points
- `psh/__main__.py`: Main entry point with basic argument parsing
- Currently supports: `-c command`, `--version`, `--help`, and command arguments
- Missing: Script file execution support

### Core Components
- `Shell` class: Main shell implementation with execution methods
- `run_command()`: Executes single command string 
- `interactive_loop()`: Interactive REPL mode
- `tokenize()` → `parse()` → `execute()` pipeline

### Current Flow
```
__main__.py → Shell() → run_command()/interactive_loop() → tokenize() → parse() → execute()
```

## Proposed Architecture Changes

### 1. Enhanced Command Line Interface

#### Modified `__main__.py`
```python
def main():
    shell = Shell()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            # Execute command with -c flag
            command = sys.argv[2]
            shell.set_positional_params(sys.argv[3:])  # $1, $2, etc.
            exit_code = shell.run_command(command, add_to_history=False)
            sys.exit(exit_code)
        elif sys.argv[1].startswith("-"):
            # Handle other flags (--version, --help, future options)
            handle_flags(sys.argv[1:])
        else:
            # Script file execution
            script_path = sys.argv[1]
            shell.set_positional_params(sys.argv[2:])  # Script args become $1, $2, etc.
            exit_code = shell.run_script(script_path)
            sys.exit(exit_code)
    else:
        # Interactive mode
        shell.interactive_loop()
```

### 2. Script Input Sources

#### New `InputSource` Abstraction
```python
from abc import ABC, abstractmethod

class InputSource(ABC):
    @abstractmethod
    def read_line(self) -> Optional[str]:
        pass
    
    @abstractmethod
    def is_interactive(self) -> bool:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass

class InteractiveInput(InputSource):
    def __init__(self, line_editor):
        self.line_editor = line_editor
    
    def read_line(self) -> Optional[str]:
        return self.line_editor.read_line("psh$ ")
    
    def is_interactive(self) -> bool:
        return True
    
    def get_name(self) -> str:
        return "<stdin>"

class FileInput(InputSource):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file = None
        self.line_number = 0
    
    def __enter__(self):
        self.file = open(self.file_path, 'r')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
    
    def read_line(self) -> Optional[str]:
        if self.file:
            line = self.file.readline()
            if line:
                self.line_number += 1
                return line.rstrip('\n\r')
            return None
        return None
    
    def is_interactive(self) -> bool:
        return False
    
    def get_name(self) -> str:
        return self.file_path

class StringInput(InputSource):
    def __init__(self, command: str, name: str = "<command>"):
        self.lines = command.split('\n')
        self.current = 0
        self.name = name
    
    def read_line(self) -> Optional[str]:
        if self.current < len(self.lines):
            line = self.lines[self.current]
            self.current += 1
            return line
        return None
    
    def is_interactive(self) -> bool:
        return False
    
    def get_name(self) -> str:
        return self.name
```

### 3. Enhanced Shell Class

#### Modified Shell Initialization
```python
class Shell:
    def __init__(self, args=None, script_name=None):
        # ... existing initialization ...
        self.script_name = script_name or "psh"  # $0 value
        self.is_script_mode = script_name is not None
        
        # Script-specific setup
        if self.is_script_mode:
            self._setup_script_mode()
        else:
            self._setup_interactive_mode()
    
    def _setup_script_mode(self):
        """Configure shell for script execution."""
        # Disable interactive features
        self.interactive = False
        # Different signal handling for scripts
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        # No job control in scripts by default
        self.job_control_enabled = False
    
    def _setup_interactive_mode(self):
        """Configure shell for interactive use."""
        self.interactive = True
        # Standard interactive signal handling
        signal.signal(signal.SIGINT, self._handle_sigint)
        self.job_control_enabled = True
```

#### New Script Execution Methods
```python
def run_script(self, script_path: str) -> int:
    """Execute a script file."""
    # Validate script file
    if not os.path.exists(script_path):
        print(f"psh: {script_path}: No such file or directory", file=sys.stderr)
        return 127
    
    if not os.access(script_path, os.R_OK):
        print(f"psh: {script_path}: Permission denied", file=sys.stderr)
        return 126
    
    # Check if it's a binary file
    if self._is_binary_file(script_path):
        print(f"psh: {script_path}: cannot execute binary file", file=sys.stderr)
        return 126
    
    # Set $0 to script name
    old_script_name = self.script_name
    self.script_name = script_path
    
    try:
        with FileInput(script_path) as input_source:
            return self._execute_from_source(input_source)
    except IOError as e:
        print(f"psh: {script_path}: {e}", file=sys.stderr)
        return 1
    finally:
        self.script_name = old_script_name

def run_command_string(self, command: str, add_to_history=True) -> int:
    """Execute command string (renamed from run_command for clarity)."""
    input_source = StringInput(command, "<command>")
    return self._execute_from_source(input_source, add_to_history)

def _execute_from_source(self, input_source: InputSource, add_to_history=True) -> int:
    """Execute commands from an input source."""
    exit_code = 0
    command_buffer = ""
    
    while True:
        line = input_source.read_line()
        if line is None:  # EOF
            break
        
        # Handle line continuation
        if line.endswith('\\'):
            command_buffer += line[:-1] + ' '
            continue
        
        command_buffer += line
        
        # Skip empty lines and comments
        if not command_buffer.strip() or command_buffer.strip().startswith('#'):
            command_buffer = ""
            continue
        
        # Execute complete command
        try:
            if add_to_history and input_source.is_interactive() and command_buffer.strip():
                self._add_to_history(command_buffer.strip())
            
            tokens = tokenize(command_buffer)
            tokens = self.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            if isinstance(ast, TopLevel):
                exit_code = self.execute_toplevel(ast)
            else:
                self._collect_heredocs(ast)
                exit_code = self.execute_command_list(ast)
                
            self.last_exit_code = exit_code
            
        except ParseError as e:
            error_msg = f"psh: {input_source.get_name()}"
            if hasattr(input_source, 'line_number'):
                error_msg += f":{input_source.line_number}"
            error_msg += f": {e}"
            print(error_msg, file=sys.stderr)
            exit_code = 1
            self.last_exit_code = 1
        except Exception as e:
            print(f"psh: {input_source.get_name()}: unexpected error: {e}", file=sys.stderr)
            exit_code = 1
            self.last_exit_code = 1
        
        command_buffer = ""
    
    return exit_code

def interactive_loop(self):
    """Interactive REPL mode."""
    # ... setup code ...
    line_editor = LineEditor(self.history, edit_mode=self.edit_mode)
    input_source = InteractiveInput(line_editor)
    
    while True:
        try:
            self.job_manager.notify_completed_jobs()
            exit_code = self._execute_from_source(input_source)
            if exit_code is None:  # EOF
                break
        except KeyboardInterrupt:
            print()
            self.last_exit_code = 130
            continue
        except EOFError:
            print()
            break
    
    self._save_history()
```

### 4. Source Builtin Enhancement

#### Enhanced source/dot builtin
```python
def _builtin_source(self, args):
    """Enhanced source builtin with better error handling."""
    if len(args) < 1:
        print("source: filename argument required", file=sys.stderr)
        return 1
    
    filename = args[0]
    
    # Search in current directory, then PATH if no slash
    if '/' not in filename:
        # Search in PATH
        for path_dir in self.env.get('PATH', '').split(':'):
            if path_dir:
                full_path = os.path.join(path_dir, filename)
                if os.path.exists(full_path):
                    filename = full_path
                    break
    
    if not os.path.exists(filename):
        print(f"source: {filename}: No such file or directory", file=sys.stderr)
        return 1
    
    if not os.access(filename, os.R_OK):
        print(f"source: {filename}: Permission denied", file=sys.stderr)
        return 1
    
    # Save current state
    old_positional = self.positional_params.copy()
    old_script_name = self.script_name
    
    # Set new positional parameters if provided
    if len(args) > 1:
        self.positional_params = args[1:]
    
    try:
        with FileInput(filename) as input_source:
            return self._execute_from_source(input_source, add_to_history=False)
    except Exception as e:
        print(f"source: {filename}: {e}", file=sys.stderr)
        return 1
    finally:
        # Restore state
        self.positional_params = old_positional
        self.script_name = old_script_name
```

### 5. Shebang Support (Future Enhancement)

#### Shebang parser
```python
def _check_shebang(self, script_path: str) -> Optional[List[str]]:
    """Check for shebang line and return interpreter args."""
    try:
        with open(script_path, 'rb') as f:
            first_line = f.readline(1024)  # Read first line, max 1024 bytes
            if first_line.startswith(b'#!'):
                shebang = first_line[2:].decode('utf-8', errors='ignore').strip()
                return shebang.split()
    except:
        pass
    return None

def _is_binary_file(self, file_path: str) -> bool:
    """Check if file is binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except:
        return True
```

### 6. Variable Improvements

#### Enhanced special variables
```python
def _get_special_variable(self, var_name: str) -> str:
    """Get special shell variables."""
    if var_name == '0':
        return self.script_name
    elif var_name == '#':
        return str(len(self.positional_params))
    # ... existing special variables ...
    elif var_name.isdigit():
        index = int(var_name)
        if index == 0:
            return self.script_name
        elif 1 <= index <= len(self.positional_params):
            return self.positional_params[index - 1]
        return ""
    # ... rest of implementation ...

def set_positional_params(self, params: List[str]):
    """Set positional parameters ($1, $2, etc.)."""
    self.positional_params = params.copy()
```

## Implementation Benefits

### 1. Clean Separation of Concerns
- `InputSource` abstraction handles different input types
- Script vs interactive mode clearly separated
- Consistent error handling across all execution modes

### 2. Bash Compatibility
- Proper `$0` handling (script name vs "psh")
- Correct positional parameter management
- Standard error codes (126, 127)
- Source builtin with PATH search

### 3. Educational Value
- Clear architectural boundaries
- Easy to understand input handling
- Proper error propagation
- Extensible design for future features

### 4. Performance
- Efficient file reading
- No unnecessary string copying
- Minimal memory overhead for large scripts

## Testing Strategy

### 1. Unit Tests
- `InputSource` implementations
- Script file validation
- Positional parameter handling
- Error code generation

### 2. Integration Tests
- Script execution end-to-end
- Source builtin functionality
- Error handling scenarios
- Signal handling in script mode

### 3. Compatibility Tests
- Compare behavior with bash
- Test edge cases (binary files, permissions, etc.)
- Verify proper exit codes

This architecture provides a solid foundation for script execution while maintaining the educational clarity that is core to psh's design philosophy.