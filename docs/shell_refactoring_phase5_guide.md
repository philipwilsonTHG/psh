# Phase 5 Implementation Guide: Script Handling

## Overview
Phase 5 focuses on extracting script execution logic from shell.py into dedicated components. This phase will handle script file execution, input source management, and command buffering/parsing logic.

## Current State Analysis

### Script-Related Methods in shell.py
- `run_script()` - Execute a script file with arguments
- `_execute_from_source()` - Execute commands from an input source
- `_execute_buffered_command()` - Execute a buffered command with error handling
- `_validate_script_file()` - Validate script file before execution
- `_is_binary_file()` - Check if file is binary
- `_parse_shebang()` - Parse shebang line from script
- `_should_execute_with_shebang()` - Determine if script should use shebang
- `_execute_with_shebang()` - Execute script using shebang interpreter

### Related Components
- `input_sources.py` - FileInput, StringInput classes
- Script validation and binary detection logic
- Shebang parsing and execution
- Multi-line command handling for scripts

## Step 1: Create Script Handling Infrastructure

### Create `psh/scripting/base.py`:
```python
"""Base classes for script handling components."""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class ScriptComponent(ABC):
    """Base class for script handling components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.executor_manager = shell.executor_manager
        self.expansion_manager = shell.expansion_manager
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> int:
        """Execute the script component functionality."""
        pass


class ScriptManager:
    """Manages all script handling components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize script components
        from .script_executor import ScriptExecutor
        from .script_validator import ScriptValidator
        from .shebang_handler import ShebangHandler
        from .source_processor import SourceProcessor
        
        self.script_executor = ScriptExecutor(shell)
        self.script_validator = ScriptValidator(shell)
        self.shebang_handler = ShebangHandler(shell)
        self.source_processor = SourceProcessor(shell)
    
    def run_script(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file with optional arguments."""
        return self.script_executor.run_script(script_path, script_args)
    
    def execute_from_source(self, input_source, add_to_history: bool = True) -> int:
        """Execute commands from an input source."""
        return self.source_processor.execute_from_source(input_source, add_to_history)
```

## Step 2: Extract Script Validation

### Create `psh/scripting/script_validator.py`:
```python
"""Script file validation."""
import os
import sys
from typing import Optional
from .base import ScriptComponent


class ScriptValidator(ScriptComponent):
    """Validates script files before execution."""
    
    def execute(self, script_path: str) -> int:
        """Validate script file. Returns 0 if valid, error code otherwise."""
        return self.validate_script_file(script_path)
    
    def validate_script_file(self, script_path: str) -> int:
        """
        Validate script file and return appropriate exit code.
        
        Returns:
            0 if file is valid
            126 if permission denied or binary file
            127 if file not found
        """
        if not os.path.exists(script_path):
            print(f"psh: {script_path}: No such file or directory", file=sys.stderr)
            return 127
        
        if os.path.isdir(script_path):
            print(f"psh: {script_path}: Is a directory", file=sys.stderr)
            return 126
        
        if not os.access(script_path, os.R_OK):
            print(f"psh: {script_path}: Permission denied", file=sys.stderr)
            return 126
        
        if self.is_binary_file(script_path):
            print(f"psh: {script_path}: cannot execute binary file", file=sys.stderr)
            return 126
        
        return 0
    
    def is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary by looking for null bytes and other indicators."""
        try:
            with open(file_path, 'rb') as f:
                # Read first 1024 bytes for analysis
                chunk = f.read(1024)
                
                if not chunk:
                    return False  # Empty file is not binary
                
                # Check for null bytes (strong indicator of binary)
                if b'\0' in chunk:
                    return True
                
                # Check for very high ratio of non-printable characters
                printable_chars = 0
                for byte in chunk:
                    # Count ASCII printable chars (32-126) plus common whitespace
                    if 32 <= byte <= 126 or byte in (9, 10, 13):  # tab, newline, carriage return
                        printable_chars += 1
                
                # If less than 70% printable characters, consider it binary
                if len(chunk) > 0 and (printable_chars / len(chunk)) < 0.70:
                    return True
                
                # Check for common binary file signatures
                binary_signatures = [
                    b'\x7fELF',      # ELF executable
                    b'MZ',           # DOS/Windows executable
                    b'\xca\xfe\xba\xbe',  # Java class file
                    b'\x89PNG',      # PNG image
                    b'\xff\xd8\xff', # JPEG image
                    b'GIF8',         # GIF image
                    b'%PDF',         # PDF file
                ]
                
                for sig in binary_signatures:
                    if chunk.startswith(sig):
                        return True
                
                return False
                
        except:
            return True  # If we can't read it, assume binary
```

