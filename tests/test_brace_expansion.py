"""Test brace expansion functionality."""
import pytest
from psh.brace_expansion import BraceExpander, BraceExpansionError


class TestBraceExpansion:
    """Test the BraceExpander class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.expander = BraceExpander()
    
    def test_simple_list_expansion(self):
        """Test basic comma-separated list expansion."""
        assert self.expander.expand_line("echo {a,b,c}") == "echo a b c"
        assert self.expander.expand_line("{x,y,z}") == "x y z"
        assert self.expander.expand_line("file.{txt,pdf}") == "file.txt file.pdf"
    
    def test_list_with_empty_elements(self):
        """Test list expansion with empty elements."""
        assert self.expander.expand_line("{a,,c}") == "a  c"
        assert self.expander.expand_line("{,b,c}") == " b c"
        assert self.expander.expand_line("{a,b,}") == "a b "
    
    def test_preamble_and_postscript(self):
        """Test brace expansion with text before and after."""
        assert self.expander.expand_line("pre{A,B}post") == "preApost preBpost"
        assert self.expander.expand_line("file{1,2,3}.txt") == "file1.txt file2.txt file3.txt"
        assert self.expander.expand_line("/path/{src,bin,lib}/") == "/path/src/ /path/bin/ /path/lib/"
    
    def test_multiple_expansions(self):
        """Test multiple brace expansions in one line."""
        assert self.expander.expand_line("{a,b} {c,d}") == "a b c d"
        assert self.expander.expand_line("{1,2}{A,B}") == "1A 1B 2A 2B"
        assert self.expander.expand_line("_{x,y}_ _{1,2}_") == "_x_ _y_ _1_ _2_"
    
    def test_nested_braces(self):
        """Test nested brace expansion."""
        assert self.expander.expand_line("{a,b{1,2}}") == "a b1 b2"
        assert self.expander.expand_line("{a,b{1,2},c}") == "a b1 b2 c"
        assert self.expander.expand_line("{{A,B},{1,2}}") == "A B 1 2"
        assert self.expander.expand_line("{a{1,2},b{3,4}}") == "a1 a2 b3 b4"
    
    def test_deeply_nested_braces(self):
        """Test deeply nested brace expansions."""
        assert self.expander.expand_line("{a,{b,{c,d}}}") == "a b c d"
        assert self.expander.expand_line("{{{1,2},3},4}") == "1 2 3 4"
    
    def test_no_expansion_single_element(self):
        """Test that single element braces don't expand."""
        assert self.expander.expand_line("{single}") == "{single}"
        assert self.expander.expand_line("prefix{one}suffix") == "prefix{one}suffix"
    
    def test_no_expansion_spaces_around_commas(self):
        """Test that spaces around commas prevent expansion."""
        assert self.expander.expand_line("{a, b, c}") == "{a, b, c}"
        assert self.expander.expand_line("{a ,b, c}") == "{a ,b, c}"
        assert self.expander.expand_line("{a , b , c}") == "{a , b , c}"
    
    def test_no_expansion_in_quotes(self):
        """Test that braces inside quotes don't expand."""
        assert self.expander.expand_line('"{a,b,c}"') == '"{a,b,c}"'
        assert self.expander.expand_line("'{a,b,c}'") == "'{a,b,c}'"
        assert self.expander.expand_line('echo "{1,2,3}"') == 'echo "{1,2,3}"'
        assert self.expander.expand_line("echo '{x,y,z}'") == "echo '{x,y,z}'"
    
    def test_partial_quotes(self):
        """Test mixed quoted and unquoted content."""
        assert self.expander.expand_line('"{a,b}" {c,d}') == '"{a,b}" c d'
        assert self.expander.expand_line('{a,b} "{c,d}"') == 'a b "{c,d}"'
        assert self.expander.expand_line("'{1,2}' {3,4} '{5,6}'") == "'{1,2}' 3 4 '{5,6}'"
    
    def test_escaped_braces(self):
        """Test that escaped braces don't expand."""
        assert self.expander.expand_line(r"\{a,b,c\}") == r"\{a,b,c\}"
        assert self.expander.expand_line(r"file\{1,2\}.txt") == r"file\{1,2\}.txt"
        # Partial escaping
        assert self.expander.expand_line(r"\{a,b}") == r"\{a,b}"
        assert self.expander.expand_line(r"{a,b\}") == r"{a,b\}"
    
    def test_escaped_commas(self):
        """Test escaped commas in brace expansion."""
        assert self.expander.expand_line(r"{a\,b,c}") == r"a\,b c"
        assert self.expander.expand_line(r"{a,b\,c}") == r"a b\,c"
    
    def test_unmatched_braces(self):
        """Test handling of unmatched braces."""
        assert self.expander.expand_line("{a,b,c") == "{a,b,c"
        assert self.expander.expand_line("a,b,c}") == "a,b,c}"
        assert self.expander.expand_line("{{a,b}") == "{{a,b}"
        assert self.expander.expand_line("{a,b}}") == "{a,b}}"
    
    def test_complex_real_world_examples(self):
        """Test real-world use cases."""
        # Backup file
        assert self.expander.expand_line("cp file.conf{,.bak}") == "cp file.conf file.conf.bak"
        
        # Multiple directory creation
        assert self.expander.expand_line("mkdir -p project/{src,test,doc}") == \
               "mkdir -p project/src project/test project/doc"
        
        # Complex nested structure
        assert self.expander.expand_line("touch {dev,prod}/{app,db}/{config,data}.txt") == \
               "touch dev/app/config.txt dev/app/data.txt dev/db/config.txt " + \
               "dev/db/data.txt prod/app/config.txt prod/app/data.txt " + \
               "prod/db/config.txt prod/db/data.txt"
    
    def test_numeric_sequence_expansion(self):
        """Test numeric sequence expansion."""
        # Basic sequences
        assert self.expander.expand_line("{1..5}") == "1 2 3 4 5"
        assert self.expander.expand_line("{5..1}") == "5 4 3 2 1"
        assert self.expander.expand_line("{0..3}") == "0 1 2 3"
        
        # Negative numbers
        assert self.expander.expand_line("{-2..2}") == "-2 -1 0 1 2"
        assert self.expander.expand_line("{2..-2}") == "2 1 0 -1 -2"
        
        # Zero padding
        assert self.expander.expand_line("{01..05}") == "01 02 03 04 05"
        assert self.expander.expand_line("{001..005}") == "001 002 003 004 005"
        assert self.expander.expand_line("{1..010}") == "001 002 003 004 005 006 007 008 009 010"
        
        # With increment
        assert self.expander.expand_line("{0..10..2}") == "0 2 4 6 8 10"
        assert self.expander.expand_line("{10..0..2}") == "10 8 6 4 2 0"
        assert self.expander.expand_line("{1..10..3}") == "1 4 7 10"
        assert self.expander.expand_line("{00..10..2}") == "00 02 04 06 08 10"
        
        # Increment edge cases
        assert self.expander.expand_line("{1..5..0}") == "1 2 3 4 5"  # 0 treated as 1
        assert self.expander.expand_line("{5..1..-1}") == "5 4 3 2 1"  # Sign ignored
        assert self.expander.expand_line("{1..5..-1}") == "1 2 3 4 5"  # Sign ignored
    
    def test_char_sequence_expansion(self):
        """Test character sequence expansion."""
        # Basic sequences
        assert self.expander.expand_line("{a..e}") == "a b c d e"
        assert self.expander.expand_line("{e..a}") == "e d c b a"
        assert self.expander.expand_line("{A..E}") == "A B C D E"
        
        # Cross-case sequences (includes non-letter ASCII)
        result = self.expander.expand_line("{X..c}")
        assert result.startswith("X Y Z")
        assert result.endswith("a b c")
        assert "[" in result  # ASCII 91 between Z and a
        
        # With increment
        assert self.expander.expand_line("{a..z..3}") == "a d g j m p s v y"
        assert self.expander.expand_line("{z..a..3}") == "z w t q n k h e b"
        assert self.expander.expand_line("{A..Z..5}") == "A F K P U Z"
    
    def test_invalid_sequences(self):
        """Test that invalid sequences don't expand."""
        # Mixed types
        assert self.expander.expand_line("{1..a}") == "{1..a}"
        assert self.expander.expand_line("{a..5}") == "{a..5}"
        
        # Invalid characters
        assert self.expander.expand_line("{@..G}") == "{@..G}"
        assert self.expander.expand_line("{!..%}") == "{!..%}"
        
        # Floating point (not supported)
        assert self.expander.expand_line("{1.5..5.5}") == "{1.5..5.5}"
        
        # Multi-character
        assert self.expander.expand_line("{aa..zz}") == "{aa..zz}"
        assert self.expander.expand_line("{10..100..step}") == "{10..100..step}"
    
    def test_sequence_with_prefix_suffix(self):
        """Test sequence expansion with surrounding text."""
        assert self.expander.expand_line("file{1..3}.txt") == "file1.txt file2.txt file3.txt"
        assert self.expander.expand_line("test_{a..c}_end") == "test_a_end test_b_end test_c_end"
        assert self.expander.expand_line("/path/{01..03}/") == "/path/01/ /path/02/ /path/03/"
    
    def test_negative_padding(self):
        """Test zero padding with negative numbers."""
        assert self.expander.expand_line("{-05..05}") == "-05 -04 -03 -02 -01 000 001 002 003 004 005"
        assert self.expander.expand_line("{-3..03}") == "-3 -2 -1 00 01 02 03"
        assert self.expander.expand_line("{-03..03}") == "-03 -02 -01 000 001 002 003"
    
    def test_sequence_and_list_combined(self):
        """Test mixing sequence and list expansions."""
        assert self.expander.expand_line("{1..3}{a,b}") == "1a 1b 2a 2b 3a 3b"
        assert self.expander.expand_line("{a,b}{1..3}") == "a1 a2 a3 b1 b2 b3"
        assert self.expander.expand_line("{{1..3},{a..c}}") == "1 2 3 a b c"
    
    def test_memory_limit(self):
        """Test that excessive expansions are prevented."""
        # Save original limit
        original_limit = BraceExpander.MAX_EXPANSION_ITEMS
        
        # Set a small limit for testing
        BraceExpander.MAX_EXPANSION_ITEMS = 10
        
        try:
            # This would create 16 items, exceeding our test limit
            with pytest.raises(BraceExpansionError) as exc_info:
                self.expander.expand_line("{a,b}{c,d}{e,f}{g,h}")
            
            assert "would create" in str(exc_info.value)
            assert "limit: 10" in str(exc_info.value)
            
            # Test sequence that would exceed limit
            with pytest.raises(BraceExpansionError) as exc_info:
                self.expander.expand_line("{1..100}")  # Would create 100 items
            
            assert "would create" in str(exc_info.value)
        finally:
            # Restore original limit
            BraceExpander.MAX_EXPANSION_ITEMS = original_limit
    
    def test_special_characters_in_expansion(self):
        """Test brace expansion with special shell characters."""
        assert self.expander.expand_line("{a,b}>out.txt") == "a>out.txt b>out.txt"
        assert self.expander.expand_line("{cmd1,cmd2}|grep") == "cmd1|grep cmd2|grep"
        # When semicolon is part of the expansion, it gets expanded with each item
        assert self.expander.expand_line("{A,B};{C,D}") == "A;C A;D B;C B;D"
    
    def test_whitespace_handling(self):
        """Test handling of various whitespace scenarios."""
        assert self.expander.expand_line("  {a,b}  ") == "  a b  "
        assert self.expander.expand_line("\t{x,y}\t") == "\tx y\t"
        assert self.expander.expand_line("{a,b}\n{c,d}") == "a b\nc d"


