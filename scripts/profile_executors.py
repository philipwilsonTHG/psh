#!/usr/bin/env python3
"""
Profile the performance of legacy vs visitor executors.

This script runs various shell commands using both executors and measures
their performance to identify optimization opportunities.
"""

import time
import statistics
import subprocess
import sys
import os

# Add psh to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse


class ExecutorProfiler:
    """Profile executor performance."""
    
    def __init__(self):
        self.results = {
            'legacy': {},
            'visitor': {}
        }
    
    def time_execution(self, shell, command, iterations=100):
        """Time command execution."""
        times = []
        
        # Silence output for profiling
        import io
        import os
        null_fd = os.open(os.devnull, os.O_WRONLY)
        saved_stdout = os.dup(1)
        saved_stderr = os.dup(2)
        
        # Pre-parse the command once to avoid including parse time
        tokens = tokenize(command)
        ast = parse(tokens)
        
        try:
            for _ in range(iterations):
                # Redirect stdout/stderr to /dev/null
                os.dup2(null_fd, 1)
                os.dup2(null_fd, 2)
                
                start = time.perf_counter()
                
                # Execute the pre-parsed AST
                shell.execute(ast)
                
                end = time.perf_counter()
                times.append(end - start)
        finally:
            # Restore original stdout/stderr
            os.dup2(saved_stdout, 1)
            os.dup2(saved_stderr, 2)
            os.close(null_fd)
            os.close(saved_stdout)
            os.close(saved_stderr)
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0,
            'min': min(times),
            'max': max(times)
        }
    
    def profile_command(self, command, iterations=100):
        """Profile a command with both executors."""
        print(f"\nProfiling: {command}")
        print(f"Iterations: {iterations}")
        
        # Legacy executor
        shell_legacy = Shell(norc=True, use_visitor_executor=False)
        legacy_stats = self.time_execution(shell_legacy, command, iterations)
        
        # Visitor executor
        shell_visitor = Shell(norc=True, use_visitor_executor=True)
        visitor_stats = self.time_execution(shell_visitor, command, iterations)
        
        # Calculate difference
        diff_percent = ((visitor_stats['mean'] - legacy_stats['mean']) / legacy_stats['mean']) * 100
        
        print(f"Legacy:  {legacy_stats['mean']*1000:.3f}ms (±{legacy_stats['stdev']*1000:.3f}ms)")
        print(f"Visitor: {visitor_stats['mean']*1000:.3f}ms (±{visitor_stats['stdev']*1000:.3f}ms)")
        print(f"Difference: {diff_percent:+.1f}%")
        
        return {
            'command': command,
            'legacy': legacy_stats,
            'visitor': visitor_stats,
            'diff_percent': diff_percent
        }
    
    def run_profiling_suite(self):
        """Run comprehensive profiling suite."""
        test_commands = [
            # Simple commands
            ('echo "hello"', 1000),
            ('true', 1000),
            ('false', 1000),
            
            # Variable operations
            ('VAR=value', 1000),
            ('VAR=value; echo $VAR', 500),
            
            # Arithmetic
            ('((x = 5 + 3))', 500),
            ('x=$((10 * 20))', 500),
            
            # Control structures
            ('if true; then echo yes; fi', 500),
            ('for i in 1 2 3; do echo $i; done', 200),
            ('while false; do echo no; done', 500),
            ('case x in x) echo match ;; esac', 500),
            
            # Functions
            ('f() { echo test; }', 500),
            ('f() { echo test; }; f', 200),
            
            # Complex commands
            ('VAR=test; if [ "$VAR" = "test" ]; then echo ok; fi', 200),
            ('for i in {1..5}; do ((x = i * 2)); done', 100),
        ]
        
        results = []
        
        print("="*60)
        print("EXECUTOR PERFORMANCE PROFILING")
        print("="*60)
        
        for command, iterations in test_commands:
            result = self.profile_command(command, iterations)
            results.append(result)
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        # Sort by difference
        results.sort(key=lambda x: x['diff_percent'], reverse=True)
        
        print("\nCommands with largest performance difference:")
        print("-"*60)
        for result in results[:5]:
            print(f"{result['diff_percent']:+6.1f}% - {result['command']}")
        
        # Overall statistics
        all_diffs = [r['diff_percent'] for r in results]
        print(f"\nOverall performance difference:")
        print(f"  Mean: {statistics.mean(all_diffs):+.1f}%")
        print(f"  Median: {statistics.median(all_diffs):+.1f}%")
        print(f"  Range: {min(all_diffs):+.1f}% to {max(all_diffs):+.1f}%")
        
        # Check if within 10% goal
        if abs(statistics.mean(all_diffs)) <= 10:
            print("\n✅ GOAL MET: Visitor executor within 10% of legacy executor")
        else:
            print(f"\n❌ GOAL NOT MET: Visitor executor is {statistics.mean(all_diffs):+.1f}% different")
        
        return results


def main():
    """Run profiling."""
    profiler = ExecutorProfiler()
    results = profiler.run_profiling_suite()
    
    # Write detailed results
    with open('executor_profile_results.txt', 'w') as f:
        f.write("Detailed Executor Profiling Results\n")
        f.write("="*60 + "\n\n")
        
        for result in results:
            f.write(f"Command: {result['command']}\n")
            f.write(f"Legacy:  {result['legacy']['mean']*1000:.3f}ms\n")
            f.write(f"Visitor: {result['visitor']['mean']*1000:.3f}ms\n")
            f.write(f"Difference: {result['diff_percent']:+.1f}%\n\n")
    
    print("\nDetailed results written to executor_profile_results.txt")


if __name__ == '__main__':
    main()