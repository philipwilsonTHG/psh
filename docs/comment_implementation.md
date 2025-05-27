# Comment Implementation Strategy for psh

## Bash Comment Behavior

The `#` character starts a comment when it appears at the beginning of a word. Everything from `#` to the end of the line is ignored.

### When # starts a comment:
- At the beginning of a line: `# comment`
- After whitespace: `echo hello # comment`
- After operators: `echo foo; # comment`
- After pipes: `ls | grep foo # comment`
- After redirects: `echo test > file # comment`

### When # does NOT start a comment:
- Inside a word: `file#name` (# is literal)
- Inside quotes: `"test # not comment"` or `'test # not comment'`
- When escaped: `\#` (# is literal)
- In parameter expansion: `${var#pattern}` (special meaning)

## Implementation Strategy

### Option 1: Handle in Tokenizer (Recommended)
Modify the tokenizer to recognize and skip comments:

```python
def tokenize(input_string):
    # When we encounter #:
    # 1. Check if we're in quotes - if yes, treat as literal
    # 2. Check if we're at word boundary - if no, treat as literal  
    # 3. Otherwise, skip everything until end of line
```

**Pros:**
- Clean separation of concerns
- Parser never sees comments
- Similar to how we handle quotes

**Cons:**
- Need to track word boundaries in tokenizer

### Option 2: Handle in Parser
Add comment handling to the parser:

```python
def parse_command():
    # After parsing each word, check if it starts with #
    # If yes, stop parsing and ignore rest of line
```

**Pros:**
- Parser already understands word boundaries
- Easier to implement

**Cons:**
- Mixes tokenization and parsing concerns
- Comments would appear in token stream

### Option 3: Preprocess Before Tokenization
Strip comments before tokenizing:

```python
def strip_comments(line):
    # Scan line and remove comments
    # Must handle quotes and escapes correctly
```

**Pros:**
- Keeps tokenizer simple
- Clear separation

**Cons:**
- Duplicate quote/escape handling logic
- Another pass over the input

## Recommended Approach

Implement in the tokenizer (Option 1) because:
1. Tokenizer already handles quotes and escapes
2. Comments are lexical, not syntactic
3. Keeps parser simple
4. Most shells handle comments during lexical analysis

## Test Cases

```bash
# Full line comment
echo test # end of line comment
echo file#name  # outputs: file#name
echo "test # not a comment"  # outputs: test # not a comment
echo test \# not comment  # outputs: test # not comment
VAR=value#not-comment  # VAR contains "value#not-comment"
VAR=value # comment  # VAR contains "value"
echo ${VAR#pattern}  # parameter expansion (future feature)
```