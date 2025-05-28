#!/usr/bin/env python3
"""Exception classes for Python Shell (psh)."""


class FunctionReturn(Exception):
    """Exception used to implement return from functions."""
    def __init__(self, exit_code):
        self.exit_code = exit_code
        super().__init__()


class LoopBreak(Exception):
    """Exception used to implement break statement."""
    pass


class LoopContinue(Exception):
    """Exception used to implement continue statement."""
    pass