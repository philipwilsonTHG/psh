# Brace Expansion Architecture Proposal

## Overview

This document proposes an architecture for implementing brace expansion (`{a,b,c}`, `{1..10}`) in psh, following bash semantics while maintaining the educational clarity of the codebase.

## Key Design Considerations

### 1. Expansion Order
Brace expansion occurs **first** in bash's expansion order, before:
- Parameter expansion ($var)
- Command substitution $(...)
- Arithmetic expansion $((...))
- Pathname expansion (globbing)

This means brace expansion is a **purely textual** operation that happens early in processing.

### 2. Current psh Architecture
Currently, psh performs expansions during the execution phase:
- Tokenizer creates tokens for words, variables, etc.
- Parser builds AST preserving expansion markers
- Executor expands variables, command substitutions, globs, etc.

### 3. Architectural Challenge
Brace expansion needs to happen **before** tokenization completes because:
- `echo {a,b,c}` should tokenize as three separate WORD tokens: "echo", "a", "b", "c"
- `file{1..3}.txt` should become three tokens: "file1.txt", "file2.txt", "file3.txt"

## Proposed Architecture: Pre-Tokenization Expansion

### Recommendation: Expand Braces Before Main Tokenization

I recommend implementing brace expansion as a **pre-processing step** that occurs before the main tokenizer runs. This matches bash's behavior and maintains clean separation of concerns.

### Implementation Strategy:

