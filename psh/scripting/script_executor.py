"""Script file execution."""
import os
from typing import List, Optional
from .base import ScriptComponent
from ..input_sources import FileInput


class ScriptExecutor(ScriptComponent):
    """Executes script files."""
    
    def execute(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file."""
        return self.run_script(script_path, script_args)
    
    def run_script(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file with optional arguments."""
        if script_args is None:
            script_args = []
            
        # Validate the script file first
        validation_result = self.shell.script_manager.script_validator.validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Check for shebang and execute with appropriate interpreter
        if self.shell.script_manager.shebang_handler.should_execute_with_shebang(script_path):
            return self.shell.script_manager.shebang_handler.execute_with_shebang(
                script_path, script_args)
        
        # Save current script state
        old_script_name = self.state.script_name
        old_script_mode = self.state.is_script_mode
        old_positional = self.state.positional_params.copy()
        
        self.state.script_name = script_path
        self.state.is_script_mode = True
        self.state.positional_params = script_args
        
        try:
            with FileInput(script_path) as input_source:
                return self.shell.script_manager.source_processor.execute_from_source(
                    input_source, add_to_history=False)
        except Exception as e:
            print(f"psh: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            self.state.script_name = old_script_name
            self.state.is_script_mode = old_script_mode
            self.state.positional_params = old_positional