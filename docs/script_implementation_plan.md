# Script Execution Implementation Plan

## Overview
This document outlines a phased approach to implementing script file execution in psh, building incrementally from basic functionality to full compatibility.

## Implementation Phases

### Phase 1: Basic Script Execution (Foundation)
**Estimated effort: 2-3 hours**
**Goal: Execute simple script files**

#### 1.1 Core Infrastructure
- [ ] Create `InputSource` abstract base class
- [ ] Implement `FileInput` class for reading script files
- [ ] Implement `StringInput` class for command strings
- [ ] Add basic file validation (exists, readable)

#### 1.2 Shell Class Enhancements
- [ ] Add `script_name` attribute to Shell class
- [ ] Add `set_positional_params()` method
- [ ] Implement `run_script()` method (basic version)
- [ ] Update `$0` special variable handling

#### 1.3 Command Line Interface
- [ ] Modify `__main__.py` to detect script file arguments
- [ ] Add basic script file execution path
- [ ] Preserve existing `-c` functionality

#### 1.4 Basic Testing
- [ ] Test script file execution with simple commands
- [ ] Test positional parameter setting (`$1`, `$2`)
- [ ] Test `$0` variable (script name)

**Deliverable: `psh script.sh` executes basic shell scripts**

### Phase 2: Enhanced Input Handling
**Estimated effort: 1-2 hours**
**Goal: Robust input processing and error handling**

