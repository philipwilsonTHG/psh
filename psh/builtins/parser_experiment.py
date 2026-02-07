"""Builtin commands for parser experimentation.

This module provides builtin commands for selecting, comparing, and
experimenting with different parser implementations.
"""

import json
import time
from typing import List

from ..parser.implementations import ParserCombinatorShellParser, RecursiveDescentAdapter
from ..parser.parser_registry import ParserRegistry, ParserStrategy
from .base import Builtin
from .registry import builtin

# Register the available parsers
ParserRegistry.register(
    "recursive_descent",
    RecursiveDescentAdapter,
    aliases=["default", "rd", "recursive"]
)

ParserRegistry.register(
    "parser_combinator",
    ParserCombinatorShellParser,
    aliases=["combinator", "pc", "functional"]
)


@builtin
class ParserSelectBuiltin(Builtin):
    """Select the active parser implementation."""
    name = "parser-select"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute parser-select command.
        
        Usage:
            parser-select              # List available parsers
            parser-select PARSER       # Switch to specified parser
            parser-select --info NAME  # Show detailed parser info
        """
        if len(args) == 1:
            # List available parsers
            return self._list_parsers(shell)

        if args[1] == "--info" and len(args) > 2:
            # Show detailed info about a parser
            return self._show_parser_info(args[2], shell)

        # Select a parser
        parser_name = args[1]
        return self._select_parser(parser_name, shell)

    def _list_parsers(self, shell: 'Shell') -> int:
        """List all available parsers."""
        print("Available parsers:")
        print()

        for info in ParserRegistry.get_parser_info():
            name = info['name']
            aliases = info.get('aliases', [])
            desc = info.get('description', 'No description')

            # Mark current parser
            current = ""
            if hasattr(shell, 'parser_strategy'):
                if shell.parser_strategy.current_parser == name:
                    current = " (current)"

            print(f"  {name}{current}")
            if aliases:
                print(f"    Aliases: {', '.join(aliases)}")
            print(f"    {desc}")
            print()

        return 0

    def _show_parser_info(self, parser_name: str, shell: 'Shell') -> int:
        """Show detailed information about a parser."""
        info_list = ParserRegistry.get_parser_info(parser_name)
        if not info_list:
            self.error(f"Unknown parser: {parser_name}", shell)
            return 1

        info = info_list[0]

        print(f"=== Parser: {info['name']} ===")
        print()
        print(f"Description: {info.get('description', 'N/A')}")
        print()

        if info.get('aliases'):
            print(f"Aliases: {', '.join(info['aliases'])}")
            print()

        if 'characteristics' in info:
            print("Characteristics:")
            chars = info['characteristics']
            for key, value in chars.items():
                print(f"  {key}: {value}")
            print()

        if 'configuration_options' in info:
            print("Configuration options:")
            for opt, desc in info['configuration_options'].items():
                print(f"  {opt}: {desc}")
            print()

        return 0

    def _select_parser(self, parser_name: str, shell: 'Shell') -> int:
        """Select a parser implementation."""
        if parser_name not in ParserRegistry.list_all_names():
            self.error(f"Unknown parser: {parser_name}", shell)
            print("Use 'parser-select' to see available parsers")
            return 1

        # Initialize parser strategy if needed
        if not hasattr(shell, 'parser_strategy'):
            shell.parser_strategy = ParserStrategy(parser_name)
        else:
            shell.parser_strategy.switch_parser(parser_name)

        # Get the canonical name
        parser_class = ParserRegistry.get(parser_name)
        if parser_class:
            parser = parser_class()
            print(f"Switched to {parser.get_name()} parser")

        return 0


@builtin
class ParserCompareBuiltin(Builtin):
    """Compare different parser implementations."""
    name = "parser-compare"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute parser-compare command.
        
        Usage:
            parser-compare 'command'              # Compare all parsers
            parser-compare 'command' p1 p2 ...    # Compare specific parsers
            parser-compare --json 'command'       # Output as JSON
        """
        if len(args) < 2:
            self.error("Usage: parser-compare 'command' [parser1 parser2 ...]", shell)
            return 1

        # Parse options
        output_json = False
        command_idx = 1

        if args[1] == "--json":
            output_json = True
            command_idx = 2
            if len(args) < 3:
                self.error("Usage: parser-compare --json 'command'", shell)
                return 1

        command = args[command_idx]
        parser_names = args[command_idx + 1:] if len(args) > command_idx + 1 else None

        # Tokenize the command
        try:
            from ..lexer import tokenize
            tokens = tokenize(command)
        except Exception as e:
            self.error(f"Failed to tokenize command: {e}", shell)
            return 1

        # Compare parsers
        if hasattr(shell, 'parser_strategy'):
            results = shell.parser_strategy.compare_parsers(tokens, parser_names)
        else:
            # Create temporary strategy
            strategy = ParserStrategy()
            results = strategy.compare_parsers(tokens, parser_names)

        # Output results
        if output_json:
            print(json.dumps(results, indent=2))
        else:
            self._print_comparison_results(command, results)

        return 0

    def _print_comparison_results(self, command: str, results: dict):
        """Print comparison results in human-readable format."""
        print(f"Comparing parsers for: {command}")
        print("=" * 60)
        print()

        # Summary table
        print("Parser            | Success | Time (ms) | Tokens | AST Type")
        print("-" * 60)

        for parser_name, result in results.items():
            success = "✓" if result.get('success') else "✗"

            if result.get('success'):
                metrics = result.get('metrics', {})
                time_ms = metrics.get('parse_time_ms', 0)
                tokens = metrics.get('tokens_consumed', 0)
                ast_type = result.get('ast_type', 'N/A')

                print(f"{parser_name:16} | {success:7} | {time_ms:9.2f} | "
                      f"{tokens:6} | {ast_type}")
            else:
                error = result.get('error', 'Unknown error')[:30]
                print(f"{parser_name:16} | {success:7} | Error: {error}...")

        print()

        # Detailed results
        for parser_name, result in results.items():
            print(f"\n=== {parser_name} ===")

            if result.get('success'):
                metrics = result.get('metrics', {})
                chars = result.get('characteristics', {})

                print("Metrics:")
                print(f"  Parse time: {metrics.get('parse_time_ms', 0):.2f} ms")
                print(f"  Tokens consumed: {metrics.get('tokens_consumed', 0)}")
                print(f"  Rules evaluated: {metrics.get('rules_evaluated', 0)}")

                if metrics.get('backtrack_count', 0) > 0:
                    print(f"  Backtracks: {metrics.get('backtrack_count', 0)}")

                print("\nCharacteristics:")
                print(f"  Type: {chars.get('type', 'unknown')}")
                print(f"  Backtracking: {chars.get('backtracking', False)}")
                print(f"  Error recovery: {chars.get('error_recovery', False)}")

            else:
                print(f"Failed: {result.get('error', 'Unknown error')}")


