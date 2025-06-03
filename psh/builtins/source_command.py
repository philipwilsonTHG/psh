"""Source command builtin."""
import os
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class SourceBuiltin(Builtin):
    """Execute commands from a file in the current shell."""
    
    @property
    def name(self) -> str:
        return "source"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the source builtin."""
        if len(args) < 2:
            print("source: filename argument required", file=sys.stderr)
            return 1
        
        filename = args[1]
        source_args = args[2:] if len(args) > 2 else []
        
        # Find the script file
        script_path = self._find_source_file(filename, shell)
        if script_path is None:
            print(f"source: {filename}: No such file or directory", file=sys.stderr)
            return 1
        
        # Validate the script file
        validation_result = shell.script_manager.script_validator.validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Save current shell state
        old_positional = shell.positional_params.copy()
        old_script_name = shell.script_name
        old_script_mode = shell.is_script_mode
        
        # Set new state for sourced script
        shell.positional_params = source_args
        shell.script_name = script_path
        # Keep current script mode (sourcing inherits mode)
        
        try:
            from ..input_sources import FileInput
            with FileInput(script_path) as input_source:
                # Execute with no history since it's sourced
                return shell.script_manager.source_processor.execute_from_source(input_source, add_to_history=False)
        except Exception as e:
            print(f"source: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            # Restore previous state
            shell.positional_params = old_positional
            shell.script_name = old_script_name
            shell.is_script_mode = old_script_mode
    
    def _find_source_file(self, filename: str, shell: 'Shell') -> str:
        """Find a source file, searching PATH if needed."""
        # If filename contains a slash, don't search PATH
        if '/' in filename:
            if os.path.exists(filename):
                return filename
            return None
        
        # First check current directory
        if os.path.exists(filename):
            return filename
        
        # Search in PATH
        path_dirs = shell.env.get('PATH', '').split(':')
        for path_dir in path_dirs:
            if path_dir:  # Skip empty path components
                full_path = os.path.join(path_dir, filename)
                if os.path.exists(full_path):
                    return full_path
        
        return None


@builtin
class DotBuiltin(SourceBuiltin):
    """Dot command (alias for source)."""
    
    @property
    def name(self) -> str:
        return "."