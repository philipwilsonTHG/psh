#!/usr/bin/env python3 -m psh
# Debug scopes demonstration

echo "=== Debug Scopes Demo ==="
echo "This demonstrates the debug-scopes feature for tracking variable scope operations."
echo

# Enable debug-scopes
echo "Enabling debug-scopes with: set -o debug-scopes"
set -o debug-scopes
echo

# Global variable
echo "Setting global variable:"
global_var="I am global"
echo

# Function with local variables
echo "Defining function with local variables:"
test_function() {
    echo "  Inside test_function"
    local local_var="I am local"
    global_var="Modified in function"
    nested_var="Created in function"
}

echo "Calling test_function:"
test_function
echo

echo "After function call:"
echo "  global_var = $global_var"
echo "  nested_var = $nested_var"
echo

# Nested functions
echo "Testing nested functions:"
outer_function() {
    local outer_var="outer"
    
    inner_function() {
        local inner_var="inner"
        echo "    In inner_function: outer_var=$outer_var"
    }
    
    echo "  In outer_function"
    inner_function
}

outer_function
echo

# Disable debug-scopes
echo "Disabling debug-scopes with: set +o debug-scopes"
set +o debug-scopes
echo

echo "Now variable operations are silent:"
silent_var="No debug output"
echo "Done!"