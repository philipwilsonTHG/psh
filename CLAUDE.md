# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed for teaching shell internals and compiler/interpreter concepts. It uses a hand-written recursive descent parser for clarity and educational value.

## Current Development Focus

**Latest**: File Descriptor Duplication Fix - v0.49.1
- ✓ **Fixed >&2 redirection parsing**: Parser now correctly handles partial form redirections
  - Fixed parser's `_parse_dup_redirect` to consume the target fd token after `>&`
  - `echo test >&2` now correctly parses as args=['echo', 'test'] with redirect fd=1, dup_fd=2
  - Previously the "2" was incorrectly parsed as an argument
  - IOManager already had correct handling for fd duplication
  - Tests confirmed working: output correctly goes to stderr
  - Known issue: capsys fixture conflicts with shell's fd manipulation in tests

**Previous**: Visitor Pattern Phase 4 - Complete Implementation - v0.49.0
- ✓ **Phase 4 Complete**: Full visitor executor implementation with major fixes
  - Fixed terminal control for foreground processes (emacs no longer immediately stopped)
  - Fixed recursive function execution with proper FunctionReturn exception handling
  - Updated 15+ test files to respect PSH_USE_VISITOR_EXECUTOR environment variable
  - Fixed command substitution to inherit visitor executor flag
  - Fixed tilde expansion in variable assignments
  - Achieved 94.7% test pass rate with visitor executor (63 failures from 1131 tests)
  - Major features verified working: functions, pipelines, control structures
  - Documented architectural limitations:
    - Command substitution output capture (test infrastructure limitation)
    - Builtin redirections (would require forking builtins)
  - Visitor executor remains experimental with --visitor-executor flag
  - Foundation complete for performance optimization and eventual migration

**Previous**: Visitor Pattern Phase 3 - Executor Implementation - v0.47.0
- ✓ **Phase 3 Complete**: ExecutorVisitor implementation for AST execution
  - Created ExecutorVisitor extending ASTVisitor[int] for command execution
  - Implemented execution for all major node types (commands, pipelines, control structures)
  - Proper process management with forking and job control integration
  - Pipeline execution with proper exit status propagation
  - Function definition and execution support
  - Integration with existing managers (ExpansionManager, IOManager, JobManager)
  - Maintains full backward compatibility with existing executor

**Previous**: Visitor Pattern Phase 2 - Enhanced Validation - v0.46.0
- ✓ **Phase 2 Integration**: Enhanced AST validation with comprehensive checks
  - Created EnhancedValidatorVisitor with VariableTracker for scope-aware analysis
  - Implemented undefined variable detection with proper scope handling
  - Added command typo detection with suggestions (grpe → grep, etc.)
  - Implemented quoting analysis to detect word splitting risks
  - Added security vulnerability detection (eval usage, world-writable files, command injection)
  - Created test command quote validation for proper variable handling
  - Added --validate flag for script validation without execution
  - 24 comprehensive tests for enhanced validator functionality
  - Consolidated validation output for entire scripts
  - ValidatorConfig for customizable validation rules
- ✓ Integration with shell via psh --validate script.sh
- ✓ Support for validation in all contexts: scripts, -c commands, stdin
- ✓ Created examples showing validation capabilities
- ✓ All 1107 tests passing with enhanced validation

(... rest of the existing content remains the same ...)

## Memories

- Refer to ARCHITECTURE.llm and keep ARCHITECTURE.llm up to date as we make changes.