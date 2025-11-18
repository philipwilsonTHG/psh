# Enhanced Parser Integration Plan

## Current Status

✅ **Completed**: Enhanced lexer infrastructure with compatibility layer working  
✅ **Completed**: Enhanced lexer can feed existing parser via `extract_legacy_tokens()`  
⏳ **In Progress**: Basic enhanced parser components created but not fully integrated  
❌ **Missing**: Full parser integration to utilize enhanced token metadata  

## Goal

Complete the parser integration to fully utilize enhanced tokens and their rich metadata, while maintaining backward compatibility and enabling gradual migration.

## Phase 4.2 Completion: Enhanced Parser Integration

### Week 1: Enhanced Parser Foundation

#### Day 1-2: Complete Enhanced Parser Base

**File**: `psh/parser/enhanced_base.py`

1. **Enhance the existing EnhancedContextBaseParser**
```python
class EnhancedContextBaseParser(ContextBaseParser):
    """Enhanced base parser that fully utilizes enhanced tokens."""
    
    def __init__(self, ctx: ParserContext, enhanced_config: EnhancedParserConfig = None):
        super().__init__(ctx)
        self.enhanced_config = enhanced_config or EnhancedParserConfig()
        self.contract_adapter = ContractAdapter()
        
        # Enhanced parsing features
        self.context_validator = ContextValidator() if enhanced_config.enable_context_validation else None
        self.semantic_analyzer = SemanticAnalyzer() if enhanced_config.enable_semantic_analysis else None
        
        # Error context from lexer
        self.lexer_errors: List[LexerError] = []
        self.lexer_warnings: List[LexerError] = []
    
    def expect_assignment(self, message: Optional[str] = None) -> EnhancedToken:
        """Expect an assignment token with metadata."""
        token = self.peek_enhanced()
        
        if not token or not token.is_assignment:
            raise self._error(message or f"Expected assignment, found {token.type if token else 'EOF'}")
        
        # Extract assignment metadata
        if hasattr(token, 'assignment_info'):
            self.ctx.current_assignment = token.assignment_info
        
        return self.advance()
    
    def expect_in_context(self, token_type: TokenType, expected_context: TokenContext, 
                         message: Optional[str] = None) -> EnhancedToken:
        """Expect token in specific context with validation."""
        token = self.peek_enhanced()
        
        if not token or token.type != token_type:
            raise self._error(message or f"Expected {token_type}, found {token.type if token else 'EOF'}")
        
        if self.enhanced_config.enable_context_validation:
            if expected_context not in token.metadata.contexts:
                contexts_str = ', '.join(c.value for c in token.metadata.contexts)
                raise self._error(f"Expected {token_type} in {expected_context.value} context, "
                                f"found in {contexts_str} context")
        
        return self.advance()
    
    def validate_semantic_type(self, token: EnhancedToken, expected_type: SemanticType) -> bool:
        """Validate token semantic type."""
        if not self.enhanced_config.enable_semantic_validation:
            return True
        
        return token.metadata.semantic_type == expected_type
    
    def get_enhanced_error_context(self, error_position: int) -> Dict[str, Any]:
        """Get enhanced error context using token metadata."""
        context = super().get_error_context(error_position) if hasattr(super(), 'get_error_context') else {}
        
        # Add enhanced context from surrounding tokens
        for i, token in enumerate(self.ctx.tokens):
            if isinstance(token, EnhancedToken) and abs(token.position - error_position) <= 20:
                context.setdefault('enhanced_tokens', []).append({
                    'value': token.value,
                    'semantic_type': token.metadata.semantic_type.value if token.metadata.semantic_type else None,
                    'contexts': [c.value for c in token.metadata.contexts],
                    'distance': abs(token.position - error_position)
                })
        
        # Add lexer errors near this position
        nearby_lexer_errors = [
            error for error in self.lexer_errors 
            if hasattr(error, 'position') and abs(error.position - error_position) <= 10
        ]
        if nearby_lexer_errors:
            context['related_lexer_errors'] = [
                {'message': error.message, 'suggestion': error.suggestion} 
                for error in nearby_lexer_errors
            ]
        
        return context
```

