# PSH Here Document Processing Fix Plan

## Problem Analysis

PSH's here document processing is fundamentally broken due to an architectural mismatch:

1. **Current Flow**: Parser identifies `<<` tokens and delimiter → Creates Redirect AST node with `heredoc_content=None` → After parsing, `HeredocHandler.collect_heredocs()` calls `input()` to read content
2. **The Issue**: When running scripts, heredoc content is already in the buffered input text, not available via `input()` 
3. **Result**: PSH treats heredoc content lines as separate commands, causing "command not found" errors

## Root Cause

The `HeredocHandler._read_heredoc_content()` method uses `input()` which only works for interactive input, not script processing. The heredoc content needs to be collected during parsing from the input source, not after parsing from stdin.

## Solution Strategy

### Phase 1: Modify the Input Processing Pipeline
1. **Enhance SourceProcessor**: Update `execute_from_source()` to detect heredoc patterns in buffered commands
2. **Collect Heredoc Content**: When heredoc is detected, continue reading lines until delimiter is found
3. **Parse Complete Commands**: Only attempt parsing when all heredoc content is collected

### Phase 2: Update Parser Integration  
1. **Parser Enhancement**: Modify parser to accept heredoc content during parsing
2. **Immediate Content Assignment**: Set `heredoc_content` in Redirect nodes during parsing, not after
3. **Remove Post-Parse Collection**: Eliminate the problematic `collect_heredocs()` call

### Phase 3: Fix HeredocHandler
1. **Update Collection Logic**: Modify `HeredocHandler` to work with pre-collected content
2. **Variable Expansion**: Ensure expansion still works correctly for unquoted delimiters
3. **Tab Stripping**: Maintain `<<-` functionality

## Implementation Steps

### Step 1: Enhance SourceProcessor (source_processor.py)
```python
def _collect_heredoc_content(self, command_buffer: str, input_source) -> str:
    """Collect heredoc content from input source until all delimiters are satisfied."""
    # Use existing multiline_handler logic to detect unclosed heredocs
    # Read additional lines until all heredocs are closed
    # Return complete command with heredoc content
```

### Step 2: Create Heredoc-Aware Parser (parser.py) 
```python
def _parse_heredoc_with_content(self, token: Token, heredoc_content: str) -> Redirect:
    """Parse heredoc and immediately set content."""
    # Extract delimiter
    # Find matching content section in heredoc_content
    # Set heredoc_content field immediately
```

### Step 3: Update HeredocHandler (heredoc.py)
```python
def process_heredoc_content(self, redirect: Redirect) -> str:
    """Process already-collected heredoc content for execution."""
    # Apply variable expansion if delimiter unquoted
    # Handle tab stripping for <<-
    # Return processed content for file creation
```

### Step 4: Integration Points
- **Lexer**: No changes needed - already detects `<<` and `<<-` correctly
- **AST Nodes**: No changes needed - Redirect already has `heredoc_content` field  
- **IOManager**: Update to work with pre-populated heredoc content
- **Execution**: Ensure temporary file creation uses processed content

## Testing Strategy

1. **Verify Basic Heredocs**: `cat << EOF\nHello\nEOF`
2. **Test Variable Expansion**: `name=test; cat << EOF\n$name\nEOF`
3. **Test Tab Stripping**: `cat <<- EOF\n\tIndented\n\tEOF`
4. **Test Quoted Delimiters**: `cat << 'EOF'\n$var\nEOF`
5. **Test Complex Cases**: Heredocs in pipelines, functions, control structures
6. **Conformance Tests**: Ensure bash compatibility

## Risk Mitigation

- **Backward Compatibility**: Keep existing HeredocHandler interface for any code depending on it
- **Error Handling**: Ensure proper error messages for malformed heredocs
- **Performance**: Avoid unnecessary buffering for non-heredoc commands
- **Interactive Mode**: Ensure interactive heredoc input still works

This fix will resolve the critical POSIX compliance issue where PSH currently produces no heredoc output versus bash's correct heredoc processing.