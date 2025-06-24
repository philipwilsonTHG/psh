 # Expansion Refactoring Plan
 
 This document details a plan to refactor the expansion subsystem (psh/expansion/manager.py and related expander modules) based on initial recommendations and code review.
 
 ## Overview
 
 The current ExpansionManager coordinates multiple expansion types (tilde, variable, command substitution, arithmetic, globbing, etc.) by iterating over command arguments and applying conditional transformations. The goal is to modularize each expansion step, clearly separate concerns (such as debug logging from core logic), and create an explicit transformation pipeline that is easier to understand, test, and extend.
 
 ## 1. Establish a Clear Expansion Pipeline Architecture
 
 - **Define an explicit transformation chain:**
   - Create a chain of responsibility or pipeline that follows the required expansion order (e.g., tilde → variable → command substitution → arithmetic → word splitting → glob → quote removal).
   - Each step in the pipeline will be implemented as an independent helper function or method.
 
 ## 2. Isolate Individual Expansion Steps
 
 - **Tilde Expansion:**
   - Retain the existing TildeExpander, but expose a simple interface (e.g., `expand(arg: str) -> str`).
 
 - **Variable Expansion:**
   - Refactor the VariableExpander API to allow processing of both full tokens and embedded variables within composite strings.
   - Consider splitting complex cases (e.g., array vs. regular variables) into helper functions.
 
 - **Command Substitution & Arithmetic Expansion:**
   - Separate command substitution (using `$(…)` or backticks) and arithmetic expansion (`$((…))`) into dedicated helper functions within their respective expander classes.
 
 - **Glob Expansion:**
   - Refactor the GlobExpander to provide a pure function: accept a string argument and return either a sorted list of matches or the original argument if no matches occur.
 
 - **Word Splitting and Quote Removal:**
   - Isolate word splitting (based on IFS) and any remaining quote removal into dedicated functions instead of inline code.
 
 ## 3. Centralize Debug Logging and Error Reporting
 
 - **Unified Logging:**
   - Replace scattered debug print statements with calls to a centralized logging helper (e.g., `self._log_debug(message)`).
   - The helper should check a debug flag (like `self.state.options.get("debug-expansion-detail")`) and output consistent, formatted messages.
 
 - **Consistent Error Handling:**
   - Each transformation step should produce consistent error messages and handle errors uniformly.
 
 ## 4. Create a Modular Transformation Pipeline
 
 - **Refactor the Main Loop:**
   - Break the main `expand_arguments` method into a clearly defined sequence of steps. For each command argument, sequentially call:
     1. `process_process_substitution(arg)` – Handle process substitutions.
     2. `process_quoted_string(arg, type, quote)` – Decide applicable expansions based on quoting.
     3. `process_variable_expansion(arg)` – Handle variable substitutions, including embedded variables.
     4. `process_command_substitution(arg)` – Execute command substitution and insert output.
     5. `process_arithmetic_expansion(arg)` – Evaluate arithmetic expressions and substitute results.
     6. `process_tilde_expansion(arg)` – Expand tildes for unquoted words.
     7. `process_glob_expansion(arg)` – Apply pathname expansion via globbing.
     8. `process_word_splitting(arg)` – Split the resulting string into multiple words if needed.
   - Each function should accept and return either a string or a list of strings, using function composition to form the pipeline.
 
 ## 5. Improve Testing and Documentation
 
 - **Unit Tests:**
   - Write tests for each individual expansion step, covering edge cases such as empty outputs, unmatched quotes, and invalid variable names.
 
 - **Documentation:**
   - Update developer documentation to describe the expansion pipeline, the order of operations, and the API of each helper function.
 
 - **Integration Tests:**
   - Confirm that the complete expansion behavior for complex command arguments remains consistent with POSIX standards and previous behavior.
 
 ## 6. Incremental Refactoring Strategy
 
 - **Step-by-Step Isolation:**
   - Start by refactoring a single expansion step (for example, tilde expansion) to use the new helper interface.
   - Test thoroughly, then progressively refactor variable expansion, command substitution, arithmetic expansion, etc.
 
 - **Preserve Compatibility:**
   - Maintain the overall external behavior and data flow, ensuring that side effects (such as process substitutions) are preserved.
 
 - **Refactor Main Loop Gradually:**
   - Gradually update the `expand_arguments` loop to delegate each transformation to the corresponding helper functions.
 
 ## 7. Risks and Considerations
 
 - **Order Preservation:**
   - Ensure that the refactoring maintains the exact expansion order to avoid regressions in command argument transformations.
 
 - **Backward Compatibility:**
   - Avoid changing the public API of the expansion subsystem in a way that would break integration tests or scripts.
 
 - **Performance Considerations:**
   - Ensure that the added function calls do not adversely affect performance.
 
 ## Summary
 
 This plan aims to:
 - Modularize each type of expansion by isolating functionality into independent helper functions.
 - Implement a clear, ordered transformation pipeline mirroring the POSIX expansion order.
 - Centralize debug logging and error reporting to improve maintainability.
 - Establish comprehensive testing to ensure the behavior remains consistent.
 
 By following this incremental refactoring strategy, the expansion subsystem will become more maintainable, extensible, and testable, positioning it well for future enhancements.