2. **Add Context Validator**
```python
class ContextValidator:
    """Validates token contexts during parsing."""
    
    def validate_command_sequence(self, tokens: List[EnhancedToken]) -> List[ValidationIssue]:
        """Validate command sequence contexts."""
        issues = []
        
        for i, token in enumerate(tokens):
            # Check command position tokens
            if TokenContext.COMMAND_POSITION in token.metadata.contexts:
                # Should be a command, builtin, or function
                if not (token.is_keyword or token.metadata.semantic_type in 
                       {SemanticType.BUILTIN, SemanticType.KEYWORD}):
                    # Check if it's a known command
                    if not self._is_known_command(token.value):
                        issues.append(ValidationIssue(
                            type="unknown_command",
                            message=f"Unknown command: {token.value}",
                            suggestion="Check spelling or add to PATH",
                            position=token.position
                        ))
        
        return issues
    
    def validate_assignment_context(self, token: EnhancedToken) -> Optional[ValidationIssue]:
        """Validate assignment in proper context."""
        if token.is_assignment:
            # Assignments should be in command position or after export/declare/local
            if TokenContext.COMMAND_POSITION not in token.metadata.contexts:
                return ValidationIssue(
                    type="assignment_position",
                    message="Assignment not in command position",
                    suggestion="Move assignment to beginning of command or use export/declare",
                    position=token.position
                )
        return None
```

3. **Add Semantic Analyzer**
```python
class SemanticAnalyzer:
    """Analyzes semantic meaning of enhanced tokens."""
    
    def analyze_variable_usage(self, tokens: List[EnhancedToken]) -> List[SemanticIssue]:
        """Analyze variable assignments and usage."""
        issues = []
        assigned_vars = set()
        
        for token in tokens:
            # Track assignments
            if token.is_assignment and hasattr(token, 'assignment_info'):
                var_name = token.assignment_info.get('variable')
                if var_name:
                    assigned_vars.add(var_name)
            
            # Check variable expansions
            elif token.type in {TokenType.VARIABLE, TokenType.ARITH_EXPANSION}:
                # Extract variable name from $VAR or ${VAR}
                var_name = self._extract_variable_name(token.value)
                if var_name and var_name not in assigned_vars:
                    # Check if it's a special variable or environment variable
                    if not self._is_special_or_env_variable(var_name):
                        issues.append(SemanticIssue(
                            type="undefined_variable",
                            message=f"Variable '{var_name}' used before assignment",
                            suggestion=f"Initialize {var_name} before use or check spelling",
                            position=token.position
                        ))
        
        return issues
    
    def analyze_command_structure(self, ast_node, tokens: List[EnhancedToken]) -> List[SemanticIssue]:
        """Analyze command structure using both AST and enhanced tokens."""
        issues = []
        
        # Find potential issues with command structure
        # e.g., redirections in wrong places, pipe to commands that don't read stdin
        
        return issues
```

#### Day 3-4: Enhanced Command Parsing

**File**: `psh/parser/enhanced_commands.py`

