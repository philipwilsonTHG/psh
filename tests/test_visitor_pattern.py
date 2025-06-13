"""
Tests for the visitor pattern implementation.

These tests verify that the visitor pattern correctly traverses AST nodes
and that different visitors produce expected results.
"""

import pytest
from psh.ast_nodes import (
    TopLevel, StatementList, SimpleCommand, Pipeline, AndOrList,
    WhileLoop, ForLoop, IfConditional, FunctionDef, BreakStatement,
    ContinueStatement, Redirect, CaseConditional, CaseItem, CasePattern
)
from psh.visitor import FormatterVisitor, ValidatorVisitor, ASTVisitor


class TestFormatterVisitor:
    """Test the formatter visitor."""
    
    def test_simple_command(self):
        """Test formatting a simple command."""
        cmd = SimpleCommand(args=['echo', 'hello'], arg_types=['WORD', 'WORD'])
        formatter = FormatterVisitor()
        result = formatter.visit(cmd)
        assert result == 'echo hello'
    
    def test_quoted_arguments(self):
        """Test formatting with quoted arguments."""
        cmd = SimpleCommand(
            args=['echo', 'hello world'],
            arg_types=['WORD', 'STRING'],
            quote_types=[None, '"']
        )
        formatter = FormatterVisitor()
        result = formatter.visit(cmd)
        assert result == 'echo "hello world"'
    
    def test_pipeline(self):
        """Test formatting a pipeline."""
        pipeline = Pipeline(commands=[
            SimpleCommand(args=['cat', 'file.txt'], arg_types=['WORD', 'WORD']),
            SimpleCommand(args=['grep', 'pattern'], arg_types=['WORD', 'WORD']),
            SimpleCommand(args=['wc', '-l'], arg_types=['WORD', 'WORD'])
        ])
        formatter = FormatterVisitor()
        result = formatter.visit(pipeline)
        assert result == 'cat file.txt | grep pattern | wc -l'
    
    def test_if_statement(self):
        """Test formatting an if statement."""
        if_stmt = IfConditional(
            condition=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['test', '-f', 'file'], arg_types=['WORD', 'WORD', 'WORD'])
                    ])
                ])
            ]),
            then_part=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', 'exists'], arg_types=['WORD', 'WORD'])
                    ])
                ])
            ])
        )
        formatter = FormatterVisitor()
        result = formatter.visit(if_stmt)
        assert 'if' in result
        assert 'then' in result
        assert 'fi' in result
        assert 'test -f file' in result
        assert 'echo exists' in result
    
    def test_for_loop(self):
        """Test formatting a for loop."""
        for_loop = ForLoop(
            variable='i',
            items=['1', '2', '3'],
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', '$i'], arg_types=['WORD', 'VARIABLE'])
                    ])
                ])
            ])
        )
        formatter = FormatterVisitor()
        result = formatter.visit(for_loop)
        assert 'for i in 1 2 3' in result
        assert 'do' in result
        assert 'done' in result
        assert 'echo $i' in result
    
    def test_function_definition(self):
        """Test formatting a function definition."""
        func = FunctionDef(
            name='greet',
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', 'Hello'], arg_types=['WORD', 'WORD'])
                    ])
                ])
            ])
        )
        formatter = FormatterVisitor()
        result = formatter.visit(func)
        assert 'greet() {' in result
        assert 'echo Hello' in result
        assert '}' in result
    
    def test_case_statement(self):
        """Test formatting a case statement."""
        case = CaseConditional(
            expr='$var',
            items=[
                CaseItem(
                    patterns=[CasePattern('yes'), CasePattern('y')],
                    commands=StatementList(statements=[
                        AndOrList(pipelines=[
                            Pipeline(commands=[
                                SimpleCommand(args=['echo', 'Yes'], arg_types=['WORD', 'WORD'])
                            ])
                        ])
                    ]),
                    terminator=';;'
                )
            ]
        )
        formatter = FormatterVisitor()
        result = formatter.visit(case)
        assert 'case $var in' in result
        assert 'yes | y)' in result
        assert 'echo Yes' in result
        assert ';;' in result
        assert 'esac' in result
    
    def test_redirections(self):
        """Test formatting with redirections."""
        cmd = SimpleCommand(
            args=['echo', 'test'],
            arg_types=['WORD', 'WORD'],
            redirects=[
                Redirect(type='>', target='output.txt'),
                Redirect(type='2>', target='error.log', fd=2)
            ]
        )
        formatter = FormatterVisitor()
        result = formatter.visit(cmd)
        assert 'echo test >output.txt 2>error.log' == result


