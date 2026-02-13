# Lexer Token Type Issues

**As of v0.169.0**

This document records design-level problems with the lexer's token type
system discovered during combinator parser development.  Issues 1 and 2
have been fixed; issues 3 and 4 are worked around at the parser level.

## Summary

| Issue | Severity | Status | Root Cause |
|-------|----------|--------|------------|
| Operator characters dropped in arithmetic | High | **Fixed (v0.169.0)** | No fallback when operator rejected and literal won't start |
| LBRACKET at command position in case patterns | Medium | **Worked around (v0.169.0)** | `command_position` doesn't distinguish case patterns |
| LBRACE/RBRACE asymmetric tokenization | Low | Worked around (v0.168.0) | "followed by delimiter" check not symmetric |
| REDIRECT_ERR hardcoded for fd 2 only | Low | Worked around (v0.167.0) | Fixed operator table instead of general fd-redirect |

## 1. Operator Characters Silently Dropped Inside Arithmetic

**Severity: High** — causes 3 test failures, silent data loss in token stream

Inside `(( ))`, after an `ARITH_EXPANSION` token, operator characters like
`>`, `<`, `>=`, `<=` vanish from the token stream entirely.

```
(( 5 > 3 ))            → DOUBLE_LPAREN, WORD '5 > 3 ', DOUBLE_RPAREN       ✓
(( $((5 / 2)) > 1 ))   → DOUBLE_LPAREN, ARITH_EXPANSION, WORD '1 ', DOUBLE_RPAREN  ✗
(( $((5)) >= 1 ))       → DOUBLE_LPAREN, ARITH_EXPANSION, WORD '= 1 ', DOUBLE_RPAREN  ✗
```

In the second example, `>` is completely absent.  In the third, `>=`
loses its `>` and only `=` survives.

### Mechanism

After an `ARITH_EXPANSION` token, `>` needs to **start** a new token.
The recognizers process it in priority order:

1. **Operator recognizer**: correctly rejects `>` as `REDIRECT_OUT`
   because `arithmetic_depth > 0` (`operator.py:305-308`)
2. **Literal recognizer**: does not accept `>` as a word-start character
   — it is an operator character, not a valid literal start
3. **No recognizer claims it** — the character is silently skipped

The simple case `(( 5 > 3 ))` works because `>` appears **mid-word**.
The literal recognizer starts with `5` and `>` is not a word terminator
in arithmetic context (`literal.py:340-348`), so it is collected as part
of `WORD '5 > 3 '`.  The bug only manifests when `>` must start a new
token after a non-word token boundary.

### Affected tests

- `test_arithmetic_in_if_conditions` (×3, same test in 3 files)

### Fix approach

Make the literal recognizer accept `>`, `<` as word-start characters
when `arithmetic_depth > 0`.  Alternatively, add a fallback recognizer
that catches characters not claimed by any other recognizer inside
arithmetic context.

---

## 2. LBRACKET at Command Position Breaks Case Patterns

**Severity: Medium** — causes 3 test failures

After `case X in` followed by a newline, `command_position` is `True`.
A case pattern like `[a-z])` on the next line gets `[` emitted as
`LBRACKET` instead of being collected as a glob word.

```
# Single line — command_position is False after 'in' + word tokens
case x in [a-z]*) echo yes;; esac
  → CASE, WORD 'x', IN, WORD '[a-z]*', RPAREN, ...     ✓

# Multi-line — command_position is True at line start
case x in
    [a-z]*) echo yes;;
esac
  → CASE, WORD 'x', IN, NEWLINE, LBRACKET '[', WORD 'a-z', WORD ']*', RPAREN, ...  ✗
```

### Mechanism

The lexer uses `command_position` to decide whether `[` is an operator
(test command `[ expr ]`) or part of a word (glob pattern).
`command_position` is set to `True` after control keywords, newlines,
semicolons, and pipe operators (`modular_lexer.py:229-266`).

After `case X in` + newline, the newline preserves `command_position=True`.
The `[` on the next line matches the operator recognizer's check
(`operator.py:328`):

```python
if not context.command_position:
    return False  # glob pattern — part of a word
return True  # test command — emit LBRACKET
```

The lexer has no concept of "case pattern context" and cannot distinguish
a test command `[` from a glob character class `[` at command position.

### Affected tests

- `test_case_with_character_classes`
- `test_append_redirection_in_case`
- `test_case_in_loop`

### Fix approach

Add an `in_case_pattern` context flag to the lexer, set after `case X in`
and cleared after `esac`.  When active, suppress `LBRACKET` emission and
let the literal recognizer collect `[...]` as a glob word.
Alternatively, handle this in the case pattern parser by reconstructing
glob patterns from `LBRACKET` + constituent tokens.