1. **Enhanced Simple Command Parser**
```python
class EnhancedSimpleCommandParser(EnhancedContextBaseParser):
    """Enhanced parser for simple commands using token metadata."""
    
    def parse_simple_command(self) -> SimpleCommand:
        """Parse simple command with enhanced features."""
        args = []
        redirects = []
        assignments = []
        
        # Parse leading assignments using enhanced detection
        while self.peek_enhanced() and self.peek_enhanced().is_assignment:
            assignment_token = self.expect_assignment()
            assignments.append(self._parse_assignment_from_token(assignment_token))
        
        # Parse command name
        if not self.match(TokenType.WORD, TokenType.STRING):
            if assignments:
                # Assignment-only command
                return SimpleCommand(
                    args=[],
                    redirects=redirects,
                    assignments=assignments
                )
            else:
                raise self._error("Expected command name")
        
        command_token = self.advance()
        
        # Validate command using semantic information
        if self.enhanced_config.enable_semantic_validation:
            self._validate_command_semantics(command_token)
        
        args.append(command_token.value)
        
        # Parse arguments and redirections
        while not self.at_end() and self._can_continue_command():
            if self.peek().type in self._redirection_types():
                redirect = self._parse_redirection_enhanced()
                redirects.append(redirect)
            else:
                arg_token = self.advance()
                args.append(arg_token.value)
        
        return SimpleCommand(
            args=args,
            redirects=redirects,
            assignments=assignments,
            enhanced_metadata=self._extract_command_metadata()
        )
    
    def _parse_assignment_from_token(self, token: EnhancedToken) -> Assignment:
        """Parse assignment from enhanced token with metadata."""
        if not hasattr(token, 'assignment_info'):
            # Fallback to basic parsing
            return self._parse_assignment_basic(token)
        
        info = token.assignment_info
        
        return Assignment(
            variable=info['variable'],
            value=info['value'],
            assignment_type=info.get('type', 'simple'),
            index=info.get('index'),  # For array assignments
            operator=info.get('operator', '='),  # For compound assignments
            position=token.position
        )
    
    def _validate_command_semantics(self, command_token: EnhancedToken):
        """Validate command using semantic information."""
        if command_token.metadata.semantic_type == SemanticType.BUILTIN:
            # Known builtin - no validation needed
            return
        
        # Check if command is in PATH or is a function
        if not self._is_executable_command(command_token.value):
            self.ctx.add_warning(f"Command '{command_token.value}' not found in PATH")
    
    def _extract_command_metadata(self) -> Dict[str, Any]:
        """Extract metadata for command from enhanced tokens."""
        return {
            'has_assignments': bool([t for t in self.ctx.tokens if t.is_assignment]),
            'has_redirections': bool([t for t in self.ctx.tokens if t.is_redirect]),
            'complexity_score': self._calculate_complexity(),
            'semantic_types': [t.metadata.semantic_type.value for t in self.ctx.tokens 
                             if isinstance(t, EnhancedToken) and t.metadata.semantic_type]
        }
```

2. **Enhanced Test Expression Parser**
```python
class EnhancedTestParser(EnhancedContextBaseParser):
    """Enhanced parser for test expressions using context information."""
    
    def parse_test_expression(self) -> TestExpression:
        """Parse test expression using enhanced context validation."""
        # Expect opening [[ with test context
        self.expect_in_context(TokenType.DOUBLE_LBRACKET, TokenContext.TEST_EXPRESSION)
        
        expr = self._parse_test_or_expression()
        
        # Expect closing ]] with test context
        self.expect_in_context(TokenType.DOUBLE_RBRACKET, TokenContext.TEST_EXPRESSION)
        
        return TestExpression(expression=expr)
    
    def _parse_test_comparison(self) -> ComparisonExpression:
        """Parse comparison with context-aware operator recognition."""
        left = self._parse_test_primary()
        
        # Check for comparison operators in test context
        op_token = self.peek_enhanced()
        if op_token and self._is_test_comparison_operator(op_token):
            # Use context-specific token types for better error messages
            if op_token.type == TokenType.LESS_THAN_TEST:
                op = self.advance()
                right = self._parse_test_primary()
                return ComparisonExpression(left, '<', right)
            # ... handle other test operators
        
        return left
    
    def _is_test_comparison_operator(self, token: EnhancedToken) -> bool:
        """Check if token is a comparison operator in test context."""
        if TokenContext.TEST_EXPRESSION not in token.metadata.contexts:
            return False
        
        return token.type in {
            TokenType.LESS_THAN_TEST, TokenType.GREATER_THAN_TEST,
            TokenType.LESS_EQUAL_TEST, TokenType.GREATER_EQUAL_TEST,
            TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.REGEX_MATCH
        }
```

