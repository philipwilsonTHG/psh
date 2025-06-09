#!/usr/bin/env psh
# Control Structures in Pipelines Demo
# Demonstrates the v0.37.0 feature that enables control structures as pipeline components

echo "=== PSH v0.37.0: Control Structures in Pipelines Demo ==="
echo "This demonstrates the ability to use control structures as pipeline components"
echo

# 1. WHILE LOOPS IN PIPELINES
echo "1. While Loops in Pipelines"
echo "----------------------------"

echo "Example 1a: Reading data through a pipeline into a while loop"
echo "one two three four five" | while read word; do 
    echo "Processing word: $word"
done
echo

echo "Example 1b: Processing file content line by line"
echo -e "apple\nbanana\ncherry\ndate" | while read fruit; do
    echo "Found fruit: $fruit (length: ${#fruit})"
done
echo

echo "Example 1c: Counting items through pipeline"
seq 1 5 | while read num; do
    echo "Number $num squared is $((num * num))"
done
echo

# 2. FOR LOOPS IN PIPELINES  
echo "2. For Loops in Pipelines"
echo "-------------------------"

echo "Example 2a: Traditional for loop with piped data"
echo "x y z" | for letter in a b c; do
    echo "Letter: $letter"
done
echo

echo "Example 2b: For loop processing sequential data"
seq 1 3 | for item in alpha beta gamma; do
    echo "Item $item"
done
echo

# 3. IF STATEMENTS IN PIPELINES
echo "3. If Statements in Pipelines"
echo "-----------------------------"

echo "Example 3a: Conditional processing based on pipeline input"
echo "success" | if grep -q "success"; then
    echo "✓ Success detected in pipeline"
else
    echo "✗ Success not found"
fi
echo

echo "Example 3b: Testing numeric values from pipeline"
echo "42" | if test $(cat) -gt 40; then
    echo "✓ Number is greater than 40"
else
    echo "✗ Number is 40 or less"
fi
echo

echo "Example 3c: Complex conditional with command substitution"
echo "hello world" | if [ $(wc -w) -eq 2 ]; then
    echo "✓ Input has exactly 2 words"
else
    echo "✗ Input does not have 2 words"
fi
echo

# 4. CASE STATEMENTS IN PIPELINES
echo "4. Case Statements in Pipelines"
echo "-------------------------------"

echo "Example 4a: Pattern matching on pipeline input"
echo "apple" | case $(cat) in apple) echo "🍎 Found an apple!" ;; banana) echo "🍌 Found a banana!" ;; *) echo "🤷 Unknown fruit" ;; esac
echo

echo "Example 4b: Processing different file types"
echo "script.sh" | case $(cat) in *.sh) echo "📜 Shell script detected" ;; *.py) echo "🐍 Python script detected" ;; *.txt) echo "📄 Text file detected" ;; *) echo "❓ Unknown file type" ;; esac
echo

# 5. ARITHMETIC COMMANDS IN PIPELINES
echo "5. Arithmetic Commands in Pipelines"
echo "-----------------------------------"

echo "Example 5a: Arithmetic evaluation with pipeline input"
echo "15" | if (($(cat) > 10)); then
    echo "✓ Number is greater than 10"
else
    echo "✗ Number is 10 or less"
fi
echo

echo "Example 5b: Mathematical operations on piped data"
echo "7" | while (($(cat) > 0)); do
    echo "Countdown: $(cat)"
    # Note: This is a demo - in practice you'd decrement the value
    break  # Prevent infinite loop in demo
done
echo

# 6. COMPLEX COMBINATIONS
echo "6. Complex Pipeline Combinations"
echo "--------------------------------"

echo "Example 6a: Nested control structures in pipeline"
seq 1 3 | while read outer; do
    echo "Processing group $outer:"
    echo "  a b c" | for inner in x y z; do
        echo "    $outer-$inner"
    done
done
echo

echo "Example 6b: Pipeline with conditional and loop"
echo "data processing pipeline" | if wc -w | while read count; do
    if [ $count -gt 2 ]; then
        echo "✓ Pipeline has $count words (sufficient data)"
        return 0
    else
        echo "✗ Pipeline has only $count words (insufficient data)"
        return 1
    fi
done; then
    echo "Pipeline validation: PASSED"
else
    echo "Pipeline validation: FAILED"
fi
echo

echo "Example 6c: Error handling in pipeline control structures"
echo "test data" | while read input; do
    if [ -z "$input" ]; then
        echo "⚠️ Warning: Empty input detected"
        continue
    fi
    echo "✓ Processing: $input"
    break  # Process only first non-empty line in demo
done
echo

# 7. PRACTICAL EXAMPLES
echo "7. Practical Real-World Examples"
echo "--------------------------------"

echo "Example 7a: Log processing pipeline"
echo "2024-01-06 INFO User login successful" | while read date time level message; do
    case $level in
        ERROR) echo "🔴 $date $time: $message" ;;
        WARN)  echo "🟡 $date $time: $message" ;;
        INFO)  echo "🔵 $date $time: $message" ;;
        *)     echo "⚪ $date $time $level: $message" ;;
    esac
done
echo

echo "Example 7b: Data transformation pipeline"
echo -e "1,John,Engineer\n2,Jane,Manager\n3,Bob,Developer" | while IFS=, read id name role; do
    if [ "$role" = "Manager" ]; then
        echo "👔 $name (ID: $id) - $role [LEADERSHIP]"
    else
        echo "👨‍💻 $name (ID: $id) - $role"
    fi
done
echo

echo "Example 7c: Configuration validation pipeline"
echo "timeout=30" | while IFS= read config; do
    case $config in
        timeout=*)
            value=${config#timeout=}
            if ((value > 0 && value <= 60)); then
                echo "✅ Valid timeout: ${value}s"
            else
                echo "❌ Invalid timeout: ${value}s (must be 1-60)"
            fi
            ;;
        *)
            echo "❓ Unknown config: $config"
            ;;
    esac
done
echo

echo "=== Demo Complete ==="
echo
echo "🚀 This feature (v0.37.0) enables advanced shell programming"
echo "   patterns by allowing control structures to be used in pipelines."
echo
echo "✨ Key Benefits:"
echo "   • More intuitive data processing pipelines"
echo "   • Cleaner script organization"
echo "   • Enhanced composability"
echo "   • Maintained backward compatibility"
echo
echo "📚 These examples demonstrate PSH's support for control structures"
echo "   as pipeline components through its unified command model."