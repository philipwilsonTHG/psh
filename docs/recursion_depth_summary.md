# Deep Recursion Limitation - Summary

## The Issue

PSH has a significant limitation with recursive shell functions due to Python stack frame overhead. Even simple recursive functions like `factorial(5)` can fail despite Python's default recursion limit of 1000.

## Root Cause

Each level of shell recursion in psh creates approximately **40-50 Python function calls** due to the layered architecture:

1. **Command Substitution `$(...)`**:
   - Creates a new subshell
   - Tokenization → Parsing → AST building → Execution
   - Each layer adds multiple function calls

2. **Arithmetic Expansion `$((...))` **:
   - Has its own tokenizer, parser, and evaluator
   - Adds additional stack frames

3. **Compound Effect**:
   ```bash
   local result=$(factorial $((n - 1)))  # Two nested expansions!
   ```

## Practical Impact

- With Python's default limit of 1000:
  - Simple recursion works up to ~20 levels
  - With arithmetic expansion: ~15-20 levels
  - With complex expressions: even less

- Real-world example:
  - `factorial(2)` fails with recursion limit of 40
  - `factorial(5)` needs recursion limit of ~250
  - `factorial(10)` needs recursion limit of ~500

## Architectural Trade-off

This is a deliberate architectural choice, not a bug:

**Benefits** (Educational Value):
- Clear separation of concerns
- Easy to understand code flow
- Each component is well-defined
- Great for learning how shells work

**Drawbacks**:
- Deep Python call stacks
- Limited recursion depth
- Performance overhead

## Workarounds

1. **Use Iterative Algorithms** (Recommended):
   ```bash
   factorial() {
       local n=$1
       local result=1
       local i=1
       while [ "$i" -le "$n" ]; do
           result=$((result * i))
           i=$((i + 1))
       done
       echo $result
   }
   ```

2. **Increase Python Recursion Limit**:
   ```bash
   python -c "import sys; sys.setrecursionlimit(5000); exec(open('script.psh').read())"
   ```

3. **Minimize Nested Expansions**:
   ```bash
   # Instead of: result=$(factorial $((n - 1)))
   # Use:
   local prev=$((n - 1))
   local result=$(factorial $prev)
   ```

## Comparison with Other Shells

- **Bash/Zsh**: Use optimized C code with minimal function overhead
- **Fish**: Written in C++, similar optimization
- **PSH**: Python-based, educational focus over performance

## Future Possibilities

Potential optimizations (would require significant refactoring):
- Cache parsed ASTs
- Optimize simple command substitutions
- Implement tail-call optimization
- Reduce intermediate function calls

However, these would compromise the educational clarity that is psh's primary goal.