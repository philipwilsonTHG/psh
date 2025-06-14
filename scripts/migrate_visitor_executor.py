#!/usr/bin/env python3
"""
Migration helper script for visitor executor.

This script helps with the migration from legacy to visitor executor by:
1. Updating code to check environment variables
2. Adding compatibility layers
3. Updating documentation
"""

import os
import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VisitorExecutorMigrator:
    """Helper for migrating to visitor executor."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.changes_made = []
    
    def update_shell_init(self):
        """Update shell.py to check environment variable."""
        shell_file = self.project_root / 'psh' / 'shell.py'
        
        print("Updating shell.py to check PSH_USE_VISITOR_EXECUTOR...")
        
        # Read current content
        with open(shell_file, 'r') as f:
            content = f.read()
        
        # Check if already updated
        if 'PSH_USE_VISITOR_EXECUTOR' in content:
            print("  Already updated!")
            return
        
        # Find the __init__ method
        init_pattern = r'(def __init__\(self.*?use_visitor_executor=False.*?\):)'
        match = re.search(init_pattern, content, re.DOTALL)
        
        if not match:
            print("  ERROR: Could not find __init__ method!")
            return
        
        # Find where use_visitor_executor is stored
        store_pattern = r'(self\.use_visitor_executor = use_visitor_executor)'
        store_match = re.search(store_pattern, content)
        
        if not store_match:
            print("  ERROR: Could not find use_visitor_executor assignment!")
            return
        
        # Replace with environment check
        new_assignment = '''# Store executor mode - check environment variable
        # Default is legacy executor for now, but check environment
        self.use_visitor_executor = use_visitor_executor or os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')'''
        
        new_content = content[:store_match.start()] + new_assignment + content[store_match.end():]
        
        # Write back
        with open(shell_file, 'w') as f:
            f.write(new_content)
        
        self.changes_made.append("Updated shell.py to check PSH_USE_VISITOR_EXECUTOR")
        print("  Done!")
    
    def add_shell_option(self):
        """Add visitor_executor as a shell option."""
        options_file = self.project_root / 'psh' / 'core' / 'options.py'
        
        print("Adding visitor_executor to shell options...")
        
        # Read current content
        with open(options_file, 'r') as f:
            content = f.read()
        
        # Check if already added
        if 'visitor_executor' in content:
            print("  Already added!")
            return
        
        # Find the OPTION_HANDLERS dict
        handlers_pattern = r'(OPTION_HANDLERS = \{[^}]+)'
        match = re.search(handlers_pattern, content, re.DOTALL)
        
        if not match:
            print("  ERROR: Could not find OPTION_HANDLERS!")
            return
        
        # Add new handler before the closing brace
        handlers_content = match.group(1)
        new_handler = '''    'visitor_executor': {
        'set': lambda shell: setattr(shell, 'use_visitor_executor', True),
        'unset': lambda shell: setattr(shell, 'use_visitor_executor', False),
        'show': lambda shell: shell.use_visitor_executor,
    },
'''
        
        # Insert before the last handler (find last comma)
        last_comma = handlers_content.rfind(',')
        if last_comma > 0:
            new_handlers = handlers_content[:last_comma+1] + '\n' + new_handler + handlers_content[last_comma+1:]
            new_content = content[:match.start()] + new_handlers + content[match.end():]
            
            # Write back
            with open(options_file, 'w') as f:
                f.write(new_content)
            
            self.changes_made.append("Added visitor_executor to shell options")
            print("  Done!")
        else:
            print("  ERROR: Could not find insertion point!")
    
    def update_main_help(self):
        """Update help text in __main__.py."""
        main_file = self.project_root / 'psh' / '__main__.py'
        
        print("Updating help text...")
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Update the experimental note
        old_text = '--visitor-executor Use visitor pattern executor (experimental)'
        new_text = '--visitor-executor Use visitor pattern executor (recommended)'
        
        if old_text in content:
            content = content.replace(old_text, new_text)
            
            # Add environment variable note
            env_note = '''
            print("\\nEnvironment Variables:")
            print("  PSH_USE_VISITOR_EXECUTOR=1   Use visitor executor by default")'''
            
            if 'Environment Variables:' not in content:
                # Find where to insert (after Examples)
                examples_end = content.find('sys.exit(0)')
                if examples_end > 0:
                    # Find the print statement before sys.exit
                    last_print = content.rfind('print(', 0, examples_end)
                    if last_print > 0:
                        # Find end of that print
                        print_end = content.find('\n', last_print)
                        if print_end > 0:
                            content = content[:print_end+1] + env_note + content[print_end+1:]
            
            with open(main_file, 'w') as f:
                f.write(content)
            
            self.changes_made.append("Updated help text to recommend visitor executor")
            print("  Done!")
        else:
            print("  Already updated or text not found!")
    
    def create_compatibility_test(self):
        """Create a test to ensure both executors behave the same."""
        test_file = self.project_root / 'tests' / 'test_executor_compatibility.py'
        
        print("Creating executor compatibility test...")
        
        if test_file.exists():
            print("  Already exists!")
            return
        
        test_content = '''"""
