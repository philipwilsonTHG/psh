#!/usr/bin/env psh
# Wait builtin demonstration script
# Shows various ways to use the wait command for process synchronization

echo "=== PSH Wait Builtin Demonstration ==="
echo

echo "1. Starting multiple background jobs..."
sleep 1 &
job1_pid=$!
echo "Started job 1 (PID: $job1_pid): sleep 1"

sleep 2 &
job2_pid=$!
echo "Started job 2 (PID: $job2_pid): sleep 2"

sleep 0.5 &
job3_pid=$!
echo "Started job 3 (PID: $job3_pid): sleep 0.5"

echo
echo "Current jobs:"
jobs
echo

echo "2. Waiting for specific job by job number..."
echo "Waiting for job 3 (%3)..."
wait %3
echo "Job 3 completed with exit status: $?"
echo

echo "3. Waiting for specific process by PID..."
echo "Waiting for PID $job1_pid..."
wait $job1_pid
echo "Process $job1_pid completed with exit status: $?"
echo

echo "4. Waiting for all remaining jobs..."
echo "Waiting for all background jobs to complete..."
wait
echo "All jobs completed with final exit status: $?"
echo

echo "5. Testing wait with failing command..."
sh -c 'sleep 0.3; exit 42' &
failing_pid=$!
echo "Started failing command (PID: $failing_pid)"
wait $failing_pid
echo "Failing command completed with exit status: $? (should be 42)"
echo

echo "6. Testing error cases..."
echo "Trying to wait for non-existent PID 99999:"
wait 99999
echo "Exit status: $? (should be 127)"
echo

echo "Trying to wait for non-existent job %99:"
wait %99
echo "Exit status: $? (should be 127)"
echo

echo "7. Testing wait with no arguments when no jobs exist..."
echo "Calling wait with no background jobs:"
wait
echo "Exit status: $? (should be 0, returns immediately)"
echo

echo "=== Wait builtin demonstration complete ==="
echo "The wait builtin enables:"
echo "- Process synchronization in shell scripts"
echo "- Background job coordination"
echo "- Exit status collection from child processes"
echo "- Proper POSIX-compliant job control"