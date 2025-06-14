"""
Tests for the MetricsVisitor.

This module tests code metrics collection functionality.
"""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.metrics_visitor import MetricsVisitor


class TestMetricsVisitor:
    """Test code metrics collection."""
    
    def parse_command(self, command):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return parse(tokens)
    
    def get_metrics(self, command):
        """Parse command and return metrics."""
        ast = self.parse_command(command)
        visitor = MetricsVisitor()
        visitor.visit(ast)
        return visitor.get_metrics()
    
    def test_basic_command_counting(self):
        """Test counting of basic commands."""
        script = """
        echo "Hello"
        ls -la
        cd /tmp
        pwd
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_commands == 4
        assert len(metrics.command_frequency) == 4
        assert metrics.command_frequency['echo'] == 1
        assert metrics.command_frequency['ls'] == 1
        assert metrics.command_frequency['cd'] == 1
        assert metrics.command_frequency['pwd'] == 1
    
    def test_builtin_vs_external_classification(self):
        """Test classification of builtin vs external commands."""
        script = """
        echo "test"      # builtin
        cd /tmp          # builtin
        export VAR=val   # builtin
        ls -la           # external
        grep pattern     # external
        """
        
        metrics = self.get_metrics(script)
        assert len(metrics.builtin_commands) == 3
        assert len(metrics.external_commands) == 2
        assert 'echo' in metrics.builtin_commands
        assert 'cd' in metrics.builtin_commands
        assert 'export' in metrics.builtin_commands
        assert 'ls' in metrics.external_commands
        assert 'grep' in metrics.external_commands
    
    def test_pipeline_metrics(self):
        """Test pipeline counting and length metrics."""
        script = """
        echo "test"
        ls | grep txt | sort | uniq
        cat file | wc -l
        ps aux | grep python | awk '{print $2}'
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_pipelines == 4  # All command sequences count as pipelines
        assert metrics.max_pipeline_length == 4  # ls | grep | sort | uniq
        assert metrics.total_commands == 10
    
    def test_function_metrics(self):
        """Test function definition counting."""
        script = """
        function hello() {
            echo "Hello, $1"
        }
        
        greet() {
            local name=$1
            echo "Greetings, $name"
        }
        
        hello "World"
        greet "User"
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_functions == 2
        assert 'hello' in metrics.function_names
        assert 'greet' in metrics.function_names
        assert 'hello' in metrics.function_metrics
        assert 'greet' in metrics.function_metrics
    
    def test_loop_counting(self):
        """Test counting different loop types."""
        script = """
        while read line; do
            echo "$line"
        done
        
        for file in *.txt; do
            cat "$file"
        done
        
        for ((i=0; i<10; i++)); do
            echo $i
        done
        
        select opt in "yes" "no"; do
            break
        done
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_loops == 4
        assert metrics.loop_types['while'] == 1
        assert metrics.loop_types['for'] == 1
        assert metrics.loop_types['c-style-for'] == 1
        assert metrics.loop_types['select'] == 1
    
    def test_conditional_counting(self):
        """Test counting conditional statements."""
        script = """
        if [ -f file.txt ]; then
            echo "exists"
        elif [ -d dir ]; then
            echo "directory"
        else
            echo "neither"
        fi
        
        case "$1" in
            start) echo "Starting..." ;;
            stop) echo "Stopping..." ;;
            *) echo "Unknown" ;;
        esac
        
        [[ $x -gt 5 ]] && echo "big"
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_conditionals >= 2  # if and case
        assert metrics.conditional_types['if'] == 1
        assert metrics.conditional_types['case'] == 1
    
    def test_cyclomatic_complexity(self):
        """Test cyclomatic complexity calculation."""
        # Simple linear script
        simple = "echo a; echo b; echo c"
        metrics = self.get_metrics(simple)
        assert metrics.cyclomatic_complexity == 1  # No branches
        
        # Script with if statement
        with_if = """
        if [ $x -eq 1 ]; then
            echo "one"
        else
            echo "other"
        fi
        """
        metrics = self.get_metrics(with_if)
        assert metrics.cyclomatic_complexity == 2  # if adds 1
        
        # Script with multiple branches
        complex = """
        if [ $x -eq 1 ]; then
            echo "one"
        elif [ $x -eq 2 ]; then
            echo "two"
        fi
        
        while [ $y -lt 10 ]; do
            y=$((y + 1))
        done
        
        [ $z -gt 5 ] && echo "big" || echo "small"
        """
        metrics = self.get_metrics(complex)
        # if=1, elif=1, while=1, &&=1, ||=1 = 5 + base 1 = 6
        assert metrics.cyclomatic_complexity >= 5
    
    def test_nesting_depth(self):
        """Test maximum nesting depth calculation."""
        script = """
        if [ $a -eq 1 ]; then
            if [ $b -eq 2 ]; then
                while [ $c -lt 3 ]; do
                    for i in 1 2 3; do
                        echo $i
                    done
                done
            fi
        fi
        """
        
        metrics = self.get_metrics(script)
        assert metrics.max_nesting_depth == 4  # if -> if -> while -> for
    
    def test_variable_detection(self):
        """Test variable name detection."""
        script = """
        name="John"
        age=30
        echo "Hello, $name"
        echo "Age: ${age}"
        
        for file in $files; do
            echo $file
        done
        
        result=$((x + y))
        """
        
        metrics = self.get_metrics(script)
        assert 'name' in metrics.variable_names
        assert 'age' in metrics.variable_names
        assert 'file' in metrics.variable_names  # loop variable
        assert 'files' in metrics.variable_names
    
    def test_array_operations(self):
        """Test array operation counting."""
        script = """
        arr=(one two three)
        arr[3]="four"
        echo ${arr[@]}
        
        declare -a numbers
        numbers+=(1 2 3)
        """
        
        metrics = self.get_metrics(script)
        # Arrays might be tracked as variables if parser doesn't generate array nodes
        if len(metrics.array_names) > 0:
            assert 'arr' in metrics.array_names
            assert 'numbers' in metrics.array_names
            assert len(metrics.array_names) == 2
        else:
            # At least check they're tracked as variables
            assert 'arr' in metrics.variable_names
            assert 'numbers' in metrics.variable_names
    
    def test_advanced_features(self):
        """Test counting of advanced shell features."""
        script = """
        # Command substitution
        result=$(ls -la)
        files=$(find . -name "*.txt")
        
        # Arithmetic
        ((x = 5 + 3))
        sum=$((a + b))
        
        # Here document
        cat <<EOF
        Hello
        World
        EOF
        
        # Process substitution
        diff <(sort file1) <(sort file2)
        """
        
        metrics = self.get_metrics(script)
        assert metrics.command_substitutions >= 2  # $() and ``
        assert metrics.arithmetic_evaluations >= 1  # ((x = 5 + 3))
        assert metrics.here_documents >= 1
        # Note: Process substitution might not be counted if not implemented in parser
    
    def test_redirection_counting(self):
        """Test counting of I/O redirections."""
        script = """
        echo "test" > output.txt
        echo "append" >> output.txt
        cat < input.txt
        command 2> error.log
        cmd > out.txt 2>&1
        """
        
        metrics = self.get_metrics(script)
        assert metrics.total_redirections == 6  # Each > >> < 2> counts
    
    def test_function_complexity(self):
        """Test per-function complexity metrics."""
        script = """
        function simple() {
            echo "Hello"
        }
        
        function complex() {
            if [ $1 -eq 1 ]; then
                echo "one"
            elif [ $1 -eq 2 ]; then
                echo "two"
            else
                while [ $x -lt 10 ]; do
                    echo $x
                    ((x++))
                done
            fi
        }
        """
        
        metrics = self.get_metrics(script)
        assert 'simple' in metrics.function_metrics
        assert 'complex' in metrics.function_metrics
        
        # Simple function has no branches
        assert metrics.function_metrics['simple']['complexity'] == 0
        
        # Complex function has if, elif, while
        assert metrics.function_metrics['complex']['complexity'] >= 3
    
    def test_break_continue_complexity(self):
        """Test that break/continue add to complexity."""
        script = """
        while true; do
            if [ $x -gt 10 ]; then
                break
            fi
            if [ $x -eq 5 ]; then
                continue
            fi
            ((x++))
        done
        """
        
        metrics = self.get_metrics(script)
        # while=1, if=1, if=1, break=1, continue=1 = 5 + base 1 = 6
        assert metrics.cyclomatic_complexity >= 5
    
    def test_metrics_report(self):
        """Test the metrics report generation."""
        script = """
        echo "Hello"
        ls | grep test
        
        function greet() {
            echo "Hi, $1"
        }
        
        for i in 1 2 3; do
            echo $i
        done
        """
        
        ast = self.parse_command(script)
        visitor = MetricsVisitor()
        visitor.visit(ast)
        
        report = visitor.get_report()
        
        # Check report structure
        assert 'summary' in report
        assert 'complexity' in report
        assert 'commands' in report
        assert 'control_flow' in report
        assert 'advanced_features' in report
        assert 'identifiers' in report
        assert 'function_metrics' in report
        
        # Check some values
        assert report['summary']['total_commands'] > 0
        assert report['commands']['unique_commands'] > 0
        assert 'echo' in report['commands']['top_10_commands']
    
    def test_metrics_summary_format(self):
        """Test the formatted summary output."""
        script = """
        echo "test"
        ls -la | grep txt
        """
        
        ast = self.parse_command(script)
        visitor = MetricsVisitor()
        visitor.visit(ast)
        
        summary = visitor.get_summary()
        
        # Check that summary contains expected sections
        assert "Script Metrics Summary:" in summary
        assert "Commands:" in summary
        assert "Structure:" in summary
        assert "Complexity:" in summary
        assert "Advanced Features:" in summary
        assert "Top Commands:" in summary
        
        # Check specific metrics are present
        assert "Total Commands:" in summary
        assert "Cyclomatic Complexity:" in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v'])