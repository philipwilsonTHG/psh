#!/usr/bin/env python3
"""
Example: Using SecurityVisitor to scan shell scripts for vulnerabilities.

This demonstrates how to use PSH's SecurityVisitor to analyze shell scripts
and detect potential security issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.security_visitor import SecurityVisitor


def scan_script(script_content: str) -> None:
    """Scan a shell script for security vulnerabilities."""
    print("Security Scan Report")
    print("=" * 60)
    
    try:
        # Parse the script
        tokens = tokenize(script_content)
        ast = parse(tokens)
        
        # Run security analysis
        visitor = SecurityVisitor()
        visitor.visit(ast)
        
        # Get the report
        report = visitor.get_report()
        
        print(f"Total Issues Found: {report['total_issues']}")
        print(f"  High Severity:    {report['high_severity']}")
        print(f"  Medium Severity:  {report['medium_severity']}")
        print(f"  Low Severity:     {report['low_severity']}")
        print()
        
        if report['issues']:
            print("Issues:")
            print("-" * 60)
            for issue in report['issues']:
                print(f"{issue}")
                print()
        else:
            print("No security issues detected!")
            
    except Exception as e:
        print(f"Error parsing script: {e}", file=sys.stderr)
        sys.exit(1)


# Example vulnerable script
vulnerable_script = """#!/bin/bash
# Example script with various security issues

# 1. Dangerous eval with unquoted variable
user_input="$1"
eval $user_input

# 2. World-writable permissions
chmod 777 /tmp/logfile

# 3. Downloading and executing remote code
curl https://example.com/install.sh | bash

# 4. Dangerous rm operation
rm -rf /$dirname/*

# 5. Writing to sensitive file
echo "new_user:x:0:0:root:/root:/bin/bash" >> /etc/passwd

# 6. Arithmetic injection risk
((result = $user_input * 2))

# 7. Unquoted command substitution in loop
for file in $(find /tmp -name "*.log"); do
    process_file "$file"
done
"""

# Safe script example
safe_script = """#!/bin/bash
# Example of safer practices

# Use quoted variables
user_input="$1"
echo "$user_input"

# Use safe permissions
chmod 644 /tmp/logfile

# Download and verify before executing
curl -o install.sh https://example.com/install.sh
# Verify checksum here...
if verify_checksum install.sh; then
    bash install.sh
fi

# Safe file operations
if [ -n "$dirname" ] && [ "$dirname" != "/" ]; then
    rm -rf "/tmp/$dirname"/*
fi

# Use proper quoting in loops
find /tmp -name "*.log" -print0 | while IFS= read -r -d '' file; do
    process_file "$file"
done
"""

if __name__ == "__main__":
    print("Scanning vulnerable script...")
    print()
    scan_script(vulnerable_script)
    
    print("\n" + "=" * 60 + "\n")
    
    print("Scanning safe script...")
    print()
    scan_script(safe_script)