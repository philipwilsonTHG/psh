#!/usr/bin/env python3
"""Demo script to show tab completion functionality."""

import os
import tempfile
import shutil
from pathlib import Path
from tab_completion import CompletionEngine

def demo():
    """Demonstrate tab completion features."""
    print("Tab Completion Demo")
    print("=" * 50)
    
    # Create demo directory structure
    demo_dir = tempfile.mkdtemp(prefix="psh_demo_")
    os.chdir(demo_dir)
    
    # Create test files and directories
    os.makedirs("documents/reports")
    os.makedirs("downloads")
    os.makedirs("projects/python")
    os.makedirs("projects/rust")
    
    Path("README.md").touch()
    Path("notes.txt").touch()
    Path("script.py").touch()
    Path(".hidden_config").touch()
    Path("file with spaces.txt").touch()
    Path("documents/report1.pdf").touch()
    Path("documents/report2.pdf").touch()
    Path("documents/reports/quarterly.xlsx").touch()
    Path("projects/python/main.py").touch()
    Path("projects/rust/Cargo.toml").touch()
    
    print(f"Created demo directory: {demo_dir}")
    print("\nDirectory structure:")
    os.system("find . -type f -o -type d | sort")
    
    # Demonstrate completions
    engine = CompletionEngine()
    
    print("\n" + "=" * 50)
    print("Tab Completion Examples:")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("do", "Complete 'do' - should match 'documents/' and 'downloads/'"),
        ("doc", "Complete 'doc' - should uniquely match 'documents/'"),
        ("s", "Complete 's' - should match 'script.py'"),
        ("file", "Complete 'file' - should match 'file with spaces.txt'"),
        (".", "Complete '.' - should show hidden files"),
        ("documents/", "Complete 'documents/' - should show files in documents"),
        ("documents/rep", "Complete 'documents/rep' - should match report files"),
        ("projects/p", "Complete 'projects/p' - should match 'projects/python/'"),
        ("~/", "Complete '~/' - should show home directory contents"),
    ]
    
    for partial, description in test_cases:
        print(f"\n{description}")
        print(f"Input: '{partial}'")
        completions = engine._get_path_completions(partial)
        if completions:
            print(f"Completions: {completions}")
            common = engine.find_common_prefix(completions)
            print(f"Common prefix: '{common}'")
        else:
            print("No completions found")
    
    # Test escaping
    print("\n" + "=" * 50)
    print("Path Escaping Examples:")
    print("=" * 50)
    
    escape_tests = [
        "file with spaces.txt",
        "file&name.txt",
        "file$var.txt",
        "file(1).txt",
        "file'quotes'.txt",
    ]
    
    for path in escape_tests:
        escaped = engine.escape_path(path)
        print(f"Original: '{path}'")
        print(f"Escaped:  '{escaped}'")
        print()
    
    # Clean up
    os.chdir("/")
    shutil.rmtree(demo_dir)
    print(f"Cleaned up demo directory")

if __name__ == "__main__":
    demo()