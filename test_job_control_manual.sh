#!/bin/bash
# Manual test script for job control

echo "Testing PSH Job Control"
echo "======================"
echo
echo "This script will test:"
echo "1. Running 'sleep 30' and suspending with Ctrl-Z"
echo "2. Checking jobs list"
echo "3. Resuming with fg"
echo "4. Running background jobs"
echo
echo "Start psh with: python3 -m psh"
echo
echo "Then try these commands:"
echo "  sleep 30      # Press Ctrl-Z to suspend"
echo "  jobs          # Should show [1]+ Stopped"
echo "  bg            # Resume in background"
echo "  jobs          # Should show [1]+ Running"
echo "  fg            # Bring back to foreground"
echo
echo "For interactive programs:"
echo "  vi test.txt   # Press Ctrl-Z to suspend"
echo "  jobs          # Should show vi is stopped"
echo "  fg            # Resume vi"
echo
echo "Test with multiple jobs:"
echo "  sleep 100 &   # Start background job"
echo "  sleep 50      # Start foreground, then Ctrl-Z"
echo "  sleep 25 &    # Another background job"
echo "  jobs          # Should show all three"
echo "  fg %2         # Resume job 2 (sleep 50)"
echo "  fg %sleep     # Resume job starting with 'sleep'"