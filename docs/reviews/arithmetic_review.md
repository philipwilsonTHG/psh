# Code Review: `psh/arithmetic.py`

**Date:** 2026-02-17
**Reviewer:** Claude Opus 4.6
**Reviewed version:** 0.187.4
**Fixed in:** 0.188.0 (commit 83132f3), 0.189.0

---

## CRITICAL — Fixed in v0.188.0

### 1. ~~Modulo uses wrong semantics for negative numbers~~ (was line 777)

`left % right` used Python's floored modulo (sign matches divisor), but bash/C uses truncated remainder (sign matches dividend).

```
$((-7 % 2))  →  psh: 1,  bash: -1
$((7 % -2))  →  psh: -1, bash: 1
```

**Resolution:** Replaced `left % right` with `left - int(left / right) * right`. Also fixed `%=` compound assignment. Verified against bash.

### 2. ~~Bitwise NOT uses 32-bit mask, bash uses 64-bit~~ (was lines 734–738)

`~operand & 0xFFFFFFFF` masked to 32 bits. Bash uses 64-bit signed integers.

```
$((~0xFFFFFFFF))  →  psh: 0,  bash: -4294967296
```

**Resolution:** Changed to `0xFFFFFFFFFFFFFFFF` mask with `0x8000000000000000` sign detection.

### 3. ~~`ArithmeticError` shadows the Python builtin~~ (was line 860)

psh defined `class ArithmeticError(Exception)` which was a *different class* from Python's builtin `ArithmeticError`. Callers that caught bare `ArithmeticError` without importing from `psh.arithmetic` (e.g., `psh/executor/core.py`, `psh/executor/control_flow.py`) caught the **builtin**, not psh's. Arithmetic errors produced "unexpected error" messages instead of clean messages.

**Resolution:** Renamed to `ShellArithmeticError` inheriting from the builtin `ArithmeticError`. Old name kept as alias for backwards compatibility. All callers now correctly catch shell arithmetic errors.

---

## HIGH — Fixed in v0.188.0

### 4. ~~No bounds on exponentiation or left-shift~~ (was lines 779, 802–803)

`left ** right` and `left << right` had no limits. Expressions like `$((2 ** 100000))` or `$((1 << 100000))` consumed unbounded memory/CPU. Bash rejects negative exponents and wraps shifts at 64 bits.

**Resolution:** Negative exponents raise an error (matching bash). Exponents > 63 are rejected. Shift amounts wrap modulo 64 (matching bash/C), and left-shift results are wrapped to signed 64-bit via `_to_signed64()`. Verified: `$((1 << 64))` now returns `1` (matching bash).

### 5. ~~No recursion depth limit in parser~~ (was lines 463–681)

Deeply nested parentheses (e.g., 1000 levels) caused `RecursionError` which wasn't caught by `evaluate_arithmetic`.

**Resolution:** `evaluate_arithmetic` now catches `RecursionError` (and `ValueError`, `OverflowError`, `MemoryError`) and wraps them in `ShellArithmeticError` with a clean message.

### 6. ~~Invalid octal silently falls back to decimal~~ (was lines 164–168)

`$((09))` should be an error (9 is not a valid octal digit), but psh fell back to decimal and returned `9`. Bash errors: "value too great for base."

**Resolution:** Now raises `SyntaxError` with a message matching bash's format.

---

## MEDIUM — Fixed in v0.189.0

### 7. ~~`evaluate_arithmetic` doesn't catch all exception types~~ (was line 883)

Only caught `SyntaxError` and `ArithmeticError`. `ValueError`, `RecursionError`, and `OverflowError` could propagate uncaught.

**Resolution:** Fixed as part of issue #5 above (v0.188.0).

### 8. ~~Arithmetic doesn't wrap at 64-bit like bash~~ (was lines 763–805)

Python has arbitrary-precision integers. General arithmetic results (addition, multiplication, etc.) were not wrapped to 64-bit signed range.

**Resolution:** All arithmetic operators (`+`, `-`, `*`, `/`, `%`, `**`, bitwise, compound assignments) now wrap results via `_to_signed64()`. Verified: `$((9223372036854775807 + 1))` returns `-9223372036854775808` (matching bash).

### 9. ~~Missing bitwise assignment operators~~ (was lines 42–48)

Bash supports `<<=`, `>>=`, `&=`, `|=`, `^=` but psh only had `+=`, `-=`, `*=`, `/=`, `%=`.

**Resolution:** Added 5 new token types, tokenizer rules (including 3-char `<<=`/`>>=`), parser recognition, and evaluator cases. All verified against bash.

### 10. ~~Base range limited to 2–36, bash supports 2–64~~ (was line 117)

Bash supports bases 2–64 with digits `0-9`, `a-z`, `A-Z`, `@`, `_`. psh rejected bases > 36.

**Resolution:** Extended to base 64. For bases <= 36, letters are case-insensitive. For bases > 36, lowercase = 10–35, uppercase = 36–61, `@` = 62, `_` = 63 (matching bash).

### 11. ~~No recursive variable resolution~~ (was lines 690–704)

In bash, if `a=b` and `b=42`, then `$((a))` evaluates to 42 via recursive resolution. psh returned 0.

**Resolution:** `get_variable()` now resolves identifier chains recursively with cycle detection. Multi-hop chains (e.g., `a→b→c→42`) work correctly.

---

## LOW — Open

### 12. `evaluate` can implicitly return `None` (lines 713–857)

The `isinstance` chain in `evaluate()` has no fallback `return` for the `UnaryOpNode` and `BinaryOpNode` branches if `node.op` doesn't match any case. While current token types cover all cases, this is fragile.

**Fix:** Add `else: raise ValueError(...)` at the end of each op-matching chain.

### 13. Integer division uses float intermediary (line 773)

`int(left / right)` first computes float division then truncates. For very large integers (> 2^53), this loses precision due to float representation limits.

**Fix:** Implement integer truncation directly: `abs(left) // abs(right) * (1 if (left >= 0) == (right >= 0) else -1)`.

### 14. String concatenation in tokenizer loops (lines 109–111, 150–153, 176–179)

`num_str += self.current_char()` is O(n²) for large inputs due to string immutability. Minor for typical arithmetic expressions but technically quadratic.

**Fix:** Use list append + `''.join()`.
