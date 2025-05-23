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
        
        # Built-in command dispatch table
        self.builtins = {
            'exit': self._builtin_exit,
            'cd': self._builtin_cd,
            'export': self._builtin_export,
            'pwd': self._builtin_pwd,
            'echo': self._builtin_echo,
            'env': self._builtin_env,
            'unset': self._builtin_unset,
            'source': self._builtin_source,
            '.': self._builtin_source,
        }
    
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
        if args[0] in self.builtins:
            # Handle redirections for built-ins
            stdout_backup = None
            stdin_backup = None
            try:
                for redirect in command.redirects:
                    if redirect.type == '<':
                        stdin_backup = sys.stdin
                        sys.stdin = open(redirect.target, 'r')
                    elif redirect.type == '>':
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'w')
                    elif redirect.type == '>>':
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'a')
                
                return self.builtins[args[0]](args)
            finally:
                # Restore original stdin/stdout
                if stdin_backup:
                    sys.stdin.close()
                    sys.stdin = stdin_backup
                if stdout_backup:
                    sys.stdout.close()
                    sys.stdout = stdout_backup
        
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
    
    # Built-in command implementations
    def _builtin_exit(self, args):
        exit_code = int(args[1]) if len(args) > 1 else 0
        sys.exit(exit_code)
    
    def _builtin_cd(self, args):
        try:
            path = args[1] if len(args) > 1 else os.environ.get('HOME', '/')
            os.chdir(path)
            return 0
        except OSError as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1
    
    def _builtin_export(self, args):
        if len(args) > 1 and '=' in args[1]:
            var, value = args[1].split('=', 1)
            self.env[var] = value
            os.environ[var] = value
        return 0
    
    def _builtin_pwd(self, args):
        print(os.getcwd())
        return 0
    
    def _builtin_echo(self, args):
        # Join args with spaces, handling empty args list
        output = ' '.join(args[1:])
        print(output)
        return 0
    
    def _builtin_env(self, args):
        # Print all environment variables
        for key, value in sorted(self.env.items()):
            print(f"{key}={value}")
        return 0
    
    def _builtin_unset(self, args):
        # Remove environment variables
        for var in args[1:]:
            self.env.pop(var, None)
            os.environ.pop(var, None)
        return 0
    
    def _builtin_source(self, args):
        if len(args) < 2:
            print(f"{args[0]}: filename argument required", file=sys.stderr)
            return 1
        try:
            with open(args[1], 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.run_command(line)
            return 0
        except FileNotFoundError:
            print(f"{args[0]}: {args[1]}: No such file or directory", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"{args[0]}: {args[1]}: {e}", file=sys.stderr)
            return 1


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