class TestBraceExpansionIntegration:
    """Test brace expansion integration with tokenizer."""
    
    def test_tokenizer_integration(self):
        """Test that brace expansion works through the tokenizer."""
        from psh.lexer import tokenize
        from psh.token_types import TokenType
        
        # Simple expansion
        tokens = tokenize("echo {a,b,c}")
        values = [t.value for t in tokens if t.type == TokenType.WORD]
        assert values == ["echo", "a", "b", "c"]
        
        # With file extension
        tokens = tokenize("rm file{1,2,3}.txt")
        values = [t.value for t in tokens if t.type == TokenType.WORD]
        assert values == ["rm", "file1.txt", "file2.txt", "file3.txt"]
        
        # Multiple expansions
        tokens = tokenize("{cmd1,cmd2} {arg1,arg2}")
        values = [t.value for t in tokens if t.type == TokenType.WORD]
        assert values == ["cmd1", "cmd2", "arg1", "arg2"]
    
    def test_tokenizer_quotes_preserved(self):
        """Test that quoted braces don't expand in tokenizer."""
        from psh.lexer import tokenize
        from psh.token_types import TokenType
        
        tokens = tokenize('echo "{a,b,c}"')
        # Should have echo as WORD and {a,b,c} as STRING
        word_tokens = [t for t in tokens if t.type == TokenType.WORD]
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        
        assert len(word_tokens) == 1
        assert word_tokens[0].value == "echo"
        assert len(string_tokens) == 1
        assert string_tokens[0].value == "{a,b,c}"
    
    def test_tokenizer_with_operators(self):
        """Test brace expansion with shell operators."""
        from psh.lexer import tokenize
        from psh.token_types import TokenType
        
        # With pipe
        tokens = tokenize("{cat,head} file.txt | grep pattern")
        values = [t.value for t in tokens if t.type == TokenType.WORD]
        assert "cat" in values
        assert "head" in values
        assert "file.txt" in values
        assert "grep" in values
        assert "pattern" in values
        
        # Check pipe is present
        pipe_tokens = [t for t in tokens if t.type == TokenType.PIPE]
        assert len(pipe_tokens) == 1
    
    def test_tokenizer_error_handling(self):
        """Test that tokenizer handles brace expansion errors gracefully."""
        from psh.lexer import tokenize
        from psh.token_types import TokenType
        
        # Save original limit
        original_limit = BraceExpander.MAX_EXPANSION_ITEMS
        BraceExpander.MAX_EXPANSION_ITEMS = 5
        
        try:
            # This would exceed limit but should fall back to original string
            tokens = tokenize("{a,b,c}{d,e,f}")  # Would create 9 items
            # When expansion fails, we should get the original tokens
            # Check that we have braces and the content
            token_types = [t.type for t in tokens if t.type != TokenType.EOF]
            assert TokenType.LBRACE in token_types
            assert TokenType.RBRACE in token_types
            # Check that content wasn't expanded
            word_tokens = [t.value for t in tokens if t.type == TokenType.WORD]
            assert "a,b,c" in word_tokens  # Not expanded to separate a, b, c
            assert "d,e,f" in word_tokens  # Not expanded to separate d, e, f
        finally:
            BraceExpander.MAX_EXPANSION_ITEMS = original_limit