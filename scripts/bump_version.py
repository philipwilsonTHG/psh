#!/usr/bin/env python3
"""
Simple version bumping script for psh.
Usage: python scripts/bump_version.py <new_version>
"""

import sys
import re
import subprocess
from pathlib import Path

def bump_version(new_version):
    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(f"Error: Version must be in format X.Y.Z, got {new_version}")
        sys.exit(1)
    
    # Update version.py
    version_file = Path("psh/version.py")
    content = version_file.read_text()
    content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    version_file.write_text(content)
    print(f"✓ Updated {version_file}")
    
    # Git operations
    try:
        # Add the changed file
        subprocess.run(["git", "add", "psh/version.py"], check=True)
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", f"Bump version to {new_version}"],
            check=True
        )
        print(f"✓ Created commit")
        
        # Create tag
        subprocess.run(
            ["git", "tag", "-a", f"v{new_version}", "-m", f"Version {new_version}"],
            check=True
        )
        print(f"✓ Created tag v{new_version}")
        
        print(f"\nVersion bumped to {new_version} successfully!")
        print("Don't forget to push: git push && git push --tags")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        print("Example: python scripts/bump_version.py 0.8.0")
        sys.exit(1)
    
    bump_version(sys.argv[1])