# Chapter 10: Pipelines and Lists

Pipelines and command lists are fundamental to shell programming, allowing you to combine simple commands into powerful data processing workflows. PSH supports pipes for connecting commands, conditional execution with && and ||, and sequential execution with semicolons.

**v0.37.0 Feature**: PSH now supports **control structures in pipelines** - enabling while loops, for loops, if statements, case statements, select statements, and arithmetic commands as pipeline components.

## 10.1 Simple Pipelines (|)

A pipeline connects the stdout of one command to the stdin of the next, creating a data processing chain.

### Basic Pipeline Usage

```bash
# Simple two-command pipeline
psh$ ls | wc -l
42

# How it works:
# 1. ls writes filenames to stdout
# 2. | connects ls stdout to wc stdin  
# 3. wc counts the lines

# Multiple commands
psh$ cat file.txt | grep "error" | sort | uniq -c
      3 error: file not found
      1 error: permission denied
      5 error: timeout

# Long pipelines with line continuation
psh$ cat access.log | \
>    grep "GET" | \
>    awk '{print $1}' | \
>    sort | \
>    uniq -c | \
>    sort -rn | \
>    head -10

# Process text data
psh$ echo "hello world" | tr 'a-z' 'A-Z'
HELLO WORLD

psh$ echo "one,two,three" | tr ',' '\n'
one
two
three
```

### Pipeline Data Flow

```bash
# Understanding data flow
psh$ echo "Step 1" | sed 's/1/2/' | sed 's/2/3/'
Step 3

# Each command processes the full stream
psh$ seq 1 5 | grep -v 3 | sed 's/^/Number: /'
Number: 1
Number: 2
Number: 4
Number: 5

# Buffering in pipelines
psh$ # Commands may buffer output
psh$ tail -f logfile | grep ERROR
# May not show output immediately due to buffering

# Force line buffering
psh$ tail -f logfile | grep --line-buffered ERROR
```

### Common Pipeline Patterns

```bash
# Count occurrences
psh$ cat log.txt | grep "ERROR" | wc -l
25

# Find unique values
psh$ cut -d: -f1 /etc/passwd | sort | uniq

# Top N items
psh$ cat access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# Search and extract
psh$ ps aux | grep python | awk '{print $2}'

# Filter and format
psh$ df -h | grep -v tmpfs | awk '{print $5, $6}' | sort -n

# Process CSV data
psh$ cat data.csv | cut -d, -f2,4 | sort | uniq

# Transform data formats
psh$ cat file.json | jq '.users[]' | grep active | wc -l
```

## 10.2 Control Structures in Pipelines (v0.37.0)

PSH v0.37.0 introduces the ability to use control structures as pipeline components, enabling advanced data processing patterns.

### While Loops in Pipelines

```bash
# Process data line by line through a pipeline
psh$ echo -e "apple\nbanana\ncherry" | while read fruit; do
>     echo "Processing fruit: $fruit (length: ${#fruit})"
> done
Processing fruit: apple (length: 5)
Processing fruit: banana (length: 6)
Processing fruit: cherry (length: 6)

# Count and process sequential data
psh$ seq 1 5 | while read num; do
>     echo "Number $num squared is $((num * num))"
> done
Number 1 squared is 1
Number 2 squared is 4
Number 3 squared is 9
Number 4 squared is 16
Number 5 squared is 25

# Process file content with complex logic
psh$ cat logfile.txt | while read line; do
>     if echo "$line" | grep -q "ERROR"; then
>         echo "🔴 Error found: $line"
>     elif echo "$line" | grep -q "WARN"; then
>         echo "🟡 Warning: $line"
>     else
>         echo "ℹ️ Info: $line"
>     fi
> done
```

### For Loops in Pipelines

```bash
# Traditional for loop processing pipeline data
psh$ echo "processing data" | for item in alpha beta gamma; do
>     echo "Item: $item"
> done
Item: alpha
Item: beta
Item: gamma

# Dynamic for loop with command substitution
psh$ seq 1 3 | for i in $(cat); do
>     echo "Processing number: $i"
> done
Processing number: 1
Processing number: 2
Processing number: 3
```

### If Statements in Pipelines

