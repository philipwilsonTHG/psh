#!/usr/bin/env python3
"""Main entry point for psh when run as a module."""

import sys
from .shell import Shell


def main():
    """Main entry point for psh command."""
    # Check for debug flags first
    debug_ast = False
    debug_tokens = False
    debug_scopes = False
    debug_expansion = False
    debug_expansion_detail = False
    debug_exec = False
    debug_exec_fork = False
    norc = False
    rcfile = None
    validate_only = False
    legacy_executor = False  # Default is now visitor executor
    args = sys.argv[1:]
    
    # Extract debug flags
    if "--debug-ast" in args:
        debug_ast = True
        args.remove("--debug-ast")
    if "--debug-tokens" in args:
        debug_tokens = True
        args.remove("--debug-tokens")
    if "--debug-scopes" in args:
        debug_scopes = True
        args.remove("--debug-scopes")
    if "--debug-expansion" in args:
        debug_expansion = True
        args.remove("--debug-expansion")
    if "--debug-expansion-detail" in args:
        debug_expansion_detail = True
        debug_expansion = True  # Detail implies basic
        args.remove("--debug-expansion-detail")
    if "--debug-exec" in args:
        debug_exec = True
        args.remove("--debug-exec")
    if "--debug-exec-fork" in args:
        debug_exec_fork = True
        debug_exec = True  # Fork implies basic
        args.remove("--debug-exec-fork")
    
    # Extract validation flag
    if "--validate" in args:
        validate_only = True
        args.remove("--validate")
    
    # Extract legacy executor flag
    if "--legacy-executor" in args:
        legacy_executor = True
        args.remove("--legacy-executor")
    
    # Extract RC file flags
    if "--norc" in args:
        norc = True
        args.remove("--norc")
    
    # Handle --rcfile
    for i, arg in enumerate(args):
        if arg == "--rcfile":
            if i + 1 < len(args):
                rcfile = args[i + 1]
                args = args[:i] + args[i+2:]  # Remove both --rcfile and its argument
                break
            else:
                print("psh: --rcfile requires an argument", file=sys.stderr)
                sys.exit(2)
        elif arg.startswith("--rcfile="):
            rcfile = arg[9:]  # Remove "--rcfile=" prefix
            args.remove(arg)
            break
    
    # Update sys.argv to remove the flags
    sys.argv = [sys.argv[0]] + args
    
    shell = Shell(debug_ast=debug_ast, debug_tokens=debug_tokens, debug_scopes=debug_scopes, 
                  debug_expansion=debug_expansion, debug_expansion_detail=debug_expansion_detail,
                  debug_exec=debug_exec, debug_exec_fork=debug_exec_fork,
                  norc=norc, rcfile=rcfile, validate_only=validate_only, 
                  use_legacy_executor=legacy_executor)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            # Execute command with -c flag
            command = sys.argv[2]
            # Set positional parameters from remaining arguments
            shell.set_positional_params(sys.argv[3:])
            exit_code = shell.run_command(command, add_to_history=False)
            sys.exit(exit_code)
        elif sys.argv[1] in ("--version", "-V"):
            # Show version
            from .version import get_version_info
            print(get_version_info())
            sys.exit(0)
        elif sys.argv[1] in ("--help", "-h"):
            # Show help
            print("Usage: psh [options] [script [args...]]")
            print("       psh [options] -c command [args...]")
            print("\nPython Shell (psh) - An educational Unix shell implementation")
            print("\nOptions:")
            print("  -c command       Execute command and exit")
            print("  -h, --help       Show this help message and exit")
            print("  -V, --version    Show version information and exit")
            print("  --norc           Do not read ~/.pshrc on startup")
            print("  --rcfile FILE    Read FILE instead of ~/.pshrc")
            print("  --debug-ast      Print AST before execution (debugging)")
            print("  --debug-tokens   Print tokens before parsing (debugging)")
            print("  --debug-scopes   Print variable scope operations (debugging)")
            print("  --debug-expansion Print expansions as they occur (debugging)")
            print("  --debug-expansion-detail Print detailed expansion steps (debugging)")
            print("  --debug-exec     Print executor operations (debugging)")
            print("  --debug-exec-fork Print fork/exec details (debugging)")
            print("  --validate       Validate script without executing (check for errors)")
            print("  --legacy-executor Use legacy executor instead of visitor pattern")
            print("\nArguments:")
            print("  script           Script file to execute")
            print("  args             Arguments passed to script or command")
            print("\nExamples:")
            print("  psh                          # Start interactive shell")
            print("  psh script.sh arg1 arg2      # Execute script with arguments")
            print("  psh -c 'echo $1' hello       # Execute command with arguments")
            print("  source script.sh arg1        # Source script with arguments")
            sys.exit(0)
        elif sys.argv[1] == "--":
            # End of options marker
            if len(sys.argv) > 2:
                script_path = sys.argv[2]
                script_args = sys.argv[3:]
                exit_code = shell.run_script(script_path, script_args)
                sys.exit(exit_code)
            else:
                # No script after --, start interactive mode
                shell.interactive_loop()
        elif sys.argv[1].startswith("-"):
            # Unknown option
            print(f"psh: {sys.argv[1]}: invalid option", file=sys.stderr)
            print("Try 'psh --help' for more information.", file=sys.stderr)
            sys.exit(2)
        else:
            # Script file execution
            script_path = sys.argv[1]
            script_args = sys.argv[2:]
            exit_code = shell.run_script(script_path, script_args)
            sys.exit(exit_code)
    else:
        # Check if stdin is a terminal
        if sys.stdin.isatty():
            # Interactive mode
            shell.interactive_loop()
        else:
            # Non-interactive mode - read all commands from stdin and execute as a script
            script_content = sys.stdin.read()
            if script_content.strip():
                exit_code = shell.run_command(script_content, add_to_history=False)
                sys.exit(exit_code)
            sys.exit(0)


if __name__ == "__main__":
    main()