#### Day 5-7: Integration with Existing Parser Components

**File**: `psh/parser/enhanced_factory.py`

1. **Enhanced Parser Factory**
```python
class EnhancedParserFactory:
    """Factory for creating enhanced parsers."""
    
    @staticmethod
    def create_from_lexer_contract(
        contract: LexerParserContract,
        config: Optional[EnhancedParserConfig] = None
    ) -> EnhancedContextBaseParser:
        """Create enhanced parser from lexer contract."""
        enhanced_config = config or EnhancedParserConfig()
        
        # Create parser context with enhanced tokens
        ctx = ParserContextFactory.create_enhanced(
            tokens=contract.tokens,
            config=enhanced_config,
            lexer_validation=contract.validation_result
        )
        
        # Create appropriate parser based on configuration
        if enhanced_config.full_enhancement:
            return FullyEnhancedParser(ctx, enhanced_config)
        else:
            return EnhancedContextBaseParser(ctx, enhanced_config)
    
    @staticmethod
    def create_compatible_parser(
        tokens: List[Token],
        config: Optional[ParserConfig] = None,
        enhanced_features: bool = True
    ) -> Union[Parser, EnhancedContextBaseParser]:
        """Create parser with optional enhancement."""
        if enhanced_features and all(isinstance(t, EnhancedToken) for t in tokens):
            # Use enhanced parser
            enhanced_config = EnhancedParserConfig.from_parser_config(config)
            ctx = ParserContextFactory.create_enhanced(tokens, enhanced_config)
            return EnhancedContextBaseParser(ctx, enhanced_config)
        else:
            # Use standard parser
            return Parser(tokens, config)
    
    @staticmethod
    def migrate_existing_parser(
        parser: Parser,
        enable_enhancements: bool = True
    ) -> Union[Parser, EnhancedContextBaseParser]:
        """Migrate existing parser to enhanced version."""
        if not enable_enhancements:
            return parser
        
        # Convert tokens to enhanced tokens if needed
        enhanced_tokens = []
        for token in parser.tokens:
            if isinstance(token, EnhancedToken):
                enhanced_tokens.append(token)
            else:
                enhanced_tokens.append(EnhancedToken.from_token(token))
        
        # Create enhanced parser
        enhanced_config = EnhancedParserConfig()
        ctx = ParserContextFactory.create_enhanced(enhanced_tokens, enhanced_config)
        return EnhancedContextBaseParser(ctx, enhanced_config)
```

2. **Enhanced Parser Context Factory**
```python
class EnhancedParserContextFactory:
    """Factory for creating enhanced parser contexts."""
    
    @staticmethod
    def create_enhanced(
        tokens: List[EnhancedToken],
        config: EnhancedParserConfig,
        lexer_validation: Optional[TokenStreamValidationResult] = None
    ) -> ParserContext:
        """Create enhanced parser context."""
        # Create base context
        base_config = ParserConfig()
        base_config.__dict__.update({k: v for k, v in config.__dict__.items() 
                                   if hasattr(base_config, k)})
        
        ctx = ParserContext(tokens, base_config)
        
        # Add enhanced features
        ctx.enhanced_config = config
        ctx.lexer_validation = lexer_validation
        
        # Add enhanced error handling
        if lexer_validation:
            for error in lexer_validation.errors:
                ctx.add_lexer_error(error)
            for warning in lexer_validation.warnings:
                ctx.add_warning(warning)
        
        # Add enhanced token utilities
        ctx.peek_enhanced = lambda offset=0: ctx.peek(offset) if isinstance(ctx.peek(offset), EnhancedToken) else None
        ctx.current_enhanced = lambda: ctx.peek_enhanced(0)
        
        return ctx
```

### Week 2: Parser Component Enhancement

#### Day 1-3: Update Existing Parser Components

**Files to Update**:
- `psh/parser/commands.py` - Add enhanced command parsing
- `psh/parser/control_structures.py` - Add enhanced control flow parsing  
- `psh/parser/statements.py` - Add enhanced statement parsing

