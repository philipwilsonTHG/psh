# Architecture and Codebase Comments

*Updated 2026-02-07 after architectural cleanup (v0.118.0).*

## Strengths

- **Clear layering** between lexer, parser, AST, expansion, and executor, with explicit orchestration in `psh/shell.py`.
- **Visitor-based execution** gives a clean dispatch point and keeps control-flow logic isolated (`psh/executor/core.py`, `psh/visitor/base.py`, `psh/executor/control_flow.py`).
- **Parser strategy/registry** keeps room for multiple parser implementations without leaking details (`psh/parser/parser_registry.py`).
- **Single expansion pipeline via Word AST** — all argument expansion now flows through `_expand_word()` using structural per-part quote context. No more dual string/AST paths or `\x00` markers in argument expansion. This is the cleanest part of the architecture after the v0.114–v0.117 work.
- **First-class token adjacency** — `adjacent_to_previous` on Token eliminates position arithmetic for composite detection, assignments, and operator parsing.
- **Golden behavioral test suite** — 149 parametrized tests in `tests/behavioral/` plus cross-component regression tests in `tests/integration/parsing/test_potential_bugs.py` catch seam bugs that unit tests miss.
- **Comprehensive test coverage** — 2,932 tests (2,882 passing + 50 subshell/phase tests), 93.1% POSIX compliance, 72.7% bash compatibility.

## Risks / Technical Debt

- **Two lexer architectures coexist.** The `ModularLexer` with recognizers is the active tokenization engine, but `StateHandlers` (legacy state-machine mixin) remains as a utility class. The risk is maintenance confusion — fixes or features added to one architecture may not propagate to the other. The state-machine code should be on a deprecation track.

- **`\x00` markers remain in non-argument contexts.** While removed from the argument expansion pipeline, `\x00` is still used in:
  - `expand_string_variables()` (heredocs, here strings, control flow) — 2 insertion points in `lexer/helpers.py` and `lexer/pure_helpers.py`, 2 consumption points in `variable.py`
  - `extglob.py` — 5 references for literal character handling in glob patterns

  These are lower risk since they're in well-contained subsystems, but the pattern should eventually be replaced with structural representations in those contexts too.

- **Parser AST representation of some parameter expansions is lossy.** The parser's `ParameterExpansion` node doesn't perfectly represent all operators: `${var/#pat/repl}` is stored as `parameter='var/', operator='#'` instead of `operator='/#'`; `${var:0:-1}` is stored as `parameter='var:0', operator=':-'` instead of a substring operation. `expand_parameter_direct()` includes workarounds for these, and a string-based fallback for the ambiguous cases. These are parser-level issues that could be fixed at the `WordBuilder` layer.

- **Parser combinator is a secondary path.** The combinator parser (`psh/parser/combinators/`) was updated to always build Word AST nodes, but it receives less testing attention than the recursive descent parser. If it's intended as an educational reference only, this is fine. If it's meant for production use, it needs the same level of coverage.

## Opportunities

1. **Converge on one lexer pipeline.** Deprecate and remove the `StateHandlers` state-machine code. The `ModularLexer` with recognizers is the active path and is well-tested. This would reduce the lexer surface area and eliminate divergence risk.

2. ~~**Direct parameter expansion evaluation.**~~ **Done in v0.118.0.** `ExpansionEvaluator` now calls `VariableExpander.expand_parameter_direct()` with pre-parsed (operator, var_name, operand) components. The string round-trip through `parse_expansion()` is eliminated for all common operators.

3. **Extend Word AST to `expand_string_variables()`.** The remaining `\x00` markers in heredocs and here strings could be eliminated by threading Word-like structural context through `expand_string_variables()`. This is lower priority since these are well-contained contexts.

4. ~~**Remove the composite processor.**~~ **Done in v0.118.0.** `CompositeTokenProcessor` deleted; `use_composite_processor` parameter removed from Parser.

5. **Formalize the `args`/`arg_types` deprecation path.** `SimpleCommand.args` and `arg_types` are now derived from Word AST for backward compatibility. Over time, consumers (builtins, the `test` command, assignment extraction) should migrate to reading from `command.words` directly, after which `args`/`arg_types` can be removed.

6. **Process substitution and subshell fd management.** The `SIGTTOU` issues and pytest `-s` requirement for subshell tests point to fragility in how child processes inherit file descriptors. This isn't related to expansion but is the most significant remaining infrastructure concern.

7. **Fix parser AST for `/#`, `/%`, and substring operators.** `WordBuilder._parse_parameter_expansion()` misrepresents `${var/#pat/repl}` (stores `parameter='var/'`, `operator='#'`) and `${var:0:-1}` (stores `parameter='var:0'`, `operator=':-'`). `expand_parameter_direct()` works around these, but fixing the parser would eliminate the workarounds and the string-based fallback path.
