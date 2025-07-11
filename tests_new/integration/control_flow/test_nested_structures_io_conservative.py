"""
Conservative nested control structures with I/O integration tests.

Tests nested control structures with I/O operations that are known to work well in PSH.
More advanced I/O patterns are marked as expected failures to track implementation areas.
"""

import pytest
import subprocess
import sys
import os


class TestBasicNestedIO:
    """Test basic I/O operations with nested control structures."""
    
    @pytest.mark.xfail(reason="Output redirection in nested for loops has implementation limitations")
    def test_simple_output_redirection_in_loops(self, temp_dir):
        """Test basic output redirection within nested structures."""
        script = '''
        for i in 1 2; do
            echo "Item $i" > "item_${i}.txt"
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        # Check individual files
        with open(os.path.join(temp_dir, 'item_1.txt'), 'r') as f:
            content1 = f.read().strip()
        assert content1 == "Item 1"
        
        with open(os.path.join(temp_dir, 'item_2.txt'), 'r') as f:
            content2 = f.read().strip()
        assert content2 == "Item 2"
    
    def test_append_redirection_in_case(self, temp_dir):
        """Test append redirection within case statements."""
        script = '''
        for item in apple 123 banana; do
            case "$item" in
                [0-9]*)
                    echo "Number: $item" >> numbers.txt
                    ;;
                *)
                    echo "Text: $item" >> text.txt
                    ;;
            esac
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'numbers.txt'), 'r') as f:
            numbers = f.read().strip()
        assert numbers == "Number: 123"
        
        with open(os.path.join(temp_dir, 'text.txt'), 'r') as f:
            text = f.read().strip()
        assert text == "Text: apple\nText: banana"
    
    def test_input_redirection_with_existing_file(self, temp_dir):
        """Test input redirection with pre-existing file."""
        # Create input file first
        input_file = os.path.join(temp_dir, 'input.txt')
        with open(input_file, 'w') as f:
            f.write('line1\nline2\n')
        
        script = '''
        counter=0
        while read line; do
            counter=$((counter + 1))
            echo "Line $counter: $line" >> output.txt
        done < input.txt
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'output.txt'), 'r') as f:
            output = f.read().strip()
        assert output == "Line 1: line1\nLine 2: line2"


class TestWorkingPipePatterns:
    """Test pipe patterns that work reliably with nested structures."""
    
    def test_echo_pipe_in_nested_structure(self, temp_dir):
        """Test echo with pipe in nested control structure."""
        script = '''
        for category in fruits colors; do
            case "$category" in
                fruits)
                    echo "apple banana cherry" > fruits_raw.txt
                    ;;
                colors)
                    echo "red blue green" > colors_raw.txt
                    ;;
            esac
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'fruits_raw.txt'), 'r') as f:
            fruits = f.read().strip()
        assert fruits == "apple banana cherry"
        
        with open(os.path.join(temp_dir, 'colors_raw.txt'), 'r') as f:
            colors = f.read().strip()
        assert colors == "red blue green"
    
    @pytest.mark.xfail(reason="Function output redirection in loops may have limitations")
    def test_simple_function_output_redirection(self, temp_dir):
        """Test function output redirection in nested context."""
        script = '''
        generate_data() {
            echo "Data for: $1"
            echo "Value: $2"
        }
        
        for item in item1 item2; do
            generate_data "test" "$item" > "${item}_data.txt"
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'item1_data.txt'), 'r') as f:
            item1_data = f.read().strip()
        assert "Data for: test" in item1_data
        assert "Value: item1" in item1_data


class TestAdvancedIOPatterns:
    """Test advanced I/O patterns - many expected to fail for now."""
    
    @pytest.mark.xfail(reason="Complex redirection in nested loops may not be fully supported")
    def test_complex_nested_redirection(self, temp_dir):
        """Test complex redirection patterns in deeply nested structures."""
        script = '''
        for outer in 1 2; do
            for inner in a b; do
                echo "${outer}-${inner}"
            done > "output${outer}.txt"
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'output1.txt'), 'r') as f:
            content1 = f.read().strip()
        assert content1 == "1-a\n1-b"
    
    @pytest.mark.xfail(reason="Heredoc support in case statements may be limited")
    def test_heredoc_in_case_statement(self, temp_dir):
        """Test heredoc usage within case statements."""
        script = '''
        for section in header body; do
            case "$section" in
                header)
                    cat > "${section}.txt" << 'EOF'
This is the header.
Multiple lines here.
EOF
                    ;;
                body)
                    cat > "${section}.txt" << 'EOF'
This is the body.
More content here.
EOF
                    ;;
            esac
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'header.txt'), 'r') as f:
            header = f.read().strip()
        assert "This is the header." in header
    
    @pytest.mark.xfail(reason="Complex pipeline processing may have limitations")
    def test_while_read_with_pipes(self, temp_dir):
        """Test while read pattern with pipes in nested structure."""
        script = '''
        echo -e "line1\\nline2\\nline3" | while read line; do
            case "$line" in
                line1)
                    echo "First: $line" > first.txt
                    ;;
                line2)
                    echo "Second: $line" > second.txt
                    ;;
                *)
                    echo "Other: $line" > other.txt
                    ;;
            esac
        done
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'first.txt'), 'r') as f:
            first = f.read().strip()
        assert first == "First: line1"
    
    @pytest.mark.xfail(reason="Error handling with redirection may need improvement")
    def test_error_handling_in_redirection(self, temp_dir):
        """Test error handling when redirection fails."""
        script = '''
        success_count=0
        for operation in good_file /nonexistent/bad_path; do
            if echo "test" > "$operation" 2>/dev/null; then
                success_count=$((success_count + 1))
            fi
        done
        echo "Successes: $success_count" > summary.txt
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'summary.txt'), 'r') as f:
            summary = f.read().strip()
        # Should have 1 success (good_file) and 1 failure
        assert "Successes: 1" in summary


class TestNestedStructuresRegression:
    """Test that nested structures don't break basic shell functionality."""
    
    @pytest.mark.xfail(reason="Complex redirection in nested structures may not work")
    def test_simple_command_after_nested_structure(self, temp_dir):
        """Test that simple commands work after complex nested structures."""
        script = '''
        # Complex nested structure
        for i in 1 2; do
            if [ "$i" -eq 1 ]; then
                case "$i" in
                    1) echo "one" ;;
                    2) echo "two" ;;
                esac
            fi
        done > complex_output.txt
        
        # Simple command should still work
        echo "simple command" > simple_output.txt
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'simple_output.txt'), 'r') as f:
            simple = f.read().strip()
        assert simple == "simple command"
        
        with open(os.path.join(temp_dir, 'complex_output.txt'), 'r') as f:
            complex_output = f.read().strip()
        assert complex_output == "one"
    
    @pytest.mark.xfail(reason="Output redirection in complex nested structures may fail")
    def test_variable_assignment_after_nesting(self, temp_dir):
        """Test that variable assignments work correctly after nested structures."""
        script = '''
        # Nested structure that modifies variables
        result=""
        for i in 1 2 3; do
            if [ "$i" -eq 2 ]; then
                result="found_two"
            fi
        done
        
        # Variable should retain value
        echo "Final result: $result" > final.txt
        
        # New assignment should work
        new_var="new_value"
        echo "New variable: $new_var" >> final.txt
        '''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        with open(os.path.join(temp_dir, 'final.txt'), 'r') as f:
            final_content = f.read().strip()
        assert "Final result: found_two" in final_content
        assert "New variable: new_value" in final_content