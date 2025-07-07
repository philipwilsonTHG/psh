"""State transition framework for the lexer state machine."""

from typing import Callable, Dict, List, Optional, Tuple, Any
from .position import LexerState
from .state_context import LexerContext


class StateTransition:
    """Represents a state machine transition."""
    
    def __init__(
        self,
        from_state: LexerState,
        condition: Callable[[LexerContext, str, int], bool],
        to_state: LexerState,
        action: Optional[Callable[[LexerContext, str, int], None]] = None,
        priority: int = 0
    ):
        """
        Initialize a state transition.
        
        Args:
            from_state: State this transition applies from
            condition: Function to check if transition should occur
            to_state: Target state
            action: Optional action to perform during transition
            priority: Transition priority (higher = checked first)
        """
        self.from_state = from_state
        self.condition = condition
        self.to_state = to_state
        self.action = action
        self.priority = priority
    
    def can_apply(self, context: LexerContext, current_char: str, position: int) -> bool:
        """Check if this transition can be applied."""
        return (context.state == self.from_state and 
                self.condition(context, current_char, position))
    
    def apply(self, context: LexerContext, current_char: str, position: int) -> None:
        """Apply the transition."""
        # Perform any action
        if self.action:
            self.action(context, current_char, position)
        
        # Change state
        context.state = self.to_state
    
    def __str__(self) -> str:
        return f"Transition({self.from_state.name} -> {self.to_state.name}, priority={self.priority})"


