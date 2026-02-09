# PSH Test Reorganization Plan

> [!IMPORTANT]
> Historical migration analysis. For current contributor and CI test commands, use `docs/testing_source_of_truth.md`.

## Executive Summary

This document outlines a comprehensive plan to reorganize and improve the PSH test suite, moving from 1800+ ad-hoc tests to a well-structured, maintainable, and comprehensive testing framework. The plan includes parallel execution of old and new test suites during the transition period.

## Goals

1. **Comprehensive Coverage**: Ensure all PSH features, behaviors, and edge cases are tested
2. **Clear Organization**: Create a logical, maintainable test structure
3. **Interactive Testing**: Properly test terminal interactions, job control, and signals
4. **Documentation**: Make tests self-documenting and educational
5. **Performance**: Enable fast test execution for rapid development
6. **Reproducibility**: Ensure tests are deterministic and environment-independent

## Current State Assessment

### Existing Test Assets
- **1800+ pytest tests** in `/tests/` directory
- **54 conformance tests** comparing PSH to bash behavior
- **Mixed test types**: unit, integration, and system tests intermingled
- **Limited interactive testing**: Most tests use StringIO mocks
- **No performance tests**: No benchmarking or stress testing

### Key Problems
1. **Organization**: Tests grouped by when they were written, not by what they test
2. **Duplication**: Similar functionality tested in multiple places
3. **Gaps**: Interactive features, error paths, and edge cases under-tested
4. **Maintenance**: Hard to find relevant tests when changing code
5. **Speed**: Full test suite takes too long for rapid development

## Proposed Test Architecture

### Directory Structure
```
tests/
├── unit/                    # Pure unit tests (isolated components)
│   ├── lexer/              # Tokenization tests
│   ├── parser/             # AST generation tests
│   ├── expansion/          # Variable/command expansion tests
│   ├── builtins/           # Individual builtin tests
│   └── utils/              # Utility function tests
│
├── integration/            # Component interaction tests
│   ├── pipeline/           # Pipeline execution tests
│   ├── redirection/        # I/O redirection tests
│   ├── control_flow/       # if/while/for/case tests
│   ├── functions/          # Function definition/execution
│   └── job_control/        # Background jobs, fg/bg
│
├── system/                 # Full system behavior tests
│   ├── scripts/            # Script execution tests
│   ├── interactive/        # REPL behavior tests
│   ├── signals/            # Signal handling tests
│   └── process/            # Process management tests
│
├── conformance/            # Bash compatibility tests
│   ├── posix/              # POSIX compliance tests
│   ├── bash/               # Bash-specific compatibility
│   └── differences/        # Documented PSH differences
│
├── performance/            # Performance and stress tests
│   ├── benchmarks/         # Speed benchmarks
│   ├── memory/             # Memory usage tests
│   └── stress/             # Large input/load tests
│
├── fixtures/               # Shared test fixtures and utilities
├── resources/              # Test data files
└── helpers/                # Test helper functions
```

### Test Categories

#### 1. Unit Tests
- **Scope**: Single component/function in isolation
- **Dependencies**: Mocked/stubbed
- **Speed**: <10ms per test
- **Example**: Testing lexer tokenization of specific operators

#### 2. Integration Tests
- **Scope**: Multiple components working together
- **Dependencies**: Real components, filesystem mocked
- **Speed**: <100ms per test
- **Example**: Testing pipeline with builtin and external commands

#### 3. System Tests
- **Scope**: Full shell behavior end-to-end
- **Dependencies**: Real filesystem, subprocesses
- **Speed**: <1s per test
- **Example**: Testing script execution with signals

#### 4. Interactive Tests
- **Scope**: Terminal interaction, line editing, completion
- **Dependencies**: PTY (pseudo-terminal)
- **Framework**: pexpect or similar
- **Example**: Testing Ctrl-C during multiline input

#### 5. Conformance Tests
- **Scope**: Bash compatibility verification
- **Method**: Run same commands in PSH and bash, compare output
- **Categories**: Must match, documented differences, PSH extensions

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1-2)

#### 1.1 Create Test Framework Foundation
```python
# tests/framework/base.py
class PSHTestCase:
    """Base class for all PSH tests with common utilities"""
    
    def create_shell(self, **options):
        """Create a configured shell instance"""
        
    def run_command(self, cmd, input=None):
        """Run command and return structured result"""
        
    def assert_output(self, result, stdout=None, stderr=None, exit_code=0):
        """Assert command output matches expectations"""
```

#### 1.2 Interactive Test Framework
```python
# tests/framework/interactive.py
import pexpect

class InteractivePSHTest:
    """Base class for interactive shell tests"""
    
    def spawn_shell(self, env=None):
        """Spawn interactive PSH process"""
        
    def send_line(self, line):
        """Send line to shell with proper line ending"""
        
    def expect_prompt(self, timeout=1):
        """Wait for shell prompt"""
        
    def send_interrupt(self):
        """Send Ctrl-C to shell"""
```

