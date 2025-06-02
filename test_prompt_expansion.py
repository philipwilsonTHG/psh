#!/usr/bin/env python3
"""Test prompt expansion functionality."""

import sys
from pathlib import Path

# Add psh to path
sys.path.insert(0, str(Path(__file__).parent))

from psh.prompt import PromptExpander
from psh.shell import Shell
import os
import socket
import pwd
from unittest.mock import patch

def test_prompt_expansion():
    """Test various prompt escape sequences."""
    shell = Shell()
    expander = PromptExpander(shell)
    
    # Test basic escapes
    tests = [
        ("\\s", "psh"),
        ("\\\\", "\\"),
        ("\\n", "\n"),
        ("\\r", "\r"),
        ("\\a", "\a"),
        ("\\e", "\033"),
        ("\\$", "$" if os.geteuid() != 0 else "#"),
        ("\\[", "\001"),
        ("\\]", "\002"),
    ]
    
    print("Testing basic escape sequences:")
    for prompt, expected in tests:
        result = expander.expand_prompt(prompt)
        status = "✓" if result == expected else "✗"
        print(f"{status} {prompt} -> {repr(result)} (expected {repr(expected)})")
    
    # Test complex prompts
    print("\nTesting complex prompts:")
    
    # Basic prompt
    basic = expander.expand_prompt("\\u@\\h:\\w\\$ ")
    print(f"Basic prompt: {repr(basic)}")
    
    # Colored prompt
    colored = expander.expand_prompt("\\[\\e[32m\\]\\u@\\h\\[\\e[0m\\]:\\w\\$ ")
    print(f"Colored prompt: {repr(colored)}")
    
    # Two-line prompt
    two_line = expander.expand_prompt("\\[\\e[33m\\]┌─[\\u@\\h:\\w]\\[\\e[0m\\]\\n\\[\\e[33m\\]└─\\$\\[\\e[0m\\] ")
    print(f"Two-line prompt: {repr(two_line)}")
    
    # Prompt with time
    time_prompt = expander.expand_prompt("[\\t] \\u@\\h:\\w\\$ ")
    print(f"Prompt with time: {repr(time_prompt)}")

if __name__ == "__main__":
    test_prompt_expansion()