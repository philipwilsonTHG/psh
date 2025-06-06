#!/usr/bin/env python3
"""
Proof of concept for select statement behavior.
This demonstrates how the select builtin would work in PSH.
"""

import sys


def display_menu(items):
    """Display numbered menu to stderr."""
    if not items:
        return
    
    # Calculate width for alignment
    max_num_width = len(str(len(items)))
    
    # Print menu items
    for i, item in enumerate(items, 1):
        print(f"{i:>{max_num_width}}) {item}", file=sys.stderr)


def read_selection(ps3="#? "):
    """Read user selection with PS3 prompt."""
    print(ps3, end='', file=sys.stderr)
    sys.stderr.flush()
    
    try:
        return input().strip()
    except EOFError:
        return None


def process_selection(user_input, items):
    """Process selection and return (selected_item, reply)."""
    if user_input is None:
        return None, None  # EOF
    
    if not user_input:
        return "", user_input  # Empty input
    
    try:
        selection = int(user_input)
        if 1 <= selection <= len(items):
            return items[selection - 1], user_input
        else:
            return "", user_input  # Invalid number
    except ValueError:
        return "", user_input  # Not a number


def select_demo(variable_name, items, ps3="#? "):
    """Simulate select statement behavior."""
    print(f"\n=== Simulating: select {variable_name} in {' '.join(items)}; do ... done ===\n")
    
    while True:
        # Display menu
        display_menu(items)
        
        # Read input
        user_input = read_selection(ps3)
        
        if user_input is None:
            # EOF (Ctrl+D)
            print("\nEOF received, breaking loop", file=sys.stderr)
            break
        
        # Process selection
        selected, reply = process_selection(user_input, items)
        
        # In real implementation, these would be shell variables
        print(f"\n[Setting {variable_name}='{selected}']")
        print(f"[Setting REPLY='{reply}']")
        
        # Simulate executing loop body
        if selected:
            print(f"Loop body: You selected '{selected}'")
        else:
            print(f"Loop body: Invalid selection (REPLY={reply})")
        
        # For demo, break after one iteration
        # In real select, it would continue until explicit break
        if selected:
            print("[Breaking loop]")
            break
        else:
            print("[Continuing loop due to invalid selection]\n")


def main():
    """Run select demonstrations."""
    print("Select Statement Behavior Demonstration")
    print("=" * 40)
    
    # Demo 1: Basic select
    print("\nDemo 1: Basic select with fruits")
    items = ["apple", "banana", "cherry", "quit"]
    select_demo("fruit", items)
    
    # Demo 2: Custom PS3
    print("\n\nDemo 2: Custom PS3 prompt")
    items = ["red", "green", "blue"]
    select_demo("color", items, ps3="Pick a color: ")
    
    # Demo 3: Files
    print("\n\nDemo 3: File selection")
    items = ["file1.txt", "file2.txt", "backup.tar.gz", "None of the above"]
    select_demo("file", items, ps3="Select file: ")
    
    print("\n\nKey behaviors demonstrated:")
    print("1. Menu displayed to stderr with numbered items")
    print("2. PS3 prompt shown on stderr")
    print("3. User input sets both the variable and REPLY")
    print("4. Invalid input sets variable to empty but preserves REPLY")
    print("5. Loop continues until explicit break (or EOF)")


if __name__ == "__main__":
    main()