```bash
# Conditional processing based on pipeline input
psh$ echo "success" | if grep -q "success"; then
>     echo "✅ Success detected in pipeline"
> else
>     echo "❌ Success not found"
> fi
✅ Success detected in pipeline

# Test numeric values from pipeline
psh$ echo "42" | if [ $(cat) -gt 40 ]; then
>     echo "✅ Number is greater than 40"
> else
>     echo "❌ Number is 40 or less"
> fi
✅ Number is greater than 40

# Complex conditional with word count
psh$ echo "hello world test" | if [ $(wc -w) -eq 3 ]; then
>     echo "✅ Input has exactly 3 words"
> else
>     echo "❌ Input does not have 3 words"
> fi
✅ Input has exactly 3 words
```

### Case Statements in Pipelines

```bash
# Pattern matching on pipeline input
psh$ echo "apple" | case $(cat) in
>     apple)  echo "🍎 Found an apple!" ;;
>     banana) echo "🍌 Found a banana!" ;;
>     *)      echo "🤷 Unknown fruit" ;;
> esac
🍎 Found an apple!

# File type detection
psh$ echo "script.sh" | case $(cat) in
>     *.sh)   echo "📜 Shell script detected" ;;
>     *.py)   echo "🐍 Python script detected" ;;
>     *.txt)  echo "📄 Text file detected" ;;
>     *)      echo "❓ Unknown file type" ;;
> esac
📜 Shell script detected
```

### Arithmetic Commands in Pipelines

```bash
# Arithmetic evaluation with pipeline input
psh$ echo "15" | if (($(cat) > 10)); then
>     echo "✅ Number is greater than 10"
> else
>     echo "❌ Number is 10 or less"
> fi
✅ Number is greater than 10

# Mathematical operations on piped data
psh$ echo "5" | if (($(cat) * 2 > 8)); then
>     echo "✅ Double the number is greater than 8"
> fi
✅ Double the number is greater than 8
```

### Complex Pipeline Control Structures

```bash
# Nested control structures
psh$ seq 1 3 | while read outer; do
>     echo "Processing group $outer:"
>     echo "  a b c" | for inner in x y z; do
>         echo "    $outer-$inner"
>     done
> done
Processing group 1:
    1-x
    1-y
    1-z
Processing group 2:
    2-x
    2-y
    2-z
Processing group 3:
    3-x
    3-y
    3-z

# Pipeline validation with control structures
psh$ echo "data processing pipeline" | if wc -w | while read count; do
>     if [ $count -gt 2 ]; then
>         echo "✅ Pipeline has $count words (sufficient data)"
>         return 0
>     else
>         echo "❌ Pipeline has only $count words (insufficient data)"
>         return 1
>     fi
> done; then
>     echo "Pipeline validation: PASSED"
> else
>     echo "Pipeline validation: FAILED"
> fi
✅ Pipeline has 3 words (sufficient data)
Pipeline validation: PASSED
```

### Practical Examples

```bash
# Log processing pipeline with control structures
psh$ echo "2024-01-06 ERROR Database connection failed" | while read date time level message; do
>     case $level in
>         ERROR) echo "🔴 $date $time: $message" ;;
>         WARN)  echo "🟡 $date $time: $message" ;;
>         INFO)  echo "🔵 $date $time: $message" ;;
>         *)     echo "⚪ $date $time $level: $message" ;;
>     esac
> done
🔴 2024-01-06 ERROR: Database connection failed

# CSV data transformation
psh$ echo "1,John,Engineer" | while IFS=, read id name role; do
>     if [ "$role" = "Manager" ]; then
>         echo "👔 $name (ID: $id) - $role [LEADERSHIP]"
>     else
>         echo "👨‍💻 $name (ID: $id) - $role"
>     fi
> done
👨‍💻 John (ID: 1) - Engineer

# Configuration validation
psh$ echo "timeout=30" | while IFS= read config; do
>     case $config in
>         timeout=*)
>             value=${config#timeout=}
>             if ((value > 0 && value <= 60)); then
>                 echo "✅ Valid timeout: ${value}s"
>             else
>                 echo "❌ Invalid timeout: ${value}s (must be 1-60)"
>             fi
>             ;;
>         *)
>             echo "❓ Unknown config: $config"
>             ;;
>     esac
> done
✅ Valid timeout: 30s
```

### Technical Implementation

This feature is enabled by PSH's unified command model:
- **Simple Commands**: Traditional commands like `ls`, `cat`, `grep`
- **Compound Commands**: Control structures that can now act as pipeline components
- **Subshell Execution**: Control structures run in isolated subshells when used in pipelines
- **Full Compatibility**: All existing pipeline functionality remains unchanged

