#!/usr/bin/env python3
"""
Analyze PSH test suite to understand current coverage and organization.

This script examines all test files and generates a report showing:
- What components each test file covers
- Test counts and categories
- Potential duplications
- Coverage gaps
"""

import os
import ast
import re
from collections import defaultdict
from pathlib import Path
import json

class TestAnalyzer:
    def __init__(self, test_dir):
        self.test_dir = Path(test_dir)
        self.test_files = []
        self.test_stats = defaultdict(int)
        self.component_coverage = defaultdict(list)
        self.test_categories = defaultdict(list)
        self.imports_by_file = {}
        
    def analyze(self):
        """Run complete analysis of test suite."""
        print(f"Analyzing tests in {self.test_dir}...")
        self._collect_test_files()
        self._analyze_test_files()
        self._categorize_tests()
        self._identify_gaps()
        return self._generate_report()
    
    def _collect_test_files(self):
        """Find all test files."""
        for file in self.test_dir.rglob("test_*.py"):
            if "test_new" not in str(file):  # Skip any new test directories
                self.test_files.append(file)
        print(f"Found {len(self.test_files)} test files")
        
    def _analyze_test_files(self):
        """Analyze each test file for content and coverage."""
        for test_file in self.test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                
                # Parse AST to understand test structure
                tree = ast.parse(content)
                
                # Extract test metadata
                file_info = {
                    'path': str(test_file.relative_to(self.test_dir)),
                    'test_count': 0,
                    'test_methods': [],
                    'imports': [],
                    'components': set(),
                    'features': set(),
                }
                
                # Analyze imports to understand dependencies
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            file_info['imports'].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            file_info['imports'].append(node.module)
                    elif isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        file_info['test_count'] += 1
                        file_info['test_methods'].append(node.name)
                        
                # Detect components being tested based on imports and content
                self._detect_components(file_info, content)
                
                # Store analysis
                self.imports_by_file[test_file] = file_info
                
            except Exception as e:
                print(f"Error analyzing {test_file}: {e}")
                
    def _detect_components(self, file_info, content):
        """Detect which PSH components are tested based on imports and content."""
        # Component detection patterns
        component_patterns = {
            'lexer': [r'tokenize', r'Token', r'lexer', r'TokenType'],
            'parser': [r'parse', r'Parser', r'AST', r'ast_nodes'],
            'executor': [r'execute', r'Executor', r'visitor'],
            'expansion': [r'expand', r'Expansion', r'variable.*expansion'],
            'builtins': [r'builtin', r'BuiltinRegistry', r'execute.*builtin'],
            'io_redirect': [r'redirect', r'IOManager', r'file.*descriptor'],
            'pipeline': [r'pipeline', r'Pipeline', r'pipe.*execution'],
            'job_control': [r'job', r'JobManager', r'background', r'fg.*bg'],
            'signals': [r'signal', r'SIGINT', r'SIGTSTP', r'handle.*signal'],
            'functions': [r'function.*def', r'FunctionManager', r'return.*builtin'],
            'arrays': [r'array', r'IndexedArray', r'AssociativeArray', r'\$\{.*\[@\]\}'],
            'arithmetic': [r'arithmetic', r'\$\(\(', r'ArithmeticEvaluator'],
            'control_flow': [r'if.*then', r'while.*do', r'for.*in', r'case.*esac'],
            'interactive': [r'readline', r'prompt', r'PS1', r'completion'],
            'process': [r'subprocess', r'fork', r'exec', r'process.*substitution'],
        }
        
        for component, patterns in component_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    file_info['components'].add(component)
                    self.component_coverage[component].append(file_info['path'])
                    break
                    
        # Feature detection patterns
        feature_patterns = {
            'multiline': r'multiline|multi-line|continuation',
            'unicode': r'unicode|utf-8|encoding',
            'quotes': r'quote|single.*quote|double.*quote',
            'escaping': r'escape|backslash|\\\\',
            'glob': r'glob|wildcard|\*|\?|\[.*\]',
            'history': r'history|!!|!\d+',
            'alias': r'alias|unalias',
            'variables': r'variable|VAR=|export|unset',
            'substitution': r'substitution|\$\(.*\)|`.*`',
            'heredoc': r'heredoc|<<|<<-',
        }
        
        for feature, pattern in feature_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                file_info['features'].add(feature)
                
    def _categorize_tests(self):
        """Categorize tests by type."""
        for test_file, info in self.imports_by_file.items():
            # Categorize based on file path and content
            path_str = str(test_file)
            
            if 'comparison' in path_str or 'bash' in path_str:
                self.test_categories['conformance'].append(info['path'])
            elif 'posix' in path_str:
                self.test_categories['posix'].append(info['path'])
            elif len(info['components']) == 1:
                self.test_categories['unit'].append(info['path'])
            elif len(info['components']) > 3:
                self.test_categories['system'].append(info['path'])
            else:
                self.test_categories['integration'].append(info['path'])
                
            # Track test counts
            self.test_stats['total_files'] += 1
            self.test_stats['total_tests'] += info['test_count']
            
    def _identify_gaps(self):
        """Identify potential testing gaps."""
        self.gaps = []
        
        # Components with few tests
        for component, files in self.component_coverage.items():
            if len(files) < 3:
                self.gaps.append(f"Low coverage for {component}: only {len(files)} test files")
                
        # Missing component combinations
        common_combinations = [
            ('parser', 'executor'),
            ('expansion', 'executor'),
            ('pipeline', 'job_control'),
            ('signals', 'interactive'),
        ]
        
        for comp1, comp2 in common_combinations:
            combined = 0
            for info in self.imports_by_file.values():
                if comp1 in info['components'] and comp2 in info['components']:
                    combined += 1
            if combined < 2:
                self.gaps.append(f"Few integration tests for {comp1} + {comp2}")
                
    def _generate_report(self):
        """Generate analysis report."""
        report = {
            'summary': {
                'total_test_files': self.test_stats['total_files'],
                'total_test_methods': self.test_stats['total_tests'],
                'average_tests_per_file': self.test_stats['total_tests'] / max(1, self.test_stats['total_files']),
            },
            'by_category': {
                category: {
                    'count': len(files),
                    'percentage': len(files) / max(1, self.test_stats['total_files']) * 100
                }
                for category, files in self.test_categories.items()
            },
            'by_component': {
                component: {
                    'test_files': len(files),
                    'files': files[:5]  # First 5 files
                }
                for component, files in self.component_coverage.items()
            },
            'gaps': self.gaps,
            'recommendations': self._generate_recommendations(),
        }
        
        return report
    
    def _generate_recommendations(self):
        """Generate testing recommendations based on analysis."""
        recommendations = []
        
        # Check for test organization issues
        if self.test_stats['total_tests'] / max(1, self.test_stats['total_files']) > 50:
            recommendations.append("Consider splitting large test files for better organization")
            
        # Check for missing categories
        if len(self.test_categories.get('performance', [])) == 0:
            recommendations.append("Add performance benchmarking tests")
            
        if len(self.test_categories.get('conformance', [])) < 10:
            recommendations.append("Expand conformance testing with bash")
            
        # Component-specific recommendations
        for component in ['signals', 'job_control', 'interactive']:
            if len(self.component_coverage.get(component, [])) < 5:
                recommendations.append(f"Increase test coverage for {component}")
                
        return recommendations


