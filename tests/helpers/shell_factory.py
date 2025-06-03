"""Factory functions for creating test shells."""
from psh.shell import Shell

def create_test_shell(**kwargs):
    """Factory function to create shells for testing.
    
    This allows us to easily update test shell creation later
    as we refactor the Shell class.
    """
    return Shell(**kwargs)