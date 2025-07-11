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

class UnboundVariableError(Exception):
    """Raised when accessing unset variable with nounset option."""
    pass

class ReadonlyVariableError(Exception):
    """Raised when attempting to modify a readonly variable."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"readonly variable: {name}")

class ExpansionError(Exception):
    """Raised when parameter expansion fails (e.g., :? operator)."""
    pass