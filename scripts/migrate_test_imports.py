#!/usr/bin/env python3
"""Script to migrate test imports to suppress deprecation warnings."""

import os
import re
import sys


def migrate_imports(file_path):
    """Migrate imports in a test file to suppress deprecation warnings."""
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already migrated
    if "warnings.catch_warnings()" in content:
        print(f"Skipping {file_path} - already migrated")
        return False
    
    # Pattern to find AST node imports
    import_pattern = re.compile(
        r'^(from psh\.ast_nodes import .*(?:Statement|Command|TopLevel|CommandList|StatementList).*)$',
        re.MULTILINE
    )
    
    matches = list(import_pattern.finditer(content))
    if not matches:
        print(f"Skipping {file_path} - no AST node imports found")
        return False
    
    # Work backwards to avoid offset issues
    modified = False
    for match in reversed(matches):
        import_line = match.group(1)
        start, end = match.span()
        
        # Check if this import includes deprecated types
        deprecated_types = [
            'IfStatement', 'WhileStatement', 'ForStatement', 'CStyleForStatement',
            'CaseStatement', 'SelectStatement', 'ArithmeticCommand',
            'IfCommand', 'WhileCommand', 'ForCommand', 'CStyleForCommand',
            'CaseCommand', 'SelectCommand', 'ArithmeticCompoundCommand'
        ]
        
        has_deprecated = any(dtype in import_line for dtype in deprecated_types)
        
        if has_deprecated:
            # Add warnings import if not present
            if "import warnings" not in content[:start]:
                # Find where to insert warnings import
                sys_import = re.search(r'^import sys$', content, re.MULTILINE)
                if sys_import:
                    insert_pos = sys_import.end()
                    content = content[:insert_pos] + "\nimport warnings" + content[insert_pos:]
                    # Adjust offsets
                    start += len("\nimport warnings")
                    end += len("\nimport warnings")
            
            # Wrap the import with warnings suppression
            replacement = f"""# Import with deprecation warnings suppressed
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    {import_line}"""
            
            content = content[:start] + replacement + content[end:]
            modified = True
    
    if modified:
        # Write the modified content back
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Migrated {file_path}")
        return True
    
    return False


def main():
    """Migrate all test files."""
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'tests')
    
    migrated_count = 0
    for filename in os.listdir(test_dir):
        if filename.startswith('test_') and filename.endswith('.py'):
            file_path = os.path.join(test_dir, filename)
            if migrate_imports(file_path):
                migrated_count += 1
    
    print(f"\nMigrated {migrated_count} test files")


if __name__ == '__main__':
    main()