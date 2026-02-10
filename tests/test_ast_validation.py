"""Tests for AST validation system."""

from psh.lexer import tokenize
from psh.parser import Parser
from psh.parser.validation import Issue, SemanticAnalyzer, Severity, ValidationPipeline, ValidationReport


class TestSemanticAnalyzer:
    """Test semantic analysis."""

    def test_analyzer_initialization(self):
        """Test semantic analyzer initialization."""
        analyzer = SemanticAnalyzer()
        assert len(analyzer.errors) == 0
        assert len(analyzer.warnings) == 0
        assert analyzer.symbol_table is not None

    def test_function_definition_tracking(self):
        """Test function definition tracking."""
        code = """
        function test_func() {
            echo "hello"
        }
        test_func
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should have no errors for valid function definition and call
        assert len(errors) == 0
        # Function should be marked as used
        assert analyzer.symbol_table.has_function("test_func")

    def test_duplicate_function_error(self):
        """Test duplicate function definition error."""
        code = """
        function test_func() {
            echo "first"
        }
        function test_func() {
            echo "second"
        }
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should detect duplicate function
        assert len(errors) >= 1
        assert any("already defined" in str(error) for error in errors)

    def test_break_outside_loop_error(self):
        """Test break statement outside loop."""
        code = """
        echo "start"
        break
        echo "end"
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should detect break outside loop as warning
        assert len(warnings) >= 1
        assert any("break" in str(warning).lower() and "loop" in str(warning).lower() for warning in warnings)

    def test_continue_outside_loop_error(self):
        """Test continue statement outside loop."""
        code = """
        echo "start"
        continue
        echo "end"
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should detect continue outside loop as warning
        assert len(warnings) >= 1
        assert any("continue" in str(warning).lower() and "loop" in str(warning).lower() for warning in warnings)

    def test_return_outside_function_error(self):
        """Test return statement outside function."""
        code = """
        echo "start"
        return 1
        echo "end"
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should detect return outside function as warning
        assert len(warnings) >= 1
        assert any("return" in str(warning).lower() and "function" in str(warning).lower() for warning in warnings)

    def test_break_continue_in_loop_valid(self):
        """Test break and continue inside loops are valid."""
        code = """
        for i in 1 2 3; do
            if [ "$i" = "2" ]; then
                continue
            fi
            if [ "$i" = "3" ]; then
                break
            fi
            echo $i
        done
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should not have errors for break/continue inside loop
        break_continue_errors = [w for w in warnings if "break" in str(w).lower() or "continue" in str(w).lower()]
        assert len(break_continue_errors) == 0

    def test_unreachable_code_detection(self):
        """Test unreachable code detection."""
        code = """
        function test_func() {
            echo "start"
            return 0
            echo "unreachable"
        }
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        analyzer = SemanticAnalyzer()
        errors, warnings = analyzer.analyze(ast)

        # Should detect unreachable code
        assert len(warnings) >= 1
        assert any("unreachable" in str(warning).lower() for warning in warnings)


class TestValidationRules:
    """Test validation rules."""

    def test_validation_pipeline_initialization(self):
        """Test validation pipeline initialization."""
        pipeline = ValidationPipeline()
        assert len(pipeline.rules) > 0
        assert pipeline.context is not None

    def test_empty_loop_body_warning(self):
        """Test empty loop body detection."""
        code = """
        for i in 1 2 3; do
        done
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        pipeline = ValidationPipeline()
        report = pipeline.validate(ast)

        # Should detect empty loop body
        warnings = report.get_warnings()
        assert len(warnings) >= 1
        assert any("empty" in issue.message.lower() and "body" in issue.message.lower() for issue in warnings)

    def test_empty_if_body_warning(self):
        """Test empty if body detection."""
        code = """
        if true; then
        fi
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        pipeline = ValidationPipeline()
        report = pipeline.validate(ast)

        # Should detect empty then clause
        warnings = report.get_warnings()
        assert len(warnings) >= 1
        assert any("empty" in issue.message.lower() and "then" in issue.message.lower() for issue in warnings)

    def test_valid_redirect_passes(self):
        """Test valid redirections pass validation."""
        code = """
        echo "hello" > output.txt
        cat < input.txt
        ls 2> errors.txt
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        pipeline = ValidationPipeline()
        report = pipeline.validate(ast)

        # Should not have redirect-related errors
        redirect_errors = [issue for issue in report.issues if "redirect" in issue.message.lower()]
        assert len(redirect_errors) == 0

    def test_function_name_validation(self):
        """Test function name validation."""
        code = """
        function if() {
            echo "bad name"
        }
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        pipeline = ValidationPipeline()
        report = pipeline.validate(ast)

        # Should detect invalid function name
        errors = report.get_errors()
        assert len(errors) >= 1
        assert any("function name" in issue.message.lower() and "keyword" in issue.message.lower() for issue in errors)


class TestValidationReport:
    """Test validation report functionality."""

    def test_empty_report(self):
        """Test empty validation report."""
        report = ValidationReport()
        assert len(report.issues) == 0
        assert not report.has_errors()
        assert len(report.get_errors()) == 0
        assert len(report.get_warnings()) == 0
        assert len(report.get_info()) == 0

    def test_add_issues(self):
        """Test adding issues to report."""
        report = ValidationReport()

        error = Issue("Test error", 0, Severity.ERROR)
        warning = Issue("Test warning", 0, Severity.WARNING)
        info = Issue("Test info", 0, Severity.INFO)

        report.add_issue(error)
        report.add_issue(warning)
        report.add_issue(info)

        assert len(report.issues) == 3
        assert len(report.get_errors()) == 1
        assert len(report.get_warnings()) == 1
        assert len(report.get_info()) == 1
        assert report.has_errors()

    def test_report_string_representation(self):
        """Test report string representation."""
        report = ValidationReport()

        error = Issue("Test error", 10, Severity.ERROR, "Fix this")
        report.add_issue(error)

        report_str = str(report)
        assert "error: Test error" in report_str
        assert "Fix this" in report_str


class TestParserIntegration:
    """Test parser integration with validation."""

    def test_parse_and_validate_method(self):
        """Test parse_and_validate method."""
        code = """
        function test_func() {
            echo "hello"
        }
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        parser.enable_validation()

        ast, report = parser.parse_and_validate()

        assert ast is not None
        assert isinstance(report, ValidationReport)

    def test_validation_with_enabled_config(self):
        """Test validation with validation enabled."""
        code = """
        function test_func() {
            echo "hello"
        }
        break
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        parser.enable_validation()

        ast, report = parser.parse_and_validate()

        assert ast is not None
        assert isinstance(report, ValidationReport)
        # Should have validation enabled
        assert getattr(parser.config, 'enable_validation', False)
        # Should detect break outside loop
        assert len(report.get_warnings()) > 0

    def test_validation_disabled_by_default(self):
        """Test validation is disabled by default."""
        code = """
        break
        """
        tokens = tokenize(code)
        parser = Parser(tokens)

        ast, report = parser.parse_and_validate()

        assert ast is not None
        assert isinstance(report, ValidationReport)
        # Should have no issues since validation is disabled
        assert len(report.issues) == 0

    def test_enable_disable_validation(self):
        """Test enabling and disabling validation."""
        code = """
        break
        """
        tokens = tokenize(code)
        parser = Parser(tokens)

        # Enable validation
        parser.enable_validation()
        ast, report = parser.parse_and_validate()

        assert len(report.issues) > 0  # Should detect break outside loop

        # Disable validation
        parser.disable_validation()
        ast, report = parser.parse_and_validate()

        assert len(report.issues) == 0  # Should have no issues

    def test_validate_ast_method(self):
        """Test direct AST validation."""
        code = """
        function test_func() {
        }
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()

        # Enable validation for testing
        parser.enable_validation()
        report = parser.validate_ast(ast)

        assert isinstance(report, ValidationReport)
        # Should detect empty function body
        warnings = report.get_warnings()
        assert len(warnings) > 0
        assert any("empty" in issue.message.lower() for issue in warnings)


