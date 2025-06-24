 # Lexer Refactoring Plan
 
 This document details a step-by-step plan to refactor the lexer (psh/state_machine_lexer.py) based on the initial recommendations.
 
 ## 1. Introduce Enhanced Position Tracking and Error Reporting
 
 - **Add line and column tracking:**
   - Augment the lexer state with line and column attributes.
   - Update the `advance` method (and any related helper methods) to increment these values appropriately.
 
 - **Improve error reporting:**
   - Create a helper method (e.g., `_error(message: str)`) that includes current line, column, and a snippet of the input in error messages.
 
 ## 2. Extract Context-Specific Helper Methods to Simplify State Transitions
 
 - **Quoted sections:**
   - Implement `_consume_single_quote` to process content until the closing single quote is encountered.
   - Implement `_consume_double_quote` to manage double-quoted strings, handling escapes (using `DOUBLE_QUOTE_ESCAPES`) and variable interpolations.
   - Optionally, implement `_consume_backtick` for handling backtick command substitutions.
 
 - **Unquoted words:**
   - Create `_consume_word` to process unquoted words, looking for word terminators and embedded variable markers.
 
 ## 3. Refactor Variable and Expansion Parsing
 
 - **Separate variable parsing branches:**
   - Create `_parse_simple_variable` for ordinary variables (including special one-character variables).
   - Create `_parse_braced_variable` for handling constructs like `${...}`.
   - Create `_parse_command_substitution` for command substitution constructs (e.g., `$(` or backticks).
   - Create `_parse_arithmetic_expansion` for parsing arithmetic expansions (`$((...))`).
 
 - **Position management:**
   - Ensure that each helper updates position indices correctly and marks the boundaries of the produced token parts.
 
 ## 4. Consider Unicode Support and Identifier Validation
 
 - **Enhanced identifier rules:**
   - Replace fixed sets (e.g., `string.ascii_letters`) with more flexible methods (like `str.isalpha()` or regex with `re.UNICODE`) to support Unicode characters.
   - Validate identifiers using more robust methods (e.g., `str.isidentifier()`).
 
 ## 5. Modularize Error Handling
 
 - **Consistent error messages:**
   - Standardize error reporting across helper methods with consistent messages including context (line, column, snippet).
 
 ## 6. Update Unit Tests and Documentation
 
 - **Unit tests:**
   - Introduce new tests covering each new helper (for quoted strings, variable expansions, Unicode identifiers, etc.).
 
 - **Documentation:**
   - Update inline comments and developer documentation to reflect the new modular structure and state transitions.
 
 ## 7. Gradual Refactoring Strategy
 
 - **Incremental changes:**
   - Start by implementing the new helper methods and update parts of the existing methods to delegate to these helpers.
   - Commit and test iteratively to ensure no regression in behavior.
 
 - **Debug support:**
   - Optionally, add debug logging within the new helper functions to trace state transitions during development.
 
 ## Summary
 
 The refactoring plan aims to:
 - Improve clarity by isolating different lexing contexts
 - Enhance error reporting and debugging capabilities
 - Support Unicode identifiers with more robust validation
 - Facilitate future maintenance and extension of lexer functionality