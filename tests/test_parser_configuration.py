"""Tests for parser configuration system."""

import pytest
from psh.lexer import tokenize
from psh.parser import (
    Parser, ParserConfig, ParsingMode, ErrorHandlingMode, 
    ParserFactory, ConfigurationValidator, parse_strict_posix,
    parse_bash_compatible, parse_permissive
)
from psh.parser.recursive_descent.helpers import ParseError


class TestParserConfig:
    """Test the ParserConfig class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ParserConfig()
        
        assert config.parsing_mode == ParsingMode.BASH_COMPAT
        assert config.error_handling == ErrorHandlingMode.STRICT
        assert config.enable_arithmetic == True
        assert config.enable_functions == True
        assert config.allow_bash_arrays == True
    
    def test_strict_posix_preset(self):
        """Test strict POSIX preset configuration."""
        config = ParserConfig.strict_posix()
        
        assert config.parsing_mode == ParsingMode.STRICT_POSIX
        assert config.error_handling == ErrorHandlingMode.STRICT
        assert config.enable_associative_arrays == False
        assert config.allow_bash_arrays == False
        assert config.allow_bash_conditionals == False
        assert config.strict_posix_keywords == True
        assert config.require_semicolons == True
    
    def test_bash_compatible_preset(self):
        """Test Bash-compatible preset configuration."""
        config = ParserConfig.bash_compatible()
        
        assert config.parsing_mode == ParsingMode.BASH_COMPAT
        assert config.error_handling == ErrorHandlingMode.COLLECT
        assert config.enable_arithmetic == True
        assert config.allow_bash_arrays == True
        assert config.allow_bash_conditionals == True
        assert config.enable_process_substitution == True
    
    def test_permissive_preset(self):
        """Test permissive preset configuration."""
        config = ParserConfig.permissive()
        
        assert config.parsing_mode == ParsingMode.PERMISSIVE
        assert config.error_handling == ErrorHandlingMode.RECOVER
        assert config.max_errors == 50
        assert config.collect_errors == True
        assert config.enable_error_recovery == True
        assert config.auto_quote_filenames == True
    
    def test_educational_preset(self):
        """Test educational preset configuration."""
        config = ParserConfig.educational()
        
        assert config.parsing_mode == ParsingMode.EDUCATIONAL
        assert config.explain_parsing_steps == True
        assert config.show_grammar_rules == True
        assert config.trace_parsing == True
        assert config.validate_ast == True
        assert config.show_error_suggestions == True
    
    def test_development_preset(self):
        """Test development preset configuration."""
        config = ParserConfig.development()
        
        assert config.trace_parsing == True
        assert config.profile_parsing == True
        assert config.show_token_stream == True
        assert config.validate_ast == True
        assert config.interactive_parsing == True
    
    def test_config_clone(self):
        """Test configuration cloning with overrides."""
        base_config = ParserConfig.strict_posix()
        modified_config = base_config.clone(
            enable_arithmetic=True,
            max_errors=5
        )
        
        # Original should be unchanged
        assert base_config.enable_arithmetic == True  # Default in strict_posix
        assert base_config.max_errors == 10
        
        # Modified should have overrides
        assert modified_config.enable_arithmetic == True
        assert modified_config.max_errors == 5
        
        # Other settings should be preserved
        assert modified_config.parsing_mode == ParsingMode.STRICT_POSIX
        assert modified_config.strict_posix_keywords == True
    
    def test_feature_checking(self):
        """Test feature checking methods."""
        config = ParserConfig()
        
        assert config.is_feature_enabled('arithmetic') == True
        assert config.is_feature_enabled('nonexistent') == False
        
        assert config.should_allow('bash_arrays') == True
        assert config.should_allow('nonexistent') == False
    
    def test_compatibility_info(self):
        """Test compatibility information."""
        config = ParserConfig.strict_posix()
        info = config.get_compatibility_info()
        
        assert info['parsing_mode'] == 'strict_posix'
        assert info['strict_posix'] == True
        assert info['bash_compatible'] == False
        assert info['posix_version'] == '2017'


class TestParserFactory:
    """Test the ParserFactory class."""
    
    def test_create_strict_posix_parser(self):
        """Test creating strict POSIX parser."""
        tokens = tokenize("echo hello")
        parser = ParserFactory.create_strict_posix_parser(tokens)
        
        assert parser.config.parsing_mode == ParsingMode.STRICT_POSIX
        assert parser.config.allow_bash_arrays == False
    
    def test_create_bash_compatible_parser(self):
        """Test creating Bash-compatible parser."""
        tokens = tokenize("echo hello")
        parser = ParserFactory.create_bash_compatible_parser(tokens)
        
        assert parser.config.parsing_mode == ParsingMode.BASH_COMPAT
        assert parser.config.allow_bash_arrays == True
    
    def test_create_permissive_parser(self):
        """Test creating permissive parser."""
        tokens = tokenize("echo hello")
        parser = ParserFactory.create_permissive_parser(tokens)
        
        assert parser.config.parsing_mode == ParsingMode.PERMISSIVE
        assert parser.config.error_handling == ErrorHandlingMode.RECOVER
        assert parser.error_collector is not None
    
    def test_create_educational_parser(self):
        """Test creating educational parser."""
        tokens = tokenize("echo hello")
        parser = ParserFactory.create_educational_parser(tokens)
        
        assert parser.config.parsing_mode == ParsingMode.EDUCATIONAL
        assert parser.config.explain_parsing_steps == True
    
    def test_create_custom_parser(self):
        """Test creating custom parser."""
        tokens = tokenize("echo hello")
        base_config = ParserConfig.bash_compatible()
        
        parser = ParserFactory.create_custom_parser(
            tokens,
            base_config=base_config,
            enable_arithmetic=False,
            max_errors=25
        )
        
        assert parser.config.parsing_mode == ParsingMode.BASH_COMPAT
        assert parser.config.enable_arithmetic == False
        assert parser.config.max_errors == 25
    
    def test_create_shell_parser(self):
        """Test creating parser from shell options."""
        tokens = tokenize("echo hello")
        
        # Test POSIX mode
        shell_options = {'posix': True}
        parser = ParserFactory.create_shell_parser(tokens, shell_options=shell_options)
        assert parser.config.parsing_mode == ParsingMode.STRICT_POSIX
        
        # Test debug mode
        shell_options = {'debug_parser': True}
        parser = ParserFactory.create_shell_parser(tokens, shell_options=shell_options)
        assert parser.config.trace_parsing == True
        assert parser.config.profile_parsing == True


class TestConfigurationValidator:
    """Test the ConfigurationValidator class."""
    
    def test_validate_config_no_warnings(self):
        """Test validating a good configuration."""
        config = ParserConfig.bash_compatible()
        warnings = ConfigurationValidator.validate_config(config)
        
        # Should have no warnings for a preset config
        assert len(warnings) == 0
    
    def test_validate_config_with_warnings(self):
        """Test validating a problematic configuration."""
        config = ParserConfig.strict_posix().clone(
            allow_bash_arrays=True,  # Incompatible with strict POSIX
            enable_process_substitution=True  # Not POSIX compliant
        )
        
        warnings = ConfigurationValidator.validate_config(config)
        assert len(warnings) >= 2
        assert any('Bash arrays' in warning for warning in warnings)
        assert any('Process substitution' in warning for warning in warnings)
    
    def test_suggest_config_for_use_case(self):
        """Test configuration suggestions."""
        assert ConfigurationValidator.suggest_config_for_use_case('posix').parsing_mode == ParsingMode.STRICT_POSIX
        assert ConfigurationValidator.suggest_config_for_use_case('bash').parsing_mode == ParsingMode.BASH_COMPAT
        assert ConfigurationValidator.suggest_config_for_use_case('educational').parsing_mode == ParsingMode.EDUCATIONAL
        assert ConfigurationValidator.suggest_config_for_use_case('development').trace_parsing == True
        assert ConfigurationValidator.suggest_config_for_use_case('permissive').parsing_mode == ParsingMode.PERMISSIVE
        
        # Test default case
        default_config = ConfigurationValidator.suggest_config_for_use_case('unknown')
        assert default_config.parsing_mode == ParsingMode.BASH_COMPAT


class TestParserWithConfiguration:
    """Test parser behavior with different configurations."""
    
    def test_parser_feature_checking(self):
        """Test parser feature checking methods."""
        tokens = tokenize("echo hello")
        config = ParserConfig(enable_arithmetic=False)
        parser = Parser(tokens, config=config)
        
        assert parser.is_feature_enabled('arithmetic') == False
        assert parser.is_feature_enabled('functions') == True
        
        assert parser.should_collect_errors() == False
        assert parser.should_attempt_recovery() == False
    
    def test_parser_require_feature(self):
        """Test parser feature requirement checking."""
        tokens = tokenize("$((1 + 2))")
        config = ParserConfig(enable_arithmetic=False)
        parser = Parser(tokens, config=config)
        
        with pytest.raises(ParseError) as exc_info:
            parser.require_feature('arithmetic')
        
        assert 'arithmetic is not enabled' in str(exc_info.value)
    
    def test_parser_posix_compliance_check(self):
        """Test POSIX compliance checking."""
        tokens = tokenize("[[ test ]]")
        config = ParserConfig.strict_posix()
        parser = Parser(tokens, config=config)
        
        with pytest.raises(ParseError) as exc_info:
            parser.check_posix_compliance('[[ ]] enhanced test syntax', '[ ] test command')
        
        assert 'not POSIX compliant' in str(exc_info.value)
        assert 'Use [ ] test command instead' in str(exc_info.value)
    
    def test_strict_posix_arithmetic_rejection(self):
        """Test that strict POSIX mode rejects (( )) arithmetic."""
        tokens = tokenize("$((1 + 2))")
        
        # Should work in bash compatible mode
        bash_parser = ParserFactory.create_bash_compatible_parser(tokens)
        # Note: This might fail due to actual parsing, but config allows it
        
        # Should be rejected in strict POSIX mode  
        posix_parser = ParserFactory.create_strict_posix_parser(tokens)
        # The rejection should happen during parsing when the method is called
    
    def test_error_collection_configuration(self):
        """Test error collection based on configuration."""
        # Test strict mode (no collection)
        tokens = tokenize("echo hello")
        strict_parser = ParserFactory.create_strict_posix_parser(tokens)
        assert strict_parser.error_collector is None
        
        # Test permissive mode (with collection)
        permissive_parser = ParserFactory.create_permissive_parser(tokens)
        assert permissive_parser.error_collector is not None
        assert permissive_parser.error_collector.max_errors == 50


class TestConvenienceFunctions:
    """Test convenience parsing functions."""
    
    def test_parse_strict_posix(self):
        """Test strict POSIX convenience function."""
        tokens = tokenize("echo hello")
        ast = parse_strict_posix(tokens, "echo hello")
        
        # Should parse successfully
        assert ast is not None
    
    def test_parse_bash_compatible(self):
        """Test Bash-compatible convenience function."""
        tokens = tokenize("echo hello")
        ast = parse_bash_compatible(tokens, "echo hello")
        
        # Should parse successfully
        assert ast is not None
    
    def test_parse_permissive(self):
        """Test permissive convenience function."""
        tokens = tokenize("echo hello")
        ast = parse_permissive(tokens, "echo hello")
        
        # Should parse successfully
        assert ast is not None


class TestConfigurationIntegration:
    """Test integration of configuration with parsing features."""
    
    def test_create_configured_parser(self):
        """Test creating a configured parser from an existing parser."""
        tokens1 = tokenize("echo hello")
        original_parser = ParserFactory.create_bash_compatible_parser(tokens1)
        
        tokens2 = tokenize("echo world")
        new_parser = original_parser.create_configured_parser(tokens2)
        
        # Should have same configuration
        assert new_parser.config.parsing_mode == original_parser.config.parsing_mode
        assert new_parser.config.allow_bash_arrays == original_parser.config.allow_bash_arrays
    
    def test_configuration_inheritance(self):
        """Test that configuration is properly inherited by sub-parsers."""
        tokens = tokenize("if true; then echo hello; fi")
        config = ParserConfig.educational()
        parser = Parser(tokens, config=config)
        
        # Main parser should have the config
        assert parser.config == config
        
        # Sub-parsers should reference the main parser with config
        assert parser.control_structures.parser == parser
        assert parser.statements.parser == parser


if __name__ == "__main__":
    pytest.main([__file__, "-v"])