class TransitionTable:
    """Manages state transitions for the lexer."""
    
    def __init__(self):
        self.transitions: Dict[LexerState, List[StateTransition]] = {}
        self._default_transitions_added = False
    
    def add_transition(self, transition: StateTransition) -> None:
        """Register a state transition."""
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        
        # Insert in priority order (highest first)
        transitions = self.transitions[transition.from_state]
        inserted = False
        for i, existing in enumerate(transitions):
            if transition.priority > existing.priority:
                transitions.insert(i, transition)
                inserted = True
                break
        
        if not inserted:
            transitions.append(transition)
    
    def get_applicable_transition(
        self,
        context: LexerContext,
        current_char: str,
        position: int
    ) -> Optional[StateTransition]:
        """Find the first applicable transition for current state and input."""
        if context.state not in self.transitions:
            return None
        
        for transition in self.transitions[context.state]:
            if transition.can_apply(context, current_char, position):
                return transition
        
        return None
    
    def apply_transition(
        self,
        transition: StateTransition,
        context: LexerContext,
        current_char: str,
        position: int
    ) -> None:
        """Apply a transition to the context."""
        transition.apply(context, current_char, position)
    
    def get_transitions_from_state(self, state: LexerState) -> List[StateTransition]:
        """Get all transitions from a given state."""
        return self.transitions.get(state, []).copy()
    
    def setup_default_transitions(self) -> None:
        """Set up the default lexer state transitions."""
        if self._default_transitions_added:
            return
        
        # Transitions from NORMAL state
        self._add_normal_state_transitions()
        
        # Transitions from quote states
        self._add_quote_state_transitions()
        
        # Transitions from variable states
        self._add_variable_state_transitions()
        
        # Transitions from expansion states
        self._add_expansion_state_transitions()
        
        # Transitions from other states
        self._add_misc_state_transitions()
        
        self._default_transitions_added = True
    
    def _add_normal_state_transitions(self) -> None:
        """Add transitions from NORMAL state."""
        
        # To double quote
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == '"',
            to_state=LexerState.IN_DOUBLE_QUOTE,
            action=lambda ctx, char, pos: ctx.push_quote('"'),
            priority=100
        ))
        
        # To single quote
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == "'",
            to_state=LexerState.IN_SINGLE_QUOTE,
            action=lambda ctx, char, pos: ctx.push_quote("'"),
            priority=100
        ))
        
        # To backtick
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == '`',
            to_state=LexerState.IN_BACKTICK,
            action=lambda ctx, char, pos: ctx.push_quote('`'),
            priority=100
        ))
        
        # To comment
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=self._is_comment_start,
            to_state=LexerState.IN_COMMENT,
            priority=90
        ))
        
        # To variable (simple)
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == '$',
            to_state=LexerState.IN_VARIABLE,
            priority=80
        ))
        
        # To word
        self.add_transition(StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: not char.isspace() and char not in '"\'`#$',
            to_state=LexerState.IN_WORD,
            priority=10
        ))
    
    def _add_quote_state_transitions(self) -> None:
        """Add transitions from quote states."""
        
        # Exit double quote
        self.add_transition(StateTransition(
            from_state=LexerState.IN_DOUBLE_QUOTE,
            condition=lambda ctx, char, pos: char == '"' and ctx.current_quote_type() == '"',
            to_state=LexerState.NORMAL,
            action=lambda ctx, char, pos: ctx.pop_quote(),
            priority=100
        ))
        
        # Exit single quote
        self.add_transition(StateTransition(
            from_state=LexerState.IN_SINGLE_QUOTE,
            condition=lambda ctx, char, pos: char == "'" and ctx.current_quote_type() == "'",
            to_state=LexerState.NORMAL,
            action=lambda ctx, char, pos: ctx.pop_quote(),
            priority=100
        ))
        
        # Exit backtick
        self.add_transition(StateTransition(
            from_state=LexerState.IN_BACKTICK,
            condition=lambda ctx, char, pos: char == '`' and ctx.current_quote_type() == '`',
            to_state=LexerState.NORMAL,
            action=lambda ctx, char, pos: ctx.pop_quote(),
            priority=100
        ))
    
    def _add_variable_state_transitions(self) -> None:
        """Add transitions from variable states."""
        
        # Exit variable state when word terminators are encountered
        def is_variable_terminator(ctx: LexerContext, char: str, pos: int) -> bool:
            return char in ' \t\n|&;<>(){}[]"\''
        
        self.add_transition(StateTransition(
            from_state=LexerState.IN_VARIABLE,
            condition=is_variable_terminator,
            to_state=LexerState.NORMAL,
            priority=100
        ))
        
        # Exit brace variable when } is encountered
        self.add_transition(StateTransition(
            from_state=LexerState.IN_BRACE_VAR,
            condition=lambda ctx, char, pos: char == '}',
            to_state=LexerState.NORMAL,
            action=lambda ctx, char, pos: ctx.exit_brace_expansion(),
            priority=100
        ))
    
    def _add_expansion_state_transitions(self) -> None:
        """Add transitions from expansion states."""
        
        # Command substitution and arithmetic handled by balanced paren reading
        # These are more complex and handled in the state handlers
        pass
    
    def _add_misc_state_transitions(self) -> None:
        """Add transitions from miscellaneous states."""
        
        # Exit comment at newline
        self.add_transition(StateTransition(
            from_state=LexerState.IN_COMMENT,
            condition=lambda ctx, char, pos: char == '\n',
            to_state=LexerState.NORMAL,
            priority=100
        ))
        
        # Exit word state at word terminators
        def is_word_terminator(ctx: LexerContext, char: str, pos: int) -> bool:
            return char in ' \t\n|&;<>(){}"\''
        
        self.add_transition(StateTransition(
            from_state=LexerState.IN_WORD,
            condition=is_word_terminator,
            to_state=LexerState.NORMAL,
            priority=100
        ))
    
    def _is_comment_start(self, context: LexerContext, char: str, position: int) -> bool:
        """Check if # at current position starts a comment."""
        if char != '#':
            return False
        
        # Comments start at beginning of input or after whitespace/operators
        if position == 0:
            return True
        
        # This would need access to the input string - will be handled in lexer
        return False


class StateManager:
    """High-level state management for the lexer."""
    
    def __init__(self):
        self.context = LexerContext()
        self.transition_table = TransitionTable()
        self.transition_table.setup_default_transitions()
        self._state_history: List[Tuple[LexerState, int]] = []
    
    def reset(self) -> None:
        """Reset to initial state."""
        self.context = LexerContext()
        self._state_history.clear()
    
    def try_transition(
        self,
        current_char: str,
        position: int,
        input_text: str
    ) -> bool:
        """
        Try to apply a state transition.
        
        Returns:
            True if a transition was applied, False otherwise
        """
        # Record current state
        self._state_history.append((self.context.state, position))
        
        # Check for applicable transition
        transition = self.transition_table.get_applicable_transition(
            self.context, current_char, position
        )
        
        if transition:
            # Apply the transition
            self.transition_table.apply_transition(
                transition, self.context, current_char, position
            )
            return True
        
        return False
    
    def get_state_history(self) -> List[Tuple[LexerState, int]]:
        """Get the history of state changes."""
        return self._state_history.copy()
    
    def get_current_state(self) -> LexerState:
        """Get the current lexer state."""
        return self.context.state
    
    def get_context(self) -> LexerContext:
        """Get the current lexer context."""
        return self.context