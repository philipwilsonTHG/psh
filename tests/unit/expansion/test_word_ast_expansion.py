"""Test Word AST expansion functionality."""

from psh.ast_nodes import ExpansionPart, SimpleCommand, VariableExpansion, Word
from psh.lexer import tokenize
from psh.parser import Parser, ParserConfig


def test_word_ast_creation(captured_shell):
    """Test that Word AST nodes are created when configured."""
    shell = captured_shell

    # Set a test variable
    shell.state.set_variable('USER', 'alice')

    # Parse with Word AST enabled
    tokens = tokenize('echo hello $USER world')
    config = ParserConfig()
    parser = Parser(tokens, config=config)
    ast = parser.parse()

    # Check that we got a SimpleCommand with words
    assert len(ast.statements) == 1
    and_or_list = ast.statements[0]
    cmd = and_or_list.pipelines[0].commands[0]
    assert isinstance(cmd, SimpleCommand)
    assert cmd.words is not None
    assert len(cmd.words) == 4

    # Check word structure
    assert isinstance(cmd.words[0], Word)  # echo
    assert isinstance(cmd.words[1], Word)  # hello
    assert isinstance(cmd.words[2], Word)  # $USER
    assert isinstance(cmd.words[3], Word)  # world

    # Check that $USER word has expansion
    user_word = cmd.words[2]
    assert len(user_word.parts) == 1
    assert isinstance(user_word.parts[0], ExpansionPart)
    assert isinstance(user_word.parts[0].expansion, VariableExpansion)
    assert user_word.parts[0].expansion.name == 'USER'


def test_word_ast_expansion_simple_variable(captured_shell):
    """Test expansion of simple variable in Word AST."""
    shell = captured_shell

    # Set test variable
    shell.state.set_variable('NAME', 'Bob')

    # Run command that should create Word AST
    result = shell.run_command('echo Hello $NAME')
    assert result == 0
    assert captured_shell.get_stdout() == 'Hello Bob\n'


def test_word_ast_expansion_quoted(captured_shell):
    """Test expansion in quoted strings."""
    shell = captured_shell

    # Set test variables
    shell.state.set_variable('USER', 'alice')
    shell.state.set_variable('HOME', '/home/alice')

    # Double quotes should expand
    result = shell.run_command('echo "Hello $USER from $HOME"')
    assert result == 0
    assert captured_shell.get_stdout() == 'Hello alice from /home/alice\n'

    captured_shell.clear_output()

    # Single quotes should not expand
    result = shell.run_command('echo \'Hello $USER from $HOME\'')
    assert result == 0
    assert captured_shell.get_stdout() == 'Hello $USER from $HOME\n'


def test_word_ast_expansion_mixed_content(captured_shell):
    """Test Word with mixed literal and expansion content."""
    shell = captured_shell

    # Set test variable
    shell.state.set_variable('VERSION', '1.0')

    # Mixed content: prefix${var}suffix
    result = shell.run_command('echo app-v${VERSION}-beta')
    assert result == 0
    assert captured_shell.get_stdout() == 'app-v1.0-beta\n'


def test_word_ast_parameter_expansion(captured_shell):
    """Test parameter expansion with Word AST."""
    shell = captured_shell

    # Test ${var:-default}
    result = shell.run_command('echo ${UNDEFINED:-default}')
    assert result == 0
    assert captured_shell.get_stdout() == 'default\n'

    captured_shell.clear_output()

    # Test with defined variable
    shell.state.set_variable('DEFINED', 'value')
    result = shell.run_command('echo ${DEFINED:-default}')
    assert result == 0
    assert captured_shell.get_stdout() == 'value\n'


def test_word_ast_word_splitting(captured_shell):
    """Test that unquoted expansions undergo word splitting."""
    shell = captured_shell

    # Set variable with spaces
    shell.state.set_variable('LIST', 'one two three')

    # Unquoted should split
    result = shell.run_command('printf "[%s]\\n" $LIST')
    assert result == 0
    assert captured_shell.get_stdout() == '[one]\n[two]\n[three]\n'

    captured_shell.clear_output()

    # Quoted should not split
    result = shell.run_command('printf "[%s]\\n" "$LIST"')
    assert result == 0
    assert captured_shell.get_stdout() == '[one two three]\n'


def test_word_ast_command_substitution(captured_shell):
    """Test command substitution in Word AST."""
    shell = captured_shell

    # Simple command substitution
    result = shell.run_command('echo "Today is $(date +%A)"')
    assert result == 0
    # Output will vary by day, just check it's not empty
    output = captured_shell.get_stdout()
    assert output.startswith('Today is ')
    assert len(output) > len('Today is \n')


def test_word_ast_arithmetic_expansion(captured_shell):
    """Test arithmetic expansion in Word AST."""
    shell = captured_shell

    # Simple arithmetic
    result = shell.run_command('echo "2 + 2 = $((2 + 2))"')
    assert result == 0
    assert captured_shell.get_stdout() == '2 + 2 = 4\n'

    captured_shell.clear_output()

    # With variables
    shell.state.set_variable('X', '10')
    shell.state.set_variable('Y', '5')
    result = shell.run_command('echo "$X - $Y = $((X - Y))"')
    assert result == 0
    assert captured_shell.get_stdout() == '10 - 5 = 5\n'


def test_word_ast_double_quoted_expansion(captured_shell):
    """Test that double-quoted strings with variables expand correctly via Word AST."""
    shell = captured_shell

    shell.state.set_variable('GREETING', 'world')
    result = shell.run_command('echo "hello $GREETING!"')
    assert result == 0
    assert captured_shell.get_stdout() == 'hello world!\n'


def test_word_ast_composite_quoted_variable(captured_shell):
    """Test composite with quoted variable: foo"$var"bar."""
    shell = captured_shell

    shell.state.set_variable('MID', 'X')
    result = shell.run_command('echo foo"$MID"bar')
    assert result == 0
    assert captured_shell.get_stdout() == 'fooXbar\n'


def test_word_ast_escaped_dollar_in_double_quotes(captured_shell):
    """Test that \\$ in double quotes produces literal $."""
    shell = captured_shell

    result = shell.run_command('echo "price is \\$5"')
    assert result == 0
    assert captured_shell.get_stdout() == 'price is $5\n'
