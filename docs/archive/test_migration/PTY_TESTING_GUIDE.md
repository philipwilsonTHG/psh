# PTY Testing Guide for PSH

> [!IMPORTANT]
> Historical migration analysis. For current contributor and CI test commands, use `docs/testing_source_of_truth.md`.

This document explains the challenges and solutions for testing PSH's interactive features in pseudo-terminal (PTY) environments.

## Overview

PSH provides a full interactive shell experience with features like:
- Line editing with arrow keys
- Command history navigation
- Tab completion
- Control key shortcuts (Ctrl-A, Ctrl-E, etc.)
- Job control (Ctrl-Z, fg/bg)

While these features work correctly when using PSH interactively, testing them in automated PTY environments presents unique challenges.

## The PTY Testing Challenge

### What is a PTY?

A pseudo-terminal (PTY) is a pair of virtual character devices that provide a bidirectional communication channel. Testing tools like `pexpect` use PTYs to interact with programs that expect to be run in a terminal.

### Why PTY Testing is Difficult

1. **Terminal Emulation Complexity**
   - PTYs must emulate terminal behavior including escape sequences, cursor movement, and line discipline
   - Different terminal types (xterm, vt100, etc.) have different capabilities

2. **Echo and Buffering Issues**
   - In PTY mode, characters may be echoed back by the terminal driver
   - This can confuse test expectations when looking for specific output

3. **Timing Sensitivity**
   - Terminal operations are asynchronous
   - Small timing differences can cause tests to fail intermittently

4. **Raw Mode vs Cooked Mode**
   - PSH uses raw mode for line editing (to process each keystroke)
   - PTY testing tools may interfere with terminal mode switching

## Current Testing Approach

### 1. Mock-Based Unit Tests
For core line editor functionality, we use mock-based unit tests that don't require a PTY:
```python
# tests/unit/test_line_editor_unit.py
# Tests LineEditor methods directly without terminal emulation
```

### 2. PTY Integration Tests
For features that require terminal interaction, we have two categories:

#### Working PTY Tests
These features test reliably in PTY mode:
- Basic command execution
- Ctrl-U (clear line)
- Ctrl-K (kill to end)
- Ctrl-W (delete word)
- Tab completion
- Ctrl-D (EOF)

#### Problematic PTY Tests
These features work interactively but not reliably in PTY tests:
- Arrow key navigation (cursor movement)
- History navigation with up/down arrows
- Complex line editing operations
- Ctrl-C interrupt handling

### 3. Alternative Integration Tests
We created `test_interactive_features.py` that verifies functionality without relying on problematic PTY features:
- Tests command execution results rather than keystroke handling
- Verifies features work by checking output
- Avoids timing-sensitive operations

## PTY Test Implementation Details

### The PTY Test Framework

```python
# tests/framework/pty_test_framework.py
class PTYTestFramework:
    """Enhanced framework for PTY-based interactive testing."""
    
    def spawn_shell(self):
        """Spawn PSH with proper PTY settings."""
        # Uses pexpect with specific terminal dimensions
        # Sets TERM environment variable
        # Handles prompt detection
```

### Key Configuration
- Terminal type: `TERM=xterm` or `TERM=xterm-256color`
- Dimensions: 80x24 (standard terminal size)
- Encoding: UTF-8
- Timing: Small delays between operations

## Known Limitations

### 1. Arrow Key Sequences
- **Issue**: Arrow keys send escape sequences (e.g., `\033[D` for left arrow)
- **In PTY**: These may be echoed or processed differently
- **Workaround**: Mark tests as `xfail` with explanation

### 2. Terminal Echo
- **Issue**: PTY may echo commands back, confusing output matching
- **Solution**: Filter echoed commands in test framework

### 3. Timing Dependencies
- **Issue**: Operations may need precise timing
- **Solution**: Add appropriate delays between operations

## Alternative Testing Approaches

### 1. Script Command Recording
The Unix `script` command can record terminal sessions:
```bash
script -q session.log -c "python -m psh"
# Interact with shell
# exit
# Replay with: scriptreplay session.log
```

### 2. Expect Scripts
Traditional `expect` scripts might handle some cases better:
```tcl
#!/usr/bin/expect
spawn python -m psh
expect "psh$ "
send "echo test\r"
expect "test"
```

### 3. Docker-based Testing
Run tests in a containerized environment with a real TTY:
```bash
docker run -it --rm -v $PWD:/psh python:3.11 \
  bash -c "cd /psh && python -m pytest tests/system/interactive/"
```

### 4. tmux/screen Automation
Use terminal multiplexers for more realistic terminal emulation:
```python
# Create tmux session
# Send commands to tmux pane
# Capture pane contents
```

## Best Practices for PTY Testing

1. **Test What You Can Mock**
   - Unit test core functionality without PTY when possible
   - Use PTY tests only for integration scenarios

2. **Be Explicit About Limitations**
   - Use `xfail` markers with clear explanations
   - Document which features work interactively but not in tests

3. **Focus on Outcomes**
   - Test that commands produce correct results
   - Don't test every keystroke if the end result is correct

4. **Handle Platform Differences**
   - Terminal behavior varies between OS platforms
   - Use platform-specific markers when needed

5. **Provide Manual Test Instructions**
   - Document how to manually verify xfailed features
   - Include interactive test scripts for complex scenarios

## Manual Testing Instructions

To manually verify interactive features:

1. **Arrow Key Navigation**
   ```bash
   $ python -m psh
   psh$ hello world  # Type this
   # Press left arrow 5 times
   # Type: brave 
   # Press Enter
   # Should execute: hello brave world
   ```

2. **History Navigation**
   ```bash
   $ python -m psh
   psh$ echo one
   psh$ echo two
   psh$ echo three
   # Press up arrow - should show "echo three"
   # Press up arrow again - should show "echo two"
   ```

3. **Control Keys**
   ```bash
   $ python -m psh
   psh$ hello world  # Type this
   # Press Ctrl-A - cursor to beginning
   # Press Ctrl-E - cursor to end
   # Press Ctrl-U - clear line
   ```

## Future Improvements

1. **Investigate termios Settings**
   - Fine-tune terminal settings for better PTY compatibility
   - Consider different line discipline modes

2. **Alternative Test Runners**
   - Explore tools designed for terminal testing
   - Consider GUI terminal automation tools

3. **Record/Replay Testing**
   - Record real terminal sessions
   - Replay and verify behavior

## Conclusion

PTY testing is inherently challenging due to the complexity of terminal emulation. Our approach balances:
- Comprehensive testing where reliable
- Clear documentation of limitations
- Alternative testing strategies
- Manual verification procedures

The key insight is that **features working correctly in interactive use is more important than passing all automated tests**. Our test suite acknowledges this reality while still providing good coverage of PSH functionality.
