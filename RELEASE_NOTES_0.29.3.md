# PSH Release Notes - Version 0.29.3

**Release Date**: 2025-04-06

## Overview

This patch release focuses on comprehensive documentation improvements to reflect the current state of PSH after the major architectural refactoring and recent feature additions.

## Documentation Updates

### ARCHITECTURE.md
- Updated to reflect the current component-based architecture
- Added documentation for the state machine lexer implementation
- Documented the scope management system for local variables
- Updated component details with recent additions
- Added sections on recent architectural improvements (v0.28.x and v0.29.x)
- Documented known architectural limitations

### README.md
- Updated current version and recent major features
- Enhanced feature descriptions with latest additions
- Added examples for advanced parameter expansion
- Added examples for enhanced test operators `[[ ]]`
- Updated architecture section to reflect component-based design
- Added comprehensive implementation status section
- Updated project structure diagram with actual directory layout

### TODO.md
- Complete rewrite with consistent formatting
- Clear organization by priority (High/Medium/Low)
- Removed verbose historical entries
- Focused on actionable items and known issues
- Added concise implementation history section
- Improved test suite status documentation

## Summary

Version 0.29.3 brings the project documentation up to date with the current implementation, making it easier for contributors and users to understand PSH's architecture, features, and development status. No code changes were made in this release.

## Installation

```bash
pip install psh==0.29.3
```

## Contributors

- Documentation updates by Claude (AI assistant)

---

For the complete list of changes and previous releases, see the [VERSION_HISTORY](psh/version.py) in the source code.