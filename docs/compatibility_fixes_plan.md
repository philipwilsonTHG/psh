# PSH Compatibility Fixes Plan

## Overview

This document outlines the architectural changes needed to fix compatibility issues between PSH and Bash, as revealed by the comparison test framework.

## Issues to Address

### 1. Double Semicolon (`;;`) Outside Case Statements

**Problem**: `;;` is always tokenized as `DOUBLE_SEMICOLON`, which is only valid in case statements. The command `echo hello;; echo world` fails because `;;` should be treated as two separate semicolons outside of case contexts.

**Current Behavior**:
- Tokenizer always creates `DOUBLE_SEMICOLON` token for `;;`
- Parser expects commands after semicolons, not `;;`

**Proposed Solution**:
- Add context tracking to the tokenizer to know when we're inside a case statement
- When outside case statements, tokenize `;;` as two separate `SEMICOLON` tokens
- When inside case statements, continue to tokenize as `DOUBLE_SEMICOLON`

**Implementation**:
1. Add `in_case_statement` counter to `Tokenizer` class (similar to `in_double_brackets`)
2. Track case depth: increment on `case`, decrement on `esac`
3. Modify semicolon tokenization logic:
   ```python
   elif char == ';':
       if self.peek_char() == ';' and self.in_case_statement > 0:
           # Inside case statement - check for ;;& or ;;&
           if self.peek_char(2) == '&':
               self.tokens.append(Token(TokenType.AMP_SEMICOLON, ';;&', start_pos))
               self.advance(); self.advance(); self.advance()
           else:
               self.tokens.append(Token(TokenType.DOUBLE_SEMICOLON, ';;', start_pos))
               self.advance(); self.advance()
       elif self.peek_char() == ';' and self.in_case_statement == 0:
           # Outside case statement - treat as two semicolons
           self.tokens.append(Token(TokenType.SEMICOLON, ';', start_pos))
           self.advance()
           # Don't advance again - let next iteration handle the second semicolon
       elif self.peek_char() == '&':
           # ;& is always a case terminator
           self.tokens.append(Token(TokenType.SEMICOLON_AMP, ';&', start_pos))
           self.advance(); self.advance()
       else:
           self.tokens.append(Token(TokenType.SEMICOLON, ';', start_pos))
           self.advance()
   ```

### 2. Single Quote Escape Handling

**Problem**: PSH incorrectly allows backslash escaping within single quotes. In POSIX shells, nothing can be escaped within single quotes - not even another single quote.

**Current Behavior**:
- `read_quoted_string()` handles escape sequences differently for single vs double quotes
- For single quotes, it currently allows escaping the quote character

**Proposed Solution**:
- Remove ALL escape sequence handling within single quotes
- Single quotes should preserve everything literally until the closing quote

**Implementation**:
1. Modify `read_quoted_string()` in tokenizer.py:
   ```python
   def read_quoted_string(self, quote_char: str) -> str:
       self.advance()  # Skip opening quote
       value = ''
       
       # Single quotes: no escape sequences allowed, everything is literal
       if quote_char == "'":
           while self.current_char() and self.current_char() != quote_char:
               value += self.current_char()
               self.advance()
       else:
           # Double quotes: allow escaping of quote char and other special chars
           while self.current_char() and self.current_char() != quote_char:
               if self.current_char() == '\\' and self.peek_char() == quote_char:
                   self.advance()  # Skip backslash
                   value += self.current_char()
                   self.advance()
               else:
                   value += self.current_char()
                   self.advance()
       
       if self.current_char() == quote_char:
           self.advance()  # Skip closing quote
       else:
           raise SyntaxError(f"Unclosed quote at position {self.position}")
       
       return value
   ```

### 3. Adjacent String/Word Concatenation

**Problem**: When two words/strings are adjacent without whitespace (e.g., `'*'.txt`), they should be concatenated into a single argument, but PSH treats them as separate tokens.

**Current Behavior**:
- Tokenizer correctly identifies `'*'` as STRING and `.txt` as WORD
- Parser doesn't concatenate adjacent words/strings

**Proposed Solution**:
- Implement word concatenation in the parser when building command arguments
- Adjacent WORD, STRING, VARIABLE, COMMAND_SUB tokens should be merged

**Implementation**:
1. Modify `parse_word()` in parser.py to handle concatenation:
   ```python
   def parse_word(self):
       """Parse a word, potentially with concatenated parts."""
       parts = []
       
       # Collect all adjacent word-like tokens
       while self.current_token and self.current_token.type in (
           TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
           TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
           TokenType.ARITH_EXPANSION, TokenType.PROCESS_SUB_IN,
           TokenType.PROCESS_SUB_OUT
       ):
           parts.append(self.current_token)
           self.advance()
           
           # Check if next token is also word-like and adjacent
           if (self.current_token and 
               self.current_token.type in word_like_tokens and
               self.is_adjacent(parts[-1], self.current_token)):
               continue
           else:
               break
       
       if len(parts) == 1:
           return Word(parts[0].value, parts[0].type)
       else:
           # Create a composite word
           return CompositeWord(parts)
   ```