## 10.3 Pipeline Exit Status

The exit status of a pipeline is the exit status of the last command:

```bash
# Successful pipeline
psh$ echo "test" | grep "test" | wc -l
1
psh$ echo $?
0

# Failed command in middle
psh$ echo "test" | grep "nomatch" | wc -l
0
psh$ echo $?
0  # Exit status from wc, not grep!

# Failed last command
psh$ echo "test" | cat | false
psh$ echo $?
1

# Check intermediate failures (when pipefail is implemented)
# psh$ set -o pipefail
# psh$ false | echo "test"
# test
# psh$ echo $?
# 1

# Current behavior without pipefail
psh$ false | echo "test"
test
psh$ echo $?
0
```

### Capturing Pipeline Status

```bash
# Save intermediate results
psh$ ls | tee filelist.txt | wc -l
42

# Check specific command status using process substitution
psh$ if echo "test" | grep "test" > /dev/null; then
>     echo "Found"
> fi
Found

# Complex pipeline error handling
process_data() {
    local input="$1"
    local temp=$(mktemp)
    
    if cat "$input" | sort | uniq > "$temp"; then
        mv "$temp" "$input.processed"
        echo "Success"
    else
        rm -f "$temp"
        echo "Failed"
        return 1
    fi
}
```

## 10.3 Conditional Execution

### AND Lists (&&)

Execute the next command only if the previous succeeds:

```bash
# Basic AND list
psh$ mkdir newdir && cd newdir
# cd only runs if mkdir succeeds

# Multiple commands
psh$ cd /tmp && touch file.txt && echo "Created file"
Created file

# Conditional execution
psh$ [ -f config.txt ] && echo "Config exists"
Config exists

# Build pattern
psh$ make && make test && make install

# Backup before operation
psh$ cp important.txt important.bak && rm important.txt

# Chain of dependencies
psh$ command1 && \
>    command2 && \
>    command3 && \
>    echo "All succeeded"
```

### OR Lists (||)

Execute the next command only if the previous fails:

```bash
# Basic OR list
psh$ cd /somedir || echo "Directory not found"
Directory not found

# Fallback commands
psh$ wget file.txt || curl -O file.txt || echo "Download failed"

# Default values
psh$ grep "pattern" file.txt || echo "Pattern not found"

# Try alternatives
psh$ command1 || command2 || command3 || echo "All failed"

# Create if missing
psh$ [ -d ~/.config ] || mkdir ~/.config

# Exit on failure
psh$ important_command || exit 1
```

### Combining && and ||

```bash
# Ternary-like operation
psh$ [ -f file.txt ] && echo "exists" || echo "not found"
exists

# But be careful with side effects!
psh$ true && false || echo "This runs"
This runs

# Because:
# 1. true succeeds, so false runs
# 2. false fails, so echo runs

# Safer pattern with if/then
psh$ if [ -f file.txt ]; then
>     echo "exists"
> else
>     echo "not found"
> fi

# Complex conditions
psh$ command1 && command2 || command3 && command4
# Evaluation: (command1 && command2) || (command3 && command4)

# Explicit grouping
psh$ { command1 && command2; } || { command3 && command4; }
```

## 10.4 Command Lists (;)

Semicolons separate commands that run sequentially regardless of exit status:

```bash
# Basic command list
psh$ echo "First"; echo "Second"; echo "Third"
First
Second
Third

# Mixed with other operators
psh$ cd /tmp; ls | wc -l; pwd
15
/tmp

# Versus newlines
psh$ echo "First"
First
psh$ echo "Second"
Second
# Same as: echo "First"; echo "Second"

# In scripts
setup() {
    mkdir -p build;
    cd build;
    cmake ..;
    make -j4
}

# One-liners
psh$ for i in 1 2 3; do echo $i; done

# Combining with conditionals
psh$ [ -f file.txt ] && cat file.txt; echo "Done"
# echo runs regardless
```

## 10.5 Grouping Commands

### Subshells with ()

Parentheses create a subshell - a separate environment:

```bash
# Commands in subshell
psh$ (cd /tmp; pwd)
/tmp
psh$ pwd
/home/alice  # Original directory unchanged

# Environment isolation
psh$ var=original
psh$ (var=changed; echo "In subshell: $var")
In subshell: changed
psh$ echo "In parent: $var"
In parent: original

# Combine outputs
psh$ (echo "Header"; date; echo "Footer") > report.txt

# Parallel execution
psh$ (sleep 2; echo "Task 1") &
psh$ (sleep 1; echo "Task 2") &
psh$ wait
Task 2
Task 1

# Pipeline with subshell
psh$ (cat file1; cat file2) | sort | uniq
```