class TestComplexValidationScenarios:
    """Test complex validation scenarios."""

    def test_nested_function_validation(self):
        """Test validation of nested function calls."""
        code = """
        function outer() {
            inner
            return 0
            echo "unreachable"
        }

        function inner() {
            echo "inner function"
        }

        outer
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        parser.enable_validation()

        ast, report = parser.parse_and_validate()

        assert ast is not None
        # Should detect unreachable code
        warnings = report.get_warnings()
        unreachable_warnings = [w for w in warnings if "unreachable" in w.message.lower()]
        assert len(unreachable_warnings) > 0

    def test_loop_validation(self):
        """Test loop validation scenarios."""
        code = """
        for i in 1 2 3; do
            if [ "$i" = "2" ]; then
                continue
            fi
            while true; do
                break
            done
        done
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        parser.enable_validation()

        ast, report = parser.parse_and_validate()

        assert ast is not None
        # Should not have errors for properly nested break/continue
        break_continue_errors = [e for e in report.issues
                               if ("break" in e.message.lower() or "continue" in e.message.lower())
                               and "loop" in e.message.lower()]
        assert len(break_continue_errors) == 0

    def test_mixed_validation_issues(self):
        """Test script with multiple validation issues."""
        code = """
        function if() {
            # Bad function name
        }

        for i in 1 2 3; do
        done

        break
        return 1
        """
        tokens = tokenize(code)
        parser = Parser(tokens)
        parser.enable_validation()

        ast, report = parser.parse_and_validate()

        assert ast is not None
        # Should have multiple issues
        assert len(report.issues) >= 3

        # Check for specific issue types
        messages = [issue.message.lower() for issue in report.issues]
        assert any("function name" in msg and "keyword" in msg for msg in messages)
        assert any("empty" in msg and "body" in msg for msg in messages)
        assert any("break" in msg and "loop" in msg for msg in messages)
        assert any("return" in msg and "function" in msg for msg in messages)
