"""Parser factory for creating configured parser instances."""


def create_parser(tokens, shell, source_text=None):
    """Create a parser with configuration based on shell options.

    Args:
        tokens: List of tokens to parse.
        shell: Shell instance for reading options and active parser selection.
        source_text: Optional source text for error reporting.

    Returns:
        Configured Parser instance or wrapper with a .parse() method.
    """
    from ..parser import Parser
    from ..parser.config import ParserConfig

    parser_config = ParserConfig(
        trace_parsing=shell.state.options.get('debug-parser', False)
    )

    if shell._active_parser == 'combinator':
        from ..parser.combinators.parser import ParserCombinatorShellParser
        pc = ParserCombinatorShellParser(parser_config)

        class ParserWrapper:
            def __init__(self, parser, tokens):
                self._parser = parser
                self.tokens = tokens

            def parse(self):
                return self._parser.parse(self.tokens)

        return ParserWrapper(pc, tokens)
    else:
        return Parser(tokens, config=parser_config)
