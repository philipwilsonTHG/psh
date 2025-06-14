#!/usr/bin/env python3
"""
Example: Using MetricsVisitor to analyze shell script complexity.

This demonstrates how to use PSH's MetricsVisitor to collect code metrics
and analyze script structure and complexity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.metrics_visitor import MetricsVisitor
import json


def analyze_script(script_content: str, verbose: bool = False) -> None:
    """Analyze a shell script and display metrics."""
    try:
        # Parse the script
        tokens = tokenize(script_content)
        ast = parse(tokens)
        
        # Collect metrics
        visitor = MetricsVisitor()
        visitor.visit(ast)
        
        # Display summary
        print(visitor.get_summary())
        
        if verbose:
            # Show detailed report as JSON
            print("\nDetailed Metrics Report:")
            print("=" * 60)
            report = visitor.get_report()
            print(json.dumps(report, indent=2))
            
    except Exception as e:
        print(f"Error analyzing script: {e}", file=sys.stderr)
        sys.exit(1)


# Example: Complex script with various features
complex_script = """#!/bin/bash
# Example script demonstrating various shell features

# Configuration
readonly CONFIG_FILE="/etc/myapp.conf"
declare -a SERVERS=("web1" "web2" "web3")
declare -A PORTS=(["http"]=80 ["https"]=443)

# Functions
log_message() {
    local level=$1
    shift
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] [$level] $*" >> app.log
}

check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        log_message INFO "$service is running"
        return 0
    else
        log_message ERROR "$service is not running"
        return 1
    fi
}

# Main processing
main() {
    # Parse command line arguments
    while getopts "hvc:s:" opt; do
        case $opt in
            h) show_help; exit 0 ;;
            v) VERBOSE=true ;;
            c) CONFIG_FILE="$OPTARG" ;;
            s) SERVERS+=("$OPTARG") ;;
            *) echo "Invalid option"; exit 1 ;;
        esac
    done
    
    # Check configuration
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_message ERROR "Config file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Process each server
    for server in "${SERVERS[@]}"; do
        echo "Processing $server..."
        
        # Check services
        for service in nginx postgresql redis; do
            if ! check_service "$service"; then
                ((failed_count++))
            fi
        done
        
        # Deploy if all services are running
        if [[ $failed_count -eq 0 ]]; then
            deploy_to_server "$server" || continue
        else
            log_message WARN "Skipping $server due to failed services"
        fi
    done
    
    # Report results
    echo "Deployment complete. Failed services: $failed_count"
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
"""

# Simple script for comparison
simple_script = """#!/bin/bash
echo "Hello, World!"
ls -la | grep ".txt" | wc -l
cd /tmp && echo "Changed directory"
"""

if __name__ == "__main__":
    print("Analyzing Complex Script:")
    print("=" * 60)
    analyze_script(complex_script)
    
    print("\n\nAnalyzing Simple Script:")
    print("=" * 60)
    analyze_script(simple_script)
    
    # Show detailed report for complex script
    print("\n\nDetailed Analysis of Complex Script:")
    print("=" * 60)
    analyze_script(complex_script, verbose=True)