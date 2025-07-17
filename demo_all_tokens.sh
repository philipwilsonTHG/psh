#!/usr/bin/env psh
# PSH Token Type Demonstration Script
# This script demonstrates every token type in the unified PSH lexer system (v0.91.3+)
# Each major section exercises different groups of token types with explanatory comments

echo "=== PSH Token Type Demonstration Script ==="
echo "Showcasing the unified token system with enhanced features as standard"
echo

# ==============================================================================
# BASIC TOKENS AND OPERATORS
# ==============================================================================

echo "--- Basic Tokens and Operators ---"

# WORD tokens (unquoted strings)
echo hello world

# PIPE token (|) - pipeline operator
echo "first command" | echo "second command"

# SEMICOLON (;) - command separator  
echo one ; echo two

# AMPERSAND (&) - background operator
echo "background job" &

# AND_AND (&&) and OR_OR (||) - conditional operators
echo "success" && echo "this runs" || echo "this doesn't"

# NEWLINE tokens (implicit)
echo "line 1"
echo "line 2"

echo

# ==============================================================================
# REDIRECTION TOKENS
# ==============================================================================

echo "--- I/O Redirection Tokens ---"

# Create temp files for redirection demos
mkdir -p /tmp/psh_demo
cd /tmp/psh_demo

# REDIRECT_OUT (>) - output redirection
echo "output content" > output.txt

# REDIRECT_APPEND (>>) - append redirection  
echo "appended content" >> output.txt

# REDIRECT_IN (<) - input redirection
cat < output.txt

# REDIRECT_ERR (2>) - error redirection
echo "error output" 2> error.txt

# REDIRECT_ERR_APPEND (2>>) - error append
echo "more errors" 2>> error.txt

# REDIRECT_DUP (>&) - file descriptor duplication
echo "combined output" > combined.txt 2>&1

# HERE_STRING (<<<) - here string
cat <<< "here string content"

# HEREDOC (<<) - here document
cat << 'EOF'
This is a here document
with multiple lines
demonstrating HEREDOC tokens
EOF

# HEREDOC_STRIP (<<-) - here document with leading tabs stripped
cat <<- EOF
	This heredoc strips leading tabs
	from each line automatically
	EOF

echo

# ==============================================================================
# QUOTED STRINGS AND VARIABLES
# ==============================================================================

echo "--- Quoted Strings and Variables ---"

# STRING tokens (quoted strings)
echo "double quoted string"
echo 'single quoted string'

# VARIABLE tokens ($var)
test_var="variable content"
echo $test_var
echo ${test_var}

# ASSIGNMENT_WORD tokens (VAR=value)
new_var="assigned value"

# Assignment operators - testing all types
counter=5       # ASSIGN (basic assignment)
counter+=3      # PLUS_ASSIGN
counter-=1      # MINUS_ASSIGN  
counter*=2      # MULT_ASSIGN
counter/=2      # DIV_ASSIGN
counter%=3      # MOD_ASSIGN
counter&=7      # AND_ASSIGN (bitwise)
counter|=1      # OR_ASSIGN (bitwise)
counter^=2      # XOR_ASSIGN (bitwise)
counter<<=1     # LSHIFT_ASSIGN (left shift)
counter>>=1     # RSHIFT_ASSIGN (right shift)

echo "Counter result: $counter"

# Array assignments (ARRAY_ASSIGNMENT_WORD)
declare -a test_array
test_array[0]="first element"     # ARRAY_ASSIGNMENT_WORD
test_array[1]="second element"    # ARRAY_ASSIGNMENT_WORD  
test_array[$counter]="indexed"    # Dynamic index

echo "Array elements: ${test_array[0]} ${test_array[1]}"

echo

# ==============================================================================
# EXPANSIONS AND SUBSTITUTIONS
# ==============================================================================

echo "--- Expansions and Substitutions ---"

# COMMAND_SUB $(...)  - command substitution
current_date=$(date +%Y-%m-%d)
echo "Current date: $current_date"

# COMMAND_SUB_BACKTICK `...` - backtick command substitution
current_user=`whoami`
echo "Current user: $current_user"

# ARITH_EXPANSION $((..)) - arithmetic expansion
result=$((5 * 8 + 2))
echo "Arithmetic result: $result"