#### 2.1 Unified Input Processing
- [ ] Create `_execute_from_source()` method
- [ ] Refactor `run_command()` to use new input system
- [ ] Implement line continuation support (`\` at end of line)

#### 2.2 Error Handling
- [ ] Implement proper exit codes (126, 127)
- [ ] Add binary file detection
- [ ] Improve error messages with file/line information
- [ ] Handle permission errors gracefully

#### 2.3 Script Mode Configuration
- [ ] Add script vs interactive mode distinction
- [ ] Configure appropriate signal handling for scripts
- [ ] Disable interactive-only features in script mode

**Deliverable: Robust script execution with proper error handling**

### Phase 3: Enhanced Source Builtin
**Estimated effort: 1 hour**
**Goal: Improve source/dot command functionality**

#### 3.1 Source Command Enhancement
- [ ] Add PATH search for source files
- [ ] Implement positional parameter handling for source
- [ ] Preserve and restore shell state properly
- [ ] Add comprehensive error handling

#### 3.2 Testing
- [ ] Test source with relative paths
- [ ] Test source with PATH search
- [ ] Test source with arguments
- [ ] Test nested source calls

**Deliverable: Enhanced `source`/`.` builtin with full functionality**

### Phase 4: Command Line Argument Improvements
**Estimated effort: 30 minutes**
**Goal: Better argument parsing and compatibility**

#### 4.1 Argument Processing
- [ ] Support script arguments after script name
- [ ] Support `-c` with additional arguments
- [ ] Add better help and version handling

#### 4.2 Compatibility
- [ ] Match bash behavior for argument parsing
- [ ] Proper handling of `--` argument separator
- [ ] Test various invocation patterns

**Deliverable: Full command line compatibility**

### Phase 5: Shebang Support (Optional)
**Estimated effort: 1-2 hours**
**Goal: Support for shebang (#!) lines**

#### 5.1 Shebang Processing
- [ ] Implement shebang detection
- [ ] Add interpreter execution logic
- [ ] Handle shebang argument parsing
- [ ] Support common shebang patterns

#### 5.2 Integration
- [ ] Integrate with existing script execution
- [ ] Handle edge cases (binary files, etc.)
- [ ] Test with various interpreters

**Deliverable: Full shebang support**

## Detailed Implementation Steps

### Step 1: Create InputSource Infrastructure

```python
# File: psh/input_sources.py
from abc import ABC, abstractmethod
from typing import Optional

class InputSource(ABC):
    @abstractmethod
    def read_line(self) -> Optional[str]:
        """Read next line, return None on EOF."""
        pass
    
    @abstractmethod
    def is_interactive(self) -> bool:
        """Return True if this is an interactive source."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return source name for error messages."""
        pass

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

### Step 2: Modify Shell Class

```python
# In psh/shell.py

class Shell:
    def __init__(self, args=None, script_name=None):
        # ... existing initialization ...
        self.script_name = script_name or "psh"
        self.is_script_mode = script_name is not None
        
    def set_positional_params(self, params: List[str]):
        """Set positional parameters ($1, $2, etc.)."""
        self.positional_params = params.copy()
    
    def run_script(self, script_path: str) -> int:
        """Execute a script file."""
        if not os.path.exists(script_path):
            print(f"psh: {script_path}: No such file or directory", file=sys.stderr)
            return 127
        
        if not os.access(script_path, os.R_OK):
            print(f"psh: {script_path}: Permission denied", file=sys.stderr)
            return 126
        
        old_script_name = self.script_name
        self.script_name = script_path
        
        try:
            from .input_sources import FileInput
            with FileInput(script_path) as input_source:
                return self._execute_from_source(input_source)
        except Exception as e:
            print(f"psh: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            self.script_name = old_script_name
    
    def _execute_from_source(self, input_source, add_to_history=True) -> int:
        """Execute commands from an input source."""
        exit_code = 0
        
        while True:
            line = input_source.read_line()
            if line is None:
                break
            
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Execute the command (simplified for now)
            exit_code = self.run_command(line, add_to_history=add_to_history and input_source.is_interactive())
        
        return exit_code
```

### Step 3: Update Main Entry Point

```python
# In psh/__main__.py

def main():
    shell = Shell()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            command = sys.argv[2]
            shell.set_positional_params(sys.argv[3:])
            exit_code = shell.run_command(command, add_to_history=False)
            sys.exit(exit_code)
        elif sys.argv[1] == "--version":
            from .version import get_version_info
            print(get_version_info())
            sys.exit(0)
        elif sys.argv[1] == "--help":
            print("Usage: psh [-c command] [script] [--version] [--help]")
            print("\nPython Shell (psh) - An educational Unix shell implementation")
            print("\nOptions:")
            print("  -c command    Execute command and exit")
            print("  script        Execute script file")
            print("  --version     Show version information")
            print("  --help        Show this help message")
            sys.exit(0)
        elif sys.argv[1].startswith("-"):
            print(f"psh: {sys.argv[1]}: invalid option", file=sys.stderr)
            sys.exit(2)
        else:
            # Script file execution
            script_path = sys.argv[1]
            shell.set_positional_params(sys.argv[2:])
            exit_code = shell.run_script(script_path)
            sys.exit(exit_code)
    else:
        shell.interactive_loop()
```

## Testing Strategy

### Phase 1 Tests
```bash
# Test basic script execution
echo 'echo "Hello World"' > test_script.sh
psh test_script.sh

# Test positional parameters
echo 'echo "Args: $1 $2 $#"' > test_args.sh
psh test_args.sh arg1 arg2

# Test $0 variable
echo 'echo "Script name: $0"' > test_name.sh
psh test_name.sh
```

### Phase 2 Tests
```bash
# Test error handling
psh nonexistent.sh  # Should return 127
touch no_read.sh && chmod 000 no_read.sh
psh no_read.sh      # Should return 126

# Test line continuation
echo -e 'echo "line 1" \\\n  "line 2"' > test_continuation.sh
psh test_continuation.sh
```

### Phase 3 Tests
```bash
# Test enhanced source
echo 'echo "Sourced with args: $1 $2"' > sourced.sh
echo 'source sourced.sh arg1 arg2' > test_source.sh
psh test_source.sh
```

## Success Criteria

### Phase 1 Success
- [ ] Can execute basic shell scripts
- [ ] Positional parameters work correctly
- [ ] `$0` contains script name
- [ ] Exit codes are preserved

### Phase 2 Success
- [ ] Proper error codes for missing/unreadable files
- [ ] Line continuation works
- [ ] Clear error messages with file/line info
- [ ] Binary file detection

### Phase 3 Success
- [ ] Source command searches PATH
- [ ] Source arguments become positional parameters
- [ ] Nested sourcing works correctly

### Phase 4 Success
- [ ] All bash-compatible invocation patterns work
- [ ] Script arguments passed correctly
- [ ] Help and version output improved

### Phase 5 Success
- [ ] Shebang lines are processed correctly
- [ ] Different interpreters can be specified
- [ ] Fallback to psh when no shebang

## Risk Mitigation

### Potential Issues
1. **File encoding problems**: Implement proper UTF-8 handling
2. **Large script files**: Use streaming input processing
3. **Nested script calls**: Properly manage shell state stack
4. **Signal handling**: Different behavior for scripts vs interactive

### Mitigation Strategies
1. **Comprehensive testing**: Test with various script types and sizes
2. **Error handling**: Graceful degradation and clear error messages
3. **Incremental implementation**: Each phase builds on previous
4. **Backwards compatibility**: Don't break existing functionality

## Conclusion

This phased approach allows for incremental development and testing, ensuring each component works correctly before building the next layer. The architecture maintains psh's educational clarity while providing full script execution capabilities.