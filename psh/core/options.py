"""Shell option handlers."""

from typing import TYPE_CHECKING
from .exceptions import UnboundVariableError

if TYPE_CHECKING:
    from .state import ShellState


class OptionHandler:
    """Handle shell option behaviors."""
    
    @staticmethod
    def should_exit_on_error(state: 'ShellState', in_conditional: bool = False, 
                           in_pipeline: bool = False, is_negated: bool = False) -> bool:
        """
        Check if shell should exit on command failure.
        
        Args:
            state: Shell state
            in_conditional: True if command is in if/while/&&/|| context  
            in_pipeline: True if command is part of a pipeline (not the last)
            is_negated: True if command is negated with !
            
        Returns:
            True if shell should exit due to errexit
        """
        if not state.options.get('errexit', False):
            return False
        
        # Don't exit in conditional contexts
        if in_conditional:
            return False
        
        # Don't exit for negated commands
        if is_negated:
            return False
            
        # Don't exit for non-final pipeline commands (unless pipefail is set)
        if in_pipeline and not state.options.get('pipefail', False):
            return False
            
        # Don't exit if in a function and a return statement was used
        # (This is handled by the LoopReturn exception mechanism)
        
        return True
    
    @staticmethod
    def check_unset_variable(state: 'ShellState', var_name: str, 
                           in_expansion: bool = False) -> None:
        """
        Check if accessing unset variable should cause error.
        
        Args:
            state: Shell state
            var_name: Variable name being accessed
            in_expansion: True if in parameter expansion context like ${var:-default}
            
        Raises:
            UnboundVariableError: If variable is unset and nounset is enabled
        """
        if not state.options.get('nounset', False):
            return
            
        # Special handling for parameter expansions that provide defaults
        if in_expansion:
            return
            
        # Special handling for $@ and $* when no positional params
        if var_name in ['@', '*'] and not state.positional_params:
            # Bash allows these even with nounset
            return
            
        # Special variables that always have a value
        if var_name in ['?', '$', '#', '0']:
            return
            
        # Positional parameters
        if var_name.isdigit():
            index = int(var_name)
            if index > len(state.positional_params):
                raise UnboundVariableError(f"${var_name}: unbound variable")
            return
            
        # Check if variable exists in shell variables or environment
        # We need to check explicitly because get_variable returns a default
        if (state.scope_manager.get_variable(var_name) is None and 
            var_name not in state.env):
            raise UnboundVariableError(f"{var_name}: unbound variable")
    
    @staticmethod
    def print_xtrace(state: 'ShellState', command_parts: list) -> None:
        """
        Print xtrace output for a command.
        
        Args:
            state: Shell state
            command_parts: List of command parts (already expanded)
        """
        if not state.options.get('xtrace', False):
            return
            
        ps4 = state.get_variable('PS4', '+ ')
        trace_line = ps4 + ' '.join(str(part) for part in command_parts)
        print(trace_line, file=state.stderr)
        state.stderr.flush()  # Ensure trace appears before command output
    
    @staticmethod
    def get_pipeline_exit_code(state: 'ShellState', exit_codes: list) -> int:
        """
        Get the exit code for a pipeline based on pipefail option.
        
        Args:
            state: Shell state
            exit_codes: List of exit codes from pipeline commands
            
        Returns:
            Exit code for the pipeline
        """
        if not exit_codes:
            return 0
            
        if state.options.get('pipefail', False):
            # Return rightmost non-zero exit status, or 0 if all succeeded
            for code in reversed(exit_codes):
                if code != 0:
                    return code
            return 0
        else:
            # Default: return status of last command
            return exit_codes[-1]