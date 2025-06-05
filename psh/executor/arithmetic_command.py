"""Arithmetic command execution."""
import sys
from ..ast_nodes import ArithmeticCommand
from .base import ExecutorComponent
from ..arithmetic import evaluate_arithmetic, ArithmeticError

class ArithmeticCommandExecutor(ExecutorComponent):
    """Executes arithmetic commands ((expression))."""
    
    def execute(self, command: ArithmeticCommand) -> int:
        """Execute arithmetic command and return exit status."""
        try:
            # Evaluate the expression with shell context
            result = evaluate_arithmetic(command.expression, self.shell)
            
            # Return 0 if result is non-zero, 1 if zero
            exit_code = 0 if result != 0 else 1
            return exit_code
            
        except ArithmeticError as e:
            # Print error to stderr
            print(f"psh: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            # Print generic error to stderr
            print(f"psh: arithmetic error: {e}", file=sys.stderr)
            return 1