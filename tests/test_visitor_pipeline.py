"""
Tests for the visitor pipeline and registry.

This module tests the visitor composition and pipeline functionality.
"""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.visitor_pipeline import (
    VisitorRegistry, VisitorPipeline, get_global_registry
)
from psh.visitor.base import ASTVisitor, ASTTransformer
from psh.visitor.metrics_visitor import MetricsVisitor
from psh.visitor.security_visitor import SecurityVisitor
from psh.visitor.optimization_visitor import OptimizationVisitor
from psh.visitor.formatter_visitor import FormatterVisitor
from psh.ast_nodes import ASTNode, SimpleCommand


# Test visitor classes
class DummyAnalyzer(ASTVisitor[None]):
    """Simple test analyzer."""
    def __init__(self):
        super().__init__()
        self.node_count = 0
    
    def generic_visit(self, node: ASTNode) -> None:
        self.node_count += 1
        # Don't call super to avoid NotImplementedError
        # Instead traverse children manually
        if hasattr(node, '__dict__'):
            for value in node.__dict__.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ASTNode):
                            self.visit(item)
                elif isinstance(value, ASTNode):
                    self.visit(value)
    
    def get_report(self):
        return {'total_nodes': self.node_count}


class DummyTransformer(ASTTransformer):
    """Simple test transformer."""
    def __init__(self, prefix="test_"):
        super().__init__()
        self.prefix = prefix
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> SimpleCommand:
        # Prefix all commands
        if node.args:
            new_args = [self.prefix + node.args[0]] + node.args[1:]
            return SimpleCommand(
                args=new_args,
                arg_types=node.arg_types,
                quote_types=node.quote_types,
                redirects=node.redirects,
                background=node.background,
                array_assignments=node.array_assignments
            )
        return node
    
    def generic_visit(self, node: ASTNode) -> ASTNode:
        """Generic visit that properly transforms children."""
        # For most nodes, we need to traverse and transform children
        if hasattr(node, '__dict__'):
            # Create a copy of the node with transformed children
            import copy
            new_node = copy.copy(node)
            
            for attr_name, value in node.__dict__.items():
                if isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, ASTNode):
                            new_list.append(self.visit(item))
                        else:
                            new_list.append(item)
                    setattr(new_node, attr_name, new_list)
                elif isinstance(value, ASTNode):
                    setattr(new_node, attr_name, self.visit(value))
            
            return new_node
        
        return node


class TestVisitorRegistry:
    """Test visitor registry functionality."""
    
    def test_register_and_get_visitor(self):
        """Test registering and retrieving visitors."""
        registry = VisitorRegistry()
        
        # Register a visitor
        registry.register(
            'test_analyzer',
            DummyAnalyzer,
            "Test analyzer for counting nodes",
            "testing"
        )
        
        # Get the visitor
        visitor_class = registry.get('test_analyzer')
        assert visitor_class == DummyAnalyzer
    
    def test_duplicate_registration_error(self):
        """Test that duplicate registration raises error."""
        registry = VisitorRegistry()
        
        registry.register('test', DummyAnalyzer)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register('test', DummyAnalyzer)
    
    def test_get_nonexistent_visitor(self):
        """Test getting non-existent visitor raises error."""
        registry = VisitorRegistry()
        
        with pytest.raises(KeyError, match="No visitor registered"):
            registry.get('nonexistent')
    
    def test_list_visitors(self):
        """Test listing registered visitors."""
        registry = VisitorRegistry()
        
        # Register multiple visitors
        registry.register('analyzer1', DummyAnalyzer, "Analyzer 1", "analysis")
        registry.register('analyzer2', DummyAnalyzer, "Analyzer 2", "analysis")
        registry.register('transformer1', DummyTransformer, "Transformer 1", "transformation")
        
        # List all
        all_visitors = registry.list_visitors()
        assert len(all_visitors) == 3
        
        # List by category
        analysis_visitors = registry.list_visitors(category="analysis")
        assert len(analysis_visitors) == 2
        
        transform_visitors = registry.list_visitors(category="transformation")
        assert len(transform_visitors) == 1
    
    def test_get_categories(self):
        """Test getting unique categories."""
        registry = VisitorRegistry()
        
        registry.register('v1', DummyAnalyzer, "V1", "cat1")
        registry.register('v2', DummyAnalyzer, "V2", "cat2")
        registry.register('v3', DummyAnalyzer, "V3", "cat1")
        
        categories = registry.get_categories()
        assert categories == ['cat1', 'cat2']
    
    def test_global_registry_has_builtins(self):
        """Test that global registry has built-in visitors."""
        registry = get_global_registry()
        
        # Check some built-in visitors are registered
        assert registry.get('metrics') == MetricsVisitor
        assert registry.get('security') == SecurityVisitor
        assert registry.get('optimizer') == OptimizationVisitor
        assert registry.get('formatter') == FormatterVisitor
        
        # Check categories
        categories = registry.get_categories()
        assert 'analysis' in categories
        assert 'transformation' in categories


