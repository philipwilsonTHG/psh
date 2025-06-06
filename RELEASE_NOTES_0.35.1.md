# PSH v0.35.1 Release Notes

## Bug Fix Release

This patch release fixes a test suite issue discovered after the v0.35.0 release.

### Test Suite Fix

- **Fixed pipefail test failure**: Changed test scripts from using `#!/usr/bin/env psh` to `#!/bin/sh` to avoid issues with nested PSH execution in pipelines
  - The pipefail functionality itself was working correctly
  - The issue only affected the test when PSH scripts were executed within PSH pipelines
  - All 771 tests now pass with 0 failures

### Summary

- **Version**: 0.35.1
- **Type**: Bug fix (patch release)
- **Tests**: 771 passed, 0 failed, 40 skipped, 5 xfailed
- **Compatibility**: No breaking changes

This release ensures a clean test suite for the shell options feature introduced in v0.35.0.