---

## 3. LBRACE/RBRACE Asymmetric Tokenization

**Severity: Low** — caused 1 test failure (now worked around)

`{` becomes `LBRACE` only when followed by whitespace (standalone).
`}` becomes `RBRACE` when followed by whitespace, a delimiter, or EOF.
In brace expansion with non-word content, this creates asymmetric tokens:

```
echo {$((1)),$((2)),$((3))}
  → WORD 'echo', WORD '{', ARITH_EXPANSION, ..., ARITH_EXPANSION, RBRACE '}'
```

The opening `{` is `WORD` (followed by `$`, not a delimiter) but the
closing `}` is `RBRACE` (followed by EOF, which counts as a delimiter).

### Mechanism

The operator recognizer (`operator.py:247-256`) checks whether the
character after `{` or `}` is a shell token delimiter:

```python
if candidate in ('{', '}'):
    next_pos = pos + 1
    if next_pos < len(input_text) and not self._is_shell_token_delimiter(input_text[next_pos]):
        continue  # not standalone — skip
```

For `{$((1)),...}`:
- `{` is followed by `$` → not a delimiter → `WORD`
- `}` is followed by EOF → the `next_pos < len(input_text)` check fails,
  so the `continue` is not reached → `RBRACE`

### Current workaround

The combinator parser's simple command argument parser consumes `RBRACE`
tokens when they are adjacent to the previous token
(`adjacent_to_previous=True`), indicating brace expansion context rather
than a standalone brace group closer (`commands.py`).

### Fix approach

Make the operator recognizer treat `}` followed by EOF consistently
with `{` followed by non-delimiter.  If the corresponding `{` was emitted
as `WORD`, `}` should also be `WORD`.  This would require tracking brace
balance or applying a post-tokenization normalisation pass.

---

## 4. REDIRECT_ERR Hardcoded for fd 2 Only

**Severity: Low** — no current test failures (worked around in v0.167.0)

`2>` and `2>>` have dedicated token types (`REDIRECT_ERR`,
`REDIRECT_ERR_APPEND`) with the fd number baked into the operator string.
Other fd redirects do not:

```
echo err 2> file   → REDIRECT_ERR '2>'            (fd embedded in value)
echo err 3> file   → WORD '3', REDIRECT_OUT '>'   (fd is a separate preceding token)
```

### Mechanism

`2>` is a hardcoded 2-character entry in the operator table
(`constants.py:49`).  No other `N>` combination exists in the table.
File descriptor duplication (`2>&1`, `3>&2`) is handled by a separate
dynamic parser (`operator.py:69-174`), but plain fd redirects like `3>`
fall through to the default `WORD` + `REDIRECT_OUT` tokenisation.

### Impact

The parser needs two code paths for fd-prefixed redirects:

1. For `REDIRECT_ERR` / `REDIRECT_ERR_APPEND`: strip the `2` prefix from
   the token value (`'2>'[1:]` → `'>'`) and set `fd=2`
2. For `REDIRECT_OUT` / `REDIRECT_APPEND`: check if the preceding token
   is a numeric `WORD` and use it as the fd number

The combinator parser initially lacked the first path and produced
`Redirect(type='2>', fd=None)` instead of `Redirect(type='>', fd=2)`.
This was fixed in v0.167.0.

### Fix approach

Either generalise the operator table to recognise all `N>` and `N>>`
patterns dynamically (matching the fd duplication parser's approach),
or remove `REDIRECT_ERR` / `REDIRECT_ERR_APPEND` entirely and let `2>`
tokenise as `WORD '2'` + `REDIRECT_OUT '>'` like every other fd redirect.
The latter would simplify the parser at the cost of slightly more complex
redirect assembly.

---

## Common Root Cause

All four problems stem from the same design tension: the lexer uses
**positional and contextual heuristics** to assign token types, but
those heuristics lack sufficient information:

| Problem | Heuristic | Missing context |
|---------|-----------|-----------------|
| Dropped operators in arithmetic | `arithmetic_depth` suppresses operators | No fallback to collect suppressed operators as word chars |
| LBRACKET in case patterns | `command_position` flag | No `in_case_pattern` context |
| Asymmetric braces | "followed by delimiter" check | No brace balance tracking |
| REDIRECT_ERR hardcoding | Fixed operator table for `2>` | General `N>` recognition |

The recursive descent parser compensates for most of these via its own
context flags (`in_arithmetic`, `in_case_pattern`) that suppress or
reinterpret certain token types during parsing.  The combinator parser,
which operates bottom-up without mutable context, is more exposed to
these tokenisation inconsistencies.
