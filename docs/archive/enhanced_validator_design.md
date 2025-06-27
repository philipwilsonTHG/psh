# Enhanced ValidatorVisitor Design

## Overview

This document details the enhancements to the ValidatorVisitor for Phase 2, focusing on comprehensive AST validation including undefined variable detection, command validation, quoting analysis, and security checks.

## Current State

The existing ValidatorVisitor already provides:
- Break/continue validation outside loops
- Empty command detection
- Function name validation
- Duplicate function detection
- Basic array validation
- Redirection syntax checking
- Case pattern duplicate detection

## Proposed Enhancements

### 1. Variable Tracking System

```python
@dataclass
class VariableInfo:
    """Information about a variable."""
    name: str
    defined_at: Optional[str] = None  # Context where defined
    is_exported: bool = False
    is_readonly: bool = False
    is_array: bool = False
    is_local: bool = False
    is_special: bool = False  # $?, $$, etc.

class VariableTracker:
    """Track variable definitions and usage."""
    
    def __init__(self):
        self.scopes: List[Dict[str, VariableInfo]] = [{}]  # Stack of scopes
        self.special_vars = {
            '?', '$', '!', '#', '@', '*', '-', '_',
            'HOME', 'PATH', 'PWD', 'SHELL', 'USER',
            'HOSTNAME', 'RANDOM', 'LINENO', 'SECONDS',
            'BASH_VERSION', 'BASH', 'IFS', 'PS1', 'PS2', 'PS4'
        }
    
    def enter_scope(self):
        """Enter a new variable scope (function)."""
        self.scopes.append({})
    
    def exit_scope(self):
        """Exit current scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def define_variable(self, name: str, info: VariableInfo):
        """Define a variable in current scope."""
        self.scopes[-1][name] = info
    
    def lookup_variable(self, name: str) -> Optional[VariableInfo]:
        """Look up variable in all scopes."""
        # Check from current scope up to global
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        
        # Check if it's a special variable
        if name in self.special_vars or name.isdigit():
            return VariableInfo(name=name, is_special=True)
        
        return None
```

### 2. Enhanced Validation Checks

#### A. Undefined Variable Detection

```python
def visit_SimpleCommand(self, node: SimpleCommand) -> None:
    """Enhanced simple command validation."""
    # ... existing validation ...
    
    # Check for variable assignments
    for arg in node.args:
        if '=' in arg and not arg.startswith('='):
            var_name = arg.split('=', 1)[0]
            value = arg.split('=', 1)[1]
            
            # Track variable definition
            self.var_tracker.define_variable(
                var_name, 
                VariableInfo(name=var_name, defined_at=self._get_context())
            )
            
            # Check value for undefined variables
            self._check_string_for_variables(value, node)

def _check_string_for_variables(self, text: str, node: ASTNode):
    """Check a string for variable references."""
    import re
    
    # Find variable references: $VAR, ${VAR}, ${VAR:-default}, etc.
    var_pattern = r'\$\{?([A-Za-z_][A-Za-z0-9_]*)\b'
    
    for match in re.finditer(var_pattern, text):
        var_name = match.group(1)
        var_info = self.var_tracker.lookup_variable(var_name)
        
        if not var_info:
            # Check if it's in a parameter expansion with default
            full_match = match.group(0)
            if ':-' in text[match.start():] or ':=' in text[match.start():]:
                continue  # Has default value
            
            self._add_warning(
                f"Possible use of undefined variable '${var_name}'",
                node
            )
```

#### B. Command Existence Validation

