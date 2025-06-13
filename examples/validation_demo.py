#!/usr/bin/env python3
"""
Demonstration of PSH's enhanced validation capabilities.

This script shows how to use the EnhancedValidatorVisitor programmatically
to validate shell scripts and analyze their quality.
"""

import sys
import os

# Add parent directory to path to use development version
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor import EnhancedValidatorVisitor, ValidatorConfig


def validate_script(script_content: str, config: ValidatorConfig = None) -> None:
    """Validate a shell script and print results."""
    try:
        # Tokenize and parse the script
        tokens = tokenize(script_content)
        ast = parse(tokens)
        
        # Create validator with optional configuration
        validator = EnhancedValidatorVisitor(config or ValidatorConfig())
        
        # Run validation
        validator.visit(ast)
        
        # Print results
        print(validator.get_summary())
        
        # Return exit code
        error_count = sum(1 for i in validator.issues 
                         if i.severity.value == 'error')
        return 0 if error_count == 0 else 1
        
    except Exception as e:
        print(f"Error during validation: {e}", file=sys.stderr)
        return 2


def main():
    # Example 1: Basic validation
    print("=== Example 1: Basic undefined variable detection ===")
    script1 = '''
    echo "Hello, $UNDEFINED_USER"
    echo "Path: $PATH"  # This is OK - PATH is a special variable
    '''
    validate_script(script1)
    
    # Example 2: Security issues
    print("\n=== Example 2: Security vulnerability detection ===")
    script2 = '''
    USER_INPUT="$1"
    eval "$USER_INPUT"  # Dangerous!
    chmod 777 /tmp/data  # World-writable
    '''
    validate_script(script2)
    
    # Example 3: Custom configuration
    print("\n=== Example 3: Custom validation configuration ===")
    config = ValidatorConfig(
        check_undefined_vars=True,
        check_security=False,  # Disable security checks
        check_typos=True,
        check_quoting=True
    )
    
    script3 = '''
    grpe "pattern" file.txt  # Typo
    FILES=$HOME/*.txt
    ls $FILES  # Unquoted variable
    '''
    validate_script(script3, config)
    
    # Example 4: Good practices
    print("\n=== Example 4: Well-written script ===")
    script4 = '''
    #!/bin/bash
    set -euo pipefail
    
    # Define variables
    readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    OUTPUT_FILE="${1:-output.txt}"
    
    # Check arguments
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <output_file>" >&2
        exit 1
    fi
    
    # Safe file handling
    if [ -f "$OUTPUT_FILE" ]; then
        echo "File already exists: $OUTPUT_FILE" >&2
        exit 1
    fi
    
    # Create file with secure permissions
    touch "$OUTPUT_FILE"
    chmod 644 "$OUTPUT_FILE"
    
    echo "File created: $OUTPUT_FILE"
    '''
    validate_script(script4)


if __name__ == '__main__':
    main()