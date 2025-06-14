"""
Visitor pipeline and registry for PSH.

This module provides a registry for managing visitors and a pipeline
system for composing and running multiple visitors on an AST.
"""

from typing import Dict, List, Any, Type, Optional, Union
from collections import OrderedDict
from .base import ASTVisitor, ASTTransformer
from ..ast_nodes import ASTNode


class VisitorRegistry:
    """Registry for managing available visitors."""
    
    def __init__(self):
        """Initialize the visitor registry."""
        self._visitors: Dict[str, Type[ASTVisitor]] = {}
        self._descriptions: Dict[str, str] = {}
        self._categories: Dict[str, str] = {}
    
    def register(self, name: str, visitor_class: Type[ASTVisitor], 
                 description: str = "", category: str = "general") -> None:
        """
        Register a visitor class.
        
        Args:
            name: Unique name for the visitor
            visitor_class: The visitor class to register
            description: Human-readable description
            category: Category for grouping (analysis, transformation, etc.)
        """
        if name in self._visitors:
            raise ValueError(f"Visitor '{name}' is already registered")
        
        self._visitors[name] = visitor_class
        self._descriptions[name] = description
        self._categories[name] = category
    
    def get(self, name: str) -> Type[ASTVisitor]:
        """Get a visitor class by name."""
        if name not in self._visitors:
            raise KeyError(f"No visitor registered with name '{name}'")
        return self._visitors[name]
    
    def list_visitors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered visitors.
        
        Args:
            category: Filter by category if specified
            
        Returns:
            List of visitor info dictionaries
        """
        visitors = []
        for name, visitor_class in self._visitors.items():
            if category and self._categories[name] != category:
                continue
            
            visitors.append({
                'name': name,
                'class': visitor_class.__name__,
                'description': self._descriptions[name],
                'category': self._categories[name],
                'type': 'transformer' if issubclass(visitor_class, ASTTransformer) else 'analyzer'
            })
        
        return sorted(visitors, key=lambda x: (x['category'], x['name']))
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return sorted(set(self._categories.values()))


class VisitorPipeline:
    """
    Pipeline for composing and running multiple visitors.
    
    Supports both analysis visitors (collect data) and transformation
    visitors (modify AST).
    """
    
    def __init__(self, registry: Optional[VisitorRegistry] = None):
        """
        Initialize the pipeline.
        
        Args:
            registry: Optional visitor registry to use for lookups
        """
        self.registry = registry
        self._steps: List[Tuple[str, Union[Type[ASTVisitor], ASTVisitor], dict]] = []
        self._results: OrderedDict[str, Any] = OrderedDict()
    
    def add_visitor(self, visitor: Union[str, Type[ASTVisitor], ASTVisitor], 
                    name: Optional[str] = None, **kwargs) -> 'VisitorPipeline':
        """
        Add a visitor to the pipeline.
        
        Args:
            visitor: Visitor name (if registry), class, or instance
            name: Optional name for the step (defaults to class name)
            **kwargs: Arguments to pass to visitor constructor
            
        Returns:
            Self for chaining
        """
        if isinstance(visitor, str):
            # Look up in registry
            if not self.registry:
                raise ValueError("No registry available for visitor lookup")
            visitor_class = self.registry.get(visitor)
            step_name = name or visitor
            self._steps.append((step_name, visitor_class, kwargs))
        elif isinstance(visitor, type) and issubclass(visitor, ASTVisitor):
            # Visitor class
            step_name = name or visitor.__name__
            self._steps.append((step_name, visitor, kwargs))
        elif isinstance(visitor, ASTVisitor):
            # Visitor instance
            step_name = name or visitor.__class__.__name__
            self._steps.append((step_name, visitor, {}))
        else:
            raise TypeError("Visitor must be a string name, visitor class, or visitor instance")
        
        return self
    
    def run(self, ast: ASTNode) -> OrderedDict[str, Any]:
        """
        Run all visitors in the pipeline.
        
        Args:
            ast: The AST to process
            
        Returns:
            Ordered dictionary of results keyed by step name
        """
        self._results.clear()
        current_ast = ast
        
        for step_name, visitor_or_class, kwargs in self._steps:
            # Create visitor instance if needed
            if isinstance(visitor_or_class, type):
                visitor = visitor_or_class(**kwargs)
            else:
                visitor = visitor_or_class
            
            # Run visitor
            if isinstance(visitor, ASTTransformer):
                # Transformer modifies and returns new AST
                current_ast = visitor.visit(current_ast)
                self._results[step_name] = {
                    'type': 'transformer',
                    'visitor': visitor,
                    'output_ast': current_ast
                }
            else:
                # Analyzer just collects data
                visitor.visit(current_ast)
                self._results[step_name] = {
                    'type': 'analyzer',
                    'visitor': visitor
                }
                
                # Try to get results from common methods
                if hasattr(visitor, 'get_report'):
                    self._results[step_name]['report'] = visitor.get_report()
                elif hasattr(visitor, 'get_metrics'):
                    self._results[step_name]['metrics'] = visitor.get_metrics()
                elif hasattr(visitor, 'issues'):
                    self._results[step_name]['issues'] = visitor.issues
        
        return self._results
    
    def get_result(self, step_name: str) -> Any:
        """Get the result from a specific step."""
        if step_name not in self._results:
            raise KeyError(f"No result for step '{step_name}'")
        return self._results[step_name]
    
    def get_visitor(self, step_name: str) -> ASTVisitor:
        """Get the visitor instance from a specific step."""
        if step_name not in self._results:
            raise KeyError(f"No result for step '{step_name}'")
        return self._results[step_name]['visitor']
    
    def get_final_ast(self) -> Optional[ASTNode]:
        """Get the final transformed AST (if any transformers were run)."""
        for result in reversed(self._results.values()):
            if result['type'] == 'transformer':
                return result['output_ast']
        return None
    
    def clear(self) -> 'VisitorPipeline':
        """Clear the pipeline steps and results."""
        self._steps.clear()
        self._results.clear()
        return self


# Global registry instance
_global_registry = VisitorRegistry()


def get_global_registry() -> VisitorRegistry:
    """Get the global visitor registry."""
    return _global_registry


def register_builtin_visitors():
    """Register all built-in visitors."""
    from .formatter_visitor import FormatterVisitor
    from .validator_visitor import ValidatorVisitor
    from .optimization_visitor import OptimizationVisitor
    from .security_visitor import SecurityVisitor
    from .metrics_visitor import MetricsVisitor
    from .debug_ast_visitor import DebugASTVisitor
    
    registry = get_global_registry()
    
    # Register analysis visitors
    registry.register(
        'debug',
        DebugASTVisitor,
        "Display AST structure for debugging",
        "debug"
    )
    
    registry.register(
        'validator',
        ValidatorVisitor,
        "Validate script for syntax and semantic errors",
        "analysis"
    )
    
    registry.register(
        'security',
        SecurityVisitor,
        "Analyze script for security vulnerabilities",
        "analysis"
    )
    
    registry.register(
        'metrics',
        MetricsVisitor,
        "Collect code metrics and complexity analysis",
        "analysis"
    )
    
    # Register transformation visitors
    registry.register(
        'formatter',
        FormatterVisitor,
        "Format AST back to shell script",
        "transformation"
    )
    
    registry.register(
        'optimizer',
        OptimizationVisitor,
        "Optimize AST for better performance",
        "transformation"
    )


# Auto-register built-in visitors when module is imported
register_builtin_visitors()