**Example Enhancement** (`psh/parser/commands.py`):
```python
# Add to existing CommandParser class
class CommandParser(BaseParser):
    
    def parse_simple_command_enhanced(self) -> SimpleCommand:
        """Enhanced version of simple command parsing."""
        if isinstance(self, EnhancedContextBaseParser):
            return self._parse_simple_command_with_metadata()
        else:
            return self.parse_simple_command()  # Fallback to existing
    
    def _parse_simple_command_with_metadata(self) -> SimpleCommand:
        """Parse simple command using enhanced token metadata."""
        # Use enhanced assignment detection
        assignments = []
        while self.peek_enhanced() and self.peek_enhanced().is_assignment:
            assignment_token = self.advance()
            assignments.append(self._extract_assignment_from_metadata(assignment_token))
        
        # Rest of parsing with enhanced features...
        return super().parse_simple_command()  # Use existing logic but with enhancements
```

#### Day 4-5: Enhanced Error Recovery

**File**: `psh/parser/enhanced_error_recovery.py`

```python
class EnhancedErrorRecovery:
    """Enhanced error recovery using lexer validation results."""
    
    def __init__(self, parser: EnhancedContextBaseParser):
        self.parser = parser
        self.lexer_errors = parser.lexer_errors
        self.recovery_strategies = [
            self._recover_from_lexer_errors,
            self._recover_using_token_contexts,
            self._recover_using_semantic_types,
            self._fallback_recovery
        ]
    
    def attempt_recovery(self, parse_error: ParseError) -> Optional[Any]:
        """Attempt to recover from parse error using enhanced information."""
        for strategy in self.recovery_strategies:
            result = strategy(parse_error)
            if result:
                return result
        return None
    
    def _recover_from_lexer_errors(self, parse_error: ParseError) -> Optional[Any]:
        """Try to recover using lexer error information."""
        # If lexer detected unclosed quotes/brackets, suggest fixes
        for lexer_error in self.lexer_errors:
            if lexer_error.error_type == 'UNCLOSED_QUOTE':
                return self._recover_unclosed_quote(lexer_error)
            elif lexer_error.error_type == 'UNCLOSED_EXPANSION':
                return self._recover_unclosed_expansion(lexer_error)
        
        return None
    
    def _recover_using_token_contexts(self, parse_error: ParseError) -> Optional[Any]:
        """Use token context information for recovery."""
        current_token = self.parser.peek_enhanced()
        if current_token and current_token.metadata.contexts:
            # Use context to determine what token should be here
            contexts = current_token.metadata.contexts
            if TokenContext.TEST_EXPRESSION in contexts:
                return self._recover_in_test_context(current_token)
        
        return None
```

#### Day 6-7: Integration Testing and Validation

**File**: `psh/parser/enhanced_integration_tests.py`

```python
class EnhancedParserIntegrationTests:
    """Comprehensive tests for enhanced parser integration."""
    
    def test_assignment_parsing_with_metadata(self):
        """Test that assignment metadata is properly used."""
        from psh.lexer.enhanced_integration import enhanced_tokenize
        from psh.parser.enhanced_integration import create_enhanced_parser
        
        command = "VAR=value arr[0]=element COUNT+=1 echo $VAR"
        
        # Get enhanced contract
        contract = enhanced_tokenize(command)
        
        # Parse with enhanced parser
        parser = create_enhanced_parser(contract)
        ast = parser.parse()
        
        # Validate that assignments were properly parsed using metadata
        simple_cmd = self._extract_simple_command(ast)
        assert len(simple_cmd.assignments) == 3
        
        # Check metadata was used
        var_assignment = simple_cmd.assignments[0]
        assert var_assignment.variable == "VAR"
        assert var_assignment.value == "value"
        assert var_assignment.assignment_type == "simple"
    
    def test_context_aware_parsing(self):
        """Test context-aware parsing features."""
        command = "if [[ $VAR -gt 5 ]]; then echo big; fi"
        
        contract = enhanced_tokenize(command)
        parser = create_enhanced_parser(contract, 
                                       config=EnhancedParserConfig(enable_context_validation=True))
        
        ast = parser.parse()
        
        # Should parse successfully with context validation
        assert ast is not None
        
        # Check that test context was properly recognized
        # (Implementation specific validation)
    
    def test_semantic_analysis_integration(self):
        """Test semantic analysis during parsing."""
        command = "echo $UNDEFINED_VAR"  # Variable used before definition
        
        contract = enhanced_tokenize(command)
        parser = create_enhanced_parser(contract,
                                       config=EnhancedParserConfig(enable_semantic_analysis=True))
        
        ast = parser.parse()
        
        # Should have warnings about undefined variable
        warnings = parser.get_semantic_warnings()
        assert any("undefined" in warning.lower() for warning in warnings)
```

