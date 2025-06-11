#!/usr/bin/env python3
"""Test suite for line continuation functionality."""

import pytest
from psh.input_preprocessing import process_line_continuations
from psh.state_machine_lexer import tokenize


class TestLineContinuationPreprocessing:
    """Test the line continuation preprocessing function."""
    
    def test_basic_line_continuation(self):
        """Test basic line continuation processing."""
        result = process_line_continuations("echo hello \\\nworld")
        assert result == "echo hello world"
        
        # Verify tokenization works correctly
        tokens = tokenize(result)
        token_values = [t.value for t in tokens if t.type.name != 'EOF']
        assert token_values == ['echo', 'hello', 'world']
    
    def test_line_continuation_without_space(self):
        """Test line continuation without space before backslash."""
        result = process_line_continuations("echo hello\\\nworld")
        assert result == "echo helloworld"
    
    def test_line_continuation_with_spaces_after(self):
        """Test line continuation with spaces after the newline."""
        result = process_line_continuations("echo hello \\\n   world")
        assert result == "echo hello    world"
    
    def test_multiple_continuations(self):
        """Test multiple line continuations."""
        result = process_line_continuations("echo \\\nhello \\\nworld")
        assert result == "echo hello world"
    
    def test_escaped_backslashes_with_continuation(self):
        """Test escaped backslashes with line continuations."""
        # 3 backslashes: \\\\ -> \\, last \ escapes \n
        result = process_line_continuations("echo hello\\\\\\\nworld")
        assert result == "echo hello\\\\world"
        
        # 5 backslashes: \\\\\\\\\\ -> \\\\, last \ escapes \n  
        result = process_line_continuations("echo hello\\\\\\\\\\\nworld")
        assert result == "echo hello\\\\\\\\world"
    
    def test_even_backslashes_no_continuation(self):
        """Test even number of backslashes - no line continuation."""
        # 2 backslashes: \\\\ -> \\, \n stays as literal
        result = process_line_continuations("echo hello\\\\\nworld")
        assert result == "echo hello\\\\\nworld"
        
        # 4 backslashes: \\\\\\\\ -> \\\\, \n stays as literal
        result = process_line_continuations("echo hello\\\\\\\\\nworld")
        assert result == "echo hello\\\\\\\\\nworld"
    
    def test_quotes_prevent_processing(self):
        """Test that quotes prevent line continuation processing."""
        # Single quotes
        result = process_line_continuations("echo 'hello \\\nworld'")
        assert result == "echo 'hello \\\nworld'"
        
        # Double quotes
        result = process_line_continuations('echo "hello \\\nworld"')
        assert result == 'echo "hello \\\nworld"'
    
    def test_mixed_quotes_and_continuations(self):
        """Test mixed quotes and line continuations."""
        result = process_line_continuations("echo 'no \\\nprocess' \\\nyes")
        assert result == "echo 'no \\\nprocess' yes"
    
    def test_escaped_quotes(self):
        """Test that escaped quotes don't affect quote state."""
        result = process_line_continuations("echo \\\"hello \\\nworld\\\"")
        assert result == "echo \\\"hello world\\\""
    
    def test_carriage_return_line_endings(self):
        """Test Windows-style line endings."""
        result = process_line_continuations("echo hello \\\r\nworld")
        assert result == "echo hello world"
    
    def test_empty_input(self):
        """Test empty input."""
        assert process_line_continuations("") == ""
    
    def test_no_continuation(self):
        """Test input without line continuations."""
        result = process_line_continuations("echo hello world")
        assert result == "echo hello world"
    
    def test_trailing_backslash_no_newline(self):
        """Test trailing backslash without newline."""
        result = process_line_continuations("echo hello\\")
        assert result == "echo hello\\"


class TestLineContinuationIntegration:
    """Test line continuation integration with PSH components."""
    
    def test_tokenization_after_preprocessing(self):
        """Test that tokenization works correctly after preprocessing."""
        # Test case that previously failed
        input_text = "echo hello \\\nworld"
        processed = process_line_continuations(input_text)
        tokens = tokenize(processed)
        
        # Should produce: echo, hello, world, EOF
        assert len(tokens) == 4
        assert tokens[0].value == "echo"
        assert tokens[1].value == "hello" 
        assert tokens[2].value == "world"
        assert tokens[3].type.name == "EOF"
    
    def test_complex_command_preprocessing(self):
        """Test preprocessing of complex multi-line commands."""
        complex_command = """echo {1..3} \\
    | while read num
do
    echo "Number: $num"
done"""
        
        processed = process_line_continuations(complex_command)
        expected = """echo {1..3}     | while read num
do
    echo "Number: $num"
done"""
        
        assert processed == expected
    
    def test_pipeline_with_continuations(self):
        """Test pipeline with line continuations."""
        pipeline = "ls -la \\\n| grep test \\\n| sort"
        processed = process_line_continuations(pipeline)
        assert processed == "ls -la | grep test | sort"
        
        # Verify it tokenizes correctly
        tokens = tokenize(processed)
        pipe_count = sum(1 for t in tokens if t.type.name == 'PIPE')
        assert pipe_count == 2
    
    def test_complex_script_like_testscript(self):
        """Test complex script similar to testscript.sh."""
        script = """echo {1..10} \\
    | sed 's/ /\\n/g' \\
    | while read num
do echo -n "$num "
   if [ $((num%2)) -eq 0 ]
   then echo "even"
   else echo "odd"
   fi
done \\
    | sort +1"""
        
        processed = process_line_continuations(script)
        
        # Should not contain any \\\n sequences
        assert '\\\n' not in processed
        
        # Should contain the expected pipeline structure
        assert 'echo {1..10}     | sed' in processed
        assert 'done     | sort +1' in processed
        
        # Verify it can be tokenized without errors
        tokens = tokenize(processed)
        assert len(tokens) > 10  # Should have many tokens


class TestLineContinuationEdgeCases:
    """Test edge cases for line continuation processing."""
    
    def test_continuation_at_start_of_line(self):
        """Test line continuation at start of line."""
        result = process_line_continuations("\\\necho hello")
        assert result == "echo hello"
    
    def test_multiple_consecutive_continuations(self):
        """Test multiple consecutive line continuations."""
        result = process_line_continuations("echo \\\n\\\n\\\nhello")
        assert result == "echo hello"
    
    def test_continuation_with_only_whitespace_after(self):
        """Test line continuation with only whitespace after newline."""
        result = process_line_continuations("echo hello \\\n   \\\nworld")
        assert result == "echo hello    world"
    
    def test_complex_quoting_scenarios(self):
        """Test complex quoting scenarios."""
        # Escaped quote doesn't end quote context
        result = process_line_continuations('echo "hello \\" \\\nworld"')
        assert result == 'echo "hello \\" \\\nworld"'
        
        # Multiple quote levels
        result = process_line_continuations("echo 'single \"double \\\ninside\" single'")
        assert result == "echo 'single \"double \\\ninside\" single'"
    
    def test_backslash_quote_interactions(self):
        """Test interactions between backslashes and quotes."""
        # Backslash before quote
        result = process_line_continuations("echo \\' \\\nhello")
        assert result == "echo \\' hello"
        
        # Multiple backslashes before quote
        result = process_line_continuations("echo \\\\\\' \\\nhello")
        assert result == "echo \\\\\\' hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])