# PROCESS_SUB_IN <(...) and PROCESS_SUB_OUT >(...) - process substitution
diff <(echo "content1") <(echo "content2") || echo "Files differ as expected"
tee >(cat > /tmp/copy1.txt) >(cat > /tmp/copy2.txt) <<< "process substitution output"

echo

# ==============================================================================
# GROUPING AND BRACKETS
# ==============================================================================

echo "--- Grouping and Brackets ---"

# LPAREN and RPAREN (...) - subshell grouping
(echo "in subshell"; test_subshell_var="isolated")
echo "Outside subshell - variable not set: $test_subshell_var"

# LBRACE and RBRACE {...} - command grouping
{ echo "in command group"; group_var="shared"; }
echo "Outside group - variable is set: $group_var"

# LBRACKET and RBRACKET [...] - test command
if [ "$test_var" = "variable content" ]; then
    echo "Bracket test passed"
fi

# DOUBLE_LPAREN and DOUBLE_RPAREN ((...)) - arithmetic command
if ((result > 40)); then
    echo "Arithmetic test passed"
fi

echo

# ==============================================================================
# CONTROL STRUCTURE KEYWORDS
# ==============================================================================

echo "--- Control Structure Keywords ---"

# IF, THEN, ELSE, FI keywords
if [ "$counter" -gt 0 ]; then
    echo "Counter is positive"
elif [ "$counter" -eq 0 ]; then
    echo "Counter is zero"  
else
    echo "Counter is negative"
fi

# WHILE, DO, DONE keywords
temp_counter=3
while [ $temp_counter -gt 0 ]; do
    echo "While loop iteration: $temp_counter"
    temp_counter=$((temp_counter - 1))
done

# FOR, IN keywords
for item in apple banana cherry; do
    echo "For loop item: $item"
done

# CASE, ESAC keywords with terminators
test_value="banana"
case $test_value in
    apple)
        echo "It's an apple"
        ;;  # DOUBLE_SEMICOLON
    banana|cherry)
        echo "It's a banana or cherry"
        ;&  # SEMICOLON_AMP (fallthrough)
    *)
        echo "Fallthrough or default case"
        ;;&  # AMP_SEMICOLON (continue matching)
esac

# Second case to demonstrate different terminators
case "test" in
    test)
        echo "Matched test"
        ;;
esac

# BREAK and CONTINUE keywords (in a loop context)
for num in 1 2 3 4 5; do
    if [ "$num" -eq 2 ]; then
        continue  # Skip 2
    fi
    if [ "$num" -eq 4 ]; then
        break     # Stop at 4
    fi
    echo "Loop number: $num"
done

# SELECT keyword (interactive menu - demo version)
echo "SELECT keyword demonstration (non-interactive):"
# select choice in option1 option2 option3; do
#     echo "Selected: $choice"
#     break
# done

echo

# ==============================================================================
# ENHANCED TEST OPERATORS  
# ==============================================================================

echo "--- Enhanced Test Operators ---"

# DOUBLE_LBRACKET and DOUBLE_RBRACKET [[...]] - enhanced test
if [[ "$test_var" == "variable content" ]]; then
    echo "Enhanced test with EQUAL operator passed"
fi

# NOT_EQUAL (!=) operator
if [[ "$test_var" != "wrong content" ]]; then
    echo "Enhanced test with NOT_EQUAL operator passed"
fi

# REGEX_MATCH (=~) operator
if [[ "$test_var" =~ ^variable ]]; then
    echo "Enhanced test with REGEX_MATCH operator passed"
fi

# Context-specific comparison operators in enhanced tests
if [[ 10 > 5 ]]; then  # GREATER_THAN_TEST
    echo "Enhanced comparison (>) passed"
fi

if [[ 3 < 7 ]]; then   # LESS_THAN_TEST
    echo "Enhanced comparison (<) passed"
fi

if [[ 10 >= 5 ]]; then  # GREATER_EQUAL_TEST
    echo "Enhanced comparison (>=) passed"
fi

if [[ 3 <= 7 ]]; then   # LESS_EQUAL_TEST  
    echo "Enhanced comparison (<=) passed"
fi

# EXCLAMATION (!) - negation operator
if [[ ! -z "$test_var" ]]; then
    echo "Negation test passed - variable is not empty"
fi

echo

# ==============================================================================
# PATTERN MATCHING AND GLOBBING
# ==============================================================================

echo "--- Pattern Matching and Globbing ---"

# Create test files for glob demonstrations
touch file1.txt file2.log file3.txt