### Command Groups with {}

Braces group commands without creating a subshell:

```bash
# Commands in current shell
psh$ { echo "Start"; date; echo "End"; }
Start
Mon Jan 15 10:00:00 PST 2024
End

# Note: spaces and semicolon/newline required
psh$ {echo "bad"}      # Error - needs space
psh$ { echo "good"; }  # Correct

# Affect current environment
psh$ var=original
psh$ { var=changed; echo "In group: $var"; }
In group: changed
psh$ echo "After group: $var"
After group: changed

# Redirect group output
psh$ {
>     echo "Line 1"
>     echo "Line 2"
>     echo "Line 3"
> } > output.txt

# Error handling for groups
psh$ {
>     command1 &&
>     command2 &&
>     command3
> } || echo "Group failed"
```

## Practical Examples

### Log Analysis Pipeline

```bash
#!/usr/bin/env psh
# Analyze web server logs with pipelines

analyze_logs() {
    local logfile="$1"
    local date_filter="${2:-.*}"  # Optional date filter
    
    echo "=== Log Analysis for $logfile ==="
    echo
    
    # Top IP addresses
    echo "Top 10 IP Addresses:"
    grep "$date_filter" "$logfile" | \
        awk '{print $1}' | \
        sort | \
        uniq -c | \
        sort -rn | \
        head -10 | \
        awk '{printf "%5d %s\n", $1, $2}'
    echo
    
    # Response code distribution
    echo "HTTP Response Codes:"
    grep "$date_filter" "$logfile" | \
        awk '{print $9}' | \
        grep '^[0-9]' | \
        sort | \
        uniq -c | \
        sort -rn | \
        awk '{printf "%5d %s\n", $1, $2}'
    echo
    
    # Top requested URLs
    echo "Top 10 Requested URLs:"
    grep "$date_filter" "$logfile" | \
        awk '$6 == "\"GET" {print $7}' | \
        sort | \
        uniq -c | \
        sort -rn | \
        head -10 | \
        awk '{printf "%5d %s\n", $1, $2}'
    echo
    
    # Traffic by hour
    echo "Traffic by Hour:"
    grep "$date_filter" "$logfile" | \
        awk '{print $4}' | \
        cut -d: -f2 | \
        sort | \
        uniq -c | \
        awk '{printf "Hour %02d: %5d requests\n", $2, $1}'
}

# Usage
analyze_logs access.log
analyze_logs access.log "15/Jan/2024"

# Real-time monitoring
monitor_errors() {
    tail -f "$1" | \
    grep --line-buffered "ERROR\|FATAL" | \
    while read line; do
        echo "[$(date +%H:%M:%S)] $line"
        
        # Alert on critical errors
        if echo "$line" | grep -q "FATAL"; then
            echo "CRITICAL ALERT: $line" | \
                mail -s "Fatal Error" admin@example.com
        fi
    done
}
```

### Data Processing Pipeline

