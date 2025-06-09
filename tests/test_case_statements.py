import pytest
import warnings
from io import StringIO
from unittest.mock import patch
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse
# Import with deprecation warnings suppressed
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from psh.ast_nodes import CaseStatement, CaseItem, CasePattern


def test_case_basic_parsing():
    """Test basic case statement parsing."""
    tokens = tokenize("""case $var in
        pattern1) echo "one" ;;
        pattern2) echo "two" ;;
    esac""")
    result = parse(tokens)
    
    # Should be a top-level with one case statement
    assert hasattr(result, 'items')
    assert len(result.items) == 1
    assert isinstance(result.items[0], CaseStatement)
    
    case_stmt = result.items[0]
    assert case_stmt.expr == '$var'  # Variable preserved correctly
    assert len(case_stmt.items) == 2
    
    # Check first case item
    item1 = case_stmt.items[0]
    assert len(item1.patterns) == 1
    assert item1.patterns[0].pattern == 'pattern1'
    assert item1.terminator == ';;'
    
    # Check second case item
    item2 = case_stmt.items[1]
    assert len(item2.patterns) == 1
    assert item2.patterns[0].pattern == 'pattern2'
    assert item2.terminator == ';;'


def test_case_multiple_patterns():
    """Test case statement with multiple patterns per item."""
    tokens = tokenize("""case $var in
        a|b|c) echo "abc" ;;
    esac""")
    result = parse(tokens)
    
    case_stmt = result.items[0]
    item = case_stmt.items[0]
    assert len(item.patterns) == 3
    assert item.patterns[0].pattern == 'a'
    assert item.patterns[1].pattern == 'b'
    assert item.patterns[2].pattern == 'c'


def test_case_pattern_matching():
    """Test case statement pattern matching execution."""
    shell = Shell()
    shell.state.set_variable('test_var', 'hello')
    
    # Test exact match
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in hello) echo 'matched' ;; esac")
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'matched'
    
    # Test wildcard match
    shell.state.set_variable('test_var', 'hello_world')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in hello*) echo 'wildcard' ;; esac")
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'wildcard'
    
    # Test no match
    shell.state.set_variable('test_var', 'goodbye')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in hello*) echo 'not matched' ;; esac")
        assert result == 0  # No match still returns 0
        assert mock_stdout.getvalue().strip() == ''  # No output


def test_case_character_classes():
    """Test case statement with character classes."""
    shell = Shell()
    
    # Test character class [abc]
    shell.state.set_variable('test_var', 'a')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in [abc]) echo 'in class' ;; esac")
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'in class'
    
    # Test character range [a-z]
    shell.state.set_variable('test_var', 'm')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in [a-z]) echo 'lowercase' ;; esac")
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'lowercase'


def test_case_question_mark_wildcard():
    """Test case statement with ? wildcard."""
    shell = Shell()
    
    # Test single character match
    shell.state.set_variable('test_var', 'ab')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in a?) echo 'two chars' ;; esac")
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'two chars'
    
    # Test no match (too many chars)
    shell.state.set_variable('test_var', 'abc')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command("case $test_var in a?) echo 'should not match' ;; esac")
        assert result == 0  # No match, but case still succeeds
        assert mock_stdout.getvalue().strip() == ''  # No output


def test_case_multiple_items():
    """Test case statement with multiple items and proper matching."""
    shell = Shell()
    
    shell.state.set_variable('test_var', 'hello')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        shell.run_command("case $test_var in hi) echo 'greeting1' ;; hello) echo 'greeting2' ;; bye) echo 'farewell' ;; esac")
        assert mock_stdout.getvalue().strip() == 'greeting2'


def test_case_default_pattern():
    """Test case statement with default (*) pattern."""
    shell = Shell()
    
    shell.state.set_variable('test_var', 'unknown')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        shell.run_command("case $test_var in hello) echo 'greeting' ;; *) echo 'default' ;; esac")
        assert mock_stdout.getvalue().strip() == 'default'


def test_case_empty_commands():
    """Test case statement with empty command sections."""
    shell = Shell()
    shell.state.set_variable('test_var', 'test')
    
    # Should not fail with empty commands
    result = shell.run_command("case $test_var in test) ;; other) echo 'other' ;; esac")
    assert result == 0


def test_case_variable_expansion():
    """Test variable expansion in case expressions and patterns."""
    shell = Shell()
    
    shell.state.set_variable('pattern', 'test*')
    shell.state.set_variable('value', 'testing')
    
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        shell.run_command("case $value in $pattern) echo 'matched pattern' ;; *) echo 'no match' ;; esac")
        assert mock_stdout.getvalue().strip() == 'matched pattern'


def test_case_quoted_patterns():
    """Test case statement with quoted patterns."""
    shell = Shell()
    
    shell.state.set_variable('test_var', 'hello world')
    
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        shell.run_command('case "$test_var" in "hello world") echo "exact match" ;; *) echo "no match" ;; esac')
        assert mock_stdout.getvalue().strip() == 'exact match'


def test_case_keyword_patterns():
    """Test case statement with shell keywords as patterns."""
    shell = Shell()
    
    # Test keyword 'if' as a pattern
    shell.state.set_variable('test_var', 'if')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command('case $test_var in if) echo "matched if" ;; *) echo "no match" ;; esac')
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'matched if'
    
    # Test keyword 'for' as a pattern
    shell.state.set_variable('test_var', 'for')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command('case $test_var in for) echo "matched for" ;; *) echo "no match" ;; esac')
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'matched for'
    
    # Test multiple keywords as patterns
    shell.state.set_variable('test_var', 'while')
    with patch('sys.stdout', new=StringIO()) as mock_stdout:
        result = shell.run_command('case $test_var in if|then|while) echo "control keyword" ;; *) echo "other" ;; esac')
        assert result == 0
        assert mock_stdout.getvalue().strip() == 'control keyword'