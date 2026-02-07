# Architecture and Codebase Comments

*Updated 2026-02-07 after v0.120.0 — arg_types migration complete.*

## Strengths

- **Clear layering** between lexer, parser, AST, expansion, and executor, with explicit orchestration in `psh/shell.py`.
- **Visitor-based execution** gives a clean dispatch point and keeps control-flow logic isolated (`psh/executor/core.py`, `psh/visitor/base.py`, `psh/executor/control_flow.py`).
- **Parser strategy/registry** keeps room for multiple parser implementations without leaking details (`psh/parser/parser_registry.py`).
- **Single expansion pipeline via Word AST** — all argument expansion now flows through `_expand_word()` using structural per-part quote context. No more dual string/AST paths or `\x00` markers in argument expansion.
- **Word AST is the sole argument metadata representation** — as of v0.120.0, `SimpleCommand.words` (type `List[Word]`) is always present and is the only source of quoting/expansion structure. The legacy `arg_types`/`quote_types` fields have been removed. Word helper properties (`is_quoted`, `is_unquoted_literal`, `is_variable_expansion`, `has_expansion_parts`, `has_unquoted_expansion`, `effective_quote_char`) provide clean semantic queries for all consumers.
- **First-class token adjacency** — `adjacent_to_previous` on Token eliminates position arithmetic for composite detection, assignments, and operator parsing.
- **Golden behavioral test suite** — 149 parametrized tests in `tests/behavioral/` plus cross-component regression tests in `tests/integration/parsing/test_potential_bugs.py` catch seam bugs that unit tests miss.
- **Comprehensive test coverage** — 2,960+ tests, 93.1% POSIX compliance, 72.7% bash compatibility.

## Risks / Technical Debt

- ~~**Two lexer architectures coexist.**~~ **Resolved in v0.119.0.** `StateHandlers` (597 lines) deleted. `ModularLexer` with recognizers is the sole tokenization engine.

- **`\x00` markers remain in non-argument contexts.** While removed from the argument expansion pipeline, `\x00` is still used in:
  - `expand_string_variables()` (heredocs, here strings, control flow) — 2 insertion points in `lexer/helpers.py` and `lexer/pure_helpers.py`, 2 consumption points in `variable.py`
  - `extglob.py` — 5 references for literal character handling in glob patterns

  These are lower risk since they're in well-contained subsystems, but the pattern should eventually be replaced with structural representations in those contexts too.

- ~~**Parser AST representation of some parameter expansions is lossy.**~~ **Resolved in v0.119.0.** `_parse_parameter_expansion()` now uses earliest-position matching with `/#`, `/%`, and `:` operators in the operator list. The workarounds in `expand_parameter_direct()` and the string-based fallback `_evaluate_parameter_via_string()` have been removed.

- **Parser combinator is a secondary path.** The combinator parser (`psh/parser/combinators/`) was updated to always build Word AST nodes, but it receives less testing attention than the recursive descent parser. If it's intended as an educational reference only, this is fine. If it's meant for production use, it needs the same level of coverage.

## Opportunities

1. ~~**Converge on one lexer pipeline.**~~ **Done in v0.119.0.** `StateHandlers` deleted (597 lines). `ModularLexer` with recognizers is the sole lexer.

2. ~~**Direct parameter expansion evaluation.**~~ **Done in v0.118.0.** `ExpansionEvaluator` now calls `VariableExpander.expand_parameter_direct()` with pre-parsed (operator, var_name, operand) components. The string round-trip through `parse_expansion()` is eliminated for all common operators.

3. **Extend Word AST to `expand_string_variables()`.** The remaining `\x00` markers in heredocs and here strings could be eliminated by threading Word-like structural context through `expand_string_variables()`. This is lower priority since these are well-contained contexts.

4. ~~**Remove the composite processor.**~~ **Done in v0.118.0.** `CompositeTokenProcessor` deleted; `use_composite_processor` parameter removed from Parser.

5. ~~**Formalize the `args`/`arg_types` deprecation path.**~~ **Done in v0.120.0.** `arg_types` and `quote_types` fields removed from `SimpleCommand`. `words: List[Word]` is now required (not optional). All consumers migrated to Word helper properties. The `_word_to_arg_type()` bridge method deleted.

6. **Process substitution and subshell fd management.** The `SIGTTOU` issues and pytest `-s` requirement for subshell tests point to fragility in how child processes inherit file descriptors. This isn't related to expansion but is the most significant remaining infrastructure concern.

7. ~~**Fix parser AST for `/#`, `/%`, and substring operators.**~~ **Done in v0.119.0.** `_parse_parameter_expansion()` now uses earliest-position matching with the full operator set. Workarounds and string fallback removed.
