#!/usr/bin/env python3

from tokenizer import tokenize
from parser import parse
from ast_nodes import Command, Pipeline, CommandList, Redirect


def print_tokens(tokens):
    print("Tokens:")
    for token in tokens:
        print(f"  {token.type.name:15} '{token.value}'")
    print()


def print_ast(node, indent=0):
    prefix = "  " * indent
    
    if isinstance(node, CommandList):
        print(f"{prefix}CommandList:")
        for pipeline in node.pipelines:
            print_ast(pipeline, indent + 1)
    
    elif isinstance(node, Pipeline):
        print(f"{prefix}Pipeline:")
        for command in node.commands:
            print_ast(command, indent + 1)
    
    elif isinstance(node, Command):
        print(f"{prefix}Command:")
        print(f"{prefix}  args: {node.args}")
        if node.redirects:
            print(f"{prefix}  redirects:")
            for redirect in node.redirects:
                print_ast(redirect, indent + 2)
        if node.background:
            print(f"{prefix}  background: True")
    
    elif isinstance(node, Redirect):
        print(f"{prefix}Redirect: {node.type} -> {node.target}")


def demo_parse(command_string):
    print(f"Parsing: {command_string!r}")
    print("-" * 50)
    
    try:
        # Tokenize
        tokens = tokenize(command_string)
        print_tokens(tokens)
        
        # Parse
        ast = parse(tokens)
        print("AST:")
        print_ast(ast)
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n")


if __name__ == "__main__":
    # Basic command
    demo_parse("ls -la")
    
    # Pipeline
    demo_parse("cat file.txt | grep pattern | wc -l")
    
    # Redirections
    demo_parse("echo hello > output.txt")
    demo_parse("sort < input.txt > output.txt")
    demo_parse("echo world >> output.txt")
    
    # Multiple commands
    demo_parse("echo first; echo second; echo third")
    
    # Background command
    demo_parse("sleep 10 &")
    
    # Complex example
    demo_parse("cat < input.txt | grep -v error | sort > output.txt; echo done")
    
    # With quotes
    demo_parse('echo "Hello World" > file.txt')
    
    # With variables
    demo_parse('echo $HOME $USER')
    
    # With glob patterns
    demo_parse('ls *.py')
    demo_parse('echo file?.txt')
    demo_parse('rm [abc]*.log')
    demo_parse('echo "*.txt"')  # Quoted glob not expanded