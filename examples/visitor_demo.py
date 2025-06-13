#!/usr/bin/env python3
"""
Demonstration of the visitor pattern implementation for PSH.

This script shows how different visitors can be used to perform various
operations on the same AST structure.
"""

import sys
import os

# Add parent directory to path so we can import PSH modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.ast_nodes import (
    TopLevel, StatementList, SimpleCommand, Pipeline, AndOrList,
    WhileLoop, ForLoop, IfConditional, FunctionDef, BreakStatement,
    Redirect
)
from psh.visitor import FormatterVisitor, ValidatorVisitor


def create_sample_ast():
    """Create a sample AST for demonstration."""
    # Build an AST representing this script:
    # ```
    # count_files() {
    #     local total=0
    #     for file in *.txt
    #     do
    #         if [ -f "$file" ]
    #         then
    #             echo "Processing $file"
    #             total=$((total + 1))
    #         fi
    #     done
    #     echo "Total files: $total"
    # }
    # 
    # count_files > output.log
    # ```
    
    ast = TopLevel(items=[
        # Function definition
        FunctionDef(
            name='count_files',
            body=StatementList(statements=[
                # local total=0
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['local', 'total=0'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ]),
                
                # for file in *.txt
                ForLoop(
                    variable='file',
                    items=['*.txt'],
                    body=StatementList(statements=[
                        # if [ -f "$file" ]
                        IfConditional(
                            condition=StatementList(statements=[
                                AndOrList(pipelines=[
                                    Pipeline(commands=[
                                        SimpleCommand(
                                            args=['[', '-f', '$file', ']'],
                                            arg_types=['WORD', 'WORD', 'VARIABLE', 'WORD']
                                        )
                                    ])
                                ])
                            ]),
                            then_part=StatementList(statements=[
                                # echo "Processing $file"
                                AndOrList(pipelines=[
                                    Pipeline(commands=[
                                        SimpleCommand(
                                            args=['echo', 'Processing $file'],
                                            arg_types=['WORD', 'STRING'],
                                            quote_types=[None, '"']
                                        )
                                    ])
                                ]),
                                # total=$((total + 1))
                                AndOrList(pipelines=[
                                    Pipeline(commands=[
                                        SimpleCommand(
                                            args=['total=$((total + 1))'],
                                            arg_types=['WORD']
                                        )
                                    ])
                                ])
                            ])
                        )
                    ])
                ),
                
                # echo "Total files: $total"
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', 'Total files: $total'],
                            arg_types=['WORD', 'STRING'],
                            quote_types=[None, '"']
                        )
                    ])
                ])
            ])
        ),
        
        # count_files > output.log
        StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[
                    SimpleCommand(
                        args=['count_files'],
                        arg_types=['WORD'],
                        redirects=[
                            Redirect(type='>', target='output.log')
                        ]
                    )
                ])
            ])
        ])
    ])
    
    return ast


def create_error_ast():
    """Create an AST with various errors for validation demonstration."""
    ast = TopLevel(items=[
        # Empty command
        StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[
                    SimpleCommand(args=[], arg_types=[])
                ])
            ])
        ]),
        
        # break outside of loop
        StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[
                    BreakStatement(level=2)
                ])
            ])
        ]),
        
        # cd with too many arguments
        StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[
                    SimpleCommand(
                        args=['cd', 'dir1', 'dir2'],
                        arg_types=['WORD', 'WORD', 'WORD']
                    )
                ])
            ])
        ]),
        
        # While loop with break exceeding nesting
        WhileLoop(
            condition=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['true'], arg_types=['WORD'])
                    ])
                ])
            ]),
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        BreakStatement(level=2)  # Error: only 1 loop deep
                    ])
                ])
            ])
        )
    ])
    
    return ast


def demonstrate_formatter():
    """Demonstrate the formatter visitor."""
    print("=== FORMATTER VISITOR DEMO ===\n")
    
    ast = create_sample_ast()
    formatter = FormatterVisitor(indent=2)
    formatted = formatter.visit(ast)
    
    print("Formatted output:")
    print("-" * 40)
    print(formatted)
    print("-" * 40)
    print()


def demonstrate_validator():
    """Demonstrate the validator visitor."""
    print("=== VALIDATOR VISITOR DEMO ===\n")
    
    # First, validate a correct AST
    print("Validating correct AST:")
    ast = create_sample_ast()
    validator = ValidatorVisitor()
    validator.visit(ast)
    print(validator.get_summary())
    print()
    
    # Now validate an AST with errors
    print("Validating AST with errors:")
    error_ast = create_error_ast()
    error_validator = ValidatorVisitor()
    error_validator.visit(error_ast)
    print(error_validator.get_summary())
    print()


def demonstrate_multiple_visitors():
    """Demonstrate using multiple visitors on the same AST."""
    print("=== MULTIPLE VISITORS DEMO ===\n")
    
    ast = create_sample_ast()
    
    # Format and validate the same AST
    formatter = FormatterVisitor()
    validator = ValidatorVisitor()
    
    formatted = formatter.visit(ast)
    validator.visit(ast)
    
    print("Formatted code:")
    print(formatted)
    print("\nValidation results:")
    print(validator.get_summary())
    print()


def demonstrate_ast_analysis():
    """Demonstrate analyzing AST structure."""
    print("=== AST ANALYSIS DEMO ===\n")
    
    from psh.visitor.base import ASTVisitor
    
    class NodeCounterVisitor(ASTVisitor[None]):
        """Count different types of nodes in the AST."""
        
        def __init__(self):
            self.counts = {}
        
        def visit(self, node):
            node_type = node.__class__.__name__
            self.counts[node_type] = self.counts.get(node_type, 0) + 1
            # Continue visiting children
            super().visit(node)
        
        def generic_visit(self, node):
            # For this visitor, we want to visit all nodes
            # so we don't raise an error for unknown nodes
            from dataclasses import is_dataclass, fields
            
            if is_dataclass(node):
                for field in fields(node):
                    value = getattr(node, field.name)
                    if isinstance(value, list):
                        for item in value:
                            if hasattr(item, '__class__') and hasattr(item.__class__, '__name__'):
                                self.visit(item)
                    elif hasattr(value, '__class__') and hasattr(value.__class__, '__name__'):
                        self.visit(value)
    
    ast = create_sample_ast()
    counter = NodeCounterVisitor()
    counter.visit(ast)
    
    print("Node type counts:")
    for node_type, count in sorted(counter.counts.items()):
        print(f"  {node_type}: {count}")
    print()


if __name__ == '__main__':
    demonstrate_formatter()
    demonstrate_validator()
    demonstrate_multiple_visitors()
    demonstrate_ast_analysis()