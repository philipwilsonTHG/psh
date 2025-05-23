#!/usr/bin/env python3

import os
import sys
import subprocess
from tokenizer import tokenize
from parser import parse, ParseError
from ast_nodes import Command, Pipeline, CommandList, Redirect


class Shell:
    def __init__(self):
        self.env = os.environ.copy()
        self.last_exit_code = 0
    
    def execute_command(self, command: Command):
        # Expand variables in arguments
        args = []
        for arg in command.args:
            if arg.startswith('$'):
                var_name = arg[1:]
                args.append(self.env.get(var_name, ''))
            else:
                args.append(arg)
        
        if not args:
            return 0
        
        # Check for built-in commands
        if args[0] == 'exit':
            exit_code = int(args[1]) if len(args) > 1 else 0
            sys.exit(exit_code)
        elif args[0] == 'cd':
            try:
                path = args[1] if len(args) > 1 else os.environ.get('HOME', '/')
                os.chdir(path)
                return 0
            except OSError as e:
                print(f"cd: {e}", file=sys.stderr)
                return 1
        elif args[0] == 'export':
            if len(args) > 1 and '=' in args[1]:
                var, value = args[1].split('=', 1)
                self.env[var] = value
                os.environ[var] = value
            return 0
        
        # Execute external command
        try:
            # Set up redirections
            stdin = None
            stdout = None
            stderr = None
            
            for redirect in command.redirects:
                if redirect.type == '<':
                    stdin = open(redirect.target, 'r')
                elif redirect.type == '>':
                    stdout = open(redirect.target, 'w')
                elif redirect.type == '>>':
                    stdout = open(redirect.target, 'a')
            
            # Run the command
            proc = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=self.env
            )
            
            if command.background:
                print(f"[{proc.pid}]")
                return 0
            else:
                proc.wait()
                return proc.returncode
        
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1
        finally:
            # Close any opened files
            if stdin and stdin != sys.stdin:
                stdin.close()
            if stdout and stdout != sys.stdout:
                stdout.close()
    
    def execute_pipeline(self, pipeline: Pipeline):
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            return self.execute_command(pipeline.commands[0])
        
        # Execute pipeline - simplified version
        # In a real shell, you'd create pipes between processes
        print("Pipeline execution not yet implemented", file=sys.stderr)
        return 1
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        for pipeline in command_list.pipelines:
            exit_code = self.execute_pipeline(pipeline)
            self.last_exit_code = exit_code
        return exit_code
    
    def run_command(self, command_string: str):
        try:
            tokens = tokenize(command_string)
            ast = parse(tokens)
            return self.execute_command_list(ast)
        except ParseError as e:
            print(f"psh: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"psh: unexpected error: {e}", file=sys.stderr)
            return 1
    
    def interactive_loop(self):
        print("Python Shell (psh) - Educational Unix Shell")
        print("Type 'exit' to quit")
        
        while True:
            try:
                # Simple prompt
                prompt = f"{os.getcwd()}$ "
                command = input(prompt)
                
                if command.strip():
                    self.run_command(command)
            
            except EOFError:
                print("\nexit")
                break
            except KeyboardInterrupt:
                print("^C")
                continue


if __name__ == "__main__":
    shell = Shell()
    
    if len(sys.argv) > 1:
        # Execute command from arguments
        command = ' '.join(sys.argv[1:])
        exit_code = shell.run_command(command)
        sys.exit(exit_code)
    else:
        # Interactive mode
        shell.interactive_loop()