2. Add `is_adjacent()` helper to check if tokens are adjacent:
   ```python
   def is_adjacent(self, token1, token2):
       """Check if two tokens are adjacent (no whitespace between)."""
       # This requires tracking token end positions in the tokenizer
       return token1.end_position == token2.position
   ```

3. Update tokenizer to track token end positions:
   ```python
   @dataclass
   class Token:
       type: TokenType
       value: str
       position: int
       end_position: int  # Add this field
       quote_type: Optional[str] = None
   ```

### 4. Alternative Approach: Two-Phase Tokenization

**Alternative Architecture**: Instead of making the tokenizer context-aware, we could use a two-phase approach:

1. **Phase 1**: Basic tokenization (current approach)
2. **Phase 2**: Token transformation based on context

**Benefits**:
- Keeps tokenizer simple and stateless
- Easier to test and debug
- More flexible for future syntax additions

**Implementation**:
1. Create a `TokenTransformer` class:
   ```python
   class TokenTransformer:
       def transform(self, tokens: List[Token]) -> List[Token]:
           """Transform tokens based on context."""
           transformed = []
           in_case = 0
           
           for i, token in enumerate(tokens):
               if token.type == TokenType.CASE:
                   in_case += 1
               elif token.type == TokenType.ESAC:
                   in_case -= 1
               elif token.type == TokenType.DOUBLE_SEMICOLON and in_case == 0:
                   # Split into two semicolons
                   transformed.append(Token(TokenType.SEMICOLON, ';', token.position))
                   transformed.append(Token(TokenType.SEMICOLON, ';', token.position + 1))
                   continue
               
               transformed.append(token)
           
           return transformed
   ```

### 5. Test Infrastructure Improvements

**Problem**: Glob tests fail due to repeated directory creation in the same test run.

**Solution**:
- Modify test setup to use unique temporary directories
- Clean up between test runs
- Use proper test isolation

**Implementation**:
1. Update `run_glob_tests()` in test_basic_commands.py:
   ```python
   def run_glob_tests():
       """Run globbing/wildcard tests."""
       runner = ComparisonTestRunner()
       
       tests = [
           ("ls *.txt | sort", "glob txt files"),
           # ... other tests ...
       ]
       
       print("\nRunning glob tests...")
       for command, test_name in tests:
           # Create fresh setup for each test
           with tempfile.TemporaryDirectory() as temp_dir:
               setup_commands = f"""
               cd {temp_dir}
               mkdir -p test_dir
               cd test_dir
               touch file1.txt file2.txt file3.log
               touch .hidden
               mkdir subdir
               touch subdir/nested.txt
               """
               
               # Run with setup
               full_command = setup_commands + "\n" + command
               result = runner.run_command(full_command, test_name, working_dir=temp_dir)
               # ... rest of test logic ...
   ```

## Testing Strategy

1. **Unit Tests**: Add specific tests for each fix:
   - `test_double_semicolon_outside_case.py`
   - `test_single_quote_literal.py`
   - `test_word_concatenation.py`

2. **Integration Tests**: Ensure fixes don't break existing functionality:
   - Run full test suite after each change
   - Add new comparison tests for edge cases

3. **Regression Tests**: Create tests that specifically check for these issues:
   ```python
   def test_compatibility_fixes():
       """Test all compatibility fixes."""
       tests = [
           ("echo hello;; echo world", "double semicolon as two commands"),
           ("echo 'can\\'t escape'", "no escape in single quotes"),
           ("echo '*'.txt", "adjacent string concatenation"),
           ("echo a'b'c\"d\"e", "complex concatenation"),
       ]
   ```

## Implementation Order

1. **Phase 1**: Fix single quote escaping (simplest, most isolated change)
2. **Phase 2**: Implement word concatenation (medium complexity)
3. **Phase 3**: Fix double semicolon handling (most complex, requires context tracking)
4. **Phase 4**: Fix test infrastructure issues

## Backwards Compatibility

These changes should not break existing valid PSH scripts:
- Single quote fix makes PSH more restrictive (correct behavior)
- Word concatenation adds missing functionality
- Double semicolon fix only affects invalid syntax outside case statements

## Timeline Estimate

- Single quote fix: 1 hour
- Word concatenation: 2-3 hours
- Double semicolon fix: 2-3 hours
- Test infrastructure: 1 hour
- Testing and validation: 2 hours

**Total: 8-10 hours of development time**