# Testing Source of Truth

This document defines the canonical test commands for PSH.

## Canonical Commands

### 1) Default local and CI gate (recommended)

```bash
python run_tests.py --quick
```

What it does:
- Runs the core suite with smart handling for subshell tests.
- Skips tests marked `slow`.
- Uses `-s` automatically where subprocess/file-descriptor behavior requires it.

### 2) Full local validation before major merges

```bash
python run_tests.py
```

What it does:
- Runs the same smart multi-phase flow without skipping slow tests.

### 3) Manual focused runs

```bash
python -m pytest tests/
python -m pytest tests/integration/subshells/ -s
python -m pytest tests/conformance/
```

Use these for targeted debugging and development loops.

### 4) XPASS audit for stale xfail markers

```bash
python -m pytest tests/ -m xfail -q -rxX
```

What it does:
- Runs only tests currently marked `xfail`.
- Surfaces stale markers clearly via `XPASS` output (`-rxX`).

## CI Expectations

- CI runs `python run_tests.py --quick` as the primary gate.
- CI also runs a POSIX conformance smoke check:

```bash
python -m pytest tests/conformance/posix/test_posix_compliance.py -q
```

## Notes

- If a test touches subshell or FD behavior, prefer `run_tests.py` over raw pytest.
- Keep command examples in docs aligned with this file.