#### 1.3 Test Utilities
- **Fixtures**: Common test scenarios (shells, files, directories)
- **Assertions**: Custom assertions for shell-specific checks
- **Helpers**: Command builders, output parsers, etc.

### Phase 2: Test Migration Strategy (Week 3-4)

#### 2.1 Test Inventory Script
```python
#!/usr/bin/env python3
"""Analyze existing tests and categorize them"""

def analyze_test_file(filepath):
    """Extract test metadata from file"""
    # Parse test file
    # Identify what components are tested
    # Detect test type (unit/integration/system)
    # Find duplicate tests
    # Generate migration recommendations
```

#### 2.2 Migration Priorities
1. **Core Components First**: Lexer, parser, expansion
2. **High-Risk Areas**: Job control, signals, interactive features
3. **Complex Features**: Arrays, functions, arithmetic
4. **Conformance**: Bash compatibility tests

#### 2.3 Parallel Execution
```yaml
# .github/workflows/tests.yml
- name: Run Legacy Tests
  run: pytest tests/
  
- name: Run New Tests  
  run: pytest tests/

- name: Coverage Report
  run: |
    coverage run -m pytest tests/
    coverage report
```

### Phase 3: Core Component Tests (Week 5-6)

#### 3.1 Lexer Tests
```python
# tests/unit/lexer/test_tokenization.py
class TestBasicTokenization(PSHTestCase):
    """Test basic token recognition"""
    
    def test_simple_command(self):
        tokens = tokenize("echo hello")
        assert_tokens(tokens, [
            Token(WORD, "echo"),
            Token(WORD, "hello")
        ])
    
    def test_operators(self):
        # Test each operator in isolation
        # Test operator combinations
        # Test operator context sensitivity
```

#### 3.2 Parser Tests
```python
# tests/unit/parser/test_ast_generation.py
class TestASTGeneration(PSHTestCase):
    """Test AST generation from tokens"""
    
    def test_simple_command_ast(self):
        ast = parse(tokenize("echo hello"))
        assert_ast_structure(ast, 
            CommandList([
                Pipeline([
                    SimpleCommand(["echo", "hello"])
                ])
            ])
        )
```

#### 3.3 Expansion Tests
- Variable expansion with all special cases
- Command substitution including nested
- Arithmetic expansion with all operators
- Brace expansion with all patterns
- Parameter expansion with all modifiers

### Phase 4: Interactive Testing (Week 7-8)

#### 4.1 Terminal Interaction Tests
```python
# tests/system/interactive/test_line_editing.py
class TestLineEditing(InteractivePSHTest):
    """Test interactive line editing features"""
    
    def test_cursor_movement(self):
        shell = self.spawn_shell()
        shell.send("echo hello")
        shell.send("\x01")  # Ctrl-A (beginning of line)
        shell.send("test ")
        shell.send("\n")
        shell.expect("test echo hello")
    
    def test_history_navigation(self):
        shell = self.spawn_shell()
        shell.send_line("echo first")
        shell.send_line("echo second")
        shell.send("\x10")  # Ctrl-P (previous history)
        shell.send("\n")
        shell.expect("echo second")
```

#### 4.2 Signal Handling Tests
```python
# tests/system/signals/test_signal_handling.py
class TestSignalHandling(InteractivePSHTest):
    """Test signal handling in various contexts"""
    
    def test_interrupt_during_sleep(self):
        shell = self.spawn_shell()
        shell.send_line("sleep 10")
        time.sleep(0.5)
        shell.send_interrupt()
        shell.expect_prompt()
        # Verify sleep was interrupted
    
    def test_sigtstp_job_control(self):
        shell = self.spawn_shell()
        shell.send_line("sleep 100")
        shell.send("\x1a")  # Ctrl-Z (SIGTSTP)
        shell.expect("Stopped")
        shell.send_line("jobs")
        shell.expect("[1].*Stopped.*sleep 100")
```

#### 4.3 Multiline Input Tests
```python
# tests/system/interactive/test_multiline.py
class TestMultilineInput(InteractivePSHTest):
    """Test multiline command input"""
    
    def test_incomplete_quote(self):
        shell = self.spawn_shell()
        shell.send_line('echo "hello')
        shell.expect("> ")  # PS2 prompt
        shell.send_line('world"')
        shell.expect("hello\nworld")
    
    def test_ctrl_c_cancels_multiline(self):
        shell = self.spawn_shell()
        shell.send_line('echo "hello')
        shell.expect("> ")
        shell.send_interrupt()
        shell.expect_prompt()  # Back to PS1
```

### Phase 5: Conformance Testing (Week 9-10)

