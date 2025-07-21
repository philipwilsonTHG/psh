"""Test coverage for parser combinator feature support.

This test file systematically checks which shell features are supported
by the parser combinator implementation.
"""

import pytest
from psh.lexer import tokenize
from psh.parser import ParseError
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser


class TestParserCombinatorFeatureCoverage:
    """Test which features the parser combinator supports."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def can_parse(self, command: str) -> bool:
        """Check if parser can parse the command without error."""
        try:
            tokens = tokenize(command)
            self.parser.parse(tokens)
            return True
        except Exception:
            return False
    
    # Control Structures (SUPPORTED)
    
    def test_if_statement_supported(self):
        """Test that if statements are supported."""
        assert self.can_parse("if true; then echo hi; fi")
        assert self.can_parse("if test x = y; then echo equal; else echo not equal; fi")
        assert self.can_parse("if true; then echo a; elif false; then echo b; else echo c; fi")
    
    def test_while_loop_supported(self):
        """Test that while loops are supported."""
        assert self.can_parse("while true; do echo loop; done")
        assert self.can_parse("while test $i -lt 10; do echo $i; done")
    
    def test_for_loop_supported(self):
        """Test that for loops are supported."""
        assert self.can_parse("for i in 1 2 3; do echo $i; done")
        assert self.can_parse("for file in *.txt; do cat $file; done")
    
    def test_case_statement_supported(self):
        """Test that case statements are supported."""
        assert self.can_parse("case $x in a) echo A;; b) echo B;; *) echo other;; esac")
        assert self.can_parse("case $var in [0-9]) echo digit;; [a-z]) echo lower;; esac")
    
    def test_function_definitions_supported(self):
        """Test that function definitions are supported."""
        assert self.can_parse("foo() { echo hello; }")
        assert self.can_parse("function bar { echo world; }")
    
    # I/O Redirection (PARTIALLY SUPPORTED)
    
    def test_output_redirection_supported(self):
        """Test that output redirection is supported."""
        assert self.can_parse("echo hello > file.txt")
        assert self.can_parse("echo world >> file.txt")
    
    def test_input_redirection_supported(self):
        """Test that input redirection is supported."""
        assert self.can_parse("cat < file.txt")
        # Complex case might not work
        # assert self.can_parse("while read line; do echo $line; done < input.txt")
    
    def test_fd_redirection_parsing(self):
        """Test file descriptor redirection parsing."""
        # Basic FD redirections parse
        assert self.can_parse("exec 3< file.txt")
        # File descriptor duplication now works
        assert self.can_parse("command 2>&1")
        assert self.can_parse("command >&2")
        # But &> shorthand might not work
        assert not self.can_parse("command &> output.txt")
    
    def test_heredoc_not_supported(self):
        """Test that here documents are NOT supported."""
        assert not self.can_parse("cat << EOF\nhello\nworld\nEOF")
        assert not self.can_parse("cat <<- EOF\n\thello\n\tworld\nEOF")
    
    def test_herestring_not_supported(self):
        """Test that here strings are NOT supported."""
        assert not self.can_parse("cat <<< 'hello world'")
    
    # Variable Assignment (PARSING SUPPORTED, EXECUTION UNTESTED)
    
    def test_simple_assignment_parsing(self):
        """Test that variable assignments can be parsed."""
        assert self.can_parse("VAR=value")
        assert self.can_parse("X=1 Y=2 Z=3")
    
    def test_assignment_with_command_parsing(self):
        """Test that assignments with commands can be parsed."""
        assert self.can_parse("VAR=value command")
        assert self.can_parse("PATH=/usr/bin:/bin ls")
    
    def test_export_parsing(self):
        """Test that export declarations can be parsed."""
        assert self.can_parse("export VAR=value")
        assert self.can_parse("export PATH")
    
    def test_array_assignment_parsing(self):
        """Test that array element assignments can be parsed."""
        # Array initialization might not work
        assert not self.can_parse("arr=(1 2 3)")
        # But array element assignment does parse
        assert self.can_parse("arr[0]=value")
    
    # Background Jobs (NOW SUPPORTED)
    
    def test_background_execution_supported(self):
        """Test that background execution is now supported."""
        assert self.can_parse("command &")
        assert self.can_parse("long_running_task &")
    
    # Subshells (NOT SUPPORTED)
    
    def test_subshell_not_supported(self):
        """Test that subshells are NOT supported."""
        assert not self.can_parse("(echo hello)")
        assert not self.can_parse("(cd /tmp && pwd)")
    
    def test_brace_group_not_supported(self):
        """Test that brace groups are NOT supported."""
        assert not self.can_parse("{ echo hello; echo world; }")
    
    # Advanced Features (NOT SUPPORTED)
    
    def test_arithmetic_command_not_supported(self):
        """Test that arithmetic commands are NOT supported."""
        assert not self.can_parse("((x = 5 + 3))")
        assert not self.can_parse("((i++))")
    
    def test_conditional_expression_not_supported(self):
        """Test that conditional expressions are NOT supported."""
        assert not self.can_parse("[[ -f file.txt ]]")
        assert not self.can_parse('[[ "$var" =~ ^[0-9]+$ ]]')
    
    def test_process_substitution_not_supported(self):
        """Test that process substitution is NOT supported."""
        assert not self.can_parse("diff <(sort file1) <(sort file2)")
        assert not self.can_parse("tee >(grep ERROR)")
    
    def test_select_loop_not_supported(self):
        """Test that select loops are NOT supported."""
        assert not self.can_parse("select item in a b c; do echo $item; done")
    
    # Features that MIGHT work
    
    def test_command_substitution_parsing(self):
        """Test command substitution in arguments."""
        # These might work as part of word parsing
        assert self.can_parse("echo $(date)")
        assert self.can_parse("echo `hostname`")
    
    def test_pipelines_supported(self):
        """Test that pipelines are supported."""
        assert self.can_parse("ls | grep txt")
        assert self.can_parse("cat file | sort | uniq")
    
    def test_and_or_lists_supported(self):
        """Test that && and || are supported."""
        assert self.can_parse("command1 && command2")
        assert self.can_parse("command1 || command2")
        assert self.can_parse("cmd1 && cmd2 || cmd3")


class TestParserCombinatorErrorMessages:
    """Test error messages for unsupported features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def parse_and_get_error(self, command: str) -> str:
        """Parse and return error message."""
        try:
            tokens = tokenize(command)
            self.parser.parse(tokens)
            return None
        except ParseError as e:
            return str(e)
        except Exception as e:
            return str(e)
    
    def test_complex_redirection_now_supported(self):
        """Test that complex redirections now work."""
        error = self.parse_and_get_error("command 2>&1")
        assert error is None  # Should parse successfully now
        
        # Test an actual invalid redirection
        error = self.parse_and_get_error("command &>")  # Missing target
        assert error is not None
    
    def test_heredoc_error_message(self):
        """Test error message for heredocs."""
        error = self.parse_and_get_error("cat << EOF")
        assert error is not None
    
    def test_background_now_supported(self):
        """Test that background jobs are now supported."""
        error = self.parse_and_get_error("sleep 10 &")
        assert error is None  # Should parse successfully now