@builtin
class ParserExplainBuiltin(Builtin):
    """Explain how a parser works on given input."""
    name = "parser-explain"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute parser-explain command.
        
        Usage:
            parser-explain 'command'              # Explain with current parser
            parser-explain PARSER 'command'       # Explain with specific parser
        """
        if len(args) < 2:
            self.error("Usage: parser-explain [PARSER] 'command'", shell)
            return 1

        # Parse arguments
        if len(args) == 2:
            # Use current parser
            command = args[1]
            if hasattr(shell, 'parser_strategy'):
                parser_name = shell.parser_strategy.current_parser
            else:
                parser_name = "recursive_descent"
        else:
            # Use specified parser
            parser_name = args[1]
            command = args[2]

        # Check parser exists
        if parser_name not in ParserRegistry.list_all_names():
            self.error(f"Unknown parser: {parser_name}", shell)
            return 1

        # Tokenize command
        try:
            from ..lexer import tokenize
            tokens = tokenize(command)
        except Exception as e:
            self.error(f"Failed to tokenize: {e}", shell)
            return 1

        # Get explanation
        try:
            parser = ParserRegistry.create(parser_name)
            explanation = parser.explain_parse(tokens)
            print(explanation)
        except Exception as e:
            self.error(f"Failed to explain: {e}", shell)
            return 1

        return 0


@builtin
class ParserBenchmarkBuiltin(Builtin):
    """Benchmark parser performance."""
    name = "parser-benchmark"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute parser-benchmark command.
        
        Usage:
            parser-benchmark 'command' [iterations]
        """
        if len(args) < 2:
            self.error("Usage: parser-benchmark 'command' [iterations]", shell)
            return 1

        command = args[1]
        iterations = int(args[2]) if len(args) > 2 else 100

        # Tokenize once
        try:
            from ..lexer import tokenize
            tokens = tokenize(command)
        except Exception as e:
            self.error(f"Failed to tokenize: {e}", shell)
            return 1

        print(f"Benchmarking parsers with {iterations} iterations")
        print(f"Command: {command}")
        print(f"Tokens: {len(tokens)}")
        print()

        # Benchmark each parser
        for parser_name in ParserRegistry.list_parsers():
            try:
                parser = ParserRegistry.create(parser_name)

                # Warmup
                for _ in range(10):
                    parser.parse(tokens.copy())

                # Benchmark
                start_time = time.perf_counter()
                for _ in range(iterations):
                    parser.parse(tokens.copy())
                elapsed = time.perf_counter() - start_time

                avg_time = (elapsed / iterations) * 1000  # Convert to ms
                print(f"{parser_name:20} {avg_time:8.3f} ms/parse")

            except Exception as e:
                print(f"{parser_name:20} Failed: {e}")

        return 0
