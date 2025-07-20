# PSH Parser Configuration Guide

## Overview

The PSH parser's behavior can be extensively customized through the `ParserConfig` class. This guide explains each configuration option with practical examples and use cases.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Parsing Modes](#parsing-modes)
3. [Error Handling Options](#error-handling-options)
4. [Feature Toggles](#feature-toggles)
5. [Parsing Behavior](#parsing-behavior)
6. [Debugging Options](#debugging-options)
7. [Common Configuration Patterns](#common-configuration-patterns)
8. [Performance Tuning](#performance-tuning)

## Basic Usage

### Creating a Custom Configuration

```python
from psh.parser import Parser, ParserConfig, ParsingMode

# Create a custom configuration
config = ParserConfig(
    parsing_mode=ParsingMode.BASH_COMPAT,
    enable_arrays=True,
    enable_functions=True,
    collect_errors=True
)

# Use it with the parser
parser = Parser(tokens, config=config)
ast = parser.parse()
```

### Using Factory Methods

```python
# Pre-configured for common use cases
config_posix = ParserConfig.strict_posix()
config_bash = ParserConfig.bash_compatible()
config_permissive = ParserConfig.permissive()
config_educational = ParserConfig.educational()
```

## Parsing Modes

### `parsing_mode`

Controls the overall parsing strategy and feature set.

```python
from psh.parser import ParsingMode

# Strict POSIX compliance
config = ParserConfig(parsing_mode=ParsingMode.STRICT_POSIX)
# - Disables bash extensions
# - Enforces POSIX.1-2017 standard
# - Stricter validation

# Bash compatibility mode
config = ParserConfig(parsing_mode=ParsingMode.BASH_COMPAT)
# - Enables bash-specific features
# - Allows bash syntax extensions
# - More permissive parsing

# Permissive mode (default)
config = ParserConfig(parsing_mode=ParsingMode.PERMISSIVE)
# - Maximum compatibility
# - Accepts most shell variants
# - Minimal restrictions

# Educational mode
config = ParserConfig(parsing_mode=ParsingMode.EDUCATIONAL)
# - Extra validation and warnings
# - Helpful error messages
# - Best practices enforcement
```

**Example: POSIX vs Bash Mode**

```python
# This works in bash mode but fails in POSIX
tokens = tokenize("arr=(1 2 3)")  # Arrays are bash-specific

# Bash mode - succeeds
config_bash = ParserConfig(parsing_mode=ParsingMode.BASH_COMPAT)
parser = Parser(tokens, config=config_bash)
ast = parser.parse()  # Success!

# POSIX mode - fails
config_posix = ParserConfig(parsing_mode=ParsingMode.STRICT_POSIX)
parser = Parser(tokens, config=config_posix)
try:
    ast = parser.parse()
except ParseError as e:
    print(f"POSIX error: {e.message}")  # Arrays not allowed in POSIX
```

## Error Handling Options

### `error_handling`

Determines how the parser responds to errors.

```python
from psh.parser import ErrorHandlingMode

# Strict mode - fail on first error (default)
config = ParserConfig(error_handling=ErrorHandlingMode.STRICT)

# Collect mode - gather all errors
config = ParserConfig(error_handling=ErrorHandlingMode.COLLECT)

# Recover mode - attempt to continue parsing
config = ParserConfig(error_handling=ErrorHandlingMode.RECOVER)
```

### `collect_errors`

Boolean flag to enable error collection.

```python
# Collect multiple errors
config = ParserConfig(collect_errors=True, max_errors=20)
parser = Parser(tokens, config=config)
result = parser.parse_with_error_collection()

if result.errors:
    print(f"Found {len(result.errors)} errors:")
    for error in result.errors:
        print(f"  Line {error.error_context.line}: {error.message}")
```

### `max_errors`

Maximum number of errors to collect before stopping.

```python
# Stop after 5 errors to avoid overwhelming output
config = ParserConfig(
    collect_errors=True,
    max_errors=5
)
```

### `enable_error_recovery`

Attempt to recover from errors and continue parsing.

```python
# Enable recovery for IDE/linting scenarios
config = ParserConfig(
    enable_error_recovery=True,
    collect_errors=True
)

# Parser will try to recover at statement boundaries
tokens = tokenize("echo hello; if then echo bad; fi; echo world")
parser = Parser(tokens, config=config)
result = parser.parse_with_error_collection()

# result.ast will contain partial AST with valid statements
# result.errors will contain the parsing errors
```

## Feature Toggles

### Shell Feature Flags

Each feature can be individually enabled or disabled:

```python
config = ParserConfig(
    # Core features
    enable_aliases=True,          # Shell aliases
    enable_functions=True,        # Function definitions
    enable_arithmetic=True,       # $((...)) arithmetic
    enable_arrays=True,           # Array syntax
    enable_associative_arrays=True,  # Associative arrays
    
    # Advanced features
    enable_process_substitution=True,  # <(...) and >(...)
    enable_extended_glob=True,    # Extended globbing patterns
    enable_brace_expansion=True,  # {a,b,c} expansion
    enable_coprocesses=True,      # Coprocess support
    
    # Expansion features
    enable_command_substitution=True,   # $(...) and `...`
    enable_parameter_expansion=True,    # ${var} expansions
    enable_tilde_expansion=True,        # ~ expansion
    enable_pathname_expansion=True,     # Glob patterns
    enable_ansi_c_quoting=True,        # $'...' strings
)
```

### Feature Toggle Examples

#### Disabling Functions for Restricted Shell

```python
# Create a restricted parser that doesn't allow functions
config = ParserConfig(
    enable_functions=False,
    enable_aliases=False
)

tokens = tokenize("function foo() { echo dangerous; }")
parser = Parser(tokens, config=config)
try:
    ast = parser.parse()
except ParseError as e:
    print("Functions disabled:", e.message)
```

#### POSIX-Only Arrays

```python
# POSIX doesn't support arrays
config = ParserConfig(
    parsing_mode=ParsingMode.STRICT_POSIX,
    enable_arrays=False,
    enable_associative_arrays=False
)
```

#### Minimal Feature Set

```python
# Very restricted parsing
config = ParserConfig(
    enable_functions=False,
    enable_arithmetic=False,
    enable_arrays=False,
    enable_process_substitution=False,
    enable_command_substitution=False,
    # Only basic commands allowed
)
```

## Parsing Behavior

### `allow_empty_commands`

Controls whether empty commands are allowed.

```python
# Default: empty commands are errors
config = ParserConfig(allow_empty_commands=False)
tokens = tokenize("; ; echo hello")  # Empty commands
parser = Parser(tokens, config=config)
# Raises ParseError

# Allow empty commands
config = ParserConfig(allow_empty_commands=True)
parser = Parser(tokens, config=config)
ast = parser.parse()  # Success
```

### `strict_word_splitting`

Controls word splitting behavior.

```python
# Strict word splitting (POSIX-like)
config = ParserConfig(strict_word_splitting=True)

# More permissive word splitting
config = ParserConfig(strict_word_splitting=False)
```

### `posix_compliance`

Master flag for POSIX compliance.

```python
# Enable all POSIX compliance checks
config = ParserConfig(
    posix_compliance=True,
    # Automatically sets:
    # - enable_arrays=False
    # - enable_process_substitution=False
    # - strict_word_splitting=True
    # etc.
)
```

### `validate_names`

Controls identifier validation.

```python
# Strict name validation
config = ParserConfig(validate_names=True)
tokens = tokenize("function 123invalid() { :; }")
# Will error - function names can't start with digits

# Permissive naming
config = ParserConfig(validate_names=False)
# Allows non-standard names
```

## Debugging Options

### `trace_parsing`

Enable detailed parsing trace.

```python
# Enable parse tracing
config = ParserConfig(trace_parsing=True)
parser = Parser(tokens, config=config)

# Parsing will output trace information:
# > Entering parse_pipeline
# >> Entering parse_command
# >>> Matched WORD: "echo"
# >> Exiting parse_command
# > Exiting parse_pipeline
```

### `profile_parsing`

Enable performance profiling.

```python
# Enable profiling
config = ParserConfig(profile_parsing=True)
parser = Parser(tokens, config=config)
ast = parser.parse()

# Access profiling data
if parser.context.profiler:
    stats = parser.context.profiler.get_stats()
    print(f"Total parse time: {stats.total_time:.3f}s")
    print(f"Tokens parsed: {stats.token_count}")
    print(f"Rules executed: {stats.rule_count}")
    
    # Find slow rules
    for rule, time in stats.slowest_rules[:5]:
        print(f"  {rule}: {time:.3f}s")
```

### `debug_mode`

General debug mode flag.

```python
# Enable all debugging features
config = ParserConfig(
    debug_mode=True,  # Sets trace_parsing and profile_parsing
)
```

## Common Configuration Patterns

### IDE/Editor Integration

```python
# Configuration for IDE parsing
config_ide = ParserConfig(
    # Collect all errors for display
    collect_errors=True,
    max_errors=100,
    enable_error_recovery=True,
    
    # Parse everything for completions
    parsing_mode=ParsingMode.PERMISSIVE,
    
    # Quick parsing
    profile_parsing=False,
    trace_parsing=False
)
```

### Linting Configuration

```python
# Strict linting configuration
config_lint = ParserConfig(
    # Educational mode for best practices
    parsing_mode=ParsingMode.EDUCATIONAL,
    
    # Collect all issues
    collect_errors=True,
    enable_error_recovery=True,
    
    # Strict validation
    validate_names=True,
    strict_word_splitting=True,
    
    # Warn about deprecated features
    warn_deprecated=True
)
```

### Script Validation

```python
# Validate shell scripts
config_validate = ParserConfig(
    # Check POSIX compliance
    parsing_mode=ParsingMode.STRICT_POSIX,
    posix_compliance=True,
    
    # Fail fast on errors
    error_handling=ErrorHandlingMode.STRICT,
    
    # Validate everything
    validate_names=True,
    validate_redirections=True
)
```

### Interactive Shell

```python
# Configuration for interactive use
config_interactive = ParserConfig(
    # Maximum compatibility
    parsing_mode=ParsingMode.PERMISSIVE,
    
    # Allow partial input
    allow_empty_commands=True,
    
    # All features enabled
    enable_aliases=True,
    enable_functions=True,
    enable_arrays=True,
    
    # Quick feedback
    error_handling=ErrorHandlingMode.STRICT
)
```

## Performance Tuning

### Disabling Unused Features

```python
# Minimal parser for simple scripts
config_minimal = ParserConfig(
    # Disable complex features
    enable_functions=False,
    enable_arrays=False,
    enable_arithmetic=False,
    enable_process_substitution=False,
    
    # Skip validation
    validate_names=False,
    validate_redirections=False,
    
    # No debugging
    trace_parsing=False,
    profile_parsing=False
)
```

### Optimized for Speed

```python
# Fast parsing configuration
config_fast = ParserConfig(
    # Skip all optional checks
    validate_names=False,
    check_command_validity=False,
    
    # No error recovery overhead
    enable_error_recovery=False,
    collect_errors=False,
    
    # Minimal features
    parsing_mode=ParsingMode.PERMISSIVE
)
```

## Configuration Inheritance

### Extending Configurations

```python
# Start with a base configuration
base_config = ParserConfig.bash_compatible()

# Create a modified version
custom_config = ParserConfig(
    # Copy all settings from base
    **base_config.__dict__,
    # Override specific settings
    enable_arrays=False,
    collect_errors=True
)
```

### Configuration Composition

```python
def create_custom_config(base_mode=ParsingMode.BASH_COMPAT, 
                        strict_validation=False,
                        ide_mode=False):
    """Create a configuration with custom options."""
    
    config = ParserConfig(parsing_mode=base_mode)
    
    if strict_validation:
        config.validate_names = True
        config.validate_redirections = True
        config.strict_word_splitting = True
    
    if ide_mode:
        config.collect_errors = True
        config.enable_error_recovery = True
        config.max_errors = 50
    
    return config
```

## Debugging Configuration Issues

### Checking Active Configuration

```python
# Print active configuration
parser = Parser(tokens, config=config)
print("Parser configuration:")
print(f"  Mode: {parser.config.parsing_mode}")
print(f"  Arrays enabled: {parser.config.enable_arrays}")
print(f"  Error recovery: {parser.config.enable_error_recovery}")
```

### Configuration Validation

```python
# Validate configuration consistency
def validate_config(config):
    """Check configuration for consistency."""
    
    if config.parsing_mode == ParsingMode.STRICT_POSIX:
        if config.enable_arrays:
            print("Warning: Arrays enabled in POSIX mode")
        if config.enable_process_substitution:
            print("Warning: Process substitution in POSIX mode")
    
    if config.collect_errors and config.max_errors < 1:
        print("Error: collect_errors with max_errors < 1")
    
    return config
```

## Best Practices

1. **Start with Factory Methods**: Use predefined configurations as starting points
2. **Be Explicit**: Explicitly set important flags rather than relying on defaults
3. **Match Your Use Case**: Choose configurations that match your specific needs
4. **Test Configuration**: Test with representative input to ensure configuration works
5. **Document Choices**: Document why specific configuration options were chosen

## Summary

The ParserConfig system provides fine-grained control over parser behavior. By understanding these options, you can:

- Create parsers tailored to specific use cases
- Enforce compliance with shell standards
- Optimize for performance or functionality
- Build better tooling and integrations

Remember that configuration choices affect both what syntax is accepted and how errors are reported, so choose settings that match your users' expectations and needs.