# Bash Declare Builtin - Comprehensive Options Reference

The `declare` builtin is used to declare variables and give them attributes. It can also be used to display variable values and attributes.

## Syntax
```bash
declare [-aAfFgiIlnprtux] [-p] [name[=value] ...]
declare -p [-aAfFgiIlnprtux] [name ...]
```

## All Options/Flags

### Array Options
- **`-a`** - Declare indexed array
  - Creates an indexed array variable (numeric indices)
  - Example: `declare -a myarray=(one two three)`
  
- **`-A`** - Declare associative array
  - Creates an associative array (string indices/keys)
  - Example: `declare -A mymap=([key1]="value1" [key2]="value2")`

### Function Options
- **`-f`** - Function names only
  - Restricts action to function names and definitions
  - With no names, displays all function definitions
  - Example: `declare -f` (list all functions)
  - Example: `declare -f myfunction` (show specific function)

- **`-F`** - Function names without definitions
  - Displays only function names (no body)
  - More concise than -f
  - Example: `declare -F` (list all function names)

### Variable Type Options
- **`-i`** - Integer
  - Treats variable as an integer
  - Arithmetic evaluation performed on assignment
  - Example: `declare -i num=5+5` (num becomes 10)
  
- **`-l`** - Lowercase
  - Converts value to lowercase on assignment
  - Example: `declare -l name="JOHN"` (name becomes "john")
  
- **`-u`** - Uppercase
  - Converts value to uppercase on assignment
  - Example: `declare -u name="john"` (name becomes "JOHN")

### Reference and Export Options
- **`-n`** - Nameref (reference)
  - Creates a reference to another variable
  - Changes to the nameref affect the referenced variable
  - Example: `declare -n ref=original_var`
  
- **`-x`** - Export
  - Marks variable for export to environment of subsequent commands
  - Equivalent to using `export`
  - Example: `declare -x PATH="/usr/bin:$PATH"`

### Access Control Options
- **`-r`** - Readonly
  - Makes variable readonly (cannot be modified or unset)
  - Example: `declare -r CONSTANT="immutable"`

### Scope Options
- **`-g`** - Global
  - Forces variables to be created at global scope
  - Useful inside functions to create global variables
  - Example: Inside function: `declare -g global_var="accessible everywhere"`

- **`-I`** - Inherit attributes
  - Local variables inherit attributes from variables with same name in surrounding scope
  - New in bash 5.0+
  - Example: If global var is integer (-i), local with -I inherits that

### Display Options
- **`-p`** - Print/display
  - Displays attributes and values of variables
  - Can be combined with other options to filter
  - Example: `declare -p` (show all variables)
  - Example: `declare -pi` (show only integer variables)

### Function Attribute Options
- **`-t`** - Trace
  - Gives each function the trace attribute
  - Inherited by functions defined within traced functions
  - Causes DEBUG and RETURN traps to be inherited
  - Example: `declare -tf myfunc`

## Combining Options

Many options can be combined:
- `declare -ix` - Integer variable that's exported
- `declare -lr` - Lowercase readonly variable
- `declare -Ar` - Readonly associative array
- `declare -ai` - Integer indexed array
- `declare -gx` - Global exported variable (in function)

## Using + to Remove Attributes

Using `+` instead of `-` turns OFF the attribute:
- `declare +x VAR` - Remove export attribute
- `declare +i VAR` - Remove integer attribute
- `declare +r VAR` - Error! Cannot remove readonly

## Special Behaviors and Edge Cases

1. **Local by default in functions**: When used inside a function without `-g`, variables are local
2. **Readonly is permanent**: Once set with `-r`, cannot be removed
3. **Array attributes**: `-a` and `-A` are mutually exclusive
4. **Case conversion**: `-l` and `-u` are mutually exclusive
5. **Nameref loops**: `declare -n ref=ref` creates an invalid circular reference

## Examples

```bash
# Integer arithmetic
declare -i x=5
x=x+10          # x is now 15
x="5 + 5"       # x is now 10

# Uppercase/lowercase conversion
declare -u upper="hello"    # upper="HELLO"
declare -l lower="WORLD"    # lower="world"

# Readonly variables
declare -r PI=3.14159
PI=3.14  # Error: PI: readonly variable

# Associative arrays
declare -A colors
colors[red]="#FF0000"
colors[green]="#00FF00"
colors[blue]="#0000FF"

# Global variable in function
function myfunc() {
    declare -g GLOBAL_VAR="I'm global"
    local LOCAL_VAR="I'm local"
}

# Nameref (reference)
original="initial value"
declare -n myref=original
myref="new value"  # original is now "new value"

# Export and integer combined
declare -ix COUNT=0

# Display specific variable attributes
declare -p PATH
declare -p -f  # Show all functions

# Function with trace
declare -tf traced_function
```

## Bash Version Notes

- `-I` (inherit) option added in Bash 5.0
- `-n` (nameref) added in Bash 4.3
- `-A` (associative array) added in Bash 4.0
- `-g` (global) added in Bash 4.2