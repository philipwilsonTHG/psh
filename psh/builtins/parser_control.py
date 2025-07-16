"""Parser configuration control commands."""

import sys
from typing import List
from .base import Builtin
from .registry import builtin


@builtin
class ParserConfigBuiltin(Builtin):
    """Control parser configuration settings."""
    
    name = "parser-config"
    
    def execute(self, args: List[str], shell) -> int:
        """Execute the parser-config builtin.
        
        Usage: parser-config [COMMAND] [OPTIONS]
        
        Commands:
            show              Show current parser configuration
            mode MODE         Set parsing mode (posix|bash|permissive|educational)
            strict            Enable strict POSIX mode
            permissive        Enable permissive mode
            enable FEATURE    Enable a parser feature
            disable FEATURE   Disable a parser feature
            
        Features:
            arithmetic        Arithmetic evaluation (( ))
            arrays            Array support
            functions         Function definitions
            aliases           Alias expansion
            process-subst     Process substitution
            brace-expand      Brace expansion
            
        Examples:
            parser-config show
            parser-config mode posix
            parser-config strict
            parser-config enable arithmetic
            parser-config disable arrays
        """
        if len(args) == 1:
            # No arguments - show current configuration
            return self._show_config(shell)
        
        command = args[1].lower()
        
        if command == "show":
            return self._show_config(shell)
        elif command == "mode":
            if len(args) < 3:
                self.error("mode requires an argument", shell)
                return 2
            return self._set_mode(args[2], shell)
        elif command == "strict":
            return self._set_mode("posix", shell)
        elif command == "permissive":
            return self._set_mode("permissive", shell)
        elif command == "enable":
            if len(args) < 3:
                self.error("enable requires a feature name", shell)
                return 2
            return self._enable_feature(args[2], shell)
        elif command == "disable":
            if len(args) < 3:
                self.error("disable requires a feature name", shell)
                return 2
            return self._disable_feature(args[2], shell)
        else:
            self.error(f"unknown command: {command}", shell)
            return 1
    
    def _show_config(self, shell) -> int:
        """Show current parser configuration."""
        print("Parser Configuration:")
        
        # Show parsing mode
        posix_mode = shell.state.options.get('posix', False)
        collect_errors = shell.state.options.get('collect_errors', False)
        debug_parser = shell.state.options.get('debug-parser', False)
        
        if posix_mode:
            mode = "strict POSIX"
        elif collect_errors:
            mode = "permissive"
        else:
            mode = "bash compatible"
        
        print(f"  Mode:            {mode}")
        print(f"  POSIX strict:    {'on' if posix_mode else 'off'}")
        print(f"  Collect errors:  {'on' if collect_errors else 'off'}")
        print(f"  Debug parser:    {'on' if debug_parser else 'off'}")
        
        # Show feature status (based on shell options)
        print("\nFeatures:")
        print(f"  Arithmetic:      {'on' if not shell.state.options.get('no_arithmetic', False) else 'off'}")
        print(f"  Arrays:          {'on' if not shell.state.options.get('no_arrays', False) else 'off'}")
        print(f"  Functions:       {'on' if not shell.state.options.get('no_functions', False) else 'off'}")
        print(f"  Aliases:         {'on' if not shell.state.options.get('no_aliases', False) else 'off'}")
        print(f"  Brace expansion: {'on' if shell.state.options.get('braceexpand', True) else 'off'}")
        print(f"  History expand:  {'on' if shell.state.options.get('histexpand', True) else 'off'}")
        
        return 0
    
    def _set_mode(self, mode: str, shell) -> int:
        """Set parsing mode."""
        mode = mode.lower()
        
        if mode in ('posix', 'strict'):
            shell.state.options['posix'] = True
            shell.state.options['collect_errors'] = False
            # Disable non-POSIX features
            shell.state.options['braceexpand'] = False
            shell.state.options['histexpand'] = False
            print("Parser mode set to strict POSIX")
            
        elif mode in ('bash', 'compatible'):
            shell.state.options['posix'] = False
            shell.state.options['collect_errors'] = False
            # Enable bash features
            shell.state.options['braceexpand'] = True
            shell.state.options['histexpand'] = True
            print("Parser mode set to Bash compatible")
            
        elif mode == 'permissive':
            shell.state.options['posix'] = False
            shell.state.options['collect_errors'] = True
            # Enable all features
            shell.state.options['braceexpand'] = True
            shell.state.options['histexpand'] = True
            print("Parser mode set to permissive")
            
        elif mode == 'educational':
            shell.state.options['posix'] = False
            shell.state.options['collect_errors'] = True
            shell.state.options['debug-parser'] = True
            # Enable features but with debugging
            shell.state.options['braceexpand'] = True
            shell.state.options['histexpand'] = True
            print("Parser mode set to educational (with debugging)")
            
        else:
            self.error(f"unknown mode: {mode}", shell)
            self.error("Valid modes: posix, bash, permissive, educational", shell)
            return 1
        
        return 0
    
    def _enable_feature(self, feature: str, shell) -> int:
        """Enable a parser feature."""
        feature = feature.lower().replace('-', '_')
        
        # Map feature names to shell options
        feature_map = {
            'arithmetic': 'no_arithmetic',
            'arrays': 'no_arrays', 
            'functions': 'no_functions',
            'aliases': 'no_aliases',
            'brace_expand': 'braceexpand',
            'brace_expansion': 'braceexpand',
            'history_expand': 'histexpand',
            'history_expansion': 'histexpand',
            'process_subst': 'process_substitution',
            'process_substitution': 'process_substitution'
        }
        
        if feature in feature_map:
            option_name = feature_map[feature]
            
            # Handle positive options (enable by setting True)
            if option_name in ('braceexpand', 'histexpand', 'process_substitution'):
                shell.state.options[option_name] = True
                print(f"Parser feature '{feature}' enabled")
            # Handle negative options (enable by removing/setting False)
            else:
                shell.state.options[option_name] = False
                print(f"Parser feature '{feature}' enabled")
        else:
            self.error(f"unknown feature: {feature}", shell)
            self.error("Valid features: arithmetic, arrays, functions, aliases, brace-expand, history-expand", shell)
            return 1
        
        return 0
    
    def _disable_feature(self, feature: str, shell) -> int:
        """Disable a parser feature."""
        feature = feature.lower().replace('-', '_')
        
        # Map feature names to shell options
        feature_map = {
            'arithmetic': 'no_arithmetic',
            'arrays': 'no_arrays',
            'functions': 'no_functions', 
            'aliases': 'no_aliases',
            'brace_expand': 'braceexpand',
            'brace_expansion': 'braceexpand',
            'history_expand': 'histexpand',
            'history_expansion': 'histexpand',
            'process_subst': 'process_substitution',
            'process_substitution': 'process_substitution'
        }
        
        if feature in feature_map:
            option_name = feature_map[feature]
            
            # Handle positive options (disable by setting False)
            if option_name in ('braceexpand', 'histexpand', 'process_substitution'):
                shell.state.options[option_name] = False
                print(f"Parser feature '{feature}' disabled")
            # Handle negative options (disable by setting True)
            else:
                shell.state.options[option_name] = True
                print(f"Parser feature '{feature}' disabled")
        else:
            self.error(f"unknown feature: {feature}", shell)
            self.error("Valid features: arithmetic, arrays, functions, aliases, brace-expand, history-expand", shell)
            return 1
        
        return 0


@builtin
class ParserModeBuiltin(Builtin):
    """Quick parser mode switching command."""
    
    name = "parser-mode"
    
    def execute(self, args: List[str], shell) -> int:
        """Execute the parser-mode builtin.
        
        Usage: parser-mode [MODE]
        
        Modes:
            posix          Strict POSIX compliance mode
            bash           Bash-compatible mode (default)
            permissive     Permissive mode with error collection
            educational    Educational mode with debugging
            
        Examples:
            parser-mode posix
            parser-mode bash
            parser-mode permissive
        """
        if len(args) == 1:
            # Show current mode
            posix_mode = shell.state.options.get('posix', False)
            collect_errors = shell.state.options.get('collect_errors', False)
            debug_parser = shell.state.options.get('debug-parser', False)
            
            if posix_mode:
                mode = "posix"
            elif debug_parser:
                mode = "educational"
            elif collect_errors:
                mode = "permissive"
            else:
                mode = "bash"
            
            print(f"Parser mode: {mode}")
            return 0
        
        mode = args[1].lower()
        
        # Delegate to parser-config builtin
        config_builtin = ParserConfigBuiltin()
        return config_builtin._set_mode(mode, shell)