## 1. New Module: brace_expansion.py
```python
# psh/brace_expansion.py
from typing import List, Tuple, Optional
import re

class BraceExpander:
    """Expands brace expressions in command lines before tokenization."""
    
    def expand_line(self, line: str) -> str:
        """Expand all brace expressions in a command line."""
        # Handle quoted sections specially - don't expand inside quotes
        segments = self._split_respecting_quotes(line)
        expanded_segments = []
        
        for segment, in_quotes in segments:
            if in_quotes:
                expanded_segments.append(segment)
            else:
                # Expand braces in unquoted segment
                expanded = self._expand_braces(segment)
                expanded_segments.append(' '.join(expanded))
        
        return ''.join(expanded_segments)
    
    def _expand_braces(self, text: str) -> List[str]:
        """Expand all brace expressions in text, returning list of results."""
        # Find and expand brace expressions iteratively
        results = [text]
        
        while True:
            new_results = []
            expanded_any = False
            
            for item in results:
                expanded = self._expand_one_brace(item)
                if len(expanded) > 1 or expanded[0] != item:
                    expanded_any = True
                new_results.extend(expanded)
            
            results = new_results
            if not expanded_any:
                break
        
        return results
    
    def _expand_one_brace(self, text: str) -> List[str]:
        """Expand the first brace expression found in text."""
        # Find a complete brace expression
        brace_match = self._find_brace_expression(text)
        if not brace_match:
            return [text]
        
        start, end, brace_content = brace_match
        prefix = text[:start]
        suffix = text[end:]
        
        # Determine brace type and expand
        if '..' in brace_content:
            # Sequence expansion
            expanded = self._expand_sequence(brace_content)
        else:
            # List expansion
            expanded = self._expand_list(brace_content)
        
        # Combine with prefix/suffix
        return [prefix + item + suffix for item in expanded]
    
    def _expand_sequence(self, content: str) -> List[str]:
        """Expand sequence like 1..10 or a..z"""
        parts = content.split('..')
        if len(parts) == 2:
            start, end = parts
            increment = 1
        elif len(parts) == 3:
            start, end, increment = parts
            try:
                increment = int(increment)
            except ValueError:
                return ['{' + content + '}']  # Invalid sequence
        else:
            return ['{' + content + '}']  # Invalid sequence
        
        # Try numeric sequence
        try:
            start_num = int(start)
            end_num = int(end)
            # Determine padding
            pad_width = max(len(start), len(end)) if start[0] == '0' else 0
            
            if start_num <= end_num:
                values = range(start_num, end_num + 1, increment)
            else:
                values = range(start_num, end_num - 1, -increment)
            
            if pad_width:
                return [str(v).zfill(pad_width) for v in values]
            else:
                return [str(v) for v in values]
        except ValueError:
            pass
        
        # Try character sequence
        if len(start) == 1 and len(end) == 1:
            start_ord = ord(start)
            end_ord = ord(end)
            
            if start_ord <= end_ord:
                return [chr(c) for c in range(start_ord, end_ord + 1)]
            else:
                return [chr(c) for c in range(start_ord, end_ord - 1, -1)]
        
        return ['{' + content + '}']  # Invalid sequence
    
    def _expand_list(self, content: str) -> List[str]:
        """Expand comma-separated list like a,b,c"""
        # Handle nested braces by careful parsing
        items = []
        current = []
        depth = 0
        
        for char in content:
            if char == '{':
                depth += 1
                current.append(char)
            elif char == '}':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                items.append(''.join(current))
                current = []
            else:
                current.append(char)
        
        if current:
            items.append(''.join(current))
        
        # Recursively expand any nested braces in items
        expanded_items = []
        for item in items:
            expanded_items.extend(self._expand_braces(item))
        
        return expanded_items
    
    def _find_brace_expression(self, text: str) -> Optional[Tuple[int, int, str]]:
        """Find the first valid brace expression in text.
        Returns (start_index, end_index, content) or None."""
        depth = 0
        start = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    content = text[start+1:i]
                    # Validate it's a real brace expression
                    if self._is_valid_brace_content(content):
                        return (start, i+1, content)
                    start = -1
        
        return None
    
    def _is_valid_brace_content(self, content: str) -> bool:
        """Check if content represents a valid brace expression."""
        if not content:
            return False
        
        # Check for sequence
        if '..' in content:
            return True
        
        # Check for list (must have comma not inside nested braces)
        depth = 0
        for char in content:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            elif char == ',' and depth == 0:
                return True
        
        return False
    
    def _split_respecting_quotes(self, line: str) -> List[Tuple[str, bool]]:
        """Split line into segments, tracking which are inside quotes."""
        segments = []
        current = []
        in_single_quotes = False
        in_double_quotes = False
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char == "'" and not in_double_quotes:
                if in_single_quotes:
                    # End single quotes
                    current.append(char)
                    segments.append((''.join(current), True))
                    current = []
                    in_single_quotes = False
                else:
                    # Start single quotes
                    if current:
                        segments.append((''.join(current), False))
                        current = []
                    current.append(char)
                    in_single_quotes = True
            elif char == '"' and not in_single_quotes:
                if in_double_quotes:
                    # End double quotes
                    current.append(char)
                    segments.append((''.join(current), True))
                    current = []
                    in_double_quotes = False
                else:
                    # Start double quotes
                    if current:
                        segments.append((''.join(current), False))
                        current = []
                    current.append(char)
                    in_double_quotes = True
            elif char == '\\' and i + 1 < len(line):
                # Handle escape
                current.append(char)
                i += 1
                if i < len(line):
                    current.append(line[i])
            else:
                current.append(char)
            
            i += 1
        
        if current:
            segments.append((''.join(current), 
                           in_single_quotes or in_double_quotes))
        
        return segments
```

## 2. Integration with Tokenizer

```python
# In psh/tokenizer.py

def tokenize(input_string: str) -> List[Token]:
    """Tokenize input string, with brace expansion preprocessing."""
    from .brace_expansion import BraceExpander
    
    # Expand braces first
    expander = BraceExpander()
    expanded_string = expander.expand_line(input_string)
    
    # Then run normal tokenization
    tokenizer = Tokenizer(expanded_string)
    tokenizer.tokenize()
    return tokenizer.tokens
```

## 3. Special Cases and Edge Behaviors

### Escaping and Quoting
```python
# These should NOT expand:
"{a,b,c}"      # Inside quotes
'{a,b,c}'      # Inside quotes  
\{a,b,c\}      # Escaped braces
{hello}        # Single element
{a, b, c}      # Spaces around commas

# These SHOULD expand:
{a,b,c}        # → a b c
pre{A,B}post   # → preApost preBpost
{1..5}         # → 1 2 3 4 5
```

### Memory Safety
Large expansions could consume memory:
```bash
{1..1000000}   # Creates 1 million strings
{a,b}{c,d}{e,f}{g,h}{i,j}  # Exponential expansion
```

