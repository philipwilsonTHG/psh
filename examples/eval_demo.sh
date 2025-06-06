#!/usr/bin/env psh
# Demonstration of the eval builtin

echo "=== PSH Eval Builtin Demo ==="
echo

# Basic eval usage
echo "1. Basic eval:"
eval "echo Hello from eval"
echo

# Variable assignment in eval
echo "2. Variable assignment:"
eval "name='PSH Shell'"
echo "Variable set in eval: $name"
echo

# Multiple commands
echo "3. Multiple commands:"
eval "echo First command; echo Second command"
echo

# Using variables to build commands
echo "4. Dynamic command building:"
cmd="echo"
msg="Dynamic message"
eval "$cmd '$msg'"
echo

# Function definition in eval
echo "5. Function definition:"
eval "greet() { echo \"Hello, \$1!\"; }"
greet "World"
echo

# Control structures in eval
echo "6. Control structures:"
eval "for i in 1 2 3; do echo \"  Number: \$i\"; done"
echo

# Pipeline in eval
echo "7. Pipeline:"
eval "printf 'apple\\nbanana\\ncherry\\n' | grep an"
echo

# Command substitution in eval
echo "8. Command substitution:"
eval "result=\$(echo computed); echo \"Result: \$result\""
echo

# Nested eval
echo "9. Nested eval:"
eval "eval \"echo 'Nested eval works!'\""
echo

# Exit status
echo "10. Exit status:"
eval "true"
echo "  Exit status after 'true': $?"
eval "false" 
echo "  Exit status after 'false': $?"
echo

echo "=== Demo Complete ==="