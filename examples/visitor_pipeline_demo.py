#!/usr/bin/env python3
"""
Example: Using the visitor pipeline to analyze and transform shell scripts.

This demonstrates how to compose multiple visitors using the pipeline system
to perform complex analysis and transformations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.visitor_pipeline import VisitorPipeline, get_global_registry
from psh.visitor.formatter_visitor import FormatterVisitor
import json


def analyze_and_optimize_script(script_content: str) -> None:
    """Analyze, optimize, and report on a shell script."""
    print("Original Script:")
    print("=" * 60)
    print(script_content)
    print()
    
    try:
        # Parse the script
        tokens = tokenize(script_content)
        ast = parse(tokens)
        
        # Create a pipeline with multiple visitors
        pipeline = VisitorPipeline(get_global_registry())
        
        # Add analysis visitors
        pipeline.add_visitor('metrics', name='metrics_analysis')
        pipeline.add_visitor('security', name='security_check')
        pipeline.add_visitor('validator', name='validation')
        
        # Add transformation visitor
        pipeline.add_visitor('optimizer', name='optimization')
        
        # Run the pipeline
        results = pipeline.run(ast)
        
        # Display metrics
        print("Code Metrics:")
        print("=" * 60)
        metrics = results['metrics_analysis']['report']
        print(f"Total Commands: {metrics['summary']['total_commands']}")
        print(f"Unique Commands: {metrics['commands']['unique_commands']}")
        print(f"Functions: {metrics['summary']['total_functions']}")
        print(f"Loops: {metrics['summary']['total_loops']}")
        print(f"Cyclomatic Complexity: {metrics['complexity']['cyclomatic_complexity']}")
        print()
        
        # Display security issues
        print("Security Analysis:")
        print("=" * 60)
        security_report = pipeline.get_visitor('security_check').get_report()
        if security_report['total_issues'] > 0:
            print(f"Found {security_report['total_issues']} security issues:")
            print(f"  High severity: {security_report['high_severity']}")
            print(f"  Medium severity: {security_report['medium_severity']}")
            print(f"  Low severity: {security_report['low_severity']}")
            print("\nIssues:")
            for issue in security_report['issues'][:5]:  # Show first 5
                print(f"  - {issue}")
        else:
            print("No security issues found!")
        print()
        
        # Display validation errors
        print("Validation Results:")
        print("=" * 60)
        validator = pipeline.get_visitor('validation')
        if validator.issues:
            errors = [i for i in validator.issues if i.severity.value == 'error']
            warnings = [i for i in validator.issues if i.severity.value == 'warning']
            
            if errors:
                print(f"Found {len(errors)} validation errors:")
                for error in errors[:5]:  # Show first 5
                    print(f"  - {error.message}")
            
            if warnings:
                print(f"\nFound {len(warnings)} warnings:")
                for warning in warnings[:5]:  # Show first 5
                    print(f"  - {warning.message}")
            
            if not errors and not warnings:
                print("Script is valid!")
        else:
            print("Script is valid!")
        print()
        
        # Show optimized version
        print("Optimized Script:")
        print("=" * 60)
        optimized_ast = pipeline.get_final_ast()
        formatter = FormatterVisitor()
        optimized_script = formatter.visit(optimized_ast)
        print(optimized_script)
        
        # Show optimization stats
        optimizer = pipeline.get_visitor('optimization')
        opt_stats = optimizer.get_optimization_stats()
        print(f"\nOptimizations applied: {opt_stats['optimizations_applied']}")
        
    except Exception as e:
        print(f"Error analyzing script: {e}", file=sys.stderr)
        sys.exit(1)


def demonstrate_custom_pipeline():
    """Demonstrate creating a custom analysis pipeline."""
    print("\n\nCustom Pipeline Demo:")
    print("=" * 60)
    
    # Simple script to analyze
    script = """
    echo "Starting process..." | cat
    
    if true; then
        echo "Always runs"
    fi
    
    while false; do
        echo "Never runs"
    done
    """
    
    # Parse
    tokens = tokenize(script)
    ast = parse(tokens)
    
    # Create custom pipeline with just optimization and formatting
    pipeline = VisitorPipeline(get_global_registry())
    pipeline.add_visitor('optimizer')
    
    # Run pipeline
    results = pipeline.run(ast)
    
    # Get optimized AST and format it
    optimized_ast = pipeline.get_final_ast()
    formatter = FormatterVisitor()
    optimized = formatter.visit(optimized_ast)
    
    print("Original script had unnecessary constructs.")
    print("\nOptimized version:")
    print(optimized)
    
    # Show what was optimized
    optimizer = pipeline.get_visitor('optimizer')
    stats = optimizer.get_optimization_stats()
    print(f"\nRemoved {stats['optimizations_applied']} unnecessary constructs")


# Example: Complex script with various issues
vulnerable_script = """#!/bin/bash
# Deploy script with security and performance issues

# Unnecessary cat
ls -la | cat | grep "\\.conf$"

# Security issue: eval with user input
user_cmd="$1"
eval $user_cmd

# World-writable permissions
chmod 777 /tmp/deploy.log

# Complex function
deploy_app() {
    local server=$1
    
    # Nested conditions
    if [ -f config.yml ]; then
        if [ -r config.yml ]; then
            source config.yml
        else
            echo "Cannot read config"
            exit 1
        fi
    fi
    
    # Inefficient pipeline
    cat /var/log/app.log | grep ERROR | cat > errors.txt
    
    # Download and execute
    curl http://example.com/script.sh | bash
}

# Main execution
for server in prod1 prod2 prod3; do
    deploy_app "$server"
done
"""

if __name__ == "__main__":
    # Run full analysis pipeline
    analyze_and_optimize_script(vulnerable_script)
    
    # Demonstrate custom pipeline
    demonstrate_custom_pipeline()
    
    # Show available visitors
    print("\n\nAvailable Visitors:")
    print("=" * 60)
    registry = get_global_registry()
    for visitor_info in registry.list_visitors():
        print(f"{visitor_info['name']:15} ({visitor_info['category']:15}) - {visitor_info['description']}")