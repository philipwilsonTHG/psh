"""
Parser utilities for PSH shell.

This module contains utility functions for parser operations like heredoc handling.
"""

from typing import Union, List, Dict
from ..token_types import Token
from ..ast_nodes import CommandList, TopLevel


class ParserUtils:
    """Utility functions for parser operations."""
    
    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser
    
    def populate_heredoc_content(self, node, heredoc_map: dict):
        """Recursively populate heredoc content in AST nodes."""
        if hasattr(node, 'redirects') and node.redirects:
            for redirect in node.redirects:
                if redirect.type in ('<<', '<<-') and redirect.target in heredoc_map:
                    heredoc_info = heredoc_map[redirect.target]
                    redirect.heredoc_content = heredoc_info['content']
                    # Store whether the delimiter was quoted for expansion decisions
                    redirect.heredoc_quoted = heredoc_info['quoted']
        
        # Recursively process child nodes
        if hasattr(node, 'statements') and node.statements:
            for stmt in node.statements:
                self.populate_heredoc_content(stmt, heredoc_map)
        
        if hasattr(node, 'commands') and node.commands:
            for cmd in node.commands:
                self.populate_heredoc_content(cmd, heredoc_map)
        
        if hasattr(node, 'pipelines') and node.pipelines:
            for pipeline in node.pipelines:
                self.populate_heredoc_content(pipeline, heredoc_map)
        
        # Handle control structures
        if hasattr(node, 'condition'):
            self.populate_heredoc_content(node.condition, heredoc_map)
        if hasattr(node, 'then_part'):
            self.populate_heredoc_content(node.then_part, heredoc_map)
        if hasattr(node, 'else_part') and node.else_part:
            self.populate_heredoc_content(node.else_part, heredoc_map)
        if hasattr(node, 'elif_parts'):
            for elif_condition, elif_then in node.elif_parts:
                self.populate_heredoc_content(elif_condition, heredoc_map)
                self.populate_heredoc_content(elif_then, heredoc_map)
        if hasattr(node, 'body'):
            self.populate_heredoc_content(node.body, heredoc_map)
        if hasattr(node, 'items') and hasattr(node.items, '__iter__'):
            for item in node.items:
                self.populate_heredoc_content(item, heredoc_map)


def parse_with_heredocs(tokens: List[Token], heredoc_map: dict) -> Union[CommandList, TopLevel]:
    """Parse a list of tokens into an AST with pre-collected heredoc content."""
    from .main import Parser
    parser = Parser(tokens)
    parser.heredoc_map = heredoc_map
    ast = parser.parse()
    # Populate heredoc content in the AST
    parser.utils.populate_heredoc_content(ast, heredoc_map)
    return ast