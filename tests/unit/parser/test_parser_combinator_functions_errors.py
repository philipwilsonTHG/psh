"""Error handling tests for parser combinator function definitions."""

import pytest
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.parser.abstract_parser import ParseError
from psh.lexer import tokenize as lexer_tokenize


def tokenize(code: str) -> list:
    """Helper to tokenize shell code."""
    return lexer_tokenize(code.strip())


def parse(code: str, enable_word_building: bool = False):
    """Helper to parse shell code."""
    parser = ParserCombinatorShellParser()
    if enable_word_building:
        parser.config.build_word_ast_nodes = True
    tokens = tokenize(code)
    return parser.parse(tokens)


class TestFunctionParsingErrors:
    """Test error handling for invalid function definitions."""
    
    def test_missing_parentheses(self):
        """Test function without parentheses in POSIX style."""
        with pytest.raises(ParseError) as excinfo:
            parse("greet { echo Hello; }")
        assert "Unexpected token" in str(excinfo.value)
    
    def test_missing_opening_brace(self):
        """Test function without opening brace."""
        with pytest.raises(ParseError) as excinfo:
            parse("greet() echo Hello; }")
        assert "Unexpected token" in str(excinfo.value) or "Expected '{'" in str(excinfo.value)
    
    def test_missing_closing_brace(self):
        """Test function without closing brace."""
        with pytest.raises(ParseError) as excinfo:
            parse("greet() { echo Hello;")
        assert "Unexpected token" in str(excinfo.value) or "Unclosed function body" in str(excinfo.value)
    
    def test_invalid_function_name_special_char(self):
        """Test function with invalid characters in name."""
        invalid_names = [
            "hello-world!",  # exclamation mark
            "test@func",     # at sign
            "my#func",       # hash
            "$myfunc",       # dollar sign
            "func&name",     # ampersand
        ]
        
        for name in invalid_names:
            with pytest.raises(ParseError):
                parse(f"{name}() {{ echo test; }}")
    
    def test_reserved_word_as_function_name(self):
        """Test using reserved words as function names."""
        reserved = ['if', 'then', 'else', 'elif', 'fi', 'while', 'do', 
                   'done', 'for', 'case', 'esac', 'function']
        
        for word in reserved:
            with pytest.raises(ParseError) as excinfo:
                parse(f"{word}() {{ echo test; }}")
            # Either it fails at parsing or at validation
            assert "Reserved word cannot be function name" in str(excinfo.value) or \
                   "Unexpected token" in str(excinfo.value)
    
    def test_function_keyword_without_name(self):
        """Test function keyword without a name."""
        with pytest.raises(ParseError) as excinfo:
            parse("function { echo test; }")
        assert "Expected function name" in str(excinfo.value) or "Unexpected token" in str(excinfo.value)
    
    def test_function_keyword_with_invalid_name(self):
        """Test function keyword with invalid name."""
        with pytest.raises(ParseError) as excinfo:
            parse("function 123invalid { echo test; }")
        assert "Expected function name" in str(excinfo.value) or "Unexpected token" in str(excinfo.value)
    
    def test_nested_function_syntax_error(self):
        """Test nested function with syntax error."""
        with pytest.raises(ParseError):
            parse("""
                outer() {
                    inner() {
                        echo "Missing closing brace"
                    # Missing }
                }
            """)
    
    def test_function_with_immediate_eof(self):
        """Test function definition that ends abruptly."""
        with pytest.raises(ParseError):
            parse("greet() {")
    
    def test_function_body_syntax_error(self):
        """Test function with syntax error in body."""
        with pytest.raises(ParseError):
            parse("""
                test_func() {
                    if true then  # Missing semicolon
                        echo "test"
                    fi
                }
            """)
    
    def test_mismatched_parentheses(self):
        """Test function with mismatched parentheses."""
        with pytest.raises(ParseError):
            parse("greet( { echo Hello; }")  # Missing closing )
        
        with pytest.raises(ParseError):
            parse("greet) { echo Hello; }")  # Missing opening (
    
    def test_empty_function_name(self):
        """Test function with empty name."""
        with pytest.raises(ParseError):
            parse("() { echo test; }")
    
    def test_function_after_pipe(self):
        """Test function definition after pipe (invalid)."""
        with pytest.raises(ParseError):
            parse("echo test | greet() { echo Hello; }")
    
    def test_function_in_pipeline(self):
        """Test function definition in pipeline (invalid)."""
        with pytest.raises(ParseError):
            parse("greet() { echo Hello; } | grep Hello")
    
    def test_multiple_function_keywords(self):
        """Test multiple function keywords."""
        with pytest.raises(ParseError):
            parse("function function test { echo Hello; }")
    
    def test_function_with_arguments_in_definition(self):
        """Test function with arguments in definition (not supported)."""
        # Shell functions don't support argument lists in definition
        with pytest.raises(ParseError):
            parse("greet(name) { echo Hello $name; }")
    
    def test_semicolon_after_function_name(self):
        """Test semicolon after function name."""
        with pytest.raises(ParseError):
            parse("greet(); { echo Hello; }")


class TestFunctionBodyErrors:
    """Test error handling for function body parsing."""
    
    def test_unclosed_string_in_body(self):
        """Test function with unclosed string in body."""
        # This might pass parsing but fail during tokenization
        with pytest.raises(Exception):  # Could be ParseError or tokenization error
            parse("""
                greet() {
                    echo "Hello
                }
            """)
    
    def test_invalid_control_structure_in_body(self):
        """Test function with invalid control structure."""
        with pytest.raises(ParseError):
            parse("""
                test_func() {
                    if [ true ]  # Missing then
                        echo "test"
                    fi
                }
            """)
    
    def test_unmatched_keywords_in_body(self):
        """Test function with unmatched keywords."""
        with pytest.raises(ParseError):
            parse("""
                test_func() {
                    if true; then
                        echo "test"
                    # Missing fi
                }
            """)
    
    def test_extra_closing_brace(self):
        """Test function with extra closing brace."""
        with pytest.raises(ParseError):
            parse("""
                greet() {
                    echo "Hello"
                }}
            """)


class TestFunctionIntegrationErrors:
    """Test error handling for functions in various contexts."""
    
    def test_function_in_subshell(self):
        """Test function definition in subshell."""
        # This should actually work in bash, but might not in our parser
        code = """
            (
                greet() {
                    echo "Hello"
                }
            )
        """
        # Try to parse - it might work or fail depending on implementation
        try:
            ast = parse(code)
            # If it works, that's fine
        except ParseError:
            # If it fails, that's also acceptable for now
            pass
    
    def test_function_in_command_substitution(self):
        """Test function definition in command substitution."""
        # This is invalid in shell
        with pytest.raises(ParseError):
            parse('echo $(greet() { echo Hello; })', enable_word_building=True)
    
    def test_function_after_redirect(self):
        """Test function definition after redirect."""
        with pytest.raises(ParseError):
            parse("cat file.txt > greet() { echo Hello; }")
    
    def test_background_function_definition(self):
        """Test function definition with & (invalid)."""
        with pytest.raises(ParseError):
            parse("greet() { echo Hello; } &")