## Step 3: Extract Shebang Handling

### Create `psh/scripting/shebang_handler.py`:
```python
"""Shebang parsing and execution."""
import os
import sys
import subprocess
from typing import Tuple, List, Optional
from .base import ScriptComponent


class ShebangHandler(ScriptComponent):
    """Handles shebang parsing and execution."""
    
    def execute(self, script_path: str, script_args: List[str]) -> int:
        """Execute script using its shebang interpreter."""
        return self.execute_with_shebang(script_path, script_args)
    
    def parse_shebang(self, script_path: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Parse shebang line from script file.
        
        Returns:
            tuple: (has_shebang, interpreter_path, interpreter_args)
        """
        try:
            with open(script_path, 'rb') as f:
                # Read first line, max 1024 bytes
                first_line = f.readline(1024)
                
                # Check for shebang
                if not first_line.startswith(b'#!'):
                    return (False, None, [])
                
                # Decode shebang line
                try:
                    shebang_line = first_line[2:].decode('utf-8', errors='ignore').strip()
                except UnicodeDecodeError:
                    return (False, None, [])
                
                if not shebang_line:
                    return (False, None, [])
                
                # Parse interpreter and arguments
                parts = shebang_line.split()
                if not parts:
                    return (False, None, [])
                
                interpreter = parts[0]
                interpreter_args = parts[1:] if len(parts) > 1 else []
                
                return (True, interpreter, interpreter_args)
                
        except (IOError, OSError):
            return (False, None, [])
    
    def should_execute_with_shebang(self, script_path: str) -> bool:
        """Determine if script should be executed with its shebang interpreter."""
        has_shebang, interpreter, interpreter_args = self.parse_shebang(script_path)
        
        if not has_shebang:
            return False
        
        # If interpreter is psh or our script name, use psh directly
        if interpreter.endswith('/psh') or interpreter == 'psh':
            return False
        
        # Handle /usr/bin/env pattern - check the actual interpreter
        if interpreter.endswith('/env') or interpreter == 'env':
            # Get the actual interpreter from interpreter_args
            if not interpreter_args:
                return False
            actual_interpreter = interpreter_args[0]
            if actual_interpreter.endswith('/psh') or actual_interpreter == 'psh':
                return False
        
        # Check if interpreter exists and is executable
        if interpreter.startswith('/'):
            # Absolute path
            return os.path.exists(interpreter) and os.access(interpreter, os.X_OK)
        else:
            # Search in PATH
            path_dirs = self.state.env.get('PATH', '').split(':')
            for path_dir in path_dirs:
                if path_dir:
                    full_path = os.path.join(path_dir, interpreter)
                    if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                        return True
            return False
    
    def execute_with_shebang(self, script_path: str, script_args: List[str]) -> int:
        """Execute script using its shebang interpreter."""
        has_shebang, interpreter, interpreter_args = self.parse_shebang(script_path)
        
        if not has_shebang:
            return 1
        
        # Build command line for interpreter
        cmd_args = []
        
        # Add interpreter
        cmd_args.append(interpreter)
        
        # Add interpreter arguments
        cmd_args.extend(interpreter_args)
        
        # Add script path
        cmd_args.append(script_path)
        
        # Add script arguments
        if script_args:
            cmd_args.extend(script_args)
        
        try:
            # Execute the interpreter
            result = subprocess.run(cmd_args, env=self.state.env)
            return result.returncode
        except FileNotFoundError:
            print(f"psh: {interpreter}: No such file or directory", file=sys.stderr)
            return 127
        except PermissionError:
            print(f"psh: {interpreter}: Permission denied", file=sys.stderr)
            return 126
        except Exception as e:
            print(f"psh: {interpreter}: {e}", file=sys.stderr)
            return 1
```

