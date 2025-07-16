"""Context snapshots for parser backtracking."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from .context import ParserContext


@dataclass
class ContextSnapshot:
    """Snapshot of parser context for backtracking.
    
    This class captures the essential state of a ParserContext that needs
    to be restored during backtracking operations.
    """
    
    # Core parsing position
    current: int
    
    # Context stacks
    scope_stack: List[str]
    parse_stack: List[str]
    
    # Depth counters
    nesting_depth: int
    loop_depth: int
    function_depth: int
    conditional_depth: int
    
    # Special parsing state
    in_case_pattern: bool
    in_arithmetic: bool
    in_test_expr: bool
    in_function_body: bool
    in_command_substitution: bool
    in_process_substitution: bool
    
    # Error state
    errors_count: int
    error_recovery_mode: bool
    
    # Heredoc state (keys only, since content shouldn't change during backtracking)
    open_heredocs: List[str]
    
    @classmethod
    def capture(cls, ctx: ParserContext) -> 'ContextSnapshot':
        """Capture current state of context."""
        return cls(
            current=ctx.current,
            scope_stack=ctx.scope_stack.copy(),
            parse_stack=ctx.parse_stack.copy(),
            nesting_depth=ctx.nesting_depth,
            loop_depth=ctx.loop_depth,
            function_depth=ctx.function_depth,
            conditional_depth=ctx.conditional_depth,
            in_case_pattern=ctx.in_case_pattern,
            in_arithmetic=ctx.in_arithmetic,
            in_test_expr=ctx.in_test_expr,
            in_function_body=ctx.in_function_body,
            in_command_substitution=ctx.in_command_substitution,
            in_process_substitution=ctx.in_process_substitution,
            errors_count=len(ctx.errors),
            error_recovery_mode=ctx.error_recovery_mode,
            open_heredocs=ctx.get_open_heredocs()
        )
    
    def restore(self, ctx: ParserContext):
        """Restore context to snapshot state."""
        # Record backtracking for profiling
        if ctx.profiler:
            ctx.profiler.record_backtrack()
        
        ctx.current = self.current
        ctx.scope_stack = self.scope_stack.copy()
        ctx.parse_stack = self.parse_stack.copy()
        ctx.nesting_depth = self.nesting_depth
        ctx.loop_depth = self.loop_depth
        ctx.function_depth = self.function_depth
        ctx.conditional_depth = self.conditional_depth
        ctx.in_case_pattern = self.in_case_pattern
        ctx.in_arithmetic = self.in_arithmetic
        ctx.in_test_expr = self.in_test_expr
        ctx.in_function_body = self.in_function_body
        ctx.in_command_substitution = self.in_command_substitution
        ctx.in_process_substitution = self.in_process_substitution
        ctx.error_recovery_mode = self.error_recovery_mode
        
        # Truncate errors to snapshot point
        ctx.errors = ctx.errors[:self.errors_count]
        
        # Note: We don't restore heredoc state since it represents
        # actual content that was parsed, not parsing position


class BacktrackingParser:
    """Mixin class that provides backtracking support via context snapshots."""
    
    def __init__(self, ctx: ParserContext):
        self.ctx = ctx
        self._snapshots: List[ContextSnapshot] = []
    
    def save_snapshot(self) -> int:
        """Save current context state and return snapshot ID."""
        snapshot = ContextSnapshot.capture(self.ctx)
        self._snapshots.append(snapshot)
        return len(self._snapshots) - 1
    
    def restore_snapshot(self, snapshot_id: int):
        """Restore context to saved snapshot."""
        if 0 <= snapshot_id < len(self._snapshots):
            snapshot = self._snapshots[snapshot_id]
            snapshot.restore(self.ctx)
            
            # Remove snapshots newer than the one we're restoring to
            self._snapshots = self._snapshots[:snapshot_id + 1]
    
    def discard_snapshot(self, snapshot_id: int):
        """Discard a saved snapshot."""
        if 0 <= snapshot_id < len(self._snapshots):
            # Remove this snapshot and all newer ones
            self._snapshots = self._snapshots[:snapshot_id]
    
    def try_parse(self, parse_func, *args, **kwargs):
        """Try parsing with automatic backtracking on failure.
        
        Args:
            parse_func: Function to attempt parsing
            *args, **kwargs: Arguments to pass to parse_func
            
        Returns:
            Result of parse_func if successful, None if failed
        """
        snapshot_id = self.save_snapshot()
        try:
            result = parse_func(*args, **kwargs)
            # Success - discard snapshot
            self.discard_snapshot(snapshot_id)
            return result
        except Exception:
            # Failure - restore to snapshot
            self.restore_snapshot(snapshot_id)
            return None
    
    def try_alternatives(self, *parse_funcs):
        """Try multiple parsing alternatives, returning first successful result.
        
        Args:
            *parse_funcs: List of (func, args, kwargs) tuples or just functions
            
        Returns:
            Result of first successful parse function, or None if all fail
        """
        for parse_item in parse_funcs:
            if callable(parse_item):
                # Just a function
                result = self.try_parse(parse_item)
            elif isinstance(parse_item, tuple):
                if len(parse_item) == 1:
                    # (func,)
                    result = self.try_parse(parse_item[0])
                elif len(parse_item) == 2:
                    # (func, args)
                    result = self.try_parse(parse_item[0], *parse_item[1])
                elif len(parse_item) == 3:
                    # (func, args, kwargs)
                    result = self.try_parse(parse_item[0], *parse_item[1], **parse_item[2])
                else:
                    continue
            else:
                continue
            
            if result is not None:
                return result
        
        return None
    
    def lookahead(self, parse_func, *args, **kwargs) -> bool:
        """Check if parsing would succeed without advancing position.
        
        Args:
            parse_func: Function to test
            *args, **kwargs: Arguments to pass to parse_func
            
        Returns:
            True if parsing would succeed, False otherwise
        """
        result = self.try_parse(parse_func, *args, **kwargs)
        return result is not None


class SpeculativeParser(BacktrackingParser):
    """Parser that supports speculative parsing with multiple strategies."""
    
    def __init__(self, ctx: ParserContext):
        super().__init__(ctx)
        self._speculation_depth = 0
    
    def enter_speculation(self) -> int:
        """Enter speculative parsing mode."""
        self._speculation_depth += 1
        return self.save_snapshot()
    
    def exit_speculation(self, snapshot_id: int, commit: bool = True):
        """Exit speculative parsing mode.
        
        Args:
            snapshot_id: Snapshot ID from enter_speculation
            commit: If True, keep changes. If False, restore to snapshot.
        """
        self._speculation_depth = max(0, self._speculation_depth - 1)
        
        if commit:
            self.discard_snapshot(snapshot_id)
        else:
            self.restore_snapshot(snapshot_id)
    
    def speculate(self, parse_func, *args, **kwargs):
        """Speculative parsing with explicit commit/rollback control.
        
        Returns a context manager that handles speculation.
        """
        return SpeculationContext(self, parse_func, *args, **kwargs)
    
    def in_speculation(self) -> bool:
        """Check if currently in speculation mode."""
        return self._speculation_depth > 0


class SpeculationContext:
    """Context manager for speculative parsing."""
    
    def __init__(self, parser: SpeculativeParser, parse_func, *args, **kwargs):
        self.parser = parser
        self.parse_func = parse_func
        self.args = args
        self.kwargs = kwargs
        self.snapshot_id = None
        self.result = None
        self.exception = None
    
    def __enter__(self):
        self.snapshot_id = self.parser.enter_speculation()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Determine if we should commit based on whether an exception occurred
        commit = exc_type is None
        self.parser.exit_speculation(self.snapshot_id, commit)
        
        # Don't suppress exceptions
        return False
    
    def execute(self):
        """Execute the speculative parse function."""
        try:
            self.result = self.parse_func(*self.args, **self.kwargs)
            return self.result
        except Exception as e:
            self.exception = e
            raise
    
    def commit(self):
        """Explicitly commit the speculation."""
        if self.snapshot_id is not None:
            self.parser.discard_snapshot(self.snapshot_id)
            self.snapshot_id = None
    
    def rollback(self):
        """Explicitly rollback the speculation."""
        if self.snapshot_id is not None:
            self.parser.restore_snapshot(self.snapshot_id)
            self.snapshot_id = None


# Convenience functions for common backtracking patterns

def with_backtracking(ctx: ParserContext):
    """Decorator to add backtracking support to a parser class."""
    def decorator(parser_class):
        class BacktrackingParserClass(parser_class, BacktrackingParser):
            def __init__(self, *args, **kwargs):
                parser_class.__init__(self, *args, **kwargs)
                BacktrackingParser.__init__(self, ctx)
        
        return BacktrackingParserClass
    return decorator


def try_parse_alternatives(ctx: ParserContext, alternatives: List):
    """Try multiple parsing alternatives using a temporary backtracking parser.
    
    Args:
        ctx: Parser context
        alternatives: List of parsing functions to try
        
    Returns:
        Result of first successful alternative, or None
    """
    parser = BacktrackingParser(ctx)
    return parser.try_alternatives(*alternatives)