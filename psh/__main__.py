#!/usr/bin/env python3
"""Main entry point for psh when run as a module."""

import sys
from .shell import Shell


def main():
    """Main entry point for psh command."""
    shell = Shell()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            # Execute command with -c flag
            command = sys.argv[2]
            # Set positional parameters from remaining arguments
            shell.set_positional_params(sys.argv[3:])
            exit_code = shell.run_command(command, add_to_history=False)
            sys.exit(exit_code)
        elif sys.argv[1] == "--version":
            # Show version
            from .version import get_version_info
            print(get_version_info())
            sys.exit(0)
        elif sys.argv[1] == "--help":
            # Show help
            print("Usage: psh [-c command] [script] [--version] [--help]")
            print("\nPython Shell (psh) - An educational Unix shell implementation")
            print("\nOptions:")
            print("  -c command    Execute command and exit")
            print("  script        Execute script file")
            print("  --version     Show version information")
            print("  --help        Show this help message")
            sys.exit(0)
        elif sys.argv[1].startswith("-"):
            # Unknown option
            print(f"psh: {sys.argv[1]}: invalid option", file=sys.stderr)
            print("Try 'psh --help' for more information.", file=sys.stderr)
            sys.exit(2)
        else:
            # Script file execution
            script_path = sys.argv[1]
            # Set positional parameters from script arguments
            shell.set_positional_params(sys.argv[2:])
            exit_code = shell.run_script(script_path)
            sys.exit(exit_code)
    else:
        # Interactive mode
        shell.interactive_loop()


if __name__ == "__main__":
    main()