```bash
#!/usr/bin/env psh
# Complex data processing with error handling

process_csv_data() {
    local input_file="$1"
    local output_dir="${2:-.}"
    
    # Validate input
    [ -f "$input_file" ] || { echo "File not found: $input_file" >&2; return 1; }
    
    # Create output directory
    mkdir -p "$output_dir"/{processed,reports,errors}
    
    # Main processing pipeline
    {
        # Skip header and validate data
        tail -n +2 "$input_file" | \
        awk -F, '
            NF < 5 { print "Error: Too few fields:", $0 > "/dev/stderr"; next }
            $3 !~ /^[0-9]+$/ { print "Error: Invalid number:", $0 > "/dev/stderr"; next }
            { print }
        '
    } 2> "$output_dir/errors/validation.log" | \
    {
        # Transform and enrich data
        while IFS=, read -r id name value category date; do
            # Calculate derived fields
            tax=$(( value * 8 / 100 ))
            total=$(( value + tax ))
            
            # Output enriched data
            echo "$id,$name,$value,$tax,$total,$category,$date"
        done
    } | \
    {
        # Split by category
        tee >(grep ",electronics," > "$output_dir/processed/electronics.csv") \
            >(grep ",clothing," > "$output_dir/processed/clothing.csv") \
            >(grep ",food," > "$output_dir/processed/food.csv") | \
        {
            # Generate summary report
            awk -F, '
                BEGIN { print "Category,Count,Total" }
                { cat[$6]++; total[$6]+=$5 }
                END {
                    for (c in cat) {
                        print c "," cat[c] "," total[c]
                    }
                }
            ' | sort > "$output_dir/reports/summary.csv"
        }
    }
    
    # Check results
    local errors=$(wc -l < "$output_dir/errors/validation.log")
    if [ "$errors" -gt 0 ]; then
        echo "Warning: $errors validation errors found"
    fi
    
    # Generate final report
    {
        echo "=== Processing Report ==="
        echo "Date: $(date)"
        echo "Input: $input_file"
        echo "Errors: $errors"
        echo
        echo "Files created:"
        find "$output_dir" -type f -newer "$input_file" | \
            xargs ls -la | \
            awk '{print "  " $9 " (" $5 " bytes)"}'
    } | tee "$output_dir/reports/processing.log"
}

# Test data generator
generate_test_data() {
    cat > test_data.csv << 'EOF'
id,name,value,category,date
1,Product A,100,electronics,2024-01-15
2,Product B,abc,clothing,2024-01-15
3,Product C,200,food,2024-01-15
4,Product D,150,electronics
5,Product E,75,clothing,2024-01-15
EOF
}

# Usage
generate_test_data
process_csv_data test_data.csv output/
```

### Build System Pipeline

```bash
#!/usr/bin/env psh
# Build system with conditional execution

# Configuration
BUILD_DIR="build"
INSTALL_PREFIX="/usr/local"
JOBS=$(nproc 2>/dev/null || echo 4)

# Build functions
clean() {
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR" && echo "Clean successful" || return 1
}

configure() {
    echo "Configuring build..."
    mkdir -p "$BUILD_DIR" && \
    cd "$BUILD_DIR" && \
    cmake -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" .. && \
    echo "Configuration successful" || \
    { echo "Configuration failed" >&2; return 1; }
}

build() {
    echo "Building project..."
    cd "$BUILD_DIR" && \
    make -j"$JOBS" 2>&1 | \
    tee build.log | \
    grep -E "^\[|error:|warning:" || true
    
    # Check build result
    [ ${PIPESTATUS[0]} -eq 0 ] && \
    echo "Build successful" || \
    { echo "Build failed" >&2; return 1; }
}

run_tests() {
    echo "Running tests..."
    cd "$BUILD_DIR" && \
    ctest --output-on-failure 2>&1 | \
    tee test.log | \
    grep -E "Test #|Passed|Failed" || true
    
    # Check test result
    [ ${PIPESTATUS[0]} -eq 0 ] && \
    echo "All tests passed" || \
    { echo "Some tests failed" >&2; return 1; }
}

install() {
    echo "Installing..."
    cd "$BUILD_DIR" && \
    sudo make install && \
    echo "Installation successful" || \
    { echo "Installation failed" >&2; return 1; }
}

# Main build pipeline
full_build() {
    local start_time=$(date +%s)
    
    # Execute pipeline with conditional execution
    {
        clean && \
        configure && \
        build && \
        run_tests && \
        echo "Build pipeline completed successfully"
    } || {
        echo "Build pipeline failed at some step" >&2
        return 1
    }
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo "Total build time: ${duration}s"
}

# Parallel build tasks
parallel_build() {
    echo "Starting parallel build tasks..."
    
    # Run independent tasks in parallel
    {
        { build_docs && echo "Docs built"; } &
        { build_examples && echo "Examples built"; } &
        { run_linters && echo "Linting complete"; } &
        
        # Wait for all background jobs
        wait
    } && echo "All parallel tasks completed" || \
        echo "Some parallel tasks failed"
}

# Usage
case "${1:-build}" in
    clean)     clean ;;
    configure) configure ;;
    build)     configure && build ;;
    test)      build && run_tests ;;
    install)   build && run_tests && install ;;
    full)      full_build ;;
    parallel)  parallel_build ;;
    *)         echo "Usage: $0 {clean|configure|build|test|install|full|parallel}" ;;
esac
```

### Interactive Pipeline Builder