```python
def _check_command_exists(self, cmd: str, node: SimpleCommand):
    """Check if a command exists."""
    # Skip if it's a builtin
    if cmd in self.builtin_commands:
        return
    
    # Skip if it's a function we've seen
    if cmd in self.function_names:
        return
    
    # Skip if it's an alias (would need alias info)
    if hasattr(self, 'alias_names') and cmd in self.alias_names:
        return
    
    # For external commands, we can't check at parse time
    # but we can warn about common typos
    common_typos = {
        'gerp': 'grep',
        'grpe': 'grep',
        'mr': 'rm',
        'vm': 'mv',
        'pc': 'cp',
        'pyton': 'python',
        'pythn': 'python',
        'ech': 'echo',
        'ehco': 'echo',
    }
    
    if cmd in common_typos:
        self._add_warning(
            f"Possible typo: '{cmd}' - did you mean '{common_typos[cmd]}'?",
            node
        )
```

#### C. Quoting Analysis

```python
def _check_quoting_issues(self, node: SimpleCommand):
    """Check for potential quoting issues."""
    for i, (arg, arg_type) in enumerate(zip(node.args, node.arg_types)):
        if arg_type == 'WORD':
            # Check if word contains variables that should be quoted
            if '$' in arg and not self._is_in_arithmetic_context(node):
                # Skip if it's a numeric comparison
                if i > 0 and node.args[i-1] in ['-eq', '-ne', '-lt', '-le', '-gt', '-ge']:
                    continue
                
                self._add_info(
                    f"Variable expansion '{arg}' is unquoted - may cause word splitting",
                    node
                )
            
            # Check for glob patterns that might be unintentional
            if any(c in arg for c in ['*', '?', '[']) and arg_type == 'WORD':
                if not self._looks_like_intentional_glob(arg, node):
                    self._add_warning(
                        f"Unquoted pattern '{arg}' will be subject to pathname expansion",
                        node
                    )

def _looks_like_intentional_glob(self, pattern: str, node: SimpleCommand) -> bool:
    """Heuristic to determine if glob pattern is intentional."""
    # Common intentional patterns
    intentional_patterns = [
        r'^\*\.\w+$',  # *.txt, *.py, etc.
        r'^\w+\*$',    # prefix*
        r'^\*\w+$',    # *suffix
        r'^\[[\w-]+\]',  # [a-z], [0-9], etc.
    ]
    
    import re
    for pat in intentional_patterns:
        if re.match(pat, pattern):
            return True
    
    # Check context - some commands expect globs
    if node.args and node.args[0] in ['ls', 'rm', 'find', 'cp', 'mv']:
        return True
    
    return False
```

#### D. Security Checks

```python
def _check_security_issues(self, node: SimpleCommand):
    """Check for potential security issues."""
    if not node.args:
        return
    
    cmd = node.args[0]
    
    # Check for dangerous commands
    dangerous_commands = {
        'eval': "Avoid 'eval' - it can execute arbitrary code",
        'source': "Be careful with 'source' - validate the file path",
        '.': "Be careful with '.' - validate the file path",
    }
    
    if cmd in dangerous_commands:
        self._add_warning(f"Security: {dangerous_commands[cmd]}", node)
    
    # Check for command injection patterns
    for arg in node.args[1:]:
        if any(danger in arg for danger in ['$(', '`', ';', '&&', '||', '|']):
            if '$' in arg and not self._is_safe_expansion(arg):
                self._add_error(
                    f"Potential command injection in argument: {arg}",
                    node
                )
    
    # Check for world-writable operations
    if cmd in ['chmod']:
        for arg in node.args[1:]:
            if any(perm in arg for perm in ['777', 'a+w', 'o+w']):
                self._add_warning(
                    "Security: Creating world-writable files is dangerous",
                    node
                )

def _is_safe_expansion(self, text: str) -> bool:
    """Check if variable expansion is likely safe."""
    # Simple heuristic - in reality this would be more complex
    # Safe patterns: ${VAR}, ${VAR:-default}, ${#VAR}, etc.
    import re
    
    # If it's a simple variable expansion, it's generally safe
    if re.match(r'^\$\{\w+\}$', text):
        return True
    
    # Parameter expansion with defaults is safe
    if re.match(r'^\$\{\w+:-[^}]+\}$', text):
        return True
    
    return False
