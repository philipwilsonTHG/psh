# Control Structures and Pipeline Limitations in PSH

**Last Updated**: 2025-01-09 (v0.37.1)

## Overview

PSH v0.37.0 introduced the ability to use control structures as pipeline components, but with some limitations. This document details what works, what doesn't, and provides workarounds.

## What Works ✅

### 1. Control Structures as Pipeline Receivers

The main feature of v0.37.0 allows control structures to receive piped input:

```bash
# While loops
echo -e "apple\nbanana\ncherry" | while read fruit; do
    echo "Processing: $fruit"
done

# For loops
seq 1 5 | for i in $(cat); do
    echo "Number: $i"
done

# If statements
echo "test" | if grep -q "test"; then
    echo "Found match"
fi

# Case statements
echo "apple" | case $(cat) in
    apple) echo "It's an apple!" ;;
    *) echo "Unknown fruit" ;;
esac

# Select statements (interactive)
echo -e "option1\noption2" | select choice in $(cat); do
    echo "Selected: $choice"
    break
done
```

### 2. Multi-line Control Structures

Multi-line control structures work correctly in most contexts:

- ✅ Interactive prompt
- ✅ Script files
- ✅ With `psh -c` command
- ✅ As pipeline receivers

### 3. Nested Control Structures

Simple nesting works fine:

```bash
for i in 1 2; do
    if [ "$i" -eq 1 ]; then
        echo "First"
    else
        echo "Second"
    fi
done
```

## What Doesn't Work ❌

### 1. Control Structures as Pipeline Sources

Control structures cannot pipe their output to other commands:

```bash
# This fails at interactive prompt:
for i in {1..6}; do
    echo $i
done | wc -l
# Error: Parse error at position 37: Expected command

# Also fails:
while read line; do
    echo "Line: $line"
done < file.txt | grep "pattern"
```

### 2. C-Style For Loops in Pipelines

C-style for loops cannot be used in pipelines at all:

```bash
# This fails:
echo "test" | for ((i=0; i<3; i++)); do
    echo $i
done
# Error: Parse error at position 36-37
```

### 3. Subshells and Command Groups

Parentheses `()` and braces `{}` are not recognized as pipeline components:

```bash
# These fail:
(echo "test") | cat
{ echo "test"; } | cat
```

### 4. Complex Multi-stage Pipelines

Control structures in the middle of pipelines don't work:

```bash
# This fails:
cat file | while read x; do echo $x; done | sort
```

## Workarounds 💡

### 1. Command Substitution

Use command substitution to capture output:

```bash
# Instead of: for i in {1..6}; do echo $i; done | wc -l
echo "$(for i in {1..6}; do echo $i; done)" | wc -l

# Or without the echo:
wc -l <<< "$(for i in {1..6}; do echo $i; done)"
```

### 2. Functions

Wrap control structures in functions:

```bash
count_items() {
    for i in {1..6}; do
        echo $i
    done
}
count_items | wc -l
```

### 3. Alternative Approaches

For specific cases, use simpler alternatives:

```bash
# Instead of: for i in {1..6}; do echo $i; done | wc -l
seq 1 6 | wc -l

# Instead of: for f in *.txt; do cat "$f"; done | grep pattern
cat *.txt | grep pattern
```

### 4. Temporary Files

For complex pipelines:

```bash
# Create temp file
for i in {1..6}; do
    echo $i
done > /tmp/output.txt
wc -l < /tmp/output.txt
rm /tmp/output.txt
```

### 5. Script Files

For complex multi-line pipelines, use a script:

```bash
#!/usr/bin/env psh
# script.sh
for i in {1..6}; do
    echo $i
done | wc -l
```

## Technical Details

### Parser Limitations

1. The parser expects `done`, `fi`, `esac` to end their respective control structures
2. When a pipe `|` follows these keywords, the parser cannot handle it
3. Control structures are implemented as `CompoundCommand` objects that can be pipeline components when receiving input, but not when producing output

### AST Structure

- v0.37.0 created a unified command model with:
  - `Command` base class
  - `SimpleCommand` for regular commands
  - `CompoundCommand` for control structures
- The parser's `parse_pipeline_component()` can parse control structures
- But `parse_pipeline()` doesn't handle control structures followed by pipes

## Future Improvements

To fully support control structures in pipelines, the parser would need:

1. Recognition of control structures as complete units that can be followed by pipes
2. Support for subshells `()` and command groups `{}` as pipeline components
3. Enhanced pipeline parsing to handle complex multi-stage pipelines

## Summary

PSH v0.37.0's control structures in pipelines feature is a significant improvement, allowing control structures to process piped input. However, they cannot yet pipe their output to other commands, which requires using workarounds like command substitution or functions.

The limitation primarily affects interactive use cases where you want to pipe the output of loops or conditionals. Script files can work around this more easily using functions or alternative approaches.