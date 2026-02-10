"""
Alternative approaches for testing interactive shell features.

This module demonstrates various techniques for testing terminal-based
applications when traditional PTY testing has limitations.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PSH_ROOT))


class ScriptCommandTester:
    """Test PSH using Unix 'script' command for session recording."""

    def __init__(self):
        self.session_file = None
        self.timing_file = None

    def record_session(self, commands: List[str]) -> Tuple[str, str]:
        """
        Record a PSH session using the script command.

        Returns: (session_output, timing_data)
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            # Write commands to execute
            f.write('#!/bin/bash\n')
            f.write('python -m psh --norc << \'EOF\'\n')
            for cmd in commands:
                f.write(cmd + '\n')
            f.write('exit\n')
            f.write('EOF\n')
            script_file = f.name

        os.chmod(script_file, 0o755)

        try:
            # Use script command to record session
            session_file = tempfile.mktemp(suffix='.typescript')

            if sys.platform == 'darwin':
                # macOS script command syntax
                cmd = ['script', '-q', session_file, script_file]
            else:
                # Linux script command syntax
                timing_file = tempfile.mktemp(suffix='.timing')
                cmd = ['script', '-q', '-t', f'2>{timing_file}', session_file, '-c', script_file]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Read session output
            with open(session_file, 'r') as f:
                session_output = f.read()

            return session_output, result.stderr

        finally:
            # Cleanup
            os.unlink(script_file)
            if os.path.exists(session_file):
                os.unlink(session_file)

    def test_arrow_keys(self) -> bool:
        """Test arrow key functionality using script recording."""
        # This would need to use a more complex approach with expect or similar
        # to actually send arrow keys during recording
        pass


class TmuxTester:
    """Test PSH using tmux for terminal multiplexing."""

    def __init__(self, session_name: str = "psh_test"):
        self.session_name = session_name
        self.pane_id = None

    def setup(self):
        """Create tmux session and start PSH."""
        # Kill existing session if any
        subprocess.run(['tmux', 'kill-session', '-t', self.session_name],
                      stderr=subprocess.DEVNULL)

        # Create new session
        subprocess.run(['tmux', 'new-session', '-d', '-s', self.session_name])

        # Get pane ID
        result = subprocess.run(
            ['tmux', 'list-panes', '-t', self.session_name, '-F', '#{pane_id}'],
            capture_output=True, text=True
        )
        self.pane_id = result.stdout.strip()

        # Start PSH in the pane
        self.send_keys('python -m psh --norc')
        time.sleep(0.5)  # Wait for PSH to start

    def send_keys(self, keys: str):
        """Send keys to tmux pane."""
        subprocess.run(['tmux', 'send-keys', '-t', self.pane_id, keys, 'Enter'])

    def send_raw_keys(self, keys: str):
        """Send raw keys without Enter."""
        subprocess.run(['tmux', 'send-keys', '-t', self.pane_id, keys])

    def capture_pane(self) -> str:
        """Capture current pane contents."""
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', self.pane_id, '-p'],
            capture_output=True, text=True
        )
        return result.stdout

    def cleanup(self):
        """Kill tmux session."""
        subprocess.run(['tmux', 'kill-session', '-t', self.session_name])

    def test_arrow_keys(self) -> bool:
        """Test arrow key navigation in tmux."""
        try:
            self.setup()

            # Type a command
            self.send_raw_keys('hello world')
            time.sleep(0.1)

            # Send left arrow keys
            for _ in range(5):
                subprocess.run(['tmux', 'send-keys', '-t', self.pane_id, 'Left'])
                time.sleep(0.05)

            # Insert text
            self.send_raw_keys('brave ')
            time.sleep(0.1)

            # Execute
            self.send_keys('')
            time.sleep(0.2)

            # Check output
            output = self.capture_pane()
            return 'hello brave world' in output

        finally:
            self.cleanup()