```

### 3. Integration with Existing Validator

```python
class EnhancedValidatorVisitor(ValidatorVisitor):
    """Enhanced validator with comprehensive checks."""
    
    def __init__(self):
        super().__init__()
        self.var_tracker = VariableTracker()
        self.builtin_commands = {
            'cd', 'pwd', 'echo', 'printf', 'read', 'exit', 'return',
            'export', 'unset', 'set', 'source', '.', 'eval', 'exec',
            'shift', 'break', 'continue', 'true', 'false', ':', 
            'test', '[', 'declare', 'typeset', 'local', 'readonly',
            'alias', 'unalias', 'type', 'command', 'builtin',
            'history', 'jobs', 'fg', 'bg', 'wait', 'kill',
            'trap', 'umask', 'ulimit', 'help'
        }
        self.check_undefined_vars = True
        self.check_command_exists = True
        self.check_quoting = True
        self.check_security = True
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Enhanced function definition handling."""
        # Enter new scope for local variables
        self.var_tracker.enter_scope()
        
        # Call parent implementation
        super().visit_FunctionDef(node)
        
        # Exit scope
        self.var_tracker.exit_scope()
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        """Enhanced command validation."""
        # Call parent implementation first
        super().visit_SimpleCommand(node)
        
        # Additional checks
        if self.check_undefined_vars:
            self._check_undefined_variables(node)
        
        if self.check_command_exists and node.args:
            self._check_command_exists(node.args[0], node)
        
        if self.check_quoting:
            self._check_quoting_issues(node)
        
        if self.check_security:
            self._check_security_issues(node)
```

### 4. Configuration Support

```python
@dataclass
class ValidatorConfig:
    """Configuration for the validator."""
    check_undefined_vars: bool = True
    check_command_exists: bool = True
    check_quoting: bool = True
    check_security: bool = True
    
    # Undefined variable checking
    warn_undefined_in_conditionals: bool = True
    ignore_undefined_with_defaults: bool = True
    
    # Command checking
    check_typos: bool = True
    suggest_alternatives: bool = True
    
    # Quoting checks
    warn_unquoted_variables: bool = True
    warn_glob_expansion: bool = True
    strict_quoting: bool = False
    
    # Security checks
    warn_dangerous_commands: bool = True
    check_command_injection: bool = True
    check_file_permissions: bool = True
    
    @classmethod
    def from_file(cls, path: str) -> 'ValidatorConfig':
        """Load configuration from file."""
        import json
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
```

## Testing Strategy

1. **Unit Tests**: Test each validation type independently
2. **Integration Tests**: Test combined validations
3. **False Positive Tests**: Ensure we don't over-warn
4. **Real Script Tests**: Test on actual shell scripts
5. **Performance Tests**: Ensure validation is fast

## Example Output

```bash
$ psh --validate script.sh

ERRORS:
  [IfConditional] in if statement: Empty condition
  [SimpleCommand] in function process_file > while loop: Potential command injection in argument: ${untrusted_input}

WARNINGS:
  [SimpleCommand]: Possible use of undefined variable '$OUTPUT_DIR'
  [SimpleCommand] in function main: Variable expansion '$files' is unquoted - may cause word splitting
  [SimpleCommand]: Security: Avoid 'eval' - it can execute arbitrary code
  [CaseConditional]: Duplicate case pattern '*'

INFO:
  [SimpleCommand]: Consider using 'command -v' instead of 'which' for better portability
  [Pipeline]: Single-command pipeline can be simplified to just the command
  [Redirect]: Consider using '>|' to force overwrite or '>>' to append

Found 8 issue(s):
  - 2 error(s)
  - 4 warning(s)
  - 2 info message(s)
```

## Benefits

1. **Catch Bugs Early**: Find undefined variables before runtime
2. **Improve Security**: Identify potential vulnerabilities
3. **Better Code Quality**: Enforce best practices
4. **Educational**: Learn proper shell scripting
5. **Configurable**: Adapt to project needs

This enhanced validator will significantly improve shell script quality and help users write more robust, secure shell scripts.