```bash
#!/usr/bin/env psh
# Build custom pipelines interactively

# Pipeline components library
declare -A components=(
    ["filter"]="grep -v '^#' | grep -v '^$'"
    ["sort"]="sort"
    ["unique"]="sort | uniq"
    ["count"]="wc -l"
    ["columns"]="awk '{print \$1}'"
    ["lowercase"]="tr 'A-Z' 'a-z'"
    ["uppercase"]="tr 'a-z' 'A-Z'"
    ["numbers"]="grep -E '^[0-9]+$'"
    ["reverse"]="tac"
    ["sample"]="head -10"
)

# Build pipeline interactively
build_pipeline() {
    local pipeline=""
    local step=1
    
    echo "=== Interactive Pipeline Builder ==="
    echo "Available components:"
    for comp in "${!components[@]}"; do
        echo "  $comp - ${components[$comp]}"
    done
    echo
    
    while true; do
        echo -n "Step $step (enter component or 'done'): "
        read component
        
        [ "$component" = "done" ] && break
        
        if [ -n "${components[$component]}" ]; then
            if [ -n "$pipeline" ]; then
                pipeline="$pipeline | ${components[$component]}"
            else
                pipeline="${components[$component]}"
            fi
            echo "Pipeline so far: $pipeline"
            ((step++))
        else
            echo "Unknown component: $component"
        fi
    done
    
    echo
    echo "Final pipeline: $pipeline"
    echo -n "Test with file: "
    read testfile
    
    if [ -f "$testfile" ]; then
        echo "Results:"
        eval "cat '$testfile' | $pipeline"
    else
        echo "File not found"
    fi
}

# Pipeline templates
show_templates() {
    cat << 'TEMPLATES'
=== Common Pipeline Templates ===

1. Log Analysis:
   cat log | grep ERROR | awk '{print $1}' | sort | uniq -c | sort -rn

2. CSV Processing:
   cat data.csv | cut -d, -f2,4 | sort | uniq

3. Find Duplicates:
   cat file | sort | uniq -d

4. Word Frequency:
   cat text | tr -s ' ' '\n' | sort | uniq -c | sort -rn

5. Process Listing:
   ps aux | grep process | grep -v grep | awk '{print $2}'

6. Disk Usage:
   du -h | sort -hr | head -20

7. Network Connections:
   netstat -an | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c
TEMPLATES
}

# Main menu
while true; do
    echo
    echo "=== Pipeline Toolkit ==="
    echo "1) Build custom pipeline"
    echo "2) Show pipeline templates"
    echo "3) Exit"
    echo -n "Choice: "
    read choice
    
    case $choice in
        1) build_pipeline ;;
        2) show_templates ;;
        3) exit 0 ;;
        *) echo "Invalid choice" ;;
    esac
done
```

## Common Pipeline Patterns

### Error Handling in Pipelines

```bash
# Check pipeline success
if command1 | command2 | command3; then
    echo "Pipeline succeeded"
else
    echo "Pipeline failed"
fi

# Capture all exit codes (if supported)
command1 | command2 | command3
exit_codes=("${PIPESTATUS[@]}")  # Bash array

# Manual error checking
temp=$(mktemp)
if command1 > "$temp"; then
    if command2 < "$temp" > "$temp.2"; then
        command3 < "$temp.2"
    fi
fi
rm -f "$temp" "$temp.2"
```

### Performance Optimization

```bash
# Avoid useless use of cat
# Bad:
cat file | grep pattern

# Good:
grep pattern file

# Minimize pipeline stages
# Bad:
cat file | grep pattern | awk '{print $1}' | sort | uniq

# Good:
awk '/pattern/ {print $1}' file | sort -u

# Use appropriate tools
# Bad:
grep pattern file | wc -l

# Good:
grep -c pattern file
```

## Summary

Pipelines and command lists provide powerful ways to combine commands:

1. **Pipelines** (`|`) connect command output to input
2. **AND lists** (`&&`) run commands conditionally on success
3. **OR lists** (`||`) run commands conditionally on failure
4. **Command lists** (`;`) run commands sequentially
5. **Subshells** (`()`) provide environment isolation
6. **Command groups** (`{}`) group without subshells

Key concepts:
- Pipeline exit status is from the last command
- Data flows left to right through pipes
- && and || short-circuit evaluation
- Subshells isolate environment changes
- Command groups affect the current shell
- Always consider error handling in pipelines

Mastering pipelines enables you to build complex data processing workflows from simple commands. In the next chapter, we'll explore control structures for conditional execution and loops.

---

[← Previous: Chapter 9 - Input/Output Redirection](09_io_redirection.md) | [Next: Chapter 11 - Control Structures →](11_control_structures.md)