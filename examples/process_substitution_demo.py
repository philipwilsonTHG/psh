#!/usr/bin/env python3
"""
Proof of concept for process substitution in Python.
Demonstrates the core mechanism that psh would use.
"""

import os
import sys
import time

def demo_process_substitution():
    """Demonstrate how process substitution works at the OS level."""
    
    print("=== Process Substitution Proof of Concept ===\n")
    
    # Create a pipe for process substitution
    read_fd, write_fd = os.pipe()
    
    # Fork a child process (this would be the <(...) command)
    pid = os.fork()
    
    if pid == 0:  # Child process
        # Close read end
        os.close(read_fd)
        
        # Redirect stdout to write end of pipe
        os.dup2(write_fd, 1)
        os.close(write_fd)
        
        # Execute a command that produces output
        print("Hello from process substitution!")
        print("This is line 2")
        print("This is line 3")
        
        # Exit child
        sys.exit(0)
    
    else:  # Parent process
        # Close write end
        os.close(write_fd)
        
        # Create a path that represents this file descriptor
        # On Linux/macOS, /dev/fd/N is a special file that represents fd N
        fd_path = f"/dev/fd/{read_fd}"
        
        print(f"Parent: Created process substitution at {fd_path}")
        print(f"Parent: This path represents file descriptor {read_fd}")
        print()
        
        # Now we can use this path like a regular file!
        # This simulates what would happen with: cat <(echo "Hello...")
        print("Parent: Reading from process substitution using cat:")
        os.system(f"cat {fd_path}")
        
        # Clean up
        os.close(read_fd)
        os.waitpid(pid, 0)
        
    print("\n=== Demo Complete ===")

def demo_multiple_substitutions():
    """Demonstrate multiple process substitutions."""
    
    print("\n=== Multiple Process Substitutions ===\n")
    
    # Create two pipes for two process substitutions
    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    
    # First child: <(seq 1 3)
    pid1 = os.fork()
    if pid1 == 0:
        os.close(r1)
        os.close(r2)
        os.close(w2)
        os.dup2(w1, 1)
        os.close(w1)
        
        for i in range(1, 4):
            print(i)
        sys.exit(0)
    
    # Second child: <(seq 4 6)
    pid2 = os.fork()
    if pid2 == 0:
        os.close(r1)
        os.close(w1)
        os.close(r2)
        os.dup2(w2, 1)
        os.close(w2)
        
        for i in range(4, 7):
            print(i)
        sys.exit(0)
    
    # Parent
    os.close(w1)
    os.close(w2)
    
    fd1_path = f"/dev/fd/{r1}"
    fd2_path = f"/dev/fd/{r2}"
    
    print(f"Parent: Created two process substitutions:")
    print(f"  - {fd1_path} (fd {r1})")
    print(f"  - {fd2_path} (fd {r2})")
    print()
    
    # This simulates: paste <(seq 1 3) <(seq 4 6)
    print("Parent: Running paste with both substitutions:")
    os.system(f"paste {fd1_path} {fd2_path}")
    
    # Clean up
    os.close(r1)
    os.close(r2)
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)

def demo_output_substitution():
    """Demonstrate output process substitution >(...))."""
    
    print("\n=== Output Process Substitution ===\n")
    
    # Create pipe for >(grep ERROR)
    read_fd, write_fd = os.pipe()
    
    pid = os.fork()
    if pid == 0:  # Child: grep ERROR
        os.close(write_fd)
        os.dup2(read_fd, 0)  # stdin from pipe
        os.close(read_fd)
        
        # Simple grep ERROR simulation
        for line in sys.stdin:
            if 'ERROR' in line:
                print(f"FOUND: {line.strip()}")
        
        sys.exit(0)
    
    # Parent
    os.close(read_fd)
    
    fd_path = f"/dev/fd/{write_fd}"
    print(f"Parent: Created output substitution at {fd_path}")
    print(f"Parent: Writing test data...")
    print()
    
    # Write to the substitution
    with os.fdopen(write_fd, 'w') as f:
        f.write("INFO: Starting application\n")
        f.write("ERROR: Connection failed\n")
        f.write("DEBUG: Retrying...\n")
        f.write("ERROR: Timeout occurred\n")
        f.write("INFO: Shutting down\n")
    
    # Wait for child to process
    os.waitpid(pid, 0)

if __name__ == "__main__":
    # Check if /dev/fd is available
    if not os.path.exists("/dev/fd"):
        print("ERROR: /dev/fd not available on this system")
        print("Process substitution requires /dev/fd support")
        sys.exit(1)
    
    demo_process_substitution()
    demo_multiple_substitutions()
    demo_output_substitution()