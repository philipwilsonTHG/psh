#!/bin/bash
# Migration script for PSH visitor executor

echo "PSH Visitor Executor Migration Helper"
echo "===================================="
echo

# Check if .pshrc exists
if [ -f "$HOME/.pshrc" ]; then
    echo "Found existing ~/.pshrc"
    
    # Check if already configured
    if grep -q "visitor_executor" "$HOME/.pshrc"; then
        echo "Visitor executor already configured in ~/.pshrc"
    else
        echo "Adding visitor executor configuration to ~/.pshrc..."
        echo "" >> "$HOME/.pshrc"
        echo "# Enable visitor pattern executor (recommended)" >> "$HOME/.pshrc"
        echo "set -o visitor_executor" >> "$HOME/.pshrc"
        echo "Done!"
    fi
else
    echo "Creating ~/.pshrc with visitor executor enabled..."
    cat > "$HOME/.pshrc" << 'EOF'
# PSH configuration file

# Enable visitor pattern executor (recommended)
set -o visitor_executor

# Add your customizations below
EOF
    echo "Done!"
fi

echo
echo "You can also enable the visitor executor by:"
echo "  - Setting environment variable: export PSH_USE_VISITOR_EXECUTOR=1"
echo "  - Using command line flag: psh --visitor-executor"
echo "  - At runtime: set -o visitor_executor"
echo
echo "To disable visitor executor: set +o visitor_executor"
echo

# Test if visitor executor works
echo "Testing visitor executor..."
if command -v psh >/dev/null 2>&1; then
    if PSH_USE_VISITOR_EXECUTOR=1 psh -c 'echo "Visitor executor works!"' 2>/dev/null; then
        echo "✓ Visitor executor is working correctly"
    else
        echo "✗ Visitor executor test failed"
        echo "  You may need to update PSH to the latest version"
    fi
else
    echo "PSH not found in PATH"
fi