#### 5.1 Conformance Test Framework
```python
# tests/conformance/framework.py
class ConformanceTest(PSHTestCase):
    """Base class for conformance tests"""
    
    def run_in_both_shells(self, command, env=None):
        """Run command in PSH and bash, return both results"""
        psh_result = self.run_in_psh(command, env)
        bash_result = self.run_in_bash(command, env)
        return psh_result, bash_result
    
    def assert_same_behavior(self, command):
        """Assert PSH and bash produce identical results"""
        psh, bash = self.run_in_both_shells(command)
        assert psh.stdout == bash.stdout
        assert psh.stderr == bash.stderr
        assert psh.exit_code == bash.exit_code
    
    def assert_documented_difference(self, command, difference_id):
        """Assert behavior differs in documented way"""
        # Check that difference is expected and documented
```

#### 5.2 POSIX Compliance Tests
```python
# tests/conformance/posix/test_posix_features.py
class TestPOSIXCompliance(ConformanceTest):
    """Test POSIX-mandated features"""
    
    def test_parameter_expansion(self):
        self.assert_same_behavior('x=hello; echo ${x:-default}')
        self.assert_same_behavior('unset x; echo ${x:-default}')
        self.assert_same_behavior('x=; echo ${x:+set}')
        # ... comprehensive parameter expansion tests
```

### Phase 6: Performance Testing (Week 11)

#### 6.1 Benchmark Framework
```python
# tests/performance/framework.py
class BenchmarkTest(PSHTestCase):
    """Base class for performance tests"""
    
    def measure_time(self, command, iterations=100):
        """Measure average execution time"""
        
    def measure_memory(self, command):
        """Measure peak memory usage"""
        
    def assert_performance(self, command, max_time=None, max_memory=None):
        """Assert performance meets requirements"""
```

#### 6.2 Performance Test Suite
```python
# tests/performance/benchmarks/test_parsing_speed.py
class TestParsingPerformance(BenchmarkTest):
    """Test parsing performance"""
    
    def test_large_script_parsing(self):
        # Generate large script
        script = "\n".join(f"echo line{i}" for i in range(10000))
        
        # Measure parsing time
        avg_time = self.measure_time(f"psh -n -c '{script}'")
        
        # Should parse 10k lines in under 1 second
        self.assert_performance(script, max_time=1.0)
```

### Phase 7: Test Quality Assurance (Week 12)

#### 7.1 Test Coverage Analysis
- Set coverage targets (>90% for core components)
- Identify untested code paths
- Add tests for uncovered areas

#### 7.2 Test Quality Metrics
- **Speed**: Categorize tests by execution time
- **Flakiness**: Identify non-deterministic tests
- **Clarity**: Ensure tests document what they verify
- **Independence**: Verify tests don't depend on order

#### 7.3 Documentation
- Test writing guide
- Naming conventions
- Best practices
- Common patterns

## Testing Tools and Frameworks

### Core Testing Stack
1. **pytest**: Test runner and framework
2. **pexpect**: Interactive process testing
3. **coverage.py**: Code coverage analysis
4. **hypothesis**: Property-based testing for edge cases
5. **pytest-timeout**: Prevent hanging tests
6. **pytest-xdist**: Parallel test execution

### Additional Tools
1. **memray**: Memory profiling for performance tests
2. **pytest-benchmark**: Benchmarking plugin
3. **fakefs**: Filesystem mocking
4. **freezegun**: Time mocking for time-dependent tests

## Success Metrics

1. **Coverage**: >90% code coverage for all components
2. **Organization**: Clear mapping from features to tests
3. **Speed**: Unit tests <5s, integration <30s, full suite <5min
4. **Reliability**: <0.1% flaky tests
5. **Maintainability**: New contributors can easily add tests

## Migration Timeline

- **Weeks 1-2**: Infrastructure setup
- **Weeks 3-4**: Test analysis and migration planning
- **Weeks 5-6**: Core component tests
- **Weeks 7-8**: Interactive testing  
- **Weeks 9-10**: Conformance testing
- **Week 11**: Performance testing
- **Week 12**: Quality assurance and documentation
- **Week 13+**: Ongoing migration of remaining tests

## Risk Mitigation

1. **Parallel Execution**: Keep old tests running during migration
2. **Incremental Migration**: Move tests component by component
3. **Coverage Tracking**: Ensure no regression in coverage
4. **Team Review**: Regular reviews of test quality and completeness

## Next Steps

1. **Approve Plan**: Review and approve this reorganization plan
2. **Create Infrastructure**: Set up new test directory structure
3. **Build Frameworks**: Implement base test classes and utilities
4. **Start Migration**: Begin with highest-priority components
5. **Track Progress**: Weekly progress reports on migration status

## Conclusion

This test reorganization will transform PSH's test suite from an ad-hoc collection into a comprehensive, well-organized testing framework. The investment in proper testing infrastructure will pay dividends in:

- Faster development cycles
- Higher confidence in changes
- Better documentation through tests
- Easier onboarding for contributors
- More reliable software

The parallel execution approach ensures no loss of test coverage during the transition, while the phased migration allows for continuous improvement and learning.
