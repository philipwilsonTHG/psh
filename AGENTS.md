 # AGENTS.md
 
 This document provides guidelines for AI agents working with the PSH (Python Shell) codebase. It is intended for agentic coding assistants (like this one) that help maintain, refactor, and extend PSH. The document explains the agent’s role, capabilities, best practices, and expected workflow when interacting with the project.
 
 ## 1. Overview
 
 The PSH project is built with a clean, component-based architecture featuring a recursive descent parser, a modular lexer package with mixin architecture and Unicode support, an expansion manager, and a visitor-based executor. This architecture supports reliable POSIX compliance with modern Unicode capabilities and offers multiple extension points. AI agents are tasked with understanding this architecture, evaluating design decisions, and applying safe modifications to enhance the project.
 
 ## 2. Agent Role and Capabilities
 
 As an AI coding assistant, an agent is expected to:
 
 - **Understand the Codebase:** Read and analyze core components (e.g., modular lexer package, parser, expansion manager, executor) as documented in ARCHITECTURE.llm.
 - **Collaborate Effectively:** Use guidelines (as outlined in CLAUDE.md and this document) to work harmoniously with human developers.
 - **Apply Incremental Changes:** Make careful, minimal, and reversible patches. Use unit tests and golden-file tests to verify intended behavior.
 - **Use Available Tools:** Operate with features such as file reading, shell command execution, code patch application, and testing integration.
 - **Maintain Clarity and Safety:** Ensure that every change is well-documented and consistent with the project’s design, focusing on root-cause fixes rather than temporary workarounds.
 
 ## 3. Agent Workflow
 
 An AI agent should follow this workflow when addressing tasks:
 
 1. **Analyze:** Review relevant documentation (ARCHITECTURE.llm, CLAUDE.md) and project files to understand the context.
 2. **Plan:** Formulate a detailed plan for proposed changes. Consider modularity, testing, error handling, and adherence to POSIX standards.
 3. **Implement:** Apply changes incrementally using the provided patch tools. Ensure refactoring preserves behavior and test outcomes. For lexer changes, consider the modular package structure, mixin architecture, Unicode compatibility, and POSIX mode requirements.
 4. **Test:** Run unit tests, integration tests, and golden-file comparisons to validate that changes do not introduce regressions.
 5. **Document:** Update design documents (e.g., this file, other relevant markdown files) to reflect modifications or new best practices.
 
 ## 4. Best Practices for Agents
 
 - **Consult Documentation:** Always refer to ARCHITECTURE.llm and CLAUDE.md to ensure compatibility with design principles.
 - **Keep Changes Minimal:** Focus on targeted, small-scale modifications. Avoid unrelated changes to limit risk.
 - **Incrementally Improve:** Break refactoring into manageable steps. Validate each step with tests before proceeding.
 - **Use Clear Communication:** Provide concise explanations for changes. Annotate patches and commit messages with context and rationale.
 - **Prioritize Safety:** When in doubt, ask for clarification or additional instructions. Preserve user data and ensure reversibility.
 
 ## 5. Integration with Testing Framework
 
 - **Regression Detection:** Use the existing pytest framework and golden-file tests to catch regressions.
 - **Compatibility Checks:** Validate that refactored code aligns with expected POSIX behavior and Bash compatibility where applicable. For lexer changes, verify both Unicode and POSIX modes work correctly with the modular package structure.
 - **Detailed Diff Reporting:** When discrepancies arise, provide clear diffs that detail differences between expected and actual behavior.
 
 ## 6. Agent Interaction Guidelines
 
 Agents should:
 
 - **Stay Focused:** Work on the task at hand until it is fully resolved.
 - **Be Transparent:** Make intermediate decisions clear through detailed documentation and comments (keeping inline comments minimal in final patches as per project guidelines).
 - **Maintain User Trust:** Prioritize robustness and clarity, ensuring that users can rely on agentic interventions without confusion.
 
 ## 7. Summary
 
 This document serves as a reference for AI agents engaging with the PSH codebase. It outlines responsibilities, a recommended workflow, best practices, and integration with testing to ensure high-quality contributions. Agents working on lexer improvements should pay special attention to the modular package structure, mixin architecture, Unicode support, POSIX compatibility, and position tracking for error handling. Agents are encouraged to collaborate, maintain high standards of code quality, and support the continuous evolution of the PSH project.