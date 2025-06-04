#!/usr/bin/env python3 -m psh

# Test length operations
echo "=== Length Operations ==="
VAR="hello world"
echo "VAR='$VAR'"
echo 'Length of VAR: ${#VAR} = '${#VAR}

# Test with empty variable
EMPTY=""
echo "EMPTY='$EMPTY'"
echo 'Length of EMPTY: ${#EMPTY} = '${#EMPTY}

# Test undefined variable
echo 'Length of UNDEFINED: ${#UNDEFINED} = '${#UNDEFINED}

# Test special variables
echo ""
echo "=== Special Variable Lengths ==="
set -- one two three four
echo "Positional params: $@"
echo 'Number of params ${#} = '${#}
echo 'Length of all params ${#*} = '${#*}
echo 'Length of all params ${#@} = '${#@}