#!/usr/bin/env python3
"""
Fix misclassified tests in PSH conformance suite.

This script identifies and fixes tests that are incorrectly marked as
bash-specific or test errors when they actually work identically in both shells.
"""

import subprocess
import sys
import os
import re

# Add PSH to path
PSH_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PSH_ROOT)


# Commands that are misclassified as bash-specific but work in PSH
MISCLASSIFIED_COMMANDS = [
    # Arrays
    ('declare -a array', 'Arrays are supported in PSH'),
    ('arr=(1 2 3); echo ${arr[0]}', 'Array indexing works in PSH'),
    ('declare -a arr=(1 2 3)', 'Array declaration with values works'),
    
    # Local variables
    ('f() { local x=local; echo $x; }; x=global; f; echo $x', 'Local variables work in PSH'),
    
    # Arithmetic conditionals (if PSH supports them)
    ('[[ 5 -gt 3 ]]', 'Arithmetic conditionals in [[ ]] might work'),
    ('(( 5 > 3 ))', 'Arithmetic evaluation might work'),
    
    # Process substitution (if supported)
    ('diff <(echo a) <(echo b)', 'Process substitution might work'),
]


def test_command(command):
    """Test if a command works identically in PSH and bash."""
    # Test in PSH
    psh_result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', command],
        capture_output=True,
        text=True
    )
    
    # Test in bash
    bash_result = subprocess.run(
        ['bash', '-c', command],
        capture_output=True,
        text=True
    )
    
    return {
        'command': command,
        'psh_exit': psh_result.returncode,
        'bash_exit': bash_result.returncode,
        'psh_stdout': psh_result.stdout.strip(),
        'bash_stdout': bash_result.stdout.strip(),
        'psh_stderr': psh_result.stderr.strip(),
        'bash_stderr': bash_result.stderr.strip(),
        'identical': (psh_result.returncode == bash_result.returncode and
                     psh_result.stdout.strip() == bash_result.stdout.strip())
    }


def find_test_locations():
    """Find where misclassified tests are located."""
    locations = []
    
    # Search for assert_bash_specific calls
    bash_specific_pattern = re.compile(r"self\.assert_bash_specific\(['\"]([^'\"]+)['\"]\)")
    
    # Search for tests marked as xfail that might work
    xfail_pattern = re.compile(r"@pytest\.mark\.xfail.*not.*implemented")
    
    test_files = [
        'tests_new/conformance/bash/test_bash_compatibility.py',
        'tests_new/conformance/posix/test_posix_compliance.py',
        'tests_new/conformance/bash/test_basic_commands.py'
    ]
    
    for file_path in test_files:
        full_path = os.path.join(PSH_ROOT, file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
                
            # Find bash-specific assertions
            for match in bash_specific_pattern.finditer(content):
                command = match.group(1)
                line_num = content[:match.start()].count('\n') + 1
                locations.append({
                    'file': file_path,
                    'line': line_num,
                    'type': 'assert_bash_specific',
                    'command': command
                })
    
    return locations


def generate_fixes():
    """Generate recommended fixes for misclassified tests."""
    fixes = []
    
    # Test each potentially misclassified command
    print("Testing potentially misclassified commands...")
    for command, description in MISCLASSIFIED_COMMANDS:
        result = test_command(command)
        
        if result['identical']:
            fixes.append({
                'command': command,
                'action': 'Change from assert_bash_specific to assert_identical_behavior',
                'reason': 'Works identically in both shells'
            })
        elif result['psh_exit'] == 0 and result['bash_exit'] == 0:
            fixes.append({
                'command': command,
                'action': 'Change to assert_documented_difference',
                'reason': f'Both succeed but outputs differ'
            })
        
        print(f"  {command}: {'IDENTICAL' if result['identical'] else 'DIFFERENT'}")
    
    return fixes


def apply_fixes(fixes, dry_run=True):
    """Apply fixes to test files."""
    if dry_run:
        print("\nDRY RUN - No files will be modified")
    
    files_to_fix = {
        'tests_new/conformance/bash/test_bash_compatibility.py': [],
    }
    
    # Group fixes by file
    for fix in fixes:
        if fix['command'] == 'declare -a array':
            files_to_fix['tests_new/conformance/bash/test_bash_compatibility.py'].append(fix)
        elif fix['command'].startswith('f() { local'):
            files_to_fix['tests_new/conformance/bash/test_bash_compatibility.py'].append(fix)
    
    # Apply fixes
    for file_path, file_fixes in files_to_fix.items():
        if not file_fixes:
            continue
            
        full_path = os.path.join(PSH_ROOT, file_path)
        print(f"\nFixing {file_path}:")
        
        if dry_run:
            for fix in file_fixes:
                print(f"  Would {fix['action']} for: {fix['command']}")
        else:
            # Read file
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Apply fixes
            for fix in file_fixes:
                # Escape special regex characters in command
                escaped_cmd = re.escape(fix['command'])
                
                # Replace assert_bash_specific with assert_identical_behavior
                if 'assert_identical_behavior' in fix['action']:
                    pattern = f"self\\.assert_bash_specific\\(['\"]({escaped_cmd})['\"]\\)"
                    replacement = f"self.assert_identical_behavior('{fix['command']}')"
                    content = re.sub(pattern, replacement, content)
                    print(f"  Fixed: {fix['command']}")
            
            # Write file back
            with open(full_path, 'w') as f:
                f.write(content)


def main():
    """Main function."""
    print("PSH Test Misclassification Fixer")
    print("=" * 60)
    
    # Find test locations
    locations = find_test_locations()
    print(f"\nFound {len(locations)} assert_bash_specific calls")
    
    # Generate fixes
    fixes = generate_fixes()
    
    print(f"\nRecommended fixes: {len(fixes)}")
    for fix in fixes:
        print(f"\n- Command: {fix['command']}")
        print(f"  Action: {fix['action']}")
        print(f"  Reason: {fix['reason']}")
    
    # Apply fixes
    if fixes and '--apply' in sys.argv:
        print("\nApplying fixes...")
        apply_fixes(fixes, dry_run=False)
        print("\nDone! Remember to run tests to verify the fixes.")
    else:
        print("\nTo apply these fixes, run with --apply flag")


if __name__ == '__main__':
    main()