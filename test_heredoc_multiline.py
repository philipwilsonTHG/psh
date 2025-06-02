#!/usr/bin/env python3
"""Test heredoc handling in multi-line interactive mode."""

import subprocess
import time

def test_heredoc_interactive():
    """Test heredoc in interactive mode."""
    
    # Test 1: Basic heredoc
    print("Test 1: Basic heredoc")
    proc = subprocess.Popen(
        ['python3', '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send heredoc command line by line
    input_lines = [
        "cat <<EOF",
        "First line",
        "Second line",
        "EOF",
        "exit"
    ]
    
    # Join with newlines
    input_text = '\n'.join(input_lines) + '\n'
    
    stdout, stderr = proc.communicate(input=input_text)
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    
    # Check output contains our text
    assert "First line" in stdout
    assert "Second line" in stdout
    print("✓ Basic heredoc test passed\n")
    
    # Test 2: Heredoc with indentation (<<-)
    print("Test 2: Heredoc with tab stripping (<<-)")
    proc = subprocess.Popen(
        ['python3', '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    input_lines = [
        "cat <<-EOF",
        "\tIndented line",
        "\t\tDouble indented",
        "EOF",
        "exit"
    ]
    
    input_text = '\n'.join(input_lines) + '\n'
    stdout, stderr = proc.communicate(input=input_text)
    
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    
    # The <<- should strip leading tabs
    assert "Indented line" in stdout
    assert "Double indented" in stdout
    # Should not contain the tabs
    assert "\tIndented" not in stdout
    print("✓ Tab-stripping heredoc test passed\n")
    
    # Test 3: Heredoc in a function
    print("Test 3: Heredoc in function definition")
    proc = subprocess.Popen(
        ['python3', '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    input_lines = [
        "test_func() {",
        "  cat <<EOF",
        "Inside function",
        "EOF",
        "}",
        "test_func",
        "exit"
    ]
    
    input_text = '\n'.join(input_lines) + '\n'
    stdout, stderr = proc.communicate(input=input_text)
    
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    
    assert "Inside function" in stdout
    print("✓ Heredoc in function test passed\n")
    
    # Test 4: Nested heredoc in control structure
    print("Test 4: Heredoc in if statement")
    proc = subprocess.Popen(
        ['python3', '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    input_lines = [
        "if true; then",
        "  cat <<END",
        "Condition is true",
        "END",
        "fi",
        "exit"
    ]
    
    input_text = '\n'.join(input_lines) + '\n'
    stdout, stderr = proc.communicate(input=input_text)
    
    print("STDOUT:")
    print(stdout)
    print("STDERR:")
    print(stderr)
    
    assert "Condition is true" in stdout
    print("✓ Heredoc in if statement test passed\n")

if __name__ == '__main__':
    test_heredoc_interactive()