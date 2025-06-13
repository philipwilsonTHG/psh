"""
Tests for the enhanced validator visitor with variable tracking,
command validation, quoting analysis, and security checks.
"""

import pytest
from psh.ast_nodes import (
    TopLevel, StatementList, SimpleCommand, Pipeline, AndOrList,
    FunctionDef, ForLoop, WhileLoop, IfConditional, Redirect,
    ArrayInitialization, ArrayElementAssignment
)
from psh.visitor import EnhancedValidatorVisitor, ValidatorConfig, VariableTracker
from psh.visitor.validator_visitor import Severity


class TestVariableTracker:
    """Test the variable tracking system."""
    
    def test_basic_variable_tracking(self):
        """Test basic variable definition and lookup."""
        tracker = VariableTracker()
        
        # Define a variable
        from psh.visitor.enhanced_validator_visitor import VariableInfo
        tracker.define_variable('FOO', VariableInfo(name='FOO', defined_at='test'))
        
        # Should be defined
        assert tracker.is_defined('FOO')
        assert tracker.lookup_variable('FOO') is not None
        assert tracker.lookup_variable('FOO').name == 'FOO'
        
        # Undefined variable should not be found
        assert not tracker.is_defined('BAR')
        assert tracker.lookup_variable('BAR') is None
    
    def test_special_variables(self):
        """Test that special variables are always defined."""
        tracker = VariableTracker()
        
        # Special single-char variables
        for var in ['?', '$', '!', '#', '@', '*', '-', '_', '0']:
            assert tracker.is_defined(var)
            info = tracker.lookup_variable(var)
            assert info is not None
            assert info.is_special
        
        # Environment variables
        for var in ['HOME', 'PATH', 'USER', 'SHELL']:
            assert tracker.is_defined(var)
            assert tracker.lookup_variable(var).is_special
        
        # Positional parameters
        for i in range(1, 10):
            assert tracker.is_defined(str(i))
            assert tracker.lookup_variable(str(i)).is_positional
    
    def test_scope_management(self):
        """Test variable scoping."""
        tracker = VariableTracker()
        from psh.visitor.enhanced_validator_visitor import VariableInfo
        
        # Define global variable
        tracker.define_variable('GLOBAL', VariableInfo(name='GLOBAL'))
        assert tracker.is_defined('GLOBAL')
        
        # Enter function scope
        tracker.enter_scope('function test')
        
        # Global should still be visible
        assert tracker.is_defined('GLOBAL')
        
        # Define local variable
        tracker.define_variable('LOCAL', VariableInfo(name='LOCAL', is_local=True))
        assert tracker.is_defined('LOCAL')
        
        # Exit function scope
        tracker.exit_scope()
        
        # Global still visible, local is not
        assert tracker.is_defined('GLOBAL')
        assert not tracker.is_defined('LOCAL')
    
    def test_variable_attributes(self):
        """Test variable attribute tracking."""
        tracker = VariableTracker()
        from psh.visitor.enhanced_validator_visitor import VariableInfo
        
        # Define and mark as exported
        tracker.define_variable('EXPORTED', VariableInfo(name='EXPORTED'))
        tracker.mark_exported('EXPORTED')
        
        var_info = tracker.lookup_variable('EXPORTED')
        assert var_info.is_exported
        
        # Mark as readonly
        tracker.define_variable('CONSTANT', VariableInfo(name='CONSTANT'))
        tracker.mark_readonly('CONSTANT')
        
        var_info = tracker.lookup_variable('CONSTANT')
        assert var_info.is_readonly


