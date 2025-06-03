"""Prompt formatting and management."""
import os
import sys
from datetime import datetime
from .base import InteractiveComponent
from ..prompt import PromptExpander


class PromptManager(InteractiveComponent):
    """Manages shell prompts (PS1, PS2)."""
    
    def __init__(self, shell):
        super().__init__(shell)
        self.prompt_expander = PromptExpander(shell)
    
    def execute(self, prompt_type: str = "PS1") -> str:
        """Get formatted prompt."""
        if prompt_type == "PS1":
            return self.get_primary_prompt()
        elif prompt_type == "PS2":
            return self.get_continuation_prompt()
        return ""
    
    def get_primary_prompt(self) -> str:
        """Get the primary prompt (PS1)."""
        ps1 = self.state.variables.get('PS1', r'\u@\h:\w\$ ')
        return self.expand_prompt(ps1)
    
    def get_continuation_prompt(self) -> str:
        """Get the continuation prompt (PS2)."""
        ps2 = self.state.variables.get('PS2', '> ')
        return self.expand_prompt(ps2)
    
    def expand_prompt(self, prompt_string: str) -> str:
        """Expand prompt escape sequences."""
        # Use the existing prompt expansion function
        return self.prompt_expander.expand_prompt(prompt_string)
    
    def set_prompt(self, prompt_type: str, value: str) -> None:
        """Set a prompt value."""
        if prompt_type in ("PS1", "PS2"):
            self.state.variables[prompt_type] = value