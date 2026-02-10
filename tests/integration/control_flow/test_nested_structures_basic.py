"""
Basic nested control structures integration tests.

Tests fundamental two-level nesting patterns including if-for, while-if,
and for-while combinations with proper variable scoping and output handling.
"""



class TestBasicNestedStructures:
    """Test basic two-level nested control structures."""

    def test_if_inside_for(self, shell_with_temp_dir):
        """Test if statement inside for loop."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        for i in 1 2 3; do
            if [ "$i" -eq 2 ]; then
                result="${result}found_two "
            fi
            result="${result}${i} "
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "1 found_two 2 3"

    def test_while_inside_if(self, shell_with_temp_dir):
        """Test while loop inside if statement."""
        shell = shell_with_temp_dir

        script = '''
        condition="true"
        counter=0
        result=""

        if [ "$condition" = "true" ]; then
            while [ "$counter" -lt 3 ]; do
                counter=$((counter + 1))
                result="${result}${counter} "
            done
        fi
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "1 2 3"

    def test_for_inside_while(self, shell_with_temp_dir):
        """Test for loop inside while loop."""
        shell = shell_with_temp_dir

        script = '''
        outer=0
        result=""

        while [ "$outer" -lt 2 ]; do
            for inner in a b; do
                result="${result}${outer}-${inner} "
            done
            outer=$((outer + 1))
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "0-a 0-b 1-a 1-b"

    def test_nested_if_statements(self, shell_with_temp_dir):
        """Test multiple nested if statements."""
        shell = shell_with_temp_dir

        script = '''
        value=15
        result=""

        if [ "$value" -gt 10 ]; then
            result="${result}outer_true "
            if [ "$value" -gt 20 ]; then
                result="${result}inner_false "
            else
                if [ "$value" -eq 15 ]; then
                    result="${result}innermost_true "
                fi
                result="${result}inner_true "
            fi
        fi
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "outer_true innermost_true inner_true"

    def test_case_inside_for_basic(self, shell_with_temp_dir):
        """Test case statement inside for loop."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        for item in apple banana cherry; do
            case "$item" in
                apple)
                    result="${result}fruit1 "
                    ;;
                banana)
                    result="${result}fruit2 "
                    ;;
                *)
                    result="${result}other "
                    ;;
            esac
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "fruit1 fruit2 other"

    def test_variable_scoping_in_nesting(self, shell_with_temp_dir):
        """Test variable scoping across nested structures."""
        shell = shell_with_temp_dir

        script = '''
        outer_var="global"
        result=""

        for i in 1 2; do
            inner_var="loop${i}"
            if [ "$i" -eq 2 ]; then
                outer_var="modified"
                nested_var="created"
            fi
            result="${result}${outer_var}-${inner_var} "
        done

        # Check if nested_var exists outside
        if [ -n "${nested_var:-}" ]; then
            result="${result}nested_exists"
        fi

        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "global-loop1 modified-loop2 nested_exists"


class TestNestedControlFlow:
    """Test control flow statements (break/continue) in nested structures."""

    def test_break_in_nested_loops(self, shell_with_temp_dir):
        """Test break behavior in nested loops."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        for outer in 1 2 3; do
            result="${result}outer${outer}: "
            for inner in a b c; do
                if [ "$inner" = "b" ]; then
                    break
                fi
                result="${result}${inner} "
            done
            result="${result}end${outer} "
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "outer1: a end1 outer2: a end2 outer3: a end3"

    def test_continue_in_nested_loops(self, shell_with_temp_dir):
        """Test continue behavior in nested loops."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        for outer in 1 2 3; do
            if [ "$outer" -eq 2 ]; then
                continue
            fi
            for inner in a b; do
                result="${result}${outer}${inner} "
            done
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "1a 1b 3a 3b"

    def test_nested_while_with_break_continue(self, shell_with_temp_dir):
        """Test break and continue in nested while loops."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        outer=0
        while [ "$outer" -lt 3 ]; do
            outer=$((outer + 1))
            inner=0
            while [ "$inner" -lt 3 ]; do
                inner=$((inner + 1))
                if [ "$inner" -eq 2 ]; then
                    continue
                fi
                if [ "$outer" -eq 2 ] && [ "$inner" -eq 3 ]; then
                    break
                fi
                result="${result}${outer}${inner} "
            done
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "11 13 21 31 33"


class TestNestedFunctions:
    """Test functions within nested control structures."""

    def test_function_with_nested_structures(self, shell_with_temp_dir):
        """Test function containing nested control structures."""
        shell = shell_with_temp_dir

        script = '''
        process_items() {
            result=""
            for item in "$@"; do
                if [ "$item" -gt 5 ]; then
                    result="${result}big:${item} "
                else
                    result="${result}small:${item} "
                fi
            done
            echo "$result"
        }

        output=$(process_items 3 7 1 9)
        echo "$output" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "small:3 big:7 small:1 big:9"

    def test_nested_structures_calling_functions(self, shell_with_temp_dir):
        """Test nested structures that call functions."""
        shell = shell_with_temp_dir

        script = '''
        double() {
            echo $(($1 * 2))
        }

        result=""
        for i in 1 2 3; do
            doubled=$(double "$i")
            if [ "$doubled" -gt 3 ]; then
                result="${result}${doubled} "
            fi
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "4 6"

    def test_function_return_in_nested_structure(self, shell_with_temp_dir):
        """Test function return behavior within nested structures."""
        shell = shell_with_temp_dir

        script = '''
        find_value() {
            target="$1"
            for item in 5 10 15 20; do
                if [ "$item" -eq "$target" ]; then
                    return 0
                fi
            done
            return 1
        }

        result=""
        for search in 10 25 15; do
            if find_value "$search"; then
                result="${result}found:${search} "
            else
                result="${result}missing:${search} "
            fi
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "found:10 missing:25 found:15"


