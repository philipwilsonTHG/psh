# Code Review: `psh/arithmetic.py`

**Date:** 2026-02-17
**Reviewer:** Claude Opus 4.6
**Version:** 0.187.4

---

## CRITICAL

### 1. Modulo uses wrong semantics for negative numbers (line 777)

`left % right` uses Python's floored modulo (sign matches divisor), but bash/C uses truncated remainder (sign matches dividend).

```
$((-7 % 2))  →  psh: 1,  bash: -1
$((7 % -2))  →  psh: -1, bash: 1
```

**Fix:** Replace `left % right` with `int(math.fmod(left, right))` or `left - int(left / right) * right`.

### 2. Bitwise NOT uses 32-bit mask, bash uses 64-bit (lines 734–738)

`~operand & 0xFFFFFFFF` masks to 32 bits. Bash uses 64-bit signed integers.

```
$((~0xFFFFFFFF))  →  psh: 0,  bash: -4294967296
```

**Fix:** Use `0xFFFFFFFFFFFFFFFF` mask and `0x8000000000000000` for sign detection, or just use Python's native `~operand` since Python's arbitrary-precision `~` matches 64-bit for values in the 64-bit range.

### 3. `ArithmeticError` shadows the Python builtin (line 860)

psh defines `class ArithmeticError(Exception)` which is a *different class* from Python's builtin `ArithmeticError`. Callers that catch bare `ArithmeticError` without importing from `psh.arithmetic` (e.g., `psh/executor/core.py:274`, `psh/executor/control_flow.py:242,257,277`) catch the **builtin**, not psh's. This means errors like division-by-zero from `evaluate_arithmetic` escape the handler.

Arithmetic errors produce "unexpected error" messages instead of clean error messages.

**Fix:** Either rename the class (e.g., `ShellArithmeticError`), or make it inherit from the builtin `ArithmeticError` instead of `Exception`.

---

## HIGH

### 4. No bounds on exponentiation or left-shift (lines 779, 802–803)

`left ** right` and `left << right` have no limits. Expressions like `$((2 ** 100000))` or `$((1 << 100000))` consume unbounded memory/CPU. Bash rejects negative exponents and wraps shifts at 64 bits.

**Fix:** Reject negative exponents (`right < 0`), clamp shifts to 0–63, and optionally cap exponent size.

### 5. No recursion depth limit in parser (lines 463–681)

Deeply nested parentheses (e.g., 1000 levels) cause `RecursionError` which isn't caught by `evaluate_arithmetic`.

**Fix:** Add `RecursionError` to the `except` clause in `evaluate_arithmetic`, or add an explicit depth counter.

### 6. Invalid octal silently falls back to decimal (lines 164–168)

`$((09))` should be an error (9 is not a valid octal digit), but psh falls back to decimal and returns `9`. Bash errors: "value too great for base."

**Fix:** Raise `SyntaxError` instead of falling back to `read_decimal()`.

---

## MEDIUM

### 7. `evaluate_arithmetic` doesn't catch all exception types (line 883)

Only catches `SyntaxError` and `ArithmeticError`. `ValueError` (from `int()` overflow), `RecursionError`, and `OverflowError` can propagate uncaught.

**Fix:** Broaden the except clause to include `(ValueError, RecursionError, OverflowError)`.

### 8. Arithmetic doesn't wrap at 64-bit like bash (lines 763–805)

Python has arbitrary-precision integers. `$((1 << 64))` gives `18446744073709551616` in psh but `1` in bash (wraps at 64-bit).

**Fix:** Apply 64-bit signed wrapping to all arithmetic results if bash compatibility is desired.

### 9. Missing bitwise assignment operators (lines 42–48)

Bash supports `<<=`, `>>=`, `&=`, `|=`, `^=` but psh only has `+=`, `-=`, `*=`, `/=`, `%=`. These expressions produce syntax errors in psh.

**Fix:** Add the missing token types, tokenizer cases, and evaluator cases.

### 10. Base range limited to 2–36, bash supports 2–64 (line 117)

Bash supports bases 2–64 with digits `0-9`, `a-z`, `A-Z`, `@`, `_`. psh rejects bases > 36.

```
$((64#_))  →  psh: error,  bash: 63
```

**Fix:** Extend `read_number()` to accept bases up to 64 and handle `@` (62) and `_` (63) digits.

### 11. No recursive variable resolution (lines 690–704)

In bash, if `a=b` and `b=42`, then `$((a))` evaluates to 42 via recursive resolution. psh returns 0 because it sees `a`'s value as `"b"` (non-numeric → 0).

**Fix:** Implement recursive resolution in `get_variable()`: if the value is a valid identifier, look it up again (with a depth limit to prevent cycles).

---

## LOW

### 12. `evaluate` can implicitly return `None` (lines 713–857)

The `isinstance` chain in `evaluate()` has no fallback `return` for the `UnaryOpNode` and `BinaryOpNode` branches if `node.op` doesn't match any case. While current token types cover all cases, this is fragile.

**Fix:** Add `else: raise ValueError(...)` at the end of each op-matching chain.

### 13. Integer division uses float intermediary (line 773)

`int(left / right)` first computes float division then truncates. For very large integers (> 2^53), this loses precision due to float representation limits.

**Fix:** Implement integer truncation directly: `abs(left) // abs(right) * (1 if (left >= 0) == (right >= 0) else -1)`.

### 14. String concatenation in tokenizer loops (lines 109–111, 150–153, 176–179)

`num_str += self.current_char()` is O(n²) for large inputs due to string immutability. Minor for typical arithmetic expressions but technically quadratic.

**Fix:** Use list append + `''.join()`.
