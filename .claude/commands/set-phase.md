You have been put into Set-Phase Mode. This command sets the development phase for the current project, which affects how all other modes operate. Usage: `set-phase [phase]`

AVAILABLE PHASES:

**mvp** - Minimum Viable Product
- Priority: Speed and core functionality
- Include: Thorough debug logs for manual testing, rapid iteration
- Ignore: Tests, documentation, code cleanup, performance optimization
- Focus: Get it working quickly for validation

**production** - Production Ready
- Priority: Quality, security, performance, maintainability  
- Include: Comprehensive tests, clean logs, documentation, security reviews
- Ignore: Debug statements, temporary code, experimental features
- Focus: Robust, scalable, well-documented code

**hotfix** - Emergency Fix
- Priority: Minimal, targeted changes to fix critical issues
- Include: Focused fixes, immediate testing of the specific issue
- Ignore: Refactoring, new features, comprehensive test suites
- Focus: Fix the problem with minimal risk of introducing new issues

**prototype** - Proof of Concept
- Priority: Explore feasibility and approach
- Include: Experimental code, extensive logging, quick iterations
- Ignore: Production standards, comprehensive error handling, scalability
- Focus: Validate concepts and technical approaches

**refactor** - Code Improvement
- Priority: Code quality, maintainability, performance
- Include: Comprehensive testing, documentation updates, clean architecture
- Ignore: New features, rapid delivery timelines
- Focus: Improve existing code without changing functionality

**feature** - New Feature Development
- Priority: Balanced development with quality standards
- Include: Tests for new functionality, relevant documentation
- Ignore: Unrelated refactoring, premature optimization
- Focus: Well-implemented new functionality that integrates cleanly

**CUSTOM PHASES**: You can specify any custom phase name. When doing so, ask the user to define the priorities, what to include, what to ignore, and the focus for that phase.

To perform your role, you must:

1. Identify the specified phase (or ask for custom phase details)
2. Update the CLAUDE.md file with a "CURRENT PHASE" section that includes:
   - Phase name and description
   - Current priorities
   - What to focus on
   - What to ignore or deprioritize
   - Any phase-specific guidelines for other modes

3. Provide a summary of how this phase will affect development approach

YOU ARE PERMITTED TO READ AND UPDATE THE CLAUDE.md FILE.

YOU MUST HAVE EXPLICIT USER APPROVAL TO END THIS MODE