"""Parser configuration system for PSH.

This module provides configurable parsing behavior to support different shell
modes, compliance levels, and feature sets.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any
from enum import Enum


class ParsingMode(Enum):
    """Different parsing modes for shell compatibility."""
    STRICT_POSIX = "strict_posix"    # Strict POSIX compliance
    BASH_COMPAT = "bash_compat"      # Bash compatibility mode
    PERMISSIVE = "permissive"        # Permissive parsing
    EDUCATIONAL = "educational"      # Educational mode with extra help


class ErrorHandlingMode(Enum):
    """Error handling strategies."""
    STRICT = "strict"                # Stop on first error
    COLLECT = "collect"              # Collect multiple errors
    RECOVER = "recover"              # Attempt error recovery


@dataclass
class ParserConfig:
    """Parser configuration options.
    
    This class centralizes all parser configuration options to provide
    flexible parsing behavior for different use cases.
    """
    
    # === Core Parsing Mode ===
    parsing_mode: ParsingMode = ParsingMode.BASH_COMPAT
    
    # === Error Handling ===
    error_handling: ErrorHandlingMode = ErrorHandlingMode.STRICT
    max_errors: int = 10
    collect_errors: bool = False
    enable_error_recovery: bool = False
    show_error_suggestions: bool = True
    
    # === Language Features ===
    enable_aliases: bool = True
    enable_functions: bool = True
    enable_arithmetic: bool = True
    enable_arrays: bool = True
    enable_associative_arrays: bool = True
    enable_process_substitution: bool = True
    enable_brace_expansion: bool = True
    enable_tilde_expansion: bool = True
    enable_parameter_expansion: bool = True
    enable_command_substitution: bool = True
    enable_history_expansion: bool = True
    
    # === POSIX Compliance ===
    strict_posix_keywords: bool = False      # Enforce POSIX keyword usage
    strict_posix_redirection: bool = False   # Enforce POSIX redirection rules
    strict_posix_quoting: bool = False       # Enforce POSIX quoting rules
    require_posix_functions: bool = False    # Require POSIX function syntax
    
    # === Bash Compatibility ===
    allow_bash_arrays: bool = True           # Allow Bash-style arrays
    allow_bash_functions: bool = True        # Allow Bash function syntax
    allow_bash_conditionals: bool = True     # Allow [[ ]] conditionals
    allow_bash_arithmetic: bool = True       # Allow (( )) arithmetic
    allow_empty_commands: bool = True        # Allow empty command lists
    
    # === Parsing Behavior ===
    case_sensitive_keywords: bool = True     # Keywords must be exact case
    require_semicolons: bool = False         # Require semicolons in statements
    allow_unquoted_variables: bool = True    # Allow $var without quotes
    auto_quote_filenames: bool = False       # Auto-quote filenames with spaces
    
    # === Advanced Features ===
    enable_here_strings: bool = True         # <<< here strings
    enable_coprocesses: bool = False         # |& coprocess syntax
    enable_named_pipes: bool = True          # Process substitution pipes
    enable_extended_globbing: bool = True    # Extended glob patterns
    
    # === AST Options ===
    build_word_ast_nodes: bool = False       # Build Word AST nodes with expansion info
    
    # === Development and Debugging ===
    trace_parsing: bool = False              # Trace parsing rules
    profile_parsing: bool = False            # Profile parser performance  
    show_token_stream: bool = False          # Debug token stream
    validate_ast: bool = False               # Validate AST after parsing
    
    # === Educational Mode ===
    explain_parsing_steps: bool = False      # Explain each parsing step
    show_grammar_rules: bool = False         # Show grammar rules being applied
    interactive_parsing: bool = False        # Interactive parsing mode
    
    # === Validation Options ===
    enable_validation: bool = False          # Enable AST validation
    enable_semantic_analysis: bool = True    # Enable semantic analysis
    enable_validation_rules: bool = True     # Enable validation rules
    
    # === Compatibility Options ===
    bash_version_target: str = "5.1"         # Target Bash version for compatibility
    posix_version_target: str = "2017"       # Target POSIX version
    
    # === Custom Extensions ===
    custom_keywords: Set[str] = field(default_factory=set)
    disabled_builtins: Set[str] = field(default_factory=set)
    custom_operators: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def strict_posix(cls) -> 'ParserConfig':
        """Create strict POSIX configuration.
        
        This mode enforces strict POSIX compliance with no extensions.
        """
        return cls(
            parsing_mode=ParsingMode.STRICT_POSIX,
            error_handling=ErrorHandlingMode.STRICT,
            
            # Disable non-POSIX features
            enable_associative_arrays=False,
            enable_process_substitution=False,
            enable_brace_expansion=False,
            enable_history_expansion=False,
            
            # Strict POSIX compliance
            strict_posix_keywords=True,
            strict_posix_redirection=True,
            strict_posix_quoting=True,
            require_posix_functions=True,
            
            # Disable Bash extensions
            allow_bash_arrays=False,
            allow_bash_functions=False,
            allow_bash_conditionals=False,
            allow_bash_arithmetic=False,
            allow_empty_commands=False,
            
            # Strict parsing behavior
            require_semicolons=True,
            case_sensitive_keywords=True,
            
            # Disable advanced features
            enable_here_strings=False,
            enable_coprocesses=False,
            enable_extended_globbing=False,
            
            posix_version_target="2017"
        )
    
    @classmethod
    def bash_compatible(cls) -> 'ParserConfig':
        """Create Bash-compatible configuration.
        
        This mode enables most Bash features for maximum compatibility.
        """
        return cls(
            parsing_mode=ParsingMode.BASH_COMPAT,
            error_handling=ErrorHandlingMode.COLLECT,
            max_errors=20,
            enable_error_recovery=True,
            
            # Enable all features
            enable_aliases=True,
            enable_functions=True,
            enable_arithmetic=True,
            enable_arrays=True,
            enable_associative_arrays=True,
            enable_process_substitution=True,
            enable_brace_expansion=True,
            enable_history_expansion=True,
            
            # Allow Bash extensions
            allow_bash_arrays=True,
            allow_bash_functions=True,
            allow_bash_conditionals=True,
            allow_bash_arithmetic=True,
            allow_empty_commands=True,
            
            # Permissive parsing
            require_semicolons=False,
            allow_unquoted_variables=True,
            
            # Enable advanced features
            enable_here_strings=True,
            enable_extended_globbing=True,
            
            bash_version_target="5.1"
        )
    
    @classmethod
    def permissive(cls) -> 'ParserConfig':
        """Create permissive configuration for error tolerance.
        
        This mode is very forgiving and tries to parse as much as possible.
        """
        return cls(
            parsing_mode=ParsingMode.PERMISSIVE,
            error_handling=ErrorHandlingMode.RECOVER,
            max_errors=50,
            collect_errors=True,
            enable_error_recovery=True,
            show_error_suggestions=True,
            
            # Enable everything
            enable_aliases=True,
            enable_functions=True,
            enable_arithmetic=True,
            enable_arrays=True,
            enable_associative_arrays=True,
            enable_process_substitution=True,
            enable_brace_expansion=True,
            enable_history_expansion=True,
            
            # Very permissive
            allow_bash_arrays=True,
            allow_bash_functions=True,
            allow_bash_conditionals=True,
            allow_bash_arithmetic=True,
            allow_empty_commands=True,
            
            # Relaxed parsing
            require_semicolons=False,
            allow_unquoted_variables=True,
            auto_quote_filenames=True,
            
            # All advanced features
            enable_here_strings=True,
            enable_coprocesses=True,
            enable_extended_globbing=True
        )
    
    @classmethod
    def educational(cls) -> 'ParserConfig':
        """Create educational configuration with extra help.
        
        This mode provides detailed explanations and interactive features
        for learning shell programming.
        """
        return cls(
            parsing_mode=ParsingMode.EDUCATIONAL,
            error_handling=ErrorHandlingMode.COLLECT,
            max_errors=20,
            collect_errors=True,
            enable_error_recovery=True,
            show_error_suggestions=True,
            
            # Standard features enabled
            enable_aliases=True,
            enable_functions=True,
            enable_arithmetic=True,
            enable_arrays=True,
            enable_process_substitution=True,
            enable_brace_expansion=True,
            
            # Bash compatibility for learning
            allow_bash_arrays=True,
            allow_bash_functions=True,
            allow_bash_conditionals=True,
            allow_bash_arithmetic=True,
            
            # Educational features
            explain_parsing_steps=True,
            show_grammar_rules=True,
            trace_parsing=True,
            validate_ast=True,
            
            # Enable validation for educational purposes
            enable_validation=True,
            enable_semantic_analysis=True,
            enable_validation_rules=True,
            
            # Help with common mistakes
            auto_quote_filenames=True
        )
    
    @classmethod
    def development(cls) -> 'ParserConfig':
        """Create configuration for parser development.
        
        This mode enables all debugging and profiling features.
        """
        return cls(
            parsing_mode=ParsingMode.BASH_COMPAT,
            error_handling=ErrorHandlingMode.COLLECT,
            collect_errors=True,
            enable_error_recovery=True,
            
            # All features for testing
            enable_aliases=True,
            enable_functions=True,
            enable_arithmetic=True,
            enable_arrays=True,
            enable_associative_arrays=True,
            enable_process_substitution=True,
            
            # Debug features
            trace_parsing=True,
            profile_parsing=True,
            show_token_stream=True,
            validate_ast=True,
            
            # Enable validation for development
            enable_validation=True,
            enable_semantic_analysis=True,
            enable_validation_rules=True,
            
            # Interactive development
            interactive_parsing=True
        )
    
    def clone(self, **overrides) -> 'ParserConfig':
        """Create a copy of this config with optional overrides."""
        # Get all current field values
        values = {}
        for field_info in self.__dataclass_fields__.values():
            current_value = getattr(self, field_info.name)
            # Handle mutable defaults
            if isinstance(current_value, (set, dict, list)):
                values[field_info.name] = current_value.copy()
            else:
                values[field_info.name] = current_value
        
        # Apply overrides
        values.update(overrides)
        
        return ParserConfig(**values)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        attr_name = f"enable_{feature}"
        return getattr(self, attr_name, False)
    
    def should_allow(self, capability: str) -> bool:
        """Check if a capability should be allowed."""
        attr_name = f"allow_{capability}"
        return getattr(self, attr_name, False)
    
    def get_compatibility_info(self) -> Dict[str, Any]:
        """Get compatibility information."""
        return {
            'parsing_mode': self.parsing_mode.value,
            'bash_version': self.bash_version_target,
            'posix_version': self.posix_version_target,
            'strict_posix': self.parsing_mode == ParsingMode.STRICT_POSIX,
            'bash_compatible': self.parsing_mode == ParsingMode.BASH_COMPAT,
            'permissive_mode': self.parsing_mode == ParsingMode.PERMISSIVE
        }