class TestEnhancedValidator:
    """Test the enhanced validator visitor."""
    
    def test_undefined_variable_detection(self):
        """Test detection of undefined variables."""
        # Create AST with undefined variable usage
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$UNDEFINED'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have warning about undefined variable
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert len(warnings) >= 1
        assert any('undefined variable' in w.message and 'UNDEFINED' in w.message 
                  for w in warnings)
    
    def test_variable_definition_tracking(self):
        """Test that defined variables are not flagged as undefined."""
        # Create AST with variable definition and usage
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['MY_VAR=hello'],
                            arg_types=['WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$MY_VAR'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should not have warnings about MY_VAR being undefined
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings 
                            if 'undefined variable' in w.message and 'MY_VAR' in w.message]
        assert len(undefined_warnings) == 0
    
    def test_parameter_expansion_with_default(self):
        """Test that ${VAR:-default} doesn't trigger undefined warning."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '${MAYBE_UNDEFINED:-default}'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        config = ValidatorConfig(ignore_undefined_with_defaults=True)
        validator = EnhancedValidatorVisitor(config)
        validator.visit(ast)
        
        # Should not warn about MAYBE_UNDEFINED
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings if 'MAYBE_UNDEFINED' in w.message]
        assert len(undefined_warnings) == 0
    
    def test_command_typo_detection(self):
        """Test detection of command typos."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['grpe', 'pattern', 'file'],
                            arg_types=['WORD', 'WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have warning about typo
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert any('typo' in w.message and 'grep' in w.message for w in warnings)
    
    def test_deprecated_command_detection(self):
        """Test detection of deprecated commands."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['which', 'python'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have info about using command -v
        infos = [i for i in validator.issues if i.severity == Severity.INFO]
        assert any('command -v' in i.message for i in infos)
    
    def test_unquoted_variable_warning(self):
        """Test warning about unquoted variables."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['FILES=/tmp/*.txt'],
                            arg_types=['WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['ls', '$FILES'],
                            arg_types=['WORD', 'WORD']  # WORD means unquoted
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have info about word splitting
        infos = [i for i in validator.issues if i.severity == Severity.INFO]
        assert any('word splitting' in i.message for i in infos)
    
    def test_unintentional_glob_warning(self):
        """Test warning about potentially unintentional globs."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', 'file[1]'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should warn about pathname expansion
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert any('pathname expansion' in w.message for w in warnings)
    
    def test_intentional_glob_no_warning(self):
        """Test that intentional globs don't trigger warnings."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['ls', '*.txt'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should not warn about *.txt with ls command
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        glob_warnings = [w for w in warnings if '*.txt' in w.message]
        assert len(glob_warnings) == 0
    
    def test_dangerous_command_warning(self):
        """Test warning about dangerous commands."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['eval', '$USER_INPUT'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should warn about eval
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert any('eval' in w.message and 'arbitrary code' in w.message 
                  for w in warnings)
    
    def test_command_injection_detection(self):
        """Test detection of potential command injection."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$USER_INPUT;rm -rf /'],
                            arg_types=['WORD', 'WORD']  # Unquoted with dangerous chars
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have error about command injection
        errors = [i for i in validator.issues if i.severity == Severity.ERROR]
        assert any('command injection' in e.message for e in errors)
    
    def test_world_writable_warning(self):
        """Test warning about world-writable permissions."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['chmod', '777', 'file.sh'],
                            arg_types=['WORD', 'WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should warn about world-writable
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert any('world-writable' in w.message for w in warnings)
    
    def test_function_scope_variables(self):
        """Test variable scoping in functions."""
        ast = TopLevel(items=[
            FunctionDef(
                name='test_func',
                body=StatementList(statements=[
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            SimpleCommand(
                                args=['local', 'LOCAL_VAR=value'],
                                arg_types=['WORD', 'WORD']
                            )
                        ])
                    ]),
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            SimpleCommand(
                                args=['echo', '$LOCAL_VAR'],
                                arg_types=['WORD', 'VARIABLE']
                            )
                        ])
                    ])
                ])
            ),
            # Outside function - LOCAL_VAR should be undefined
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$LOCAL_VAR'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should warn about LOCAL_VAR outside function
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        assert any('undefined variable' in w.message and 'LOCAL_VAR' in w.message 
                  for w in warnings)
    
    def test_for_loop_variable_definition(self):
        """Test that for loop variables are tracked."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        ForLoop(
                            variable='i',
                            items=['1', '2', '3'],
                            body=StatementList(statements=[
                                AndOrList(pipelines=[
                                    Pipeline(commands=[
                                        SimpleCommand(
                                            args=['echo', '$i'],
                                            arg_types=['WORD', 'VARIABLE']
                                        )
                                    ])
                                ])
                            ])
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should not warn about loop variable
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings 
                            if 'undefined variable' in w.message and "'i'" in w.message]
        assert len(undefined_warnings) == 0
    
    def test_read_command_defines_variable(self):
        """Test that read command defines variables."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['read', 'USER_INPUT'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$USER_INPUT'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should not warn about USER_INPUT
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings 
                            if 'undefined variable' in w.message and 'USER_INPUT' in w.message]
        assert len(undefined_warnings) == 0
    
    def test_export_marks_variable(self):
        """Test that export marks variables as exported."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['VAR=value'],
                            arg_types=['WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['export', 'VAR'],
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Check that VAR is marked as exported
        var_info = validator.var_tracker.lookup_variable('VAR')
        assert var_info is not None
        assert var_info.is_exported
    
    def test_config_disable_checks(self):
        """Test that configuration can disable specific checks."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['echo', '$UNDEFINED'],
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        # Disable undefined variable checking
        config = ValidatorConfig(check_undefined_vars=False)
        validator = EnhancedValidatorVisitor(config)
        validator.visit(ast)
        
        # Should not have warnings about undefined variables
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings if 'undefined variable' in w.message]
        assert len(undefined_warnings) == 0
    
    def test_arithmetic_context_no_quote_warning(self):
        """Test that variables in arithmetic context don't trigger quote warnings."""
        # This would require more complex AST nodes for arithmetic expressions
        # For now, we'll skip this test
        pass
    
    def test_empty_string_not_undefined(self):
        """Test that empty string assignment is not undefined."""
        ast = TopLevel(items=[
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['EMPTY='],
                            arg_types=['WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['test', '-z', '$EMPTY'],
                            arg_types=['WORD', 'WORD', 'VARIABLE']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should not warn about EMPTY being undefined
        warnings = [i for i in validator.issues if i.severity == Severity.WARNING]
        undefined_warnings = [w for w in warnings 
                            if 'undefined variable' in w.message and 'EMPTY' in w.message]
        assert len(undefined_warnings) == 0


class TestValidatorIntegration:
    """Integration tests for the enhanced validator."""
    
    def test_complex_script_validation(self):
        """Test validation of a complex script with multiple issues."""
        # Create a complex AST with various issues
        ast = TopLevel(items=[
            # Function with local variables
            FunctionDef(
                name='process_files',
                body=StatementList(statements=[
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            SimpleCommand(
                                args=['local', 'count=0'],
                                arg_types=['WORD', 'WORD']
                            )
                        ])
                    ]),
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            ForLoop(
                                variable='file',
                                items=['$@'],  # Special variable - should be OK
                                body=StatementList(statements=[
                                    AndOrList(pipelines=[
                                        Pipeline(commands=[
                                            SimpleCommand(
                                                args=['grpe', 'pattern', '$file'],  # Typo + unquoted
                                                arg_types=['WORD', 'WORD', 'WORD']
                                            )
                                        ])
                                    ])
                                ])
                            )
                        ])
                    ])
                ])
            ),
            # Main script
            StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['OUTPUT_DIR=/tmp/output'],
                            arg_types=['WORD']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['chmod', '777', '$OUTPUT_DIR'],  # Security issue
                            arg_types=['WORD', 'WORD', 'VARIABLE']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['eval', '$USER_COMMAND'],  # Dangerous
                            arg_types=['WORD', 'VARIABLE']
                        )
                    ])
                ]),
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(
                            args=['which', 'python'],  # Deprecated
                            arg_types=['WORD', 'WORD']
                        )
                    ])
                ])
            ])
        ])
        
        validator = EnhancedValidatorVisitor()
        validator.visit(ast)
        
        # Should have multiple issues
        assert len(validator.issues) > 0
        
        # Check for specific issues
        issues_text = '\n'.join(i.message for i in validator.issues)
        
        # Typo detection
        assert 'grpe' in issues_text and 'grep' in issues_text
        
        # Security warnings
        assert 'eval' in issues_text
        assert '777' in issues_text or 'world-writable' in issues_text
        
        # Deprecated command
        assert 'which' in issues_text or 'command -v' in issues_text
        
        # Unquoted variable (file in for loop)
        assert any('word splitting' in i.message for i in validator.issues)


def test_validator_error_handling():
    """Test that validator handles malformed ASTs gracefully."""
    # Create AST with None values
    ast = TopLevel(items=[
        StatementList(statements=[
            AndOrList(pipelines=[
                Pipeline(commands=[
                    SimpleCommand(
                        args=None,  # Malformed
                        arg_types=None
                    )
                ])
            ])
        ])
    ])
    
    validator = EnhancedValidatorVisitor()
    # Should not crash
    validator.visit(ast)
    
    # Should have error about empty command
    errors = [i for i in validator.issues if i.severity == Severity.ERROR]
    assert any('empty command' in e.message.lower() for e in errors)