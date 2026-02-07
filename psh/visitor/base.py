"""
Base visitor classes for PSH AST traversal.

This module defines the abstract base classes for implementing the visitor pattern
on PSH AST nodes. It provides both read-only visitors and transforming visitors.
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


class ASTTransformer(ASTVisitor[ASTNode]):
    """
    Base class for AST transformers that modify or replace nodes.
    
    Unlike ASTVisitor which is read-only, ASTTransformer can return modified
    or replaced nodes. This is useful for optimization passes, desugaring,
    or other AST transformations.
    """

    def generic_visit(self, node: ASTNode) -> ASTNode:
        """
        Default transformation that returns the node unchanged.
        
        Subclasses can override this to provide default transformation behavior.
        
        Args:
            node: The AST node to transform
            
        Returns:
            The original node (no transformation)
        """
        return node

    def transform_children(self, node: ASTNode) -> None:
        """
        Helper method to recursively transform child nodes.
        
        This method inspects the node's attributes and recursively transforms
        any child AST nodes found in lists or as direct attributes.
        
        Args:
            node: The parent node whose children should be transformed
        """
        import dataclasses

        if not dataclasses.is_dataclass(node):
            return

        # Get all fields of the dataclass
        for field in dataclasses.fields(node):
            value = getattr(node, field.name)

            if value is None:
                continue

            # Handle single AST nodes
            if isinstance(value, ASTNode):
                new_value = self.visit(value)
                setattr(node, field.name, new_value)

            # Handle lists of AST nodes
            elif isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ASTNode):
                        new_list.append(self.visit(item))
                    else:
                        new_list.append(item)
                setattr(node, field.name, new_list)

            # Handle tuples (like elif_parts in IfConditional)
            elif isinstance(value, tuple) and value:
                new_items = []
                for item in value:
                    if isinstance(item, ASTNode):
                        new_items.append(self.visit(item))
                    else:
                        new_items.append(item)
                setattr(node, field.name, tuple(new_items))


class CompositeVisitor(ASTVisitor[None]):
    """
    A visitor that runs multiple visitors in sequence.
    
    This is useful for combining multiple analysis passes or for collecting
    different types of information in a single traversal.
    """

    def __init__(self, visitors: list[ASTVisitor]):
        """
        Initialize with a list of visitors to run.
        
        Args:
            visitors: List of visitors to execute in order
        """
        self.visitors = visitors

    def visit(self, node: ASTNode) -> None:
        """
        Run all visitors on the given node.
        
        Args:
            node: The AST node to visit
        """
        for visitor in self.visitors:
            visitor.visit(node)

    def generic_visit(self, node: ASTNode) -> None:
        """
        No-op for composite visitor.
        
        Individual visitors handle their own generic_visit behavior.
        """
        pass
