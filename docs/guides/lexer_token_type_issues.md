# Lexer Token Type Issues

**Updated v0.190.0**

This document records design-level problems with the lexer's token type
system discovered during combinator parser development.  All four issues
have been fixed.

## Summary

| Issue | Severity | Status | Root Cause |
|-------|----------|--------|------------|
| Operator characters dropped in arithmetic | High | **Fixed (v0.169.0)** | No fallback when operator rejected and literal won't start |
| LBRACKET at command position in case patterns | Medium | **Fixed (v0.190.0)** | `command_position` doesn't distinguish case patterns |
| LBRACE/RBRACE asymmetric tokenization | Low | **Fixed (v0.190.0)** | "followed by delimiter" check not symmetric |
| REDIRECT_ERR hardcoded for fd 2 only | Low | **Fixed (v0.190.0)** | Fixed operator table instead of general fd-redirect |

## 1. Operator Characters Silently Dropped Inside Arithmetic

**Severity: High** — **Fixed in v0.169.0**

Inside `(( ))`, after an `ARITH_EXPANSION` token, operator characters like
`>`, `<`, `>=`, `<=` vanish from the token stream entirely.

### Fix

Made the literal recognizer accept `>`, `<` as word-start characters
when `arithmetic_depth > 0`.

---

## 2. LBRACKET at Command Position Breaks Case Patterns

**Severity: Medium** — **Fixed in v0.190.0**

After `case X in` followed by a newline, `command_position` is `True`.
A case pattern like `[a-z])` on the next line previously got `[` emitted
as `LBRACKET` instead of being collected as a glob word.

### Fix

Added `case_depth`, `case_expecting_in`, and `in_case_pattern` context
fields to `LexerContext`.  The lexer now tracks case statement nesting
and suppresses `LBRACKET` emission when inside a case pattern context.
State transitions:

- `case` → increment `case_depth`, set `case_expecting_in`
- `in` (when expecting) → set `in_case_pattern`
- `)` (in case pattern) → clear `in_case_pattern` (now in command body)
- `;;`, `;&`, `;;&` → set `in_case_pattern` (next item's patterns)
- `esac` → decrement `case_depth`, clear `in_case_pattern`

The combinator parser's `_parse_case_pattern_value()` LBRACKET
reconstruction workaround was removed since `[` is now always `WORD`
in case patterns.

---

## 3. LBRACE/RBRACE Asymmetric Tokenization

**Severity: Low** — **Fixed in v0.190.0**

`{` becomes `LBRACE` only when followed by whitespace (standalone).
`}` previously became `RBRACE` when followed by whitespace, a delimiter,
or EOF.  In brace expansion with non-word content, this created asymmetric
tokens.

### Fix

Changed `}` to use `command_position` instead of the "followed by
delimiter" heuristic.  `}` is now only emitted as `RBRACE` when at
command position (after `;`, newline, `&&`, `||`, etc.) — the
semantically correct check since `}` is a POSIX reserved word recognized
only at command position.

The combinator parser's RBRACE-as-brace-expansion workaround was removed
since `}` at non-command position is now `WORD`.

---

## 4. REDIRECT_ERR Hardcoded for fd 2 Only

**Severity: Low** — **Fixed in v0.190.0**

`2>` and `2>>` had dedicated token types (`REDIRECT_ERR`,
`REDIRECT_ERR_APPEND`) with the fd number baked into the operator string.
Other fd redirects did not.

### Fix

Removed `REDIRECT_ERR` and `REDIRECT_ERR_APPEND` token types entirely.
`2>` now tokenizes as `WORD '2'` + `REDIRECT_OUT '>'`, matching how
`3>`, `4>`, etc. already work.  Both parsers already handle the
WORD-digit + redirect-operator pattern for fd-prefixed redirects.

The `parse_redirects()` method was updated to detect fd-prefixed
redirects (WORD digit + adjacent redirect operator), fixing compound
command trailing redirects (subshells, brace groups, control structures).

Parser workarounds removed:
- `_parse_err_redirect()` method in recursive descent parser
- REDIRECT_ERR/REDIRECT_ERR_APPEND handling block in combinator parser
- Token type entries in TokenGroups.REDIRECTS and redirect operator chains

---

## Common Root Cause (Historical)

All four problems stemmed from the same design tension: the lexer used
**positional and contextual heuristics** to assign token types, but
those heuristics lacked sufficient information.  The fixes enriched the
lexer context with the missing state (case pattern tracking,
command-position-based brace recognition) and removed unnecessary
special-case token types (REDIRECT_ERR).
