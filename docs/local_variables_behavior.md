# Bash Local Variables Behavior Documentation

## Overview

The `local` builtin in bash creates function-scoped variables that are only visible within the function where they are declared. This document describes the complete behavior of local variables based on bash documentation and testing.

## Basic Syntax

```bash
local [option] [name[=value] ...]
```

### Syntax Forms

1. **Declaration only**: `local varname`
   - Creates a local variable without setting a value
   - Variable is unset until assigned

2. **Declaration with assignment**: `local varname=value`
   - Creates a local variable and assigns it a value
   - Most common usage pattern

3. **Multiple declarations**: `local var1 var2=value var3`
   - Can declare multiple variables in one command
   - Each can optionally have an assignment

4. **With options**: `local -r readonly_var=value`
   - Options like `-r` (readonly), `-i` (integer), `-a` (array), etc.
   - Options apply to all variables in the command

## Scope Rules

### 1. Basic Scope Behavior

```bash
global_var="global value"

myfunc() {
    local local_var="local value"
    echo "Inside function: $local_var"      # Prints: local value
    echo "Inside function: $global_var"     # Prints: global value
}

myfunc
echo "Outside function: $local_var"         # Prints nothing (var doesn't exist)
echo "Outside function: $global_var"        # Prints: global value
```

### 2. Variable Shadowing

Local variables shadow (hide) global variables with the same name:

```bash
var="global"

myfunc() {
    local var="local"
    echo "$var"         # Prints: local
}

myfunc                  # Prints: local
echo "$var"             # Prints: global (unchanged)
```

### 3. Nested Function Scope

**Important**: Local variables are visible to functions called from within the declaring function:

```bash
outer() {
    local outer_var="from outer"
    inner
}

inner() {
    echo "$outer_var"   # Prints: from outer
    outer_var="modified by inner"
}

outer
```

This behavior is sometimes considered surprising or even a "bug" by some users, but it's documented bash behavior.

### 4. Function Return and Variable Lifetime

Local variables are destroyed when the function returns:

```bash
myfunc() {
    local temp="temporary"
    return
}

myfunc
echo "$temp"            # Prints nothing - variable no longer exists
```

## Interaction with Global Variables

### 1. Reading Global Variables

Functions can read global variables unless shadowed by a local:

```bash
global="value"

myfunc() {
    echo "$global"      # Reads global variable
}
```

### 2. Modifying Global Variables

Without `local`, assignments modify global variables:

```bash
var="original"

myfunc() {
    var="modified"      # Modifies global
}

myfunc
echo "$var"             # Prints: modified
```

### 3. Creating New Global Variables

Variables created in functions without `local` become global:

```bash
myfunc() {
    new_global="created in function"
}

myfunc
echo "$new_global"      # Prints: created in function
```

## Export Behavior

### Local Variables Cannot Be Exported

The `export` attribute doesn't apply to local variables:

```bash
myfunc() {
    local var="local"
    export var          # Has no effect outside function
}

myfunc
bash -c 'echo "$var"'   # Child process doesn't see the variable
```

### Exported Variables and Local Shadows

If a global variable is exported, a local variable can shadow it:

```bash
export GLOBAL="exported"

myfunc() {
    local GLOBAL="local shadow"
    bash -c 'echo "$GLOBAL"'    # Child still sees: exported
    echo "$GLOBAL"              # Function sees: local shadow
}
```

## Special Cases and Edge Cases

### 1. Declaration and Assignment Timing

When declaring and assigning in one command, the assignment happens before the variable becomes local:

```bash
var="global"

myfunc() {
    local var="$var"    # Right side evaluates before local takes effect
    echo "$var"         # Prints: global
}
```

### 2. Using Local Outside Functions

Using `local` outside a function is an error:

```bash
local var="test"        # Error: local: can only be used in a function
```

### 3. Local with Command Substitution

```bash
myfunc() {
    local result=$(command)     # Command runs, output captured in local var
}
```

### 4. Local Arrays and Special Variables

```bash
myfunc() {
    local -a array=(1 2 3)      # Local array
    local IFS=":"               # Local IFS doesn't affect global
}
```

## Options for Local

Common options that can be used with `local`:

- `-r`: Make variable readonly
- `-i`: Declare as integer
- `-a`: Declare as indexed array
- `-A`: Declare as associative array
- `-l`: Convert to lowercase on assignment
- `-u`: Convert to uppercase on assignment

Example:
```bash
myfunc() {
    local -r constant="can't change"
    local -i number=42
    local -a array=(1 2 3)
}
```

## Best Practices

1. **Always use local for function variables** unless you explicitly need to modify a global
2. **Declare locals at the beginning of functions** for clarity
3. **Be aware of nested function visibility** when designing function hierarchies
4. **Use meaningful variable names** to avoid accidental shadowing
5. **Consider using a naming convention** for local variables (e.g., prefix with underscore)

## Common Pitfalls

1. **Forgetting to use local**: Accidentally modifying global variables
2. **Assuming locals are invisible to called functions**: They are visible!
3. **Relying on local variables after function returns**: They're destroyed
4. **Trying to export local variables**: Export doesn't work with locals

## Implementation Notes for psh

To implement local variables in psh, we need:

1. **Variable scope stack**: Push new scope on function entry, pop on exit
2. **Scope resolution**: Check local scope first, then parent scopes up to global
3. **Nested function support**: Ensure inner functions see outer locals
4. **Proper cleanup**: Destroy local variables when function returns
5. **Error handling**: Report error when `local` used outside functions
6. **Integration with existing variable system**: Work with special variables, arrays, etc.

## Testing Requirements

Comprehensive tests should cover:

1. Basic local variable creation and access
2. Variable shadowing (local hiding global)
3. Nested function scope inheritance
4. Variable lifetime (destruction on return)
5. Interaction with global variables
6. Error cases (local outside function)
7. Special cases (arrays, readonly, etc.)
8. Command substitution in local declarations
9. Multiple variable declarations in one command
10. Local variables with various options (-r, -i, etc.)