We should add limits:
```python
class BraceExpander:
    MAX_EXPANSION_ITEMS = 10000  # Reasonable limit
    
    def _check_expansion_limit(self, items: List[str]) -> None:
        if len(items) > self.MAX_EXPANSION_ITEMS:
            raise BraceExpansionError(
                f"Brace expansion would create {len(items)} items "
                f"(limit: {self.MAX_EXPANSION_ITEMS})"
            )
```

## 4. Testing Strategy

```python
# tests/test_brace_expansion.py

def test_simple_list_expansion():
    """Test basic comma-separated list expansion."""
    expander = BraceExpander()
    assert expander.expand_line("echo {a,b,c}") == "echo a b c"
    assert expander.expand_line("file.{txt,pdf}") == "file.txt file.pdf"

def test_numeric_sequence():
    """Test numeric range expansion."""
    expander = BraceExpander()
    assert expander.expand_line("echo {1..5}") == "echo 1 2 3 4 5"
    assert expander.expand_line("echo {5..1}") == "echo 5 4 3 2 1"
    assert expander.expand_line("echo {01..05}") == "echo 01 02 03 04 05"

def test_character_sequence():
    """Test character range expansion."""
    expander = BraceExpander()
    assert expander.expand_line("echo {a..e}") == "echo a b c d e"
    assert expander.expand_line("echo {Z..X}") == "echo Z Y X"

def test_nested_expansion():
    """Test nested brace expansion."""
    expander = BraceExpander()
    assert expander.expand_line("{a,b{1,2}}") == "a b1 b2"
    assert expander.expand_line("{{A,B},{1,2}}") == "A B 1 2"

def test_no_expansion_cases():
    """Test cases where braces should NOT expand."""
    expander = BraceExpander()
    assert expander.expand_line('"{a,b,c}"') == '"{a,b,c}"'
    assert expander.expand_line("'{a,b,c}'") == "'{a,b,c}'"
    assert expander.expand_line("{single}") == "{single}"
    assert expander.expand_line("{a, b, c}") == "{a, b, c}"

def test_integration_with_shell():
    """Test brace expansion in full shell commands."""
    shell = Shell()
    # Test file creation
    shell.run_command("touch test{1..3}.txt")
    # Should create test1.txt, test2.txt, test3.txt
    
    # Test with other expansions
    shell.run_command("x=5")
    output = shell.run_command("echo {1..3} $x")
    assert output == "1 2 3 5"  # Brace expansion happens first
```

## 5. Alternative Approach: Post-Tokenization Expansion

While not recommended, an alternative would be to expand braces after tokenization but before parsing. This would require:

1. Tokenizer creates special `BRACE_EXPR` tokens
2. A post-processing step expands these tokens into multiple WORD tokens
3. Parser receives the expanded token stream

**Disadvantages:**
- More complex token stream manipulation
- Harder to handle cases like `pre{a,b}post` which is a single token
- Doesn't match bash's actual implementation

## Implementation Phases

### Phase 1: Basic List Expansion ✅ (Completed v0.21.0)
- Simple comma-separated lists: `{a,b,c}` ✅
- With preamble/postscript: `file{1,2,3}.txt` ✅
- Nested lists: `{a,b{1,2}}` ✅
- Empty elements: `{a,,c}` ✅
- Complex nesting: `{a,b}{c,d}{e,f}` ✅
- Memory limits and safety checks ✅

### Phase 2: Sequence Expansion ✅ (Completed v0.22.0)
- Numeric sequences: `{1..10}`, `{10..1}` ✅
- Zero-padded sequences: `{01..10}` ✅
- Character sequences: `{a..z}`, `{Z..A}` ✅
- Increment sequences: `{1..10..2}` ✅
- Special cross-zero padding behavior ✅
- Negative number sequences with proper padding ✅

### Phase 3: Advanced Features (Future)
- Additional edge cases and optimizations as needed

## Conclusion

The pre-tokenization approach provides:
- **Correct bash semantics**: Expansion happens first
- **Clean implementation**: Single-purpose module
- **Educational value**: Clear separation of concerns
- **Testability**: Can test brace expansion in isolation

This design maintains psh's educational mission while providing full bash compatibility for brace expansion.