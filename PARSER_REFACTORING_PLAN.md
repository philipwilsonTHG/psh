 # Parser Refactoring Plan
 
 This document details a step-by-step plan to refactor the parser (psh/parser.py) based on initial recommendations and a review of the existing source code.
 
 ## Overview
 
 The current parser uses a recursive descent approach to convert token streams into AST nodes while handling various control structures, command lists, pipelines, and composite tokens. The goals of this refactoring are to improve maintainability, clarity, error reporting, and testing by modularizing common patterns and functionality.
 
 ## 1. Evaluate and Map the Current Structure
 
 - **Review existing entry points:** Analyze the main parsing entry point (`parse`) and key methods such as `_parse_top_level_item`, `_parse_control_structure`, `parse_statement`, and `parse_command_list`.
 - **Identify common patterns:** Pinpoint repetitive logic in control structures, token consumption, and error checking.
 
 ## 2. Consolidate Control Structure Handling
 
 - **Extract shared logic:**
   - Create helper functions or an abstract control structure parser (or mixin) for:
     - **Condition Extraction:** Processing conditions in constructs like `if` and `while`.
     - **Body Parsing:** Consuming statement blocks following conditions.
     - **Terminator Verification:** Ensuring proper closure (e.g., `fi`, `done`, `esac`).
 - **Delegate in specific methods:** Refactor methods like `parse_if_statement`, `parse_while_statement`, etc., to delegate shared steps to these new helpers.
 
 ## 3. Enhance Error Reporting and Recovery
 
 - **Standardize error messages:**
   - Improve the `_error` method to include detailed context (current token, position, snippet).
   - Provide informative hints for common syntax issues in `ParseError` messages.
 - **Consider error recovery:** Optionally implement a recovery mode to continue parsing for non-critical errors.
 
 ## 4. Update Type Hints and Documentation
 
 - **Add explicit type hints:** Annotate input parameters and return types for public parser methods (e.g., token lists, AST nodes).
 - **Enhance docstrings:** Describe the syntax covered, expected token inputs, and exceptions raised.
 
 ## 5. Streamline Composite Token Handling
 
 - **Isolate preprocessing:**
   - Encapsulate the logic of `CompositeTokenProcessor` into a dedicated method or utility module.
   - Ensure clear separation between token preprocessing and AST construction.
 
 ## 6. Refactor Parsing of Command Lists and Statements
 
 - **Extract utility functions:**
   - Create helpers for skipping separators/newlines and constructing `CommandList` nodes from statement sequences.
 - **Revisit pipeline parsing:** Factor out common logic for handling operators (`&&`, `||`) and assembling pipelines.
 
 ## 7. Incremental Refactoring and Testing Strategy
 
 - **Implement incrementally:**
   - Begin with non-invasive changes, adding new helper methods and gradually delegating portions of existing methods to them.
   - Commit and run tests after each step to prevent regressions.
 - **Expand test coverage:** Develop or update unit tests to cover new helper functions and verify unchanged external behavior.
 
 ## 8. Documentation and Future Maintenance
 
 - **Update developer docs:** Reflect the new modular structure and control structure handling in the documentation.
 - **Document design decisions:** Record the rationale behind helper methods and the separation of concerns.
 
 ## Timeline & Milestones
 
 - **Milestone 1:** Extract and test helper methods for control structure parsing.
 - **Milestone 2:** Enhance error reporting across parsing routines.
 - **Milestone 3:** Update type hints and API documentation.
 - **Milestone 4:** Encapsulate composite token processing.
 - **Milestone 5:** Perform full regression testing and finalize cleanup.
 
 ## Risks & Considerations
 
 - Ensure that AST structures and public behaviors remain unchanged to avoid breaking shell scripts.
 - Maintain backward compatibility with existing tests.
 - Commit incremental changes with thorough regression testing.
 
 ## Summary
 
 By refactoring the parser as outlined, the code will become more modular, easier to understand, and more robust in terms of error reporting. This lays the foundation for more comprehensive testing and simplifies future enhancements.