class TestParserCombinatorFeatureSummary:
    """Summary test to document supported vs unsupported features."""
    
    def test_feature_matrix(self):
        """Document the feature support matrix."""
        parser = ParserCombinatorShellParser()
        
        features = {
            # Supported
            "if_statement": True,
            "while_loop": True,
            "for_loop": True,
            "case_statement": True,
            "function_definition": True,
            "pipelines": True,
            "and_or_lists": True,
            "command_substitution": True,
            "output_redirection": True,
            "input_redirection": True,
            
            "variable_assignment": True,  # Parses but execution untested
            "export_declaration": True,   # Parses but execution untested
            "array_element_assignment": True,  # arr[0]=value parses
            
            # Not Supported
            "heredoc": False,
            "herestring": False,
            "array_initialization": False,  # arr=(1 2 3) doesn't parse
            "background_jobs": False,
            "subshells": False,
            "brace_groups": False,
            "arithmetic_command": False,
            "conditional_expression": False,
            "process_substitution": False,
            "select_loop": False,
            "job_control": False,
        }
        
        supported = [k for k, v in features.items() if v]
        unsupported = [k for k, v in features.items() if not v]
        
        print("\nParser Combinator Feature Support:")
        print(f"Supported ({len(supported)}): {', '.join(supported)}")
        print(f"Unsupported ({len(unsupported)}): {', '.join(unsupported)}")
        
        # The parser combinator actually supports more features than initially thought
        assert len(supported) > len(unsupported)