### Week 3: Complete Integration and Migration

#### Day 1-3: Update Main Parser Entry Points

**File**: `psh/parser/__init__.py`

```python
# Add enhanced parsing functions
def parse_enhanced(
    tokens_or_contract: Union[List[Token], LexerParserContract],
    config: Optional[EnhancedParserConfig] = None
) -> Any:
    """Parse using enhanced parser with full metadata support."""
    from .enhanced_integration import create_enhanced_parser
    
    parser = create_enhanced_parser(tokens_or_contract, config)
    return parser.parse()

def parse_with_lexer_integration(
    input_string: str,
    lexer_config: Optional[Any] = None,
    parser_config: Optional[EnhancedParserConfig] = None
) -> Any:
    """Complete enhanced lexer-parser pipeline."""
    from ..lexer.enhanced_integration import enhanced_tokenize
    
    # Enhanced tokenization
    contract = enhanced_tokenize(input_string, enable_enhancements=True)
    
    # Enhanced parsing
    return parse_enhanced(contract, parser_config)

# Maintain backward compatibility
def parse(tokens, config=None):
    """Parse tokens into AST (backward compatible)."""
    # Check if we can use enhanced features
    if (isinstance(tokens, LexerParserContract) or 
        (isinstance(tokens, list) and tokens and isinstance(tokens[0], EnhancedToken))):
        
        # Try enhanced parsing with fallback
        try:
            return parse_enhanced(tokens, EnhancedParserConfig.from_parser_config(config))
        except Exception:
            # Fallback to compatibility mode
            if isinstance(tokens, LexerParserContract):
                tokens = extract_legacy_tokens(tokens)
    
    # Use original parser
    return Parser(tokens, config=config).parse()
```

#### Day 4-5: Shell Integration

**File**: `psh/shell_enhanced_parser.py`

```python
class EnhancedShellParser:
    """Enhanced parser integration for shell."""
    
    def __init__(self, shell):
        self.shell = shell
        self.enhanced_enabled = self._should_enable_enhanced_parser()
        self.parser_config = self._create_parser_config()
    
    def parse_command(self, command_string: str) -> Any:
        """Parse command using enhanced lexer-parser pipeline."""
        if not self.enhanced_enabled:
            # Fallback to existing parsing
            from .lexer import tokenize
            from .parser import parse
            tokens = tokenize(command_string)
            return parse(tokens)
        
        # Use enhanced pipeline
        from .parser import parse_with_lexer_integration
        return parse_with_lexer_integration(
            command_string,
            parser_config=self.parser_config
        )
    
    def _should_enable_enhanced_parser(self) -> bool:
        """Determine if enhanced parser should be enabled."""
        # Check environment and shell options
        return (
            hasattr(self.shell, 'lexer_manager') and 
            self.shell.lexer_manager.enhanced_lexer_enabled and
            self.shell.state.options.get('enhanced-parser', True)
        )
    
    def _create_parser_config(self) -> EnhancedParserConfig:
        """Create parser configuration from shell settings."""
        return EnhancedParserConfig(
            use_enhanced_tokens=True,
            enable_context_validation=self.shell.state.options.get('validate-context', False),
            enable_semantic_validation=self.shell.state.options.get('validate-semantics', False),
            strict_contract_validation=self.shell.state.options.get('strict-parsing', False)
        )

# Integration function
def install_enhanced_parser_integration(shell):
    """Install enhanced parser integration into shell."""
    shell.enhanced_parser = EnhancedShellParser(shell)
    
    # Add shell option
    shell.state.options['enhanced-parser'] = True
    
    # Override parse method if enhanced lexer is available
    if hasattr(shell, 'lexer_manager') and shell.lexer_manager.enhanced_lexer_enabled:
        original_parse = getattr(shell, '_parse_command', None)
        
        def enhanced_parse_command(command_string: str):
            if shell.state.options.get('enhanced-parser', True):
                return shell.enhanced_parser.parse_command(command_string)
            elif original_parse:
                return original_parse(command_string)
            else:
                # Fallback
                from .lexer import tokenize
                from .parser import parse
                tokens = tokenize(command_string)
                return parse(tokens)
        
        shell._parse_command = enhanced_parse_command
```

