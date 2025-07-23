"""Debug control commands for convenient AST debugging."""

import sys
from typing import List
from .base import Builtin
from .registry import builtin


@builtin
class DebugASTBuiltin(Builtin):
    """Control AST debugging options."""
    
    name = "debug-ast"
    
    def execute(self, args: List[str], shell) -> int:
        """Execute the debug-ast builtin.
        
        Usage: debug-ast [on|off] [FORMAT]
        
        Arguments:
            on|off     Enable or disable AST debugging (default: toggle)
            FORMAT     AST format: tree, pretty, compact, dot, sexp (default: tree)
        
        Examples:
            debug-ast              # Toggle AST debugging
            debug-ast on           # Enable AST debugging with tree format
            debug-ast off          # Disable AST debugging
            debug-ast on pretty    # Enable with pretty format
            debug-ast tree         # Enable with tree format
        """
        if len(args) == 1:
            # No arguments - toggle debug-ast
            current = shell.state.options.get('debug-ast', False)
            shell.state.options['debug-ast'] = not current
            status = "enabled" if not current else "disabled"
            format_name = shell.state.scope_manager.get_variable('PSH_AST_FORMAT') or 'tree'
            print(f"AST debugging {status} (format: {format_name})")
            return 0
        
        elif len(args) == 2:
            arg = args[1].lower()
            
            if arg in ('on', 'enable', 'true', '1'):
                shell.state.options['debug-ast'] = True
                format_name = shell.state.scope_manager.get_variable('PSH_AST_FORMAT') or 'tree'
                print(f"AST debugging enabled (format: {format_name})")
                return 0
                
            elif arg in ('off', 'disable', 'false', '0'):
                shell.state.options['debug-ast'] = False
                print("AST debugging disabled")
                return 0
                
            elif arg in ('tree', 'pretty', 'compact', 'dot', 'sexp'):
                # Format specified - enable debug and set format
                shell.state.options['debug-ast'] = True
                shell.state.scope_manager.set_variable('PSH_AST_FORMAT', arg)
                print(f"AST debugging enabled (format: {arg})")
                return 0
                
            else:
                self.error(f"invalid argument: {args[1]}", shell)
                self.error("Use: debug-ast [on|off] [tree|pretty|compact|dot|sexp]", shell)
                return 1
        
        elif len(args) == 3:
            # Enable/disable and format
            action = args[1].lower()
            format_arg = args[2].lower()
            
            if action not in ('on', 'enable', 'true', '1', 'off', 'disable', 'false', '0'):
                self.error(f"invalid action: {action}", shell)
                return 1
                
            if format_arg not in ('tree', 'pretty', 'compact', 'dot', 'sexp'):
                self.error(f"invalid format: {format_arg}", shell)
                return 1
            
            if action in ('on', 'enable', 'true', '1'):
                shell.state.options['debug-ast'] = True
                shell.state.scope_manager.set_variable('PSH_AST_FORMAT', format_arg)
                print(f"AST debugging enabled (format: {format_arg})")
            else:
                shell.state.options['debug-ast'] = False
                print("AST debugging disabled")
            
            return 0
        
        else:
            self.error("too many arguments", shell)
            self.error("Use: debug-ast [on|off] [tree|pretty|compact|dot|sexp]", shell)
            return 1


@builtin
class DebugBuiltin(Builtin):
    """Control various debug options."""
    
    name = "debug"
    
    def execute(self, args: List[str], shell) -> int:
        """Execute the debug builtin.
        
        Usage: debug [OPTION] [on|off]
        
        Options:
            ast          AST debugging
            tokens       Token debugging  
            scopes       Scope debugging
            expansion    Expansion debugging
            exec         Execution debugging
            
        Examples:
            debug                    # Show all debug options
            debug ast on             # Enable AST debugging
            debug tokens off         # Disable token debugging
            debug expansion          # Toggle expansion debugging
        """
        if len(args) == 1:
            # Show all debug options
            print("Debug Options:")
            debug_options = {
                'ast': 'debug-ast',
                'tokens': 'debug-tokens', 
                'scopes': 'debug-scopes',
                'expansion': 'debug-expansion',
                'exec': 'debug-exec',
                'parser': 'debug-parser'
            }
            
            for name, option_key in debug_options.items():
                status = "on" if shell.state.options.get(option_key, False) else "off"
                print(f"  {name:<12} {status}")
            
            # Show AST format if AST debugging is on
            if shell.state.options.get('debug-ast', False):
                format_name = shell.state.scope_manager.get_variable('PSH_AST_FORMAT') or 'tree'
                print(f"  ast-format   {format_name}")
            
            return 0
        
        elif len(args) == 2:
            # Toggle option
            option = args[1].lower()
            option_map = {
                'ast': 'debug-ast',
                'tokens': 'debug-tokens',
                'scopes': 'debug-scopes', 
                'expansion': 'debug-expansion',
                'exec': 'debug-exec',
                'parser': 'debug-parser'
            }
            
            if option not in option_map:
                self.error(f"unknown debug option: {option}", shell)
                self.error("Valid options: ast, tokens, scopes, expansion, exec, parser", shell)
                return 1
            
            option_key = option_map[option]
            current = shell.state.options.get(option_key, False)
            shell.state.options[option_key] = not current
            status = "enabled" if not current else "disabled"
            print(f"Debug {option} {status}")
            
            # Special handling for debug-scopes
            if option == 'scopes':
                shell.state.scope_manager.enable_debug(not current)
            
            return 0
        
        elif len(args) == 3:
            # Set option on/off
            option = args[1].lower()
            action = args[2].lower()
            
            option_map = {
                'ast': 'debug-ast',
                'tokens': 'debug-tokens',
                'scopes': 'debug-scopes',
                'expansion': 'debug-expansion', 
                'exec': 'debug-exec',
                'parser': 'debug-parser'
            }
            
            if option not in option_map:
                self.error(f"unknown debug option: {option}", shell)
                return 1
            
            if action in ('on', 'enable', 'true', '1'):
                shell.state.options[option_map[option]] = True
                print(f"Debug {option} enabled")
                
                # Special handling for debug-scopes
                if option == 'scopes':
                    shell.state.scope_manager.enable_debug(True)
                    
            elif action in ('off', 'disable', 'false', '0'):
                shell.state.options[option_map[option]] = False
                print(f"Debug {option} disabled")
                
                # Special handling for debug-scopes
                if option == 'scopes':
                    shell.state.scope_manager.enable_debug(False)
                    
            else:
                self.error(f"invalid action: {action}", shell)
                self.error("Use: on, off, enable, disable, true, false, 1, or 0", shell)
                return 1
            
            return 0
        
        else:
            self.error("too many arguments", shell)
            return 1