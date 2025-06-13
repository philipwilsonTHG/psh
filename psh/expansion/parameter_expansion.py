"""Advanced parameter expansion operations."""
import re
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..shell import Shell


class ParameterExpansion:
    """Advanced parameter expansion operations."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.pattern_matcher = PatternMatcher()
    
    def parse_expansion(self, expr: str) -> Tuple[str, str, str]:
        """
        Parse a parameter expansion expression.
        
        Returns (operator, var_name, operand) where:
        - operator: '#', '##', '%', '%%', '/', '//', '/#', '/%', ':', '!', '^', '^^', ',', ',,'
        - var_name: The variable name
        - operand: The pattern, string, or offset/length
        """
        # Remove ${ and }
        if expr.startswith('${') and expr.endswith('}'):
            content = expr[2:-1]
        else:
            raise ValueError(f"Invalid parameter expansion: {expr}")
        
        # Check for length operation ${#var}
        if content.startswith('#'):
            # Special case: ${#} alone means number of positional params
            if content == '#':
                return '#', '#', ''
            return '#', content[1:], ''
        
        # Check for variable name matching ${!prefix*} or ${!prefix@}
        # Handle escaped ! character
        if content.startswith('\\!'):
            content = content[1:]  # Remove the backslash
        
        if content.startswith('!'):
            if content.endswith('*'):
                return '!*', content[1:-1], ''
            elif content.endswith('@'):
                return '!@', content[1:-1], ''
        
        # Check for pattern removal and substitution first (before case modification)
        # This is important because substitution patterns can contain commas
        for i, char in enumerate(content):
            if char == '#' and i > 0:
                # ${var#pattern} or ${var##pattern}
                if i + 1 < len(content) and content[i + 1] == '#':
                    return '##', content[:i], content[i + 2:]
                else:
                    return '#', content[:i], content[i + 1:]
            elif char == '%' and i > 0:
                # ${var%pattern} or ${var%%pattern}
                if i + 1 < len(content) and content[i + 1] == '%':
                    return '%%', content[:i], content[i + 2:]
                else:
                    return '%', content[:i], content[i + 1:]
            elif char == '/' and i > 0:
                # ${var/pattern/string} or ${var//pattern/string} or ${var/#pattern/string} or ${var/%pattern/string}
                var_name = content[:i]
                rest = content[i + 1:]
                
                # Check for special prefixes
                if rest.startswith('#'):
                    # ${var/#pattern/string}
                    operator = '/#'
                    rest = rest[1:]
                elif rest.startswith('%'):
                    # ${var/%pattern/string}
                    operator = '/%'
                    rest = rest[1:]
                elif rest.startswith('/'):
                    # ${var//pattern/string}
                    operator = '//'
                    rest = rest[1:]
                else:
                    # ${var/pattern/string}
                    operator = '/'
                
                # Find the separator between pattern and replacement
                # Need to handle escaped slashes
                pattern_parts = []
                j = 0
                while j < len(rest):
                    if rest[j] == '\\' and j + 1 < len(rest):
                        pattern_parts.append(rest[j:j+2])
                        j += 2
                    elif rest[j] == '/':
                        # Found separator
                        pattern = ''.join(pattern_parts)
                        replacement = rest[j + 1:]
                        return operator, var_name, pattern + '/' + replacement
                    else:
                        pattern_parts.append(rest[j])
                        j += 1
                
                # No replacement found, treat as pattern only
                return operator, var_name, ''.join(pattern_parts) + '/'
            elif char == ':' and i > 0:
                # Check if it's ${var:-default} (handled elsewhere) vs ${var:offset}
                if i + 1 < len(content) and content[i + 1] == '-':
                    # This is ${var:-default}, skip to avoid conflict
                    continue
                # ${var:offset} or ${var:offset:length}
                var_name = content[:i]
                rest = content[i + 1:]
                return ':', var_name, rest
        
        # Check for case modification ${var^pattern}, ${var^^pattern}, etc
        # This is checked after substitution to avoid conflicts with commas in patterns
        for i, char in enumerate(content):
            if char in '^,':
                if i + 1 < len(content) and content[i + 1] == char:
                    # Double operator (^^ or ,,)
                    var_name = content[:i]
                    pattern = content[i + 2:] if i + 2 < len(content) else '?'
                    return char * 2, var_name, pattern
                else:
                    # Single operator (^ or ,)
                    var_name = content[:i]
                    pattern = content[i + 1:] if i + 1 < len(content) else '?'
                    return char, var_name, pattern
        
        # No operator found, might be ${var:-default} which is handled elsewhere
        return '', content, ''
    
    def _process_replacement_escapes(self, replacement: str) -> str:
        """Process escape sequences in replacement string."""
        result = []
        i = 0
        while i < len(replacement):
            if replacement[i] == '\\' and i + 1 < len(replacement):
                # Handle escaped characters
                next_char = replacement[i + 1]
                if next_char == '/':
                    result.append('/')
                    i += 2
                else:
                    # Keep other escapes as-is for now
                    result.append(replacement[i])
                    i += 1
            else:
                result.append(replacement[i])
                i += 1
        return ''.join(result)
    
    # Length operations
    def get_length(self, value: str) -> str:
        """Get the length of a string."""
        return str(len(value))
    
    # Pattern removal
    def remove_shortest_prefix(self, value: str, pattern: str) -> str:
        """Remove shortest matching prefix."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=True)
        # Make the regex non-greedy for shortest match
        regex = regex.replace('.*', '.*?')
        match = re.match(regex, value)
        if match:
            return value[match.end():]
        return value
    
    def remove_longest_prefix(self, value: str, pattern: str) -> str:
        """Remove longest matching prefix."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=True)
        # For longest match, use greedy regex (default behavior)
        # Try to find the longest prefix that matches
        match = re.match(regex, value)
        if match:
            # The regex will naturally find the longest match due to greedy quantifiers
            return value[match.end():]
        return value
    
    def remove_shortest_suffix(self, value: str, pattern: str) -> str:
        """Remove shortest matching suffix."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=False)
        # Convert to end-anchored regex
        regex = regex.rstrip('$') + '$'
        
        # Find shortest match from end
        for i in range(len(value), -1, -1):
            if re.match(regex, value[i:]):
                return value[:i]
        return value
    
    def remove_longest_suffix(self, value: str, pattern: str) -> str:
        """Remove longest matching suffix."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=False)
        # Convert to end-anchored regex
        regex = regex.rstrip('$') + '$'
        
        # Find longest match from end
        for i in range(len(value) + 1):
            if re.match(regex, value[i:]):
                return value[:i]
        return value
    
    # Pattern substitution
    def substitute_first(self, value: str, pattern: str, replacement: str) -> str:
        """Replace first match."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        replacement = self._process_replacement_escapes(replacement)
        return re.sub(regex, replacement, value, count=1)
    
    def substitute_all(self, value: str, pattern: str, replacement: str) -> str:
        """Replace all matches."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        replacement = self._process_replacement_escapes(replacement)
        return re.sub(regex, replacement, value)
    
    def substitute_prefix(self, value: str, pattern: str, replacement: str) -> str:
        """Replace prefix match."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=True)
        match = re.match(regex, value)
        if match:
            # Process escape sequences in replacement
            replacement = self._process_replacement_escapes(replacement)
            return replacement + value[match.end():]
        return value
    
    def substitute_suffix(self, value: str, pattern: str, replacement: str) -> str:
        """Replace suffix match."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=True, from_start=False)
        # Convert to end-anchored regex
        regex = regex.rstrip('$') + '$'
        
        # Find match at end
        match = re.search(regex, value)
        if match:
            replacement = self._process_replacement_escapes(replacement)
            return value[:match.start()] + replacement
        return value
    
    # Substring extraction
    def extract_substring(self, value: str, offset: int, length: Optional[int] = None) -> str:
        """Extract substring with offset and optional length."""
        # Handle negative offset
        if offset < 0:
            # Negative offset counts from end
            offset = len(value) + offset
            if offset < 0:
                offset = 0
        
        # Handle out of bounds
        if offset >= len(value):
            return ''
        
        if length is None:
            # No length specified, return from offset to end
            return value[offset:]
        else:
            # Handle negative length
            if length < 0:
                # Negative length means "all but last N chars"
                end = len(value) + length
                if end <= offset:
                    return ''
                return value[offset:end]
            else:
                # Normal positive length
                return value[offset:offset + length]
    
    # Variable name matching
    def match_variable_names(self, prefix: str, quoted: bool = False) -> List[str]:
        """Find all variable names starting with prefix."""
        # Get all variables from both shell variables and environment
        all_vars = set(self.state.variables.keys()) | set(self.state.env.keys())
        
        # Filter by prefix
        matching = sorted([var for var in all_vars if var.startswith(prefix)])
        
        if quoted:
            # Return as quoted strings
            return [f'"{var}"' for var in matching]
        else:
            # Return as space-separated list
            return matching
    
    # Case modification
    def uppercase_first(self, value: str, pattern: str = '?') -> str:
        """Convert first matching char to uppercase."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        
        # Find first match
        match = re.search(regex, value)
        if match:
            start, end = match.span()
            return value[:start] + value[start:end].upper() + value[end:]
        return value
    
    def uppercase_all(self, value: str, pattern: str = '?') -> str:
        """Convert all matching chars to uppercase."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        
        def upper_repl(match):
            return match.group(0).upper()
        
        return re.sub(regex, upper_repl, value)
    
    def lowercase_first(self, value: str, pattern: str = '?') -> str:
        """Convert first matching char to lowercase."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        
        # Find first match
        match = re.search(regex, value)
        if match:
            start, end = match.span()
            return value[:start] + value[start:end].lower() + value[end:]
        return value
    
    def lowercase_all(self, value: str, pattern: str = '?') -> str:
        """Convert all matching chars to lowercase."""
        regex = self.pattern_matcher.shell_pattern_to_regex(pattern, anchored=False)
        
        def lower_repl(match):
            return match.group(0).lower()
        
        return re.sub(regex, lower_repl, value)