## Step 4: Extract Source Processing

### Create `psh/scripting/source_processor.py`:
```python
"""Source file and command buffer processing."""
import sys
from typing import Optional
from .base import ScriptComponent
from ..tokenizer import tokenize
from ..parser import parse, ParseError
from ..ast_nodes import TopLevel


class SourceProcessor(ScriptComponent):
    """Processes input from various sources (files, strings, stdin)."""
    
    def execute(self, input_source, add_to_history: bool = True) -> int:
        """Execute from an input source."""
        return self.execute_from_source(input_source, add_to_history)
    
    def execute_from_source(self, input_source, add_to_history: bool = True) -> int:
        """Execute commands from an input source with enhanced processing."""
        exit_code = 0
        command_buffer = ""
        command_start_line = 0
        
        while True:
            line = input_source.read_line()
            if line is None:  # EOF
                # Execute any remaining command in buffer
                if command_buffer.strip():
                    exit_code = self._execute_buffered_command(
                        command_buffer, input_source, command_start_line, add_to_history
                    )
                break
            
            # Skip empty lines when no command is being built
            if not command_buffer and not line.strip():
                continue
            
            # Skip comment lines when no command is being built
            if not command_buffer and line.strip().startswith('#'):
                continue
            
            # Handle line continuation (backslash at end)
            if line.endswith('\\'):
                # Remove the backslash and add to buffer
                if not command_buffer:
                    command_start_line = input_source.get_line_number()
                command_buffer += line[:-1] + ' '
                continue
            
            # Add current line to buffer
            if not command_buffer:
                command_start_line = input_source.get_line_number()
            # Add line to buffer with proper spacing
            if command_buffer and not command_buffer.endswith('\n'):
                command_buffer += '\n'
            command_buffer += line
            
            # Try to parse and execute the command
            if command_buffer.strip():
                # Check if command is complete by trying to parse it
                try:
                    tokens = tokenize(command_buffer)
                    # Try parsing to see if command is complete
                    parse(tokens)
                    # If parsing succeeds, execute the command
                    exit_code = self._execute_buffered_command(
                        command_buffer.rstrip('\n'), input_source, command_start_line, add_to_history
                    )
                    # Reset buffer for next command
                    command_buffer = ""
                    command_start_line = 0
                except ParseError as e:
                    # Check if this is an incomplete command
                    if self._is_incomplete_command(e):
                        # Command is incomplete, continue reading
                        continue
                    else:
                        # It's a real parse error, report it and reset
                        filename = input_source.get_name() if hasattr(input_source, 'get_name') else 'stdin'
                        print(f"{filename}:{command_start_line}: {e}", file=sys.stderr)
                        command_buffer = ""
                        command_start_line = 0
                        exit_code = 1
                        self.state.last_exit_code = 1
        
        return exit_code
    
    def _is_incomplete_command(self, parse_error: ParseError) -> bool:
        """Check if a parse error indicates an incomplete command."""
        error_msg = str(parse_error)
        incomplete_patterns = [
            ("Expected DO", "got EOF"),
            ("Expected DONE", "got EOF"),
            ("Expected FI", "got EOF"),
            ("Expected THEN", "got EOF"),
            ("Expected IN", "got EOF"),
            ("Expected ESAC", "got EOF"),
            ("Expected '}' to end compound command", None),  # Function bodies
            ("Expected RPAREN", "got EOF"),
            ("Expected DOUBLE_RBRACKET", None),  # For incomplete [[ ]]
            ("Expected test operand", None),      # For [[ ... && at end
        ]
        
        for expected, got in incomplete_patterns:
            if expected in error_msg:
                if got is None or got in error_msg:
                    return True
        
        return False
    
    def _execute_buffered_command(self, command_string: str, input_source, 
                                  start_line: int, add_to_history: bool) -> int:
        """Execute a buffered command with enhanced error reporting."""
        # Skip empty commands and comments
        if not command_string.strip() or command_string.strip().startswith('#'):
            return 0
        
        try:
            tokens = tokenize(command_string)
            
            # Debug: Print tokens if requested
            if self.state.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                print(self.shell._format_tokens(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Expand aliases
            tokens = self.shell.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Debug: Print AST if requested
            if self.state.debug_ast:
                print("=== AST Debug Output ===", file=sys.stderr)
                print(self.shell._format_ast(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
            # Add to history if requested (for interactive or testing)
            if add_to_history and command_string.strip():
                self.shell._add_to_history(command_string.strip())
            
            # Increment command number for successful parse
            self.state.command_number += 1
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.shell.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                try:
                    # Collect here documents if any
                    self.shell._collect_heredocs(ast)
                    exit_code = self.shell.execute_command_list(ast)
                    return exit_code
                except Exception as e:
                    # Break/continue outside of loops is an error
                    if "LoopBreak" in str(type(e)) or "LoopContinue" in str(type(e)):
                        stmt_name = "break" if "LoopBreak" in str(type(e)) else "continue"
                        print(f"{stmt_name}: only meaningful in a `for' or `while' loop", 
                              file=sys.stderr)
                        return 1
                    raise
        except ParseError as e:
            # Enhanced error message with location
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
        except Exception as e:
            # Enhanced error message with location  
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: unexpected error: {e}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
```

## Step 5: Extract Script Executor

### Create `psh/scripting/script_executor.py`:
```python
"""Script file execution."""
import os
from typing import List, Optional
from .base import ScriptComponent
from ..input_sources import FileInput