class DockerTester:
    """Test PSH in a Docker container with real TTY."""

    @staticmethod
    def create_dockerfile() -> str:
        """Create a Dockerfile for PSH testing."""
        dockerfile = """
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    expect \
    tmux \
    script \
    && rm -rf /var/lib/apt/lists/*

# Copy PSH source
WORKDIR /psh
COPY . .

# Install test dependencies
RUN pip install pytest pexpect

# Create test script
RUN echo '#!/usr/bin/expect' > /test_interactive.exp && \
    echo 'spawn python -m psh --norc' >> /test_interactive.exp && \
    echo 'expect "psh$ "' >> /test_interactive.exp && \
    echo 'send "hello world"' >> /test_interactive.exp && \
    echo 'send "\\033\\[D\\033\\[D\\033\\[D\\033\\[D\\033\\[D"' >> /test_interactive.exp && \
    echo 'send "brave "' >> /test_interactive.exp && \
    echo 'send "\\r"' >> /test_interactive.exp && \
    echo 'expect "hello brave world"' >> /test_interactive.exp && \
    echo 'send "exit\\r"' >> /test_interactive.exp && \
    echo 'expect eof' >> /test_interactive.exp && \
    chmod +x /test_interactive.exp

CMD ["/test_interactive.exp"]
"""
        return dockerfile

    @staticmethod
    def run_docker_test() -> bool:
        """Run interactive tests in Docker container."""
        # Save Dockerfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='Dockerfile', delete=False) as f:
            f.write(DockerTester.create_dockerfile())
            dockerfile = f.name

        try:
            # Build image
            result = subprocess.run(
                ['docker', 'build', '-t', 'psh-test', '-f', dockerfile, '.'],
                capture_output=True
            )
            if result.returncode != 0:
                return False

            # Run test
            result = subprocess.run(
                ['docker', 'run', '--rm', '-it', 'psh-test'],
                capture_output=True
            )

            return result.returncode == 0

        finally:
            os.unlink(dockerfile)
            # Clean up image
            subprocess.run(['docker', 'rmi', 'psh-test'], stderr=subprocess.DEVNULL)


class ManualTestScriptGenerator:
    """Generate scripts for manual testing of interactive features."""

    @staticmethod
    def generate_test_script() -> str:
        """Generate a bash script for manual testing."""
        script = """#!/bin/bash
# Manual test script for PSH interactive features

echo "PSH Interactive Feature Test Script"
echo "=================================="
echo

# Function to pause and wait for user
pause() {
    echo
    echo "Press Enter to continue..."
    read
}

# Start PSH
echo "Starting PSH..."
python -m psh --norc << 'TESTSCRIPT'

echo "=== Test 1: Arrow Key Navigation ==="
echo "Type: hello world"
echo "Press left arrow 5 times"
echo "Type: brave "
echo "Press Enter"
echo "Expected: hello brave world"
pause

echo "=== Test 2: History Navigation ==="
echo "Commands will be executed:"
echo one
echo two
echo three
echo "Now press up arrow - should see 'echo three'"
echo "Press up again - should see 'echo two'"
pause

echo "=== Test 3: Control Keys ==="
echo "Type: test line"
echo "Press Ctrl-A - cursor should go to beginning"
echo "Press Ctrl-E - cursor should go to end"
echo "Press Ctrl-U - line should be cleared"
pause

echo "=== Test 4: Tab Completion ==="
touch test_file.txt
echo "Type: echo test_f"
echo "Press Tab - should complete to test_file.txt"
rm test_file.txt
pause

echo "All tests complete!"
exit

TESTSCRIPT
"""
        return script

    @staticmethod
    def save_manual_test_script():
        """Save the manual test script to a file."""
        script_path = PSH_ROOT / "tests" / "system" / "interactive" / "manual_test.sh"
        with open(script_path, 'w') as f:
            f.write(ManualTestScriptGenerator.generate_test_script())
        os.chmod(script_path, 0o755)
        return script_path


# Example usage and demonstrations
if __name__ == "__main__":
    print("Alternative Testing Approaches for PSH")
    print("=" * 40)

    # 1. Script command approach
    print("\n1. Script Command Approach:")
    if sys.platform in ('darwin', 'linux'):
        tester = ScriptCommandTester()
        output, timing = tester.record_session([
            "echo 'Testing script command'",
            "pwd",
            "echo $((2 + 2))"
        ])
        print("Session recorded successfully")
        print("Output length:", len(output))
    else:
        print("Script command not available on this platform")

    # 2. Tmux approach (requires tmux installed)
    print("\n2. Tmux Approach:")
    try:
        result = subprocess.run(['tmux', '-V'], capture_output=True)
        if result.returncode == 0:
            print("Tmux is available")
            tmux_tester = TmuxTester()
            # Uncomment to test:
            # success = tmux_tester.test_arrow_keys()
            # print(f"Arrow key test: {'PASSED' if success else 'FAILED'}")
        else:
            print("Tmux not installed")
    except FileNotFoundError:
        print("Tmux not installed")

    # 3. Docker approach (requires docker)
    print("\n3. Docker Approach:")
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True)
        if result.returncode == 0:
            print("Docker is available")
            print("Dockerfile template generated")
            # Uncomment to test:
            # success = DockerTester.run_docker_test()
            # print(f"Docker test: {'PASSED' if success else 'FAILED'}")
        else:
            print("Docker not installed")
    except FileNotFoundError:
        print("Docker not installed")

    # 4. Manual test script
    print("\n4. Manual Test Script:")
    script_path = ManualTestScriptGenerator.save_manual_test_script()
    print(f"Manual test script saved to: {script_path}")
    print("Run with: bash", script_path)