class PatternMatcher:
    """Convert shell patterns to regex and perform matching."""
    
    def shell_pattern_to_regex(self, pattern: str, anchored: bool = False, from_start: bool = True) -> str:
        """
        Convert shell glob pattern to Python regex.
        
        Args:
            pattern: Shell pattern with *, ?, [...] 
            anchored: If True, pattern must match from start or end
            from_start: If anchored, whether to anchor at start (True) or end (False)
        """
        regex_parts = []
        i = 0
        
        while i < len(pattern):
            char = pattern[i]
            
            if char == '*':
                # Match any characters
                regex_parts.append('.*')
            elif char == '?':
                # Match single character
                regex_parts.append('.')
            elif char == '[':
                # Character class
                j = i + 1
                # Find closing ]
                while j < len(pattern) and pattern[j] != ']':
                    j += 1
                if j < len(pattern):
                    # Valid character class
                    class_content = pattern[i+1:j]
                    # Handle negation (shell uses ! for negation, regex uses ^)
                    if class_content.startswith('!'):
                        # Don't escape the character class content - it's already regex-compatible
                        regex_parts.append(f'[^{class_content[1:]}]')
                    elif class_content.startswith('^'):
                        # Also support regex-style negation for compatibility
                        regex_parts.append(f'[^{class_content[1:]}]')
                    else:
                        # Don't escape the character class content
                        regex_parts.append(f'[{class_content}]')
                    i = j
                else:
                    # No closing ], treat as literal
                    regex_parts.append(re.escape(char))
            elif char == '\\' and i + 1 < len(pattern):
                # Escaped character
                regex_parts.append(re.escape(pattern[i + 1]))
                i += 1
            else:
                # Regular character
                regex_parts.append(re.escape(char))
            
            i += 1
        
        regex = ''.join(regex_parts)
        
        if anchored:
            if from_start:
                regex = '^' + regex
            else:
                # For suffix matching, we'll add $ later
                pass
        
        return regex