class ScriptExecutor(ScriptComponent):
    """Executes script files."""
    
    def execute(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file."""
        return self.run_script(script_path, script_args)
    
    def run_script(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file with optional arguments."""
        if script_args is None:
            script_args = []
            
        # Validate the script file first
        validation_result = self.shell.script_manager.script_validator.validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Check for shebang and execute with appropriate interpreter
        if self.shell.script_manager.shebang_handler.should_execute_with_shebang(script_path):
            return self.shell.script_manager.shebang_handler.execute_with_shebang(
                script_path, script_args)
        
        # Save current script state
        old_script_name = self.state.script_name
        old_script_mode = self.state.is_script_mode
        old_positional = self.state.positional_params.copy()
        
        self.state.script_name = script_path
        self.state.is_script_mode = True
        self.state.positional_params = script_args
        
        try:
            with FileInput(script_path) as input_source:
                return self.shell.script_manager.source_processor.execute_from_source(
                    input_source, add_to_history=False)
        except Exception as e:
            print(f"psh: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            self.state.script_name = old_script_name
            self.state.is_script_mode = old_script_mode
            self.state.positional_params = old_positional
```

## Step 6: Update Shell Class

### Modify shell.py to use ScriptManager:
```python
# Add import
from .scripting.base import ScriptManager

# In __init__:
self.script_manager = ScriptManager(self)

# Update methods to delegate:
def run_script(self, script_path: str, script_args: list = None) -> int:
    """Execute a script file with optional arguments."""
    return self.script_manager.run_script(script_path, script_args)

def _execute_from_source(self, input_source, add_to_history=True) -> int:
    """Execute commands from an input source with enhanced processing."""
    return self.script_manager.execute_from_source(input_source, add_to_history)

def _validate_script_file(self, script_path: str) -> int:
    """Validate script file and return appropriate exit code."""
    return self.script_manager.script_validator.validate_script_file(script_path)

def _is_binary_file(self, file_path: str) -> bool:
    """Check if file is binary by looking for null bytes and other indicators."""
    return self.script_manager.script_validator.is_binary_file(file_path)

def _parse_shebang(self, script_path: str) -> tuple:
    """Parse shebang line from script file."""
    return self.script_manager.shebang_handler.parse_shebang(script_path)

def _should_execute_with_shebang(self, script_path: str) -> bool:
    """Determine if script should be executed with its shebang interpreter."""
    return self.script_manager.shebang_handler.should_execute_with_shebang(script_path)

def _execute_with_shebang(self, script_path: str, script_args: list) -> int:
    """Execute script using its shebang interpreter."""
    return self.script_manager.shebang_handler.execute_with_shebang(script_path, script_args)
```

## Step 7: Create Command String Executor

### Create `psh/scripting/command_executor.py`:
```python
"""Command string execution."""
from typing import Optional
from .base import ScriptComponent
from ..input_sources import StringInput


class CommandStringExecutor(ScriptComponent):
    """Executes command strings."""
    
    def execute(self, command_string: str, add_to_history: bool = True) -> int:
        """Execute a command string."""
        return self.run_command(command_string, add_to_history)
    
    def run_command(self, command_string: str, add_to_history: bool = True) -> int:
        """Execute a command string using the unified input system."""
        # Use the unified execution system for consistency
        input_source = StringInput(command_string, "<command>")
        return self.shell.script_manager.source_processor.execute_from_source(
            input_source, add_to_history)
```

## Implementation Order

1. **Start with Base Infrastructure**
   - Create scripting/base.py with ScriptComponent and ScriptManager
   - Add script_manager to Shell class

2. **Extract Script Validation**
   - Move validation logic to ScriptValidator
   - Move binary file detection

3. **Extract Shebang Handling**
   - Move shebang parsing and execution
   - Handle PATH searching for interpreters

4. **Extract Source Processing**
   - This is the most complex part
   - Move command buffering and parsing logic
   - Handle incomplete command detection

5. **Extract Script Executor**
   - Ties together validation, shebang, and source processing
   - Manages script state (positional params, script_name)

6. **Update Shell Methods**
   - Convert all script-related methods to delegation
   - Remove old method bodies

## Testing Strategy

### Unit Tests for Each Component
```python
# tests/test_script_validator.py
def test_validate_nonexistent_file():
    shell = create_test_shell()
    validator = ScriptValidator(shell)
    assert validator.validate_script_file("/nonexistent") == 127

def test_validate_directory():
    shell = create_test_shell()
    validator = ScriptValidator(shell)
    assert validator.validate_script_file("/tmp") == 126

def test_binary_file_detection():
    shell = create_test_shell()
    validator = ScriptValidator(shell)
    # Create test binary file
    # Test detection
```

### Integration Tests
- Run existing script execution tests
- Test shebang execution
- Test multi-line scripts
- Test error handling

### Incremental Migration
1. Create component with minimal functionality
2. Update shell.py to use it
3. Run tests
4. Move more functionality
5. Repeat

## Common Pitfalls to Avoid

1. **Input Source Interface**
   - Ensure all input sources have consistent interface
   - Handle EOF correctly
   - Preserve line numbers for error reporting

2. **History Management**
   - Only add interactive commands to history
   - Don't add sourced script commands

3. **State Preservation**
   - Save/restore script state correctly
   - Handle nested script execution

4. **Error Reporting**
   - Include filename and line number
   - Handle parse errors vs execution errors

5. **Shebang Edge Cases**
   - Handle /usr/bin/env correctly
   - Check for recursive psh execution
   - Validate interpreter existence

## Validation Checklist

- [ ] All script execution tests pass
- [ ] Shebang scripts execute correctly
- [ ] Binary file detection works
- [ ] Multi-line commands in scripts work
- [ ] Error messages include file:line info
- [ ] Script arguments passed correctly
- [ ] Nested script execution works
- [ ] RC file loading still works
- [ ] Command string execution works
- [ ] Source builtin still works

## Expected Results

### Lines of Code Impact
- Remove ~400 lines from shell.py
- Add ~600 lines across scripting modules
- Net increase due to better organization

### Benefits
- Clear separation of script handling logic
- Easier to test individual components
- Better error reporting with context
- Reusable components for different input sources

## Next Steps After Phase 5

1. Phase 6: Interactive features extraction
   - Line editing
   - History management
   - Tab completion
   - Prompt handling

2. Phase 7: Final integration and cleanup
   - Remove remaining logic from shell.py
   - Optimize component interactions
   - Documentation updates