#!/bin/bash

# Test heredoc in psh
echo "Testing heredoc..."

# Create test script
cat > /tmp/test_heredoc.psh << 'SCRIPT'
cat <<EOF
Hello from heredoc
This is line 2
EOF
echo "After heredoc"
SCRIPT

# Run with psh
echo "Running with psh:"
python3 -m psh < /tmp/test_heredoc.psh

# Clean up
rm -f /tmp/test_heredoc.psh