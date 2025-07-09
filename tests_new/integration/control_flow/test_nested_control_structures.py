"""
Nested control structures integration tests.

Tests for arbitrarily nested control structures including if/for/while/case
combinations and complex nesting scenarios.
"""

import pytest


def test_if_inside_for(shell, capsys):
    """Test if statement inside for loop."""
    script = '''
    for i in 1 2 3; do
        if [ "$i" = "2" ]; then
            echo "Found 2"
        else
            echo "Not 2: $i"
        fi
    done
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Not 2: 1" in output
    assert "Found 2" in output
    assert "Not 2: 3" in output


def test_for_inside_if(shell, capsys):
    """Test for loop inside if statement."""
    shell.run_command('CONDITION=true')
    
    script = '''
    if $CONDITION; then
        for item in apple banana cherry; do
            echo "Item: $item"
        done
    else
        echo "Condition false"
    fi
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Item: apple" in output
    assert "Item: banana" in output
    assert "Item: cherry" in output


def test_while_inside_case(shell, capsys):
    """Test while loop inside case statement."""
    shell.run_command('ACTION=count')
    
    script = '''
    case $ACTION in
        count)
            i=1
            while [ $i -le 3 ]; do
                echo "Count: $i"
                i=$((i + 1))
            done
            ;;
        list)
            echo "List mode"
            ;;
        *)
            echo "Unknown action"
            ;;
    esac
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Count: 1" in output
    assert "Count: 2" in output
    assert "Count: 3" in output


def test_case_inside_for(shell, capsys):
    """Test case statement inside for loop."""
    script = '''
    for item in file.txt script.sh readme.md unknown; do
        case $item in
            *.txt)
                echo "$item is a text file"
                ;;
            *.sh)
                echo "$item is a shell script"
                ;;
            *.md)
                echo "$item is a markdown file"
                ;;
            *)
                echo "$item is unknown type"
                ;;
        esac
    done
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "file.txt is a text file" in output
    assert "script.sh is a shell script" in output
    assert "readme.md is a markdown file" in output
    assert "unknown is unknown type" in output


def test_nested_if_statements(shell, capsys):
    """Test deeply nested if statements."""
    shell.run_command('A=1')
    shell.run_command('B=2')
    shell.run_command('C=3')
    
    script = '''
    if [ $A -eq 1 ]; then
        echo "A is 1"
        if [ $B -eq 2 ]; then
            echo "B is 2"
            if [ $C -eq 3 ]; then
                echo "C is 3"
                echo "All conditions met"
            else
                echo "C is not 3"
            fi
        else
            echo "B is not 2"
        fi
    else
        echo "A is not 1"
    fi
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "A is 1" in output
    assert "B is 2" in output
    assert "C is 3" in output
    assert "All conditions met" in output


def test_nested_for_loops(shell, capsys):
    """Test nested for loops."""
    script = '''
    for outer in A B; do
        echo "Outer: $outer"
        for inner in 1 2; do
            echo "  Inner: $outer$inner"
        done
    done
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Outer: A" in output
    assert "  Inner: A1" in output
    assert "  Inner: A2" in output
    assert "Outer: B" in output
    assert "  Inner: B1" in output
    assert "  Inner: B2" in output


