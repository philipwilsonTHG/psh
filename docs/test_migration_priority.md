# Test Migration Priority List

Based on the test analysis, here's the prioritized migration plan:

## Immediate Priority (Core Components)

### 1. Expansion Tests (High Priority)
- **Why**: Core functionality used everywhere
- **Current**: 64 test files reference expansion
- **Target**: Create comprehensive unit tests in `tests_new/unit/expansion/`
- **Components**:
  - Variable expansion (`$var`, `${var}`)
  - Command substitution (`$(cmd)`, backticks)
  - Arithmetic expansion (`$((expr))`)
  - Brace expansion (`{a,b,c}`)
  - Tilde expansion (`~`, `~user`)
  - Parameter expansion (`${var:-default}`, etc.)
  - Glob expansion (`*.txt`, `[abc]`, `?`)

### 2. Builtin Tests (High Priority)
- **Why**: 56 test files reference builtins
- **Current**: Mixed with other tests
- **Target**: Create focused tests in `tests_new/unit/builtins/`
- **Key builtins to test**:
  - cd, pwd, echo, printf
  - export, unset, readonly
  - source, eval
  - test, [, [[
  - read, getopts
  - trap, wait, jobs, fg, bg
  - break, continue, return, exit

### 3. Control Flow Integration Tests (Medium Priority)
- **Why**: 110 test files reference control flow
- **Current**: Mixed unit/integration tests
- **Target**: `tests_new/integration/control_flow/`
- **Structures**:
  - if/then/else/elif/fi
  - while/do/done
  - for/do/done (both styles)
  - case/esac
  - Nested structures
  - Control flow in functions

## Secondary Priority

### 4. Pipeline Integration Tests
- **Why**: 48 test files reference pipelines
- **Target**: `tests_new/integration/pipeline/`
- **Focus**: Complex pipeline scenarios

### 5. IO Redirection Integration Tests
- **Why**: 53 test files reference redirections
- **Target**: `tests_new/integration/redirection/`
- **Focus**: Complex redirection combinations

### 6. Process Management Tests
- **Why**: 65 test files reference process handling
- **Target**: `tests_new/system/process/`
- **Focus**: Subprocess creation, signals, exit codes

## Already Migrated/Created

✅ Lexer unit tests (3 files)
✅ Parser unit tests (2 files)
✅ Interactive system tests (6 files)
✅ Basic conformance tests (1 file)
✅ Performance benchmarks (1 file)

## Migration Strategy

1. **Start with pure unit tests** - Easy to migrate, high value
2. **Focus on one component at a time** - Complete coverage before moving on
3. **Use existing tests as reference** - But improve organization and clarity
4. **Add missing test cases** - Fill gaps found during migration
5. **Document expected behavior** - Make tests educational

## Test Count Goals

Based on analysis:
- Total legacy tests: 1,818
- Current new tests: 172
- Target: Achieve 80% coverage with ~1,000 well-organized tests

## Next Steps

1. Create `tests_new/unit/expansion/` directory structure
2. Migrate variable expansion tests first (most fundamental)
3. Add comprehensive test cases for all expansion types
4. Move to builtins after expansion is complete