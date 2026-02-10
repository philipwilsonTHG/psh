"""Parse tree visualization builtin for interactive AST inspection."""

from typing import List

from ..lexer import tokenize
from ..parser.recursive_descent.helpers import ParseError
from ..parser.recursive_descent.parser import Parser
from .base import Builtin
from .registry import builtin


@builtin
class ParseTreeBuiltin(Builtin):
    """Show parse tree for shell commands."""

    name = "parse-tree"

    def execute(self, args: List[str], shell) -> int:
        """Execute the parse-tree builtin.

        Usage: parse-tree [OPTIONS] COMMAND

        Options:
            -f FORMAT    Output format: pretty, tree, compact, dot (default: tree)
            -p           Show position information
            -h           Show this help

        Examples:
            parse-tree "echo hello | grep world"
            parse-tree -f pretty "if true; then echo hi; fi"
            parse-tree -f dot "for i in 1 2 3; do echo $i; done"
        """
        if len(args) < 2:
            self.error("usage: parse-tree [options] command", shell)
            return 2

        # Parse options
        format_type = "tree"
        show_positions = False
        command_args = []

        i = 1
        while i < len(args):
            arg = args[i]

            if arg == "-h" or arg == "--help":
                print(self.execute.__doc__)
                return 0
            elif arg == "-f" or arg == "--format":
                if i + 1 >= len(args):
                    self.error("-f requires a format argument", shell)
                    return 2
                format_type = args[i + 1]
                if format_type not in ["pretty", "tree", "compact", "dot"]:
                    self.error(f"invalid format: {format_type}", shell)
                    return 2
                i += 2
            elif arg == "-p" or arg == "--positions":
                show_positions = True
                i += 1
            elif arg.startswith("-"):
                self.error(f"unknown option: {arg}", shell)
                return 2
            else:
                # Rest are command arguments
                command_args = args[i:]
                break

        if not command_args:
            self.error("no command specified", shell)
            return 2

        # Join command arguments back into a single command
        command = " ".join(command_args)

        try:
            # Parse the command
            tokens = tokenize(command)
            parser = Parser(tokens, source_text=command)
            ast = parser.parse()

            # Generate output based on format
            if format_type == "pretty":
                from ..parser.visualization import ASTPrettyPrinter
                formatter = ASTPrettyPrinter(
                    show_positions=show_positions,
                    compact_mode=False
                )
                output = formatter.visit(ast)

            elif format_type == "tree":
                from ..parser.visualization import AsciiTreeRenderer
                output = AsciiTreeRenderer.render(
                    ast,
                    show_positions=show_positions,
                    compact_mode=False
                )

            elif format_type == "compact":
                from ..parser.visualization import CompactAsciiTreeRenderer
                output = CompactAsciiTreeRenderer.render(ast)

            elif format_type == "dot":
                from ..parser.visualization import ASTDotGenerator
                generator = ASTDotGenerator(
                    show_positions=show_positions,
                    color_by_type=True
                )
                output = generator.to_dot(ast)

                # Add helpful comment for DOT format
                print("# Graphviz DOT format - save to file and render with:")
                print("# dot -Tpng output.dot -o ast.png && xdg-open ast.png")
                print()

            print(output)
            return 0

        except ParseError as e:
            self.error(f"parse error: {e}", shell)
            return 1
        except (ValueError, TypeError, AttributeError) as e:
            self.error(f"visualization error: {e}", shell)
            return 1


@builtin
class ShowASTBuiltin(Builtin):
    """Alias for parse-tree with pretty format."""

    name = "show-ast"

    def execute(self, args: List[str], shell) -> int:
        """Execute the show-ast builtin (alias for parse-tree -f pretty)."""
        # Prepend -f pretty to the arguments
        new_args = ["show-ast", "-f", "pretty"] + args[1:]

        # Delegate to parse-tree builtin
        parse_tree = ParseTreeBuiltin()
        return parse_tree.execute(new_args, shell)


@builtin
class ASTDotBuiltin(Builtin):
    """Generate Graphviz DOT format for AST."""

    name = "ast-dot"

    def execute(self, args: List[str], shell) -> int:
        """Execute the ast-dot builtin (alias for parse-tree -f dot)."""
        # Prepend -f dot to the arguments
        new_args = ["ast-dot", "-f", "dot"] + args[1:]

        # Delegate to parse-tree builtin
        parse_tree = ParseTreeBuiltin()
        return parse_tree.execute(new_args, shell)