def test_complex_nested_structure(shell, capsys):
    """Test complex nested structure with multiple control types."""
    script = '''
    MODE=process
    case $MODE in
        process)
            echo "Processing mode"
            for item in 1 2 3; do
                if [ $item -eq 2 ]; then
                    echo "Special handling for item $item"
                    counter=1
                    while [ $counter -le 2 ]; do
                        echo "  Processing step $counter"
                        counter=$((counter + 1))
                    done
                else
                    echo "Normal handling for item $item"
                fi
            done
            ;;
        *)
            echo "Unknown mode"
            ;;
    esac
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Processing mode" in output
    assert "Normal handling for item 1" in output
    assert "Special handling for item 2" in output
    assert "  Processing step 1" in output
    assert "  Processing step 2" in output
    assert "Normal handling for item 3" in output


def test_break_in_nested_loops(shell, capsys):
    """Test break behavior in nested loops."""
    script = '''
    for outer in 1 2 3; do
        echo "Outer loop: $outer"
        for inner in a b c; do
            echo "  Inner loop: $inner"
            if [ "$inner" = "b" ]; then
                echo "  Breaking inner loop"
                break
            fi
        done
        if [ "$outer" = "2" ]; then
            echo "Breaking outer loop"
            break
        fi
    done
    echo "Done"
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Outer loop: 1" in output
    assert "  Inner loop: a" in output
    assert "  Inner loop: b" in output
    assert "  Breaking inner loop" in output
    # Should NOT contain "Inner loop: c" for outer=1
    assert "Outer loop: 2" in output
    assert "Breaking outer loop" in output
    # Should NOT contain "Outer loop: 3"
    assert "Done" in output


def test_continue_in_nested_loops(shell, capsys):
    """Test continue behavior in nested loops."""
    script = '''
    for outer in 1 2 3; do
        echo "Outer: $outer"
        if [ "$outer" = "2" ]; then
            echo "Skipping outer 2"
            continue
        fi
        for inner in x y z; do
            if [ "$inner" = "y" ]; then
                echo "  Skipping inner y"
                continue
            fi
            echo "  Processing: $outer$inner"
        done
    done
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Outer: 1" in output
    assert "  Processing: 1x" in output
    # Should skip y and show z
    assert "  Processing: 1z" in output
    assert "Outer: 2" in output
    assert "Skipping outer 2" in output
    # Should NOT process inner loop for outer=2
    assert "Outer: 3" in output
    assert "  Processing: 3x" in output
    assert "  Processing: 3z" in output


def test_function_with_nested_structures(shell, capsys):
    """Test function containing nested control structures."""
    shell.run_command('''
    process_data() {
        local mode=$1
        case $mode in
            full)
                for i in 1 2 3; do
                    if [ $i -eq 2 ]; then
                        echo "Special: $i"
                    else
                        echo "Normal: $i"
                    fi
                done
                ;;
            simple)
                echo "Simple mode"
                ;;
        esac
    }
    ''')
    
    result = shell.run_command('process_data full')
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Normal: 1" in output
    assert "Special: 2" in output
    assert "Normal: 3" in output


def test_nested_structures_with_variables(shell, capsys):
    """Test nested structures with variable scoping."""
    script = '''
    GLOBAL=global
    echo "Global: $GLOBAL"
    
    for scope in 1 2; do
        LOCAL=local_$scope
        echo "Loop $scope: $LOCAL"
        
        if [ "$scope" = "1" ]; then
            INNER=inner_value
            echo "  If: $INNER"
        else
            echo "  Else: ${INNER:-undefined}"
        fi
        
        echo "  Global in loop: $GLOBAL"
    done
    
    echo "After loop - Local: ${LOCAL:-undefined}"
    echo "After loop - Inner: ${INNER:-undefined}"
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Global: global" in output
    assert "Loop 1: local_1" in output
    assert "  If: inner_value" in output
    assert "Loop 2: local_2" in output
    # Variables should persist outside control structures
    assert "After loop - Local: local_2" in output
    assert "After loop - Inner: inner_value" in output


@pytest.mark.xfail(reason="Very deep nesting may hit parser or execution limits")
def test_very_deep_nesting(shell, capsys):
    """Test very deep nesting to check limits."""
    script = '''
    if true; then
        if true; then
            if true; then
                if true; then
                    if true; then
                        echo "Very deep nesting works"
                    fi
                fi
            fi
        fi
    fi
    '''
    result = shell.run_command(script)
    assert result == 0
    
    captured = capsys.readouterr()
    assert "Very deep nesting works" in captured.out