# Parser Architecture Improvement Proposals

This document captures proposed architectural enhancements for the PSH parser,
inspired by patterns from the lexer refactoring phases (ARCHITECTURE.llm).

## 1. Introduce a ParserContext (Phase 1–style)
- Centralize all parse state (token stream, config, error list, heredoc trackers, nesting depth) into a new `ParserContext` class.
- Simplifies sub-parser signatures and makes nested or incremental parsing easier.

## 2. Registration-based sub-parser discovery (Phase 4–style)
- Replace hard-coded dispatch in `main.py` with a registration decorator so each parser module self-registers.
- Makes adding new constructs (e.g. future syntax extensions) pluggable and eliminates manual upkeep of a sub-parser list.

## 3. Pure-function parsing helpers (Phase 2 analogue)
- Extract side-effect-free token checks, lookahead predicates, and AST-node constructors into `parser/pure_helpers.py`.
- Improves unit-testability and documents corner cases independently of the full parser.

## 4. Pluggable error-recovery strategies
- Define an `ErrorRecoveryStrategy` interface and wire a configurable strategy via `ParserConfig`.
- Allows swapping panic-mode skip-to-next-separator recovery vs. minimal logging, or experimenting with grammar-based recovery.

## 5. Streaming/incremental parse API
- Expose a generator-style `parse_stream(ctx)` API for REPL use, yielding one AST node at a time.
- Avoids restarting the entire lexer/parser loop for interactive or IDE integrations.

## 6. Fine-grained module splitting & leaner command parsing
- Further subdivide large modules (e.g. split `commands.py` into `operators.py`, `pipeline_parser.py`, `compound_parser.py`).
- Keeps each file under ~200 lines and scopes reviewers to precise changes.

## 7. Parser profiling & tracing hooks
- Add enter/exit rule hooks (e.g. `ctx.on_enter_rule('if_statement')`) configurable via `ParserConfig.trace_hooks`.
- Enables lightweight performance tracing and aids debugging of complex syntax failures.

---

### Mapping to ARCHITECTURE.llm
| Improvement                           | Analogy / Location in ARCHITECTURE.llm                            |
|---------------------------------------|------------------------------------------------------------------|
| ParserContext                         | LexerContext (Phase 1)【ARCHITECTURE.llm:L207-L216】                |
| Registration-based sub-parsers        | Recognizer registry (Phase 4)【ARCHITECTURE.llm:L253-L262】         |
| Pure-function parsing helpers         | pure_helpers (Phase 2)【ARCHITECTURE.llm:L229-L237】               |
| Error-recovery strategies             | Parser error handling notes【ARCHITECTURE.llm:L153-L159】         |
| Streaming/incremental parse API       | Interactive REPL hints under `interactive/`                       |
| Module splitting & leaner files       | Current parser modules【ARCHITECTURE.llm:L49-L62】                 |
| Profiling/tracing hooks               | Lexer strict/recovery config knobs【ARCHITECTURE.llm:L259-L266】   |