class TestComplexNestedPatterns:
    """Test complex multi-level nested control structures."""

    def test_case_inside_for_inside_if(self, shell_with_temp_dir):
        """Test three-level nesting: if containing for containing case."""
        shell = shell_with_temp_dir

        script = '''
        mode="process"
        result=""

        if [ "$mode" = "process" ]; then
            for file in doc.txt log.dat config.ini; do
                case "$file" in
                    *.txt)
                        result="${result}text:${file} "
                        ;;
                    *.dat)
                        result="${result}data:${file} "
                        ;;
                    *.ini)
                        result="${result}config:${file} "
                        ;;
                    *)
                        result="${result}unknown:${file} "
                        ;;
                esac
            done
        fi
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "text:doc.txt data:log.dat config:config.ini"

    def test_while_with_case_and_if(self, shell_with_temp_dir):
        """Test while containing case containing if."""
        shell = shell_with_temp_dir

        script = '''
        counter=0
        result=""

        while [ "$counter" -lt 4 ]; do
            counter=$((counter + 1))
            case "$counter" in
                1|3)
                    if [ "$counter" -eq 1 ]; then
                        result="${result}first "
                    else
                        result="${result}third "
                    fi
                    ;;
                2)
                    result="${result}second "
                    ;;
                *)
                    result="${result}other "
                    ;;
            esac
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "first second third other"


class TestNestedStructuresBackwardCompatibility:
    """Test backward compatibility after nested structure implementation."""

    def test_simple_commands_still_work(self, shell_with_temp_dir):
        """Test that simple commands work correctly."""
        shell = shell_with_temp_dir

        script = 'echo "hello world" > output.txt'
        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "hello world"

    def test_basic_if_still_works(self, shell_with_temp_dir):
        """Test that basic if statements work correctly."""
        shell = shell_with_temp_dir

        script = '''
        if [ "test" = "test" ]; then
            echo "success" > output.txt
        else
            echo "failure" > output.txt
        fi
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "success"

    def test_basic_for_loop_still_works(self, shell_with_temp_dir):
        """Test that basic for loops work correctly."""
        shell = shell_with_temp_dir

        script = '''
        result=""
        for item in a b c; do
            result="${result}${item}"
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "abc"

    def test_basic_while_loop_still_works(self, shell_with_temp_dir):
        """Test that basic while loops work correctly."""
        shell = shell_with_temp_dir

        script = '''
        counter=0
        result=""
        while [ "$counter" -lt 3 ]; do
            counter=$((counter + 1))
            result="${result}${counter}"
        done
        echo "$result" > output.txt
        '''

        result = shell.run_command(script)
        assert result == 0

        with open('output.txt', 'r') as f:
            output = f.read().strip()
        assert output == "123"