def print_report(report):
    """Print formatted analysis report."""
    print("\n" + "="*60)
    print("PSH Test Suite Analysis Report")
    print("="*60)
    
    print("\n## Summary")
    print(f"Total test files: {report['summary']['total_test_files']}")
    print(f"Total test methods: {report['summary']['total_test_methods']}")
    print(f"Average tests per file: {report['summary']['average_tests_per_file']:.1f}")
    
    print("\n## Test Categories")
    for category, info in report['by_category'].items():
        print(f"{category:15} {info['count']:4d} files ({info['percentage']:5.1f}%)")
        
    print("\n## Component Coverage")
    for component, info in sorted(report['by_component'].items()):
        print(f"\n{component}:")
        print(f"  Test files: {info['test_files']}")
        if info['files']:
            print(f"  Examples: {', '.join(info['files'][:3])}")
            
    if report['gaps']:
        print("\n## Testing Gaps")
        for gap in report['gaps']:
            print(f"- {gap}")
            
    if report['recommendations']:
        print("\n## Recommendations")
        for rec in report['recommendations']:
            print(f"- {rec}")
            
    print("\n" + "="*60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze PSH test suite")
    parser.add_argument(
        '--test-dir',
        default='tests',
        help='Directory containing tests (default: tests)'
    )
    parser.add_argument(
        '--output-json',
        help='Save analysis as JSON file'
    )
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = TestAnalyzer(args.test_dir)
    report = analyzer.analyze()
    
    # Print report
    print_report(report)
    
    # Save JSON if requested
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nAnalysis saved to {args.output_json}")


if __name__ == '__main__':
    main()