Test compatibility between legacy and visitor executors.

This test ensures both executors produce identical results.
"""

import pytest
import os
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse


class TestExecutorCompatibility:
    """Test that both executors produce identical results."""
    
    def run_with_executor(self, command, use_visitor=False):
        """Run command with specified executor and capture output."""
        # Create shell with specified executor
        shell = Shell(use_visitor_executor=use_visitor)
        
        # Capture output
        stdout = StringIO()
        stderr = StringIO()
        
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Parse command once
            tokens = tokenize(command)
            ast = parse(tokens)
            
            # Execute
            exit_code = shell.execute(ast)
        
        return {
            'exit_code': exit_code,
            'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue(),
            'variables': dict(shell.variables),
            'last_exit_code': shell.last_exit_code
        }
    
    def assert_identical_results(self, command):
        """Assert that both executors produce identical results."""
        legacy_result = self.run_with_executor(command, use_visitor=False)
        visitor_result = self.run_with_executor(command, use_visitor=True)
        
        # Compare results
        assert legacy_result['exit_code'] == visitor_result['exit_code'], \\
            f"Exit codes differ: legacy={legacy_result['exit_code']}, visitor={visitor_result['exit_code']}"
        
        assert legacy_result['stdout'] == visitor_result['stdout'], \\
            f"Stdout differs:\\nLegacy: {repr(legacy_result['stdout'])}\\nVisitor: {repr(visitor_result['stdout'])}"
        
        assert legacy_result['stderr'] == visitor_result['stderr'], \\
            f"Stderr differs:\\nLegacy: {repr(legacy_result['stderr'])}\\nVisitor: {repr(visitor_result['stderr'])}"
        
        assert legacy_result['last_exit_code'] == visitor_result['last_exit_code'], \\
            f"Last exit codes differ: legacy={legacy_result['last_exit_code']}, visitor={visitor_result['last_exit_code']}"
    
    def test_simple_commands(self):
        """Test simple command execution."""
        self.assert_identical_results('echo hello')
        self.assert_identical_results('echo $HOME')
        self.assert_identical_results('VAR=value; echo $VAR')
    
    def test_pipelines(self):
        """Test pipeline execution."""
        self.assert_identical_results('echo hello | cat')
        self.assert_identical_results('echo one; echo two | cat')
    
    def test_control_structures(self):
        """Test control structure execution."""
        self.assert_identical_results('if true; then echo yes; fi')
        self.assert_identical_results('for i in 1 2 3; do echo $i; done')
        self.assert_identical_results('i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done')
    
    def test_functions(self):
        """Test function definition and execution."""
        self.assert_identical_results('foo() { echo hello; }; foo')
        self.assert_identical_results('function bar { return 42; }; bar; echo $?')
    
    def test_arithmetic(self):
        """Test arithmetic evaluation."""
        self.assert_identical_results('echo $((2 + 2))')
        self.assert_identical_results('((x = 5)); echo $x')
        self.assert_identical_results('for ((i=0; i<3; i++)); do echo $i; done')
    
    def test_expansions(self):
        """Test various expansions."""
        self.assert_identical_results('echo ${HOME:-/tmp}')
        self.assert_identical_results('X=hello; echo ${#X}')
        self.assert_identical_results('Y=foobar; echo ${Y/foo/bar}')
    
    @pytest.mark.parametrize('command', [
        'true',
        'false',
        'exit 0',
        'exit 1',
        'exit 42',
    ])
    def test_exit_codes(self, command):
        """Test that exit codes match."""
        # Note: We can't use assert_identical_results for exit commands
        # because they terminate the shell
        legacy_shell = Shell(use_visitor_executor=False)
        visitor_shell = Shell(use_visitor_executor=True)
        
        # Parse command
        tokens = tokenize(command)
        ast = parse(tokens)
        
        # Execute and compare exit codes
        legacy_exit = legacy_shell.execute(ast)
        visitor_exit = visitor_shell.execute(ast)
        
        assert legacy_exit == visitor_exit


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
'''
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        self.changes_made.append("Created executor compatibility test")
        print("  Done!")
    
    def update_readme(self):
        """Update README with visitor executor information."""
        readme_file = self.project_root / 'README.md'
        
        if not readme_file.exists():
            print("No README.md found, skipping...")
            return
        
        print("Updating README.md...")
        
        with open(readme_file, 'r') as f:
            content = f.read()
        
        # Check if already has visitor executor section
        if 'Visitor Executor' in content or 'visitor executor' in content:
            print("  Already mentions visitor executor!")
            return
        
        # Add section about visitor executor
        visitor_section = '''
## Visitor Pattern Executor

PSH includes a modern visitor pattern-based executor that provides:

- Cleaner architecture with better separation of concerns
- Advanced AST analysis and optimization capabilities  
- Security vulnerability detection
- Code metrics and complexity analysis

To use the visitor executor:

```bash
# Command line flag
psh --visitor-executor

# Environment variable  
export PSH_USE_VISITOR_EXECUTOR=1
psh

# Runtime option
psh
$ set -o visitor_executor
```

The visitor executor is recommended for new installations and will become the default in a future release.
'''
        
        # Find a good place to insert (after main features, before examples)
        insert_marker = '## Development Notes'
        if insert_marker in content:
            insert_pos = content.find(insert_marker)
            content = content[:insert_pos] + visitor_section + '\n' + content[insert_pos:]
            
            with open(readme_file, 'w') as f:
                f.write(content)
            
            self.changes_made.append("Updated README.md with visitor executor information")
            print("  Done!")
        else:
            print("  Could not find suitable insertion point!")
    
    def create_migration_script(self):
        """Create a user-facing migration script."""
        script_file = self.project_root / 'migrate_to_visitor.sh'
        
        print("Creating user migration script...")
        
        script_content = '''#!/bin/bash
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
'''
        
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_file, 0o755)
        
        self.changes_made.append("Created user migration script")
        print("  Done!")
    
    def print_summary(self):
        """Print summary of changes made."""
        print("\n" + "=" * 60)
        print("Migration Preparation Complete!")
        print("=" * 60)
        
        if self.changes_made:
            print("\nChanges made:")
            for change in self.changes_made:
                print(f"  ✓ {change}")
        else:
            print("\nNo changes were needed - already prepared!")
        
        print("\nNext steps:")
        print("  1. Run tests with visitor executor: python scripts/test_visitor_executor.py")
        print("  2. Update CLAUDE.md with migration status")
        print("  3. Create release notes highlighting visitor executor")
        print("  4. Monitor user feedback after release")


def main():
    """Main entry point."""
    migrator = VisitorExecutorMigrator()
    
    print("Preparing PSH for visitor executor migration...")
    print("=" * 60)
    print()
    
    # Make changes
    migrator.update_shell_init()
    migrator.add_shell_option()
    migrator.update_main_help()
    migrator.create_compatibility_test()
    migrator.update_readme()
    migrator.create_migration_script()
    
    # Summary
    migrator.print_summary()


if __name__ == '__main__':
    main()