#### Day 6-7: Final Integration and Testing

**File**: `psh/enhanced_shell_integration.py`

```python
def create_fully_enhanced_shell(*args, **kwargs):
    """Create shell with full enhanced lexer-parser integration."""
    from .shell import Shell
    from .shell_enhanced_lexer import install_enhanced_lexer_integration
    from .shell_enhanced_parser import install_enhanced_parser_integration
    
    # Create shell
    shell = Shell(*args, **kwargs)
    
    # Install enhanced lexer
    install_enhanced_lexer_integration(shell)
    
    # Install enhanced parser
    install_enhanced_parser_integration(shell)
    
    return shell

def enable_enhanced_features(shell, profile: str = "standard"):
    """Enable enhanced features on existing shell."""
    from .lexer.feature_flags import apply_feature_profile
    
    # Apply feature profile
    apply_feature_profile(profile)
    
    # Install integrations if not present
    if not hasattr(shell, 'lexer_manager'):
        install_enhanced_lexer_integration(shell)
    
    if not hasattr(shell, 'enhanced_parser'):
        install_enhanced_parser_integration(shell)
    
    # Enable enhanced parsing
    shell.state.options['enhanced-parser'] = True
    shell.state.options['validate-context'] = profile in ['full', 'development']
    shell.state.options['validate-semantics'] = profile in ['full', 'development']
```

## Implementation Timeline

### Week 1: Enhanced Parser Foundation (7 days)
- **Day 1-2**: Complete EnhancedContextBaseParser with metadata utilization
- **Day 3-4**: Implement enhanced command parsing with assignment metadata
- **Day 5-7**: Integration with existing parser components

### Week 2: Parser Component Enhancement (7 days)  
- **Day 1-3**: Update existing parser components for enhanced features
- **Day 4-5**: Implement enhanced error recovery using lexer information
- **Day 6-7**: Comprehensive integration testing

### Week 3: Complete Integration (7 days)
- **Day 1-3**: Update main parser entry points with enhanced support
- **Day 4-5**: Shell integration for enhanced parsing
- **Day 6-7**: Final integration testing and validation

**Total Duration**: 3 weeks

## Success Metrics

1. **Enhanced Features Working**: Assignment metadata, context validation, semantic analysis
2. **Performance**: Enhanced parser adds <50% overhead vs compatibility mode  
3. **Backward Compatibility**: 100% of existing tests pass
4. **Error Improvement**: 50% better error messages using lexer+parser information
5. **Integration**: Seamless shell integration with feature flags

## Risk Mitigation

1. **Complexity Management**: Implement incrementally with feature flags
2. **Performance**: Always maintain compatibility mode fallback
3. **Testing**: Comprehensive test suite for each integration point
4. **Rollback**: Enhanced features can be disabled individually

This plan completes the parser integration to fully utilize the enhanced lexer infrastructure while maintaining all compatibility guarantees.