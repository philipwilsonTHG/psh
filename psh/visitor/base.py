"""
Base visitor classes for PSH AST traversal.

This module defines the abstract base class for implementing the visitor pattern
on PSH AST nodes.
"""

from abc import ABC
from typing import Generic, TypeVar

from ..ast_nodes import ASTNode

T = TypeVar('T')


class ASTVisitor(ABC, Generic[T]):
    """
    Base class for AST visitors using double dispatch.

    Subclasses should implement visit_* methods for each AST node type they
    want to handle. The visit() method automatically dispatches to the correct
    visit_* method based on the node's class name.
    """

    def __init__(self):
        # Cache for method lookups to improve performance
        self._method_cache = {}

    def visit(self, node: ASTNode) -> T:
        """
        Dispatch to the appropriate visit_* method based on node type.

        Args:
            node: The AST node to visit

        Returns:
            The result of visiting the node
        """
        # Use cached method if available
        node_class = node.__class__
        if node_class not in self._method_cache:
            method_name = f'visit_{node_class.__name__}'
            self._method_cache[node_class] = getattr(self, method_name, self.generic_visit)

        return self._method_cache[node_class](node)

    def generic_visit(self, node: ASTNode) -> T:
        """
        Called if no explicit visitor method exists for a node.

        Subclasses can override this to provide a default behavior for
        unhandled nodes. By default, it raises an exception.

        Args:
            node: The unhandled AST node

        Raises:
            NotImplementedError: If no visitor is defined for the node type
        """
        raise NotImplementedError(
            f"No visit_{node.__class__.__name__} method defined in {self.__class__.__name__}"
        )
