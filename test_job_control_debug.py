#!/usr/bin/env python3
"""Debug script to test job control with verbose output."""

import os
import sys
import signal
import time

print(f"Shell PID: {os.getpid()}")
print(f"Shell PGID: {os.getpgrp()}")
print(f"Session ID: {os.getsid(0)}")

try:
    tty_pgid = os.tcgetpgrp(0)
    print(f"Terminal foreground PGID: {tty_pgid}")
except OSError as e:
    print(f"No controlling terminal: {e}")

print("\nSignal handlers:")
for sig in ['SIGINT', 'SIGTSTP', 'SIGTTOU', 'SIGTTIN', 'SIGCHLD']:
    handler = signal.getsignal(getattr(signal, sig))
    print(f"  {sig}: {handler}")

print("\nStarting psh...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psh.shell import Shell

shell = Shell()
shell.interactive_loop()