#!/usr/bin/env python3
# Let's manually trace what should happen

text = 'result=$(($(echo 10) + $(echo 20) * $(echo 2)))'
print(f"Input: {text}")
print(f"Correct tokenization should be:")
print("  WORD: 'result=$(($(echo 10) + $(echo 20) * $(echo 2)))'")
print("  EOF")
print()

# The issue is that we're getting:
print("What we're getting:")
print("  WORD: 'result=$(($(echo 10) + $(echo 20) * $(echo 2))'  # Missing last )")
print("  RPAREN: ')'")
print("  EOF")
print()

# Let's trace character by character
print("Character trace:")
pos = 0
paren_depth = 0
arith_depth = 0

for i, char in enumerate(text):
    if i > 0 and text[i-1:i+1] == '$(':
        if i+1 < len(text) and text[i+1] == '(':
            print(f"{i:2d}: '(' - Start of arithmetic expansion")
            arith_depth += 1
        else:
            print(f"{i:2d}: '(' - Start of command substitution")
    elif i > 0 and text[i-1] == ')' and char == ')' and arith_depth > 0:
        print(f"{i:2d}: ')' - End of arithmetic expansion")
        arith_depth -= 1
    else:
        print(f"{i:2d}: '{char}'", end="")
        if char == '(':
            paren_depth += 1
            print(f" - paren_depth={paren_depth}")
        elif char == ')':
            paren_depth -= 1
            print(f" - paren_depth={paren_depth}")
        else:
            print()