class TestValidatorVisitor:
    """Test the validator visitor."""
    
    def test_empty_command(self):
        """Test validation of empty command."""
        cmd = SimpleCommand(args=[], arg_types=[])
        validator = ValidatorVisitor()
        validator.visit(cmd)
        assert len(validator.issues) == 1
        assert validator.issues[0].severity.value == 'error'
        assert 'Empty command' in validator.issues[0].message
    
    def test_break_outside_loop(self):
        """Test validation of break outside loop."""
        stmt_list = StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[BreakStatement()])
            ])
        ])
        validator = ValidatorVisitor()
        validator.visit(stmt_list)
        assert any('only meaningful in a' in issue.message for issue in validator.issues)
    
    def test_break_in_loop(self):
        """Test validation of break inside loop."""
        while_loop = WhileLoop(
            condition=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['true'], arg_types=['WORD'])
                    ])
                ])
            ]),
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[BreakStatement()])
                ])
            ])
        )
        validator = ValidatorVisitor()
        validator.visit(while_loop)
        # Should not have errors about break
        assert not any('only meaningful' in issue.message for issue in validator.issues)
    
    def test_break_level_too_high(self):
        """Test validation of break with level exceeding nesting."""
        while_loop = WhileLoop(
            condition=StatementList(statements=[]),
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[BreakStatement(level=2)])
                ])
            ])
        )
        validator = ValidatorVisitor()
        validator.visit(while_loop)
        assert any('exceeds maximum nesting level' in issue.message for issue in validator.issues)
    
    def test_cd_too_many_args(self):
        """Test validation of cd with too many arguments."""
        cmd = SimpleCommand(
            args=['cd', 'dir1', 'dir2'],
            arg_types=['WORD', 'WORD', 'WORD']
        )
        validator = ValidatorVisitor()
        validator.visit(cmd)
        assert any('cd: too many arguments' in issue.message for issue in validator.issues)
    
    def test_duplicate_function_names(self):
        """Test validation of duplicate function names."""
        top_level = TopLevel(items=[
            FunctionDef(name='test', body=StatementList()),
            FunctionDef(name='test', body=StatementList())
        ])
        validator = ValidatorVisitor()
        validator.visit(top_level)
        assert any("Redefinition of function 'test'" in issue.message for issue in validator.issues)
    
    def test_case_duplicate_patterns(self):
        """Test validation of duplicate case patterns."""
        case = CaseConditional(
            expr='$var',
            items=[
                CaseItem(patterns=[CasePattern('a')], commands=StatementList()),
                CaseItem(patterns=[CasePattern('a')], commands=StatementList())
            ]
        )
        validator = ValidatorVisitor()
        validator.visit(case)
        assert any("Duplicate case pattern" in issue.message for issue in validator.issues)


class TestVisitorTraversal:
    """Test that visitors correctly traverse the AST."""
    
    def test_nested_traversal(self):
        """Test traversal of nested structures."""
        # Create a visitor that counts all nodes
        class NodeCounter(ASTVisitor[None]):
            def __init__(self):
                self.count = 0
            
            def visit(self, node):
                self.count += 1
                super().visit(node)
            
            def generic_visit(self, node):
                # Visit all children
                from dataclasses import is_dataclass, fields
                if is_dataclass(node):
                    for field in fields(node):
                        value = getattr(node, field.name)
                        if isinstance(value, list):
                            for item in value:
                                if hasattr(item, '__class__'):
                                    self.visit(item)
                        elif hasattr(value, '__class__') and value is not None:
                            if hasattr(value.__class__, '__mro__'):
                                from psh.ast_nodes import ASTNode
                                if ASTNode in value.__class__.__mro__:
                                    self.visit(value)
        
        # Create nested AST
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', 'test'], arg_types=['WORD', 'WORD'])
                    ])
                ])
            ])
        ])
        
        counter = NodeCounter()
        counter.visit(ast)
        assert counter.count >= 4  # TopLevel, StatementList, AndOrList, Pipeline, SimpleCommand
    
    def test_visitor_error_handling(self):
        """Test visitor error handling for unknown nodes."""
        # Create a custom node type that inherits from ASTNode
        from psh.ast_nodes import ASTNode
        from psh.visitor.base import ASTVisitor
        
        class UnknownNode(ASTNode):
            pass
        
        # Create a visitor that doesn't override generic_visit
        class StrictVisitor(ASTVisitor[str]):
            def visit_SimpleCommand(self, node) -> str:
                return "simple command"
        
        visitor = StrictVisitor()
        
        # Should raise NotImplementedError for unknown node
        with pytest.raises(NotImplementedError):
            visitor.visit(UnknownNode())


def test_visitor_imports():
    """Test that all visitor classes can be imported."""
    from psh.visitor import ASTVisitor, FormatterVisitor, ValidatorVisitor
    assert ASTVisitor is not None
    assert FormatterVisitor is not None
    assert ValidatorVisitor is not None