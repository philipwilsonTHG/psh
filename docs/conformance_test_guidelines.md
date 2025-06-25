# Conformance Test Guidelines for PSH

This document outlines guidelines for building a golden-file based conformance test suite for validating POSIX and Bash features in PSH. The guidelines are as follows:

## 1. Separate Test Structure
  - Create a dedicated directory (e.g., `conformance_tests/` or `golden_tests/`) to store the test cases.
  - Organize tests by mode, with subdirectories for `posix` and `bash` tests.
  - Use consistent naming, such as `test_xyz.input` for inputs and `test_xyz.golden` for expected output files.

## 2. Test Runner and Execution Environment
  - Develop a standalone test runner (in Python or as a shell script) that:
    - Iterates over test cases in the test directories.
    - Executes PSH with the appropriate configuration (POSIX or Bash mode) for each test case.
    - Captures the actual output for later comparison.
  - Ensure the test runner can be executed both locally and in CI/CD environments.

## 3. Golden File Comparison and Management
  - Implement features in the test runner to compare captured output with the corresponding golden file using a diff tool.
  - Support an option (e.g., a `--update-golden` flag) to update golden files when intentional changes occur.
  - Normalize outputs if necessary (e.g., whitespace handling) so that only meaningful differences cause test failures.

## 4. Coverage and Granularity
  - Select a representative set of shell scripts that cover various language constructs, including:
    - Control structures (if, while, for, case, etc.)
    - Arithmetic expressions
    - Command substitution
    - Redirections and pipelines
    - Special edge cases, such as complex Unicode identifiers
  - Incorporate edge-case tests and typical usage scenarios for thorough testing.

## 5. Documentation and Usage Guidelines
  - Provide a README in the test directory explaining:
    - How to add new tests
    - How to run the conformance suite
    - How to update and manage golden files
  - Ensure guidelines are clear for both developers and automated CI systems.

## 6. Integration into CI/CD
  - Configure the test runner as a separate stage in the CI/CD pipeline to catch conformance regressions early.
  - Keep the test runner independent from existing pytest tests to emphasize feature conformance.

These guidelines provide the foundation for creating a robust and maintainable golden-file test suite to ensure that PSH conforms to POSIX and Bash standards.