"""Core exceptions for shell execution flow control."""

class LoopBreak(Exception):
    """Exception used to implement break statement."""
    def __init__(self, level=1):
        self.level = level
        super().__init__()

class LoopContinue(Exception):
    """Exception used to implement continue statement."""
    def __init__(self, level=1):
        self.level = level
        super().__init__()