class TestVisitorPipeline:
    """Test visitor pipeline functionality."""
    
    def parse_command(self, command):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return parse(tokens)
    
    def test_simple_pipeline(self):
        """Test basic pipeline with one visitor."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(DummyAnalyzer())
        
        ast = self.parse_command("echo hello")
        results = pipeline.run(ast)
        
        assert len(results) == 1
        assert 'DummyAnalyzer' in results
        assert results['DummyAnalyzer']['type'] == 'analyzer'
        assert results['DummyAnalyzer']['report']['total_nodes'] > 0
    
    def test_pipeline_with_transformer(self):
        """Test pipeline with transformer."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(DummyTransformer(prefix="prefix_"))
        
        ast = self.parse_command("echo hello")
        results = pipeline.run(ast)
        
        # Check transformer ran
        assert 'DummyTransformer' in results
        assert results['DummyTransformer']['type'] == 'transformer'
        
        # Get the transformed AST and format it
        final_ast = pipeline.get_final_ast()
        formatter = FormatterVisitor()
        formatted = formatter.visit(final_ast)
        assert 'prefix_echo' in formatted
    
    def test_pipeline_with_registry(self):
        """Test pipeline using registry lookup."""
        registry = VisitorRegistry()
        registry.register('test_analyzer', DummyAnalyzer)
        
        pipeline = VisitorPipeline(registry=registry)
        pipeline.add_visitor('test_analyzer')
        
        ast = self.parse_command("echo hello")
        results = pipeline.run(ast)
        
        assert 'test_analyzer' in results
    
    def test_pipeline_chaining(self):
        """Test method chaining."""
        pipeline = VisitorPipeline()
        result = (pipeline
                  .add_visitor(DummyAnalyzer(), name="analyzer1")
                  .add_visitor(DummyAnalyzer(), name="analyzer2")
                  .add_visitor(DummyTransformer(), name="transformer"))
        
        assert result is pipeline
        assert len(pipeline._steps) == 3
    
    def test_get_result_and_visitor(self):
        """Test getting specific results and visitors."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(MetricsVisitor(), name="metrics")
        
        ast = self.parse_command("echo hello; ls -la")
        pipeline.run(ast)
        
        # Get result
        result = pipeline.get_result("metrics")
        assert result['type'] == 'analyzer'
        assert 'report' in result  # MetricsVisitor provides get_report()
        
        # Get visitor
        visitor = pipeline.get_visitor("metrics")
        assert isinstance(visitor, MetricsVisitor)
        assert visitor.metrics.total_commands == 2
    
    def test_get_final_ast(self):
        """Test getting final transformed AST."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(DummyAnalyzer())  # Doesn't transform
        pipeline.add_visitor(OptimizationVisitor())  # Transforms
        pipeline.add_visitor(DummyAnalyzer())  # Doesn't transform
        
        ast = self.parse_command("echo hello | cat")
        pipeline.run(ast)
        
        final_ast = pipeline.get_final_ast()
        assert final_ast is not None
        
        # Format to check optimization worked
        formatter = FormatterVisitor()
        formatted = formatter.visit(final_ast)
        assert 'cat' not in formatted  # cat should be optimized away
    
    def test_pipeline_with_kwargs(self):
        """Test passing kwargs to visitor constructor."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(DummyTransformer, prefix="custom_")
        
        ast = self.parse_command("echo hello")
        pipeline.run(ast)
        
        formatter = FormatterVisitor()
        final_ast = pipeline.get_final_ast()
        formatted = formatter.visit(final_ast)
        assert 'custom_echo' in formatted
    
    def test_clear_pipeline(self):
        """Test clearing pipeline."""
        pipeline = VisitorPipeline()
        pipeline.add_visitor(DummyAnalyzer())
        
        ast = self.parse_command("echo hello")
        pipeline.run(ast)
        
        assert len(pipeline._steps) == 1
        assert len(pipeline._results) == 1
        
        pipeline.clear()
        
        assert len(pipeline._steps) == 0
        assert len(pipeline._results) == 0
    
    def test_complex_analysis_pipeline(self):
        """Test realistic pipeline with multiple analyzers."""
        pipeline = VisitorPipeline(get_global_registry())
        
        # Add multiple analysis visitors
        pipeline.add_visitor('metrics')
        pipeline.add_visitor('security')
        pipeline.add_visitor('validator')
        
        script = """
        eval $user_input
        chmod 777 /tmp/file
        
        function process() {
            for file in *.txt; do
                cat $file | grep pattern
            done
        }
        """
        
        ast = self.parse_command(script)
        results = pipeline.run(ast)
        
        # Check all visitors ran
        assert 'metrics' in results
        assert 'security' in results
        assert 'validator' in results
        
        # Check metrics
        metrics = pipeline.get_visitor('metrics').get_metrics()
        assert metrics.total_functions == 1
        assert metrics.total_loops == 1
        
        # Check security issues
        security = pipeline.get_visitor('security')
        assert len(security.issues) > 0
        assert any(i.issue_type == 'DANGEROUS_COMMAND' for i in security.issues)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])