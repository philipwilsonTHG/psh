#!/usr/bin/env python3
from psh.state_machine_lexer import StateMachineLexer, TokenType, LexerState

# Test the problematic command
text = 'result=$(($(echo 10) + $(echo 20) * $(echo 2)))'
print(f"Input: {text}")
print(f"Length: {len(text)}")

lexer = StateMachineLexer(text)

# Manually trace through
print("\nTracing tokenization:")
i = 0
while lexer.position < len(text):
    char = lexer.current_char()
    print(f"Pos {lexer.position:2d}: '{char}' State: {lexer.state}")
    
    # Handle one character
    old_pos = lexer.position
    lexer.tokenize()
    
    # Check if we emitted any tokens
    if lexer.tokens:
        for j in range(i, len(lexer.tokens)):
            token = lexer.tokens[j]
            print(f"        EMIT: {token.type} = '{token.value}'")
        i = len(lexer.tokens)
    
    # Prevent infinite loop
    if lexer.position == old_pos and lexer.state == LexerState.NORMAL:
        print("        (advancing manually to prevent loop)")
        lexer.advance()
    
    # Stop after a reasonable number of iterations
    if lexer.position > 100:
        print("        (stopping after 100 positions)")
        break

print(f"\nFinal position: {lexer.position}")
print(f"Final tokens: {len(lexer.tokens)}")
for i, token in enumerate(lexer.tokens):
    print(f"  {i}: {token.type} = '{token.value}'")