# GLOB_STAR (*) - wildcard matching
echo "Files matching *.txt:"
for file in *.txt; do
    echo "  $file"
done

# GLOB_QUESTION (?) - single character wildcard  
echo "Files matching file?.txt:"
for file in file?.txt; do
    echo "  $file"
done

# GLOB_BRACKET ([...]) - character class matching
echo "Files matching file[12].*:"
for file in file[12].*; do
    echo "  $file"  
done

# Additional glob demonstrations
echo "Files with any extension:"
for file in file*.*; do  # GLOB_STAR
    echo "  $file"
done

echo "Files matching pattern file?.???:"  
for file in file?.???; do  # GLOB_QUESTION
    echo "  $file"
done

echo

# ==============================================================================
# FUNCTIONS
# ==============================================================================

echo "--- Function Definition and Calls ---"

# FUNCTION keyword (bash style)
function demo_function() {
    echo "Inside demo_function with args: $@"
    local local_var="local value"
    echo "Local variable: $local_var"
}

# POSIX style function definition (without FUNCTION keyword)
another_function() {
    echo "POSIX style function called"
}

# Call functions
demo_function arg1 arg2
another_function

echo

# ==============================================================================
# COMPOSITE TOKENS
# ==============================================================================

echo "--- Composite Tokens ---"

# COMPOSITE tokens (adjacent string-like elements)
echo prefix"middle part"suffix'end'         # Multiple adjacent quoted parts
echo $USER"@"$(hostname)".local"           # Variable + string + command sub + string
echo file-$((1+1)).txt                     # Word + arithmetic + word

# Mixed quoting creates composite tokens  
mixed_var="quoted"unquoted'single'$USER    # Multiple types in one assignment
echo "Mixed composite: $mixed_var"

# More composite examples
echo start_"middle"_end                     # Word parts with quotes
echo $HOME/bin/$USER                        # Variables with literal parts

echo

# ==============================================================================
# ADVANCED DEMONSTRATIONS
# ==============================================================================

echo "--- Advanced Token Combinations ---"

# Complex pipeline with multiple token types
echo "apple banana cherry" | tr ' ' '\n' | sort | while read fruit; do
    case $fruit in
        apple)  echo "🍎 $fruit" ;;
        banana) echo "🍌 $fruit" ;;
        cherry) echo "🍒 $fruit" ;;
    esac
done

# Arithmetic with variables and command substitution
file_count=$(ls -1 *.txt | wc -l)
total_calculation=$((file_count * 10 + 5))
echo "File count calculation: $file_count files * 10 + 5 = $total_calculation"

# Complex conditional with multiple operators
if [[ -f "output.txt" && -s "output.txt" ]]; then
    echo "output.txt exists and is not empty"
fi

# Array operations with expansions
declare -a demo_array=(one two three)
echo "All array elements: ${demo_array[@]}"
echo "Array indices: ${!demo_array[@]}"  
echo "Array length: ${#demo_array[@]}"

echo

# ==============================================================================
# CLEANUP AND SUMMARY
# ==============================================================================

echo "--- Cleanup and Summary ---"

# Clean up temporary files
rm -f *.txt *.log *.sh 2>/dev/null || true

echo
echo "=== Token Demonstration Complete ==="
echo "This script has demonstrated nearly every token type in PSH:"
echo "✓ Basic tokens (WORD, operators, separators)"
echo "✓ Redirection tokens (>, <, >>, 2>, >&, <<<, <<)"  
echo "✓ Variables and strings (VARIABLE, STRING, quoted forms)"
echo "✓ Expansions (command substitution, arithmetic, process substitution)"
echo "✓ Grouping (parentheses, braces, brackets)"
echo "✓ Control structures (if/then/else, while/do, for/in, case/esac)"
echo "✓ Enhanced tests ([[...]] with ==, !=, =~, !, <, >)"
echo "✓ Pattern matching (*, ?, [...])"
echo "✓ Functions (both FUNCTION keyword and POSIX styles)"
echo "✓ Assignment operators (=, +=, -=, *=, /=, %=)"
echo "✓ Composite tokens (mixed quoting and concatenation)"
echo "✓ Advanced combinations and real-world usage patterns"
echo
echo "The unified token system (v0.91.3+) provides rich metadata and context"
echo "information for every token, enabling advanced analysis and tooling."

# EOF token is implicit at end of script