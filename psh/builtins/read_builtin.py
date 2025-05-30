"""Read builtin command implementation."""
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class ReadBuiltin(Builtin):
    """Read a line from standard input and assign to variables."""
    
    @property
    def name(self) -> str:
        return "read"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the read builtin.
        
        read [-r] [var...]
        
        Read a line from standard input and split it into fields.
        """
        # Parse options
        raw_mode = False
        var_start_idx = 1
        
        # Check for -r option
        if len(args) > 1 and args[1] == '-r':
            raw_mode = True
            var_start_idx = 2
        
        # Get variable names (default to REPLY if none specified)
        var_names = args[var_start_idx:] if var_start_idx < len(args) else ['REPLY']
        
        try:
            # Read a line from stdin
            line = sys.stdin.readline()
            
            # Check for EOF
            if not line:
                return 1
            
            # Process backslash escapes unless in raw mode
            # This must be done BEFORE stripping the newline so that
            # backslash-newline line continuation works correctly
            if not raw_mode:
                line = self._process_escapes(line)
            
            # Remove trailing newline if present (after escape processing)
            if line.endswith('\n'):
                line = line[:-1]
            
            # Get IFS value (default is space, tab, newline)
            ifs = shell.variables.get('IFS', shell.env.get('IFS', ' \t\n'))
            
            # Handle assignment based on number of variables
            if len(var_names) == 1:
                # Single variable: trim leading/trailing IFS whitespace only
                # Don't split the line
                ifs_whitespace = [c for c in ifs if c in ' \t\n']
                if ifs_whitespace:
                    # Trim leading whitespace
                    while line and line[0] in ifs_whitespace:
                        line = line[1:]
                    # Trim trailing whitespace
                    while line and line[-1] in ifs_whitespace:
                        line = line[:-1]
                shell.variables[var_names[0]] = line
            else:
                # Multiple variables: split based on IFS
                fields = self._split_with_ifs(line, ifs)
                self._assign_to_variables(fields, var_names, shell)
            
            return 0
            
        except KeyboardInterrupt:
            # Ctrl-C pressed
            return 130
        except Exception as e:
            print(f"read: {e}", file=sys.stderr)
            return 1
    
    def _process_escapes(self, line: str) -> str:
        """Process backslash escape sequences.
        
        Handles:
        - \\ -> \
        - \n -> newline
        - \t -> tab
        - \r -> carriage return
        - \\<space> -> space (preserves space)
        - \\<newline> -> line continuation (removes both)
        - \\<other> -> <other> (backslash removed)
        """
        result = []
        i = 0
        
        while i < len(line):
            if line[i] == '\\' and i + 1 < len(line):
                next_char = line[i + 1]
                if next_char == '\\':
                    result.append('\\')
                elif next_char == 'n':
                    result.append('\n')
                elif next_char == 't':
                    result.append('\t')
                elif next_char == 'r':
                    result.append('\r')
                elif next_char == '\n':
                    # Line continuation - skip both characters  
                    # Note: This is only for backslash-newline within the line
                    # A trailing backslash at end of input is different
                    pass
                else:
                    # Other escaped character - just add the character
                    result.append(next_char)
                i += 2
            else:
                result.append(line[i])
                i += 1
        
        return ''.join(result)
    
    def _split_with_ifs(self, line: str, ifs: str) -> List[str]:
        """Split line based on IFS (Internal Field Separator).
        
        Rules:
        1. If IFS is empty, no splitting occurs
        2. Leading/trailing IFS whitespace characters are trimmed
        3. Multiple consecutive IFS whitespace characters count as one separator
        4. Non-whitespace IFS characters are always separators
        """
        if not ifs:
            # No IFS, return entire line as one field
            return [line]
        
        # Separate whitespace and non-whitespace IFS characters
        ifs_whitespace = set(c for c in ifs if c in ' \t\n')
        ifs_non_whitespace = set(c for c in ifs if c not in ' \t\n')
        
        fields = []
        current_field = []
        i = 0
        
        # Skip leading IFS whitespace
        while i < len(line) and line[i] in ifs_whitespace:
            i += 1
        
        while i < len(line):
            char = line[i]
            
            if char in ifs_non_whitespace:
                # Non-whitespace IFS character - always a separator
                fields.append(''.join(current_field))
                current_field = []
                i += 1
            elif char in ifs_whitespace:
                # Whitespace IFS character
                if current_field:
                    fields.append(''.join(current_field))
                    current_field = []
                # Skip consecutive IFS whitespace
                while i < len(line) and line[i] in ifs_whitespace:
                    i += 1
            else:
                # Regular character
                current_field.append(char)
                i += 1
        
        # Add last field if any
        if current_field:
            fields.append(''.join(current_field))
        
        # If no fields were found, return empty string
        if not fields:
            fields = ['']
        
        return fields
    
    def _assign_to_variables(self, fields: List[str], var_names: List[str], shell: 'Shell'):
        """Assign fields to variables.
        
        Rules:
        1. Each field is assigned to corresponding variable
        2. If more fields than variables, last variable gets all remaining fields
        3. If fewer fields than variables, extra variables are set to empty string
        """
        for i, var_name in enumerate(var_names):
            if i < len(fields):
                if i == len(var_names) - 1 and i < len(fields) - 1:
                    # Last variable - assign all remaining fields joined by first IFS char
                    ifs = shell.variables.get('IFS', shell.env.get('IFS', ' \t\n'))
                    if ifs:
                        sep = ifs[0]
                    else:
                        sep = ' '
                    value = sep.join(fields[i:])
                else:
                    # Normal assignment
                    value = fields[i]
            else:
                # No more fields - set to empty
                value = ''
            
            shell.variables[var_name] = value