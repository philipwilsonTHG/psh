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
    
    def test_sequence_expansion_placeholder(self):
        """Test that sequence expansions are recognized but not expanded (Phase 1)."""
        # These should remain unchanged in Phase 1
        assert self.expander.expand_line("{1..10}") == "{1..10}"
        assert self.expander.expand_line("{a..z}") == "{a..z}"
        assert self.expander.expand_line("file{01..05}.txt") == "file{01..05}.txt"
    
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
        from psh.tokenizer import tokenize, TokenType
        
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
        from psh.tokenizer import tokenize, TokenType
        
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
        from psh.tokenizer import tokenize, TokenType
        
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
        from psh.tokenizer import tokenize, TokenType
        
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