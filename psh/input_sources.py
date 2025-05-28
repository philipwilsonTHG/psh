"""Input source abstraction for psh.

This module provides different input sources for the shell:
- FileInput: Read commands from script files
- StringInput: Read commands from strings (for -c option)
- InteractiveInput: Read commands interactively (for REPL)
"""

from abc import ABC, abstractmethod
from typing import Optional


class InputSource(ABC):
    """Abstract base class for shell input sources."""
    
    @abstractmethod
    def read_line(self) -> Optional[str]:
        """Read the next line from the input source.
        
        Returns:
            The next line as a string, or None on EOF.
        """
        pass
    
    @abstractmethod
    def is_interactive(self) -> bool:
        """Return True if this is an interactive input source."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this input source for error messages."""
        pass


class FileInput(InputSource):
    """Input source for reading commands from script files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file = None
        self.line_number = 0
    
    def __enter__(self):
        self.file = open(self.file_path, 'r', encoding='utf-8')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
    
    def read_line(self) -> Optional[str]:
        """Read the next line from the file."""
        if self.file:
            line = self.file.readline()
            if line:
                self.line_number += 1
                return line.rstrip('\n\r')
        return None
    
    def is_interactive(self) -> bool:
        return False
    
    def get_name(self) -> str:
        return self.file_path


class StringInput(InputSource):
    """Input source for reading commands from a string."""
    
    def __init__(self, command: str, name: str = "<command>"):
        self.lines = command.split('\n')
        self.current = 0
        self.name = name
    
    def read_line(self) -> Optional[str]:
        """Read the next line from the string."""
        if self.current < len(self.lines):
            line = self.lines[self.current]
            self.current += 1
            return line
        return None
    
    def is_interactive(self) -> bool:
        return False
    
    def get_name(self) -> str:
        return self.name


class InteractiveInput(InputSource):
    """Input source for interactive shell sessions."""
    
    def __init__(self, line_editor, prompt_func):
        self.line_editor = line_editor
        self.prompt_func = prompt_func
    
    def read_line(self) -> Optional[str]:
        """Read the next line interactively."""
        try:
            prompt = self.prompt_func()
            return self.line_editor.read_line(prompt)
        except (EOFError, KeyboardInterrupt):
            return None
    
    def is_interactive(self) -> bool:
        return True
    
    def get_name(self) -> str:
        return "<stdin>"