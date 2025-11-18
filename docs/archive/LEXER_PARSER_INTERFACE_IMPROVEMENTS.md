# Lexer-Parser Interface Improvements: Implementation Plan

## Overview

This document outlines a comprehensive plan to improve the interface between the lexer and parser in PSH. The improvements focus on moving syntax validation earlier in the pipeline, adding context-aware tokenization, and creating a more robust contract between the two components.

## Goals

1. **Simplify Parser Logic**: Move syntax validation and token classification to the lexer phase
2. **Improve Error Messages**: Detect and report errors earlier with better context
3. **Enhance Token Information**: Preserve semantic information through the pipeline
4. **Maintain Compatibility**: Ensure backward compatibility with existing code
5. **Create Clear Contracts**: Define formal interfaces between components

## Phase 1: Enhanced Token Infrastructure (2 weeks)

### 1.1 Extended Token Types (Week 1)

#### Implementation Steps:

1. **Add Missing Token Types** (`token_types.py`)
```python
# Assignment operators
ASSIGN = auto()              # =
PLUS_ASSIGN = auto()         # +=
MINUS_ASSIGN = auto()        # -=
MULT_ASSIGN = auto()         # *=
DIV_ASSIGN = auto()          # /=
MOD_ASSIGN = auto()          # %=
AND_ASSIGN = auto()          # &=
OR_ASSIGN = auto()           # |=
XOR_ASSIGN = auto()          # ^=
LSHIFT_ASSIGN = auto()       # <<=
RSHIFT_ASSIGN = auto()       # >>=

# Pattern matching
GLOB_STAR = auto()           # * in patterns
GLOB_QUESTION = auto()       # ? in patterns
GLOB_BRACKET = auto()        # [...] in patterns

# Context-specific operators
LESS_THAN_TEST = auto()      # < in test context
GREATER_THAN_TEST = auto()   # > in test context
LESS_EQUAL_TEST = auto()     # <= in test context
GREATER_EQUAL_TEST = auto()  # >= in test context

# Special constructs
HERE_DELIMITER = auto()      # Heredoc delimiter
ASSIGNMENT_WORD = auto()     # VAR=value pattern
ARRAY_ASSIGNMENT_WORD = auto() # arr[index]=value pattern
```

2. **Create Enhanced Token Classes** (`token_enhanced.py`)
```python
from dataclasses import dataclass, field
from typing import Set, Optional, List
from enum import Enum

class TokenContext(Enum):
    """Context in which a token appears."""
    COMMAND_POSITION = "command_position"
    ARGUMENT_POSITION = "argument_position"
    TEST_EXPRESSION = "test_expression"
    ARITHMETIC_EXPRESSION = "arithmetic_expression"
    CASE_PATTERN = "case_pattern"
    REDIRECT_TARGET = "redirect_target"
    ASSIGNMENT_RHS = "assignment_rhs"

class SemanticType(Enum):
    """Semantic classification of tokens."""
    KEYWORD = "keyword"
    BUILTIN = "builtin"
    ASSIGNMENT = "assignment"
    OPERATOR = "operator"
    LITERAL = "literal"
    EXPANSION = "expansion"
    PATTERN = "pattern"

@dataclass
class TokenMetadata:
    """Additional metadata for tokens."""
    contexts: Set[TokenContext] = field(default_factory=set)
    semantic_type: Optional[SemanticType] = None
    paired_with: Optional[int] = None  # Index of paired token
    expansion_depth: int = 0
    quote_depth: int = 0
    error_info: Optional['LexerError'] = None

@dataclass
class EnhancedToken(Token):
    """Token with rich metadata."""
    metadata: TokenMetadata = field(default_factory=TokenMetadata)
    parts: List[TokenPart] = field(default_factory=list)
    
    @property
    def is_error(self) -> bool:
        return self.metadata.error_info is not None
    
    @property
    def in_test_context(self) -> bool:
        return TokenContext.TEST_EXPRESSION in self.metadata.contexts
```

3. **Lexer Error Tokens** (`lexer_errors.py`)
```python
@dataclass
class LexerError:
    """Information about lexer-detected errors."""
    error_type: str
    message: str
    expected: Optional[str] = None
    suggestion: Optional[str] = None
    severity: str = "error"  # error, warning, info

class LexerErrorType:
    """Standard lexer error types."""
    UNCLOSED_QUOTE = "unclosed_quote"
    UNCLOSED_EXPANSION = "unclosed_expansion"
    INVALID_ASSIGNMENT = "invalid_assignment"
    UNMATCHED_BRACKET = "unmatched_bracket"
    INVALID_REDIRECT = "invalid_redirect"
    MALFORMED_PATTERN = "malformed_pattern"

def create_error_token(
    position: int,
    value: str,
    error_type: str,
    message: str,
    **kwargs
) -> EnhancedToken:
    """Create a token representing a lexer error."""
    error_info = LexerError(
        error_type=error_type,
        message=message,
        **kwargs
    )
    
    token = EnhancedToken(
        type=TokenType.WORD,  # Fallback type
        value=value,
        position=position,
        end_position=position + len(value)
    )
    token.metadata.error_info = error_info
    
    return token
```

### 1.2 Token Context Tracking (Week 1)

#### Implementation Steps:

1. **Enhanced Lexer Context** (`lexer/enhanced_context.py`)
```python
@dataclass
class EnhancedLexerContext(LexerContext):
    """Lexer context with parser hints."""
    
    # Position tracking
    command_position: bool = True
    after_assignment: bool = False
    expect_pattern: bool = False
    
    # Nesting contexts
    test_expr_depth: int = 0
    arithmetic_depth: int = 0
    case_pattern_depth: int = 0
    
    # Pairing tracking
    bracket_stack: List[Tuple[TokenType, int]] = field(default_factory=list)
    
    def enter_test_expression(self):
        """Enter test expression context."""
        self.test_expr_depth += 1
    
    def exit_test_expression(self):
        """Exit test expression context."""
        self.test_expr_depth = max(0, self.test_expr_depth - 1)
    
    def get_current_contexts(self) -> Set[TokenContext]:
        """Get current token contexts."""
        contexts = set()
        
        if self.command_position:
            contexts.add(TokenContext.COMMAND_POSITION)
        else:
            contexts.add(TokenContext.ARGUMENT_POSITION)
        
        if self.test_expr_depth > 0:
            contexts.add(TokenContext.TEST_EXPRESSION)
        
        if self.arithmetic_depth > 0:
            contexts.add(TokenContext.ARITHMETIC_EXPRESSION)
        
        if self.case_pattern_depth > 0:
            contexts.add(TokenContext.CASE_PATTERN)
        
        return contexts
```

2. **Context-Aware Token Recognition** (`lexer/context_recognizer.py`)
```python
class ContextAwareRecognizer:
    """Base class for context-aware token recognition."""
    
    def recognize_with_context(
        self,
        text: str,
        position: int,
        context: EnhancedLexerContext
    ) -> Optional[EnhancedToken]:
        """Recognize token with context information."""
        # Basic recognition
        token = self.recognize(text, position)
        if not token:
            return None
        
        # Enhance with context
        enhanced = EnhancedToken.from_token(token)
        enhanced.metadata.contexts = context.get_current_contexts()
        
        # Specific enhancements based on token type
        self._enhance_token(enhanced, context)
        
        return enhanced
    
    def _enhance_token(
        self,
        token: EnhancedToken,
        context: EnhancedLexerContext
    ):
        """Add context-specific enhancements."""
        pass
```

### 1.3 Assignment Detection (Week 2)

#### Implementation Steps:

1. **Assignment Recognizer** (`lexer/recognizers/assignment.py`)
```python
import re
from typing import Optional
from .base import TokenRecognizer
from ..context import EnhancedLexerContext

class AssignmentRecognizer(TokenRecognizer):
    """Recognizes assignment patterns."""
    
    # Patterns for different assignment types
    SIMPLE_ASSIGNMENT = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)=')
    ARRAY_ASSIGNMENT = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]=')
    COMPOUND_ASSIGNMENT = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)([+\-*/]?=)')
    
    def can_recognize(self, char: str, context: LexerContext) -> bool:
        """Check if this recognizer can handle the current position."""
        # Only recognize assignments in command position
        if not context.command_position:
            return False
        
        # Look for identifier start
        return char.isalpha() or char == '_'
    
    def recognize(
        self,
        text: str,
        position: int,
        context: LexerContext
    ) -> Optional[Token]:
        """Recognize assignment patterns."""
        remaining = text[position:]
        
        # Try array assignment first (most specific)
        match = self.ARRAY_ASSIGNMENT.match(remaining)
        if match:
            full_match = match.group(0)
            return EnhancedToken(
                type=TokenType.ARRAY_ASSIGNMENT_WORD,
                value=full_match,
                position=position,
                end_position=position + len(full_match),
                metadata=TokenMetadata(
                    semantic_type=SemanticType.ASSIGNMENT
                )
            )
        
        # Try compound assignment
        match = self.COMPOUND_ASSIGNMENT.match(remaining)
        if match:
            full_match = match.group(0)
            var_name = match.group(1)
            operator = match.group(2)
            
            # Determine specific token type
            token_type = {
                '=': TokenType.ASSIGNMENT_WORD,
                '+=': TokenType.PLUS_ASSIGN,
                '-=': TokenType.MINUS_ASSIGN,
                '*=': TokenType.MULT_ASSIGN,
                '/=': TokenType.DIV_ASSIGN,
            }.get(operator, TokenType.ASSIGNMENT_WORD)
            
            return EnhancedToken(
                type=token_type,
                value=full_match,
                position=position,
                end_position=position + len(full_match),
                metadata=TokenMetadata(
                    semantic_type=SemanticType.ASSIGNMENT
                )
            )
        
        return None
```

## Phase 2: Syntax Validation in Lexer (2 weeks)

### 2.1 Expansion Validation (Week 1)

#### Implementation Steps:

1. **Enhanced Expansion Parser** (`lexer/expansion_validator.py`)
```python
from dataclasses import dataclass
from typing import Optional, Tuple, List

@dataclass
class ExpansionValidationResult:
    """Result of expansion validation."""
    is_valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    expected_close: Optional[str] = None
    suggestion: Optional[str] = None

class ExpansionValidator:
    """Validates shell expansions during lexing."""
    
    def validate_parameter_expansion(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate ${...} expansions."""
        if not text[start:].startswith('${'):
            return ExpansionValidationResult(is_valid=False)
        
        # Find closing brace
        depth = 1
        i = start + 2
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        
        if depth != 0:
            # Extract partial expansion for error message
            partial = text[start:min(start + 50, len(text))]
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message=f"Unclosed parameter expansion: {partial}...",
                expected_close='}',
                suggestion="Add closing '}' to complete the expansion"
            )
        
        return ExpansionValidationResult(is_valid=True)
    
    def validate_command_substitution(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate $(...) substitutions."""
        if not text[start:].startswith('$('):
            return ExpansionValidationResult(is_valid=False)
        
        # Find closing paren, handling nested parens
        depth = 1
        i = start + 2
        in_quotes = False
        quote_char = None
        
        while i < len(text) and depth > 0:
            char = text[i]
            
            # Handle quotes
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and text[i-1] != '\\':
                    in_quotes = False
                    quote_char = None
            
            # Handle parens outside quotes
            elif not in_quotes:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
            
            i += 1
        
        if depth != 0:
            partial = text[start:min(start + 50, len(text))]
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message=f"Unclosed command substitution: {partial}...",
                expected_close=')',
                suggestion="Add closing ')' to complete the substitution"
            )
        
        return ExpansionValidationResult(is_valid=True)
```

2. **Quote Validation** (`lexer/quote_validator.py`)
```python
class QuoteValidator:
    """Validates quote pairing during lexing."""
    
    def validate_quotes(
        self,
        tokens: List[Token]
    ) -> List[LexerError]:
        """Validate all quotes are properly closed."""
        errors = []
        quote_stack = []
        
        for i, token in enumerate(tokens):
            # Track quote tokens
            if hasattr(token, 'parts'):
                for part in token.parts:
                    if part.quote_type:
                        # Check if quote is opened but not closed
                        if part.value.startswith(part.quote_type) and \
                           not part.value.endswith(part.quote_type):
                            errors.append(LexerError(
                                error_type=LexerErrorType.UNCLOSED_QUOTE,
                                message=f"Unclosed {part.quote_type} quote",
                                expected=part.quote_type,
                                suggestion=f"Add closing {part.quote_type}"
                            ))
        
        return errors
```

### 2.2 Bracket Pairing (Week 1)

#### Implementation Steps:

1. **Bracket Tracker** (`lexer/bracket_tracker.py`)
```python
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BracketPair:
    """Information about a bracket pair."""
    open_type: TokenType
    close_type: TokenType
    open_index: int
    close_index: Optional[int] = None

class BracketTracker:
    """Tracks bracket pairing during tokenization."""
    
    BRACKET_PAIRS = {
        TokenType.LPAREN: TokenType.RPAREN,
        TokenType.LBRACE: TokenType.RBRACE,
        TokenType.LBRACKET: TokenType.RBRACKET,
        TokenType.DOUBLE_LPAREN: TokenType.DOUBLE_RPAREN,
        TokenType.DOUBLE_LBRACKET: TokenType.DOUBLE_RBRACKET,
    }
    
    def __init__(self):
        self.stack: List[BracketPair] = []
        self.pairs: List[BracketPair] = []
    
    def process_token(self, token: EnhancedToken, index: int):
        """Process a token for bracket pairing."""
        if token.type in self.BRACKET_PAIRS:
            # Opening bracket
            pair = BracketPair(
                open_type=token.type,
                close_type=self.BRACKET_PAIRS[token.type],
                open_index=index
            )
            self.stack.append(pair)
            token.metadata.paired_with = None  # Will be set when closed
        
        elif token.type in self.BRACKET_PAIRS.values():
            # Closing bracket
            if self.stack:
                # Find matching opener
                for i in range(len(self.stack) - 1, -1, -1):
                    if self.stack[i].close_type == token.type:
                        pair = self.stack.pop(i)
                        pair.close_index = index
                        self.pairs.append(pair)
                        
                        # Update metadata
                        token.metadata.paired_with = pair.open_index
                        # Will need to update opener's metadata later
                        break
                else:
                    # No matching opener
                    token.metadata.error_info = LexerError(
                        error_type=LexerErrorType.UNMATCHED_BRACKET,
                        message=f"Unmatched closing {token.type.name}",
                        suggestion="Remove this bracket or add matching opener"
                    )
            else:
                # No openers at all
                token.metadata.error_info = LexerError(
                    error_type=LexerErrorType.UNMATCHED_BRACKET,
                    message=f"Unexpected closing {token.type.name}",
                    suggestion="Remove this bracket"
                )
    
    def finalize(self, tokens: List[EnhancedToken]) -> List[LexerError]:
        """Finalize pairing and return errors for unclosed brackets."""
        errors = []
        
        # Update paired opener metadata
        for pair in self.pairs:
            if pair.close_index is not None:
                tokens[pair.open_index].metadata.paired_with = pair.close_index
        
        # Report unclosed brackets
        for pair in self.stack:
            token = tokens[pair.open_index]
            errors.append(LexerError(
                error_type=LexerErrorType.UNMATCHED_BRACKET,
                message=f"Unclosed {pair.open_type.name}",
                expected=pair.close_type.name,
                suggestion=f"Add closing {pair.close_type.name}"
            ))
            token.metadata.error_info = errors[-1]
        
        return errors
```

### 2.3 Integrated Validation (Week 2)

#### Implementation Steps:

1. **Token Stream Validator** (`lexer/stream_validator.py`)
```python
from typing import List, Set
from dataclasses import dataclass

@dataclass
class ValidationConfig:
    """Configuration for token stream validation."""
    check_quotes: bool = True
    check_expansions: bool = True
    check_brackets: bool = True
    check_redirections: bool = True
    check_assignments: bool = True
    max_errors: int = 50

class TokenStreamValidator:
    """Validates token stream before passing to parser."""
    
    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
        self.errors: List[LexerError] = []
        self.warnings: List[LexerError] = []
    
    def validate(
        self,
        tokens: List[EnhancedToken]
    ) -> 'ValidationResult':
        """Validate token stream."""
        self.errors.clear()
        self.warnings.clear()
        
        # Run validators
        if self.config.check_quotes:
            self._validate_quotes(tokens)
        
        if self.config.check_expansions:
            self._validate_expansions(tokens)
        
        if self.config.check_brackets:
            self._validate_brackets(tokens)
        
        if self.config.check_redirections:
            self._validate_redirections(tokens)
        
        if self.config.check_assignments:
            self._validate_assignments(tokens)
        
        # Check error limit
        if len(self.errors) > self.config.max_errors:
            self.errors = self.errors[:self.config.max_errors]
            self.errors.append(LexerError(
                error_type="too_many_errors",
                message=f"Too many errors (limit: {self.config.max_errors})",
                severity="error"
            ))
        
        return ValidationResult(
            tokens=tokens,
            errors=self.errors,
            warnings=self.warnings,
            is_valid=len(self.errors) == 0
        )
    
    def _validate_quotes(self, tokens: List[EnhancedToken]):
        """Validate quote pairing."""
        validator = QuoteValidator()
        errors = validator.validate_quotes(tokens)
        self.errors.extend(errors)
    
    def _validate_expansions(self, tokens: List[EnhancedToken]):
        """Validate expansions are properly closed."""
        for token in tokens:
            if token.metadata.error_info and \
               token.metadata.error_info.error_type == LexerErrorType.UNCLOSED_EXPANSION:
                self.errors.append(token.metadata.error_info)
    
    def _validate_brackets(self, tokens: List[EnhancedToken]):
        """Validate bracket pairing."""
        tracker = BracketTracker()
        
        for i, token in enumerate(tokens):
            tracker.process_token(token, i)
        
        errors = tracker.finalize(tokens)
        self.errors.extend(errors)
    
    def _validate_redirections(self, tokens: List[EnhancedToken]):
        """Validate redirection syntax."""
        for i, token in enumerate(tokens):
            if token.type in {TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                             TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR}:
                # Check next token is valid target
                if i + 1 >= len(tokens):
                    self.errors.append(LexerError(
                        error_type=LexerErrorType.INVALID_REDIRECT,
                        message=f"Missing target for {token.type.name}",
                        suggestion="Add filename or file descriptor"
                    ))
                else:
                    next_token = tokens[i + 1]
                    if next_token.type not in {TokenType.WORD, TokenType.STRING,
                                               TokenType.VARIABLE}:
                        self.warnings.append(LexerError(
                            error_type="suspicious_redirect",
                            message=f"Unusual redirect target: {next_token.type.name}",
                            severity="warning"
                        ))
    
    def _validate_assignments(self, tokens: List[EnhancedToken]):
        """Validate assignment syntax."""
        for token in tokens:
            if token.type in {TokenType.ASSIGNMENT_WORD, TokenType.ARRAY_ASSIGNMENT_WORD}:
                # Validate assignment format
                if '=' not in token.value:
                    self.errors.append(LexerError(
                        error_type=LexerErrorType.INVALID_ASSIGNMENT,
                        message=f"Invalid assignment format: {token.value}",
                        suggestion="Use VAR=value format"
                    ))

@dataclass
class ValidationResult:
    """Result of token stream validation."""
    tokens: List[EnhancedToken]
    errors: List[LexerError]
    warnings: List[LexerError]
    is_valid: bool
```

## Phase 3: Lexer-Parser Contract (1 week)

### 3.1 Contract Definition (Week 1)

#### Implementation Steps:

1. **Contract Interface** (`contracts/lexer_parser_contract.py`)
```python
from abc import ABC, abstractmethod
from typing import List, Protocol
from dataclasses import dataclass

class TokenStream(Protocol):
    """Protocol for token streams."""
    
    def get_tokens(self) -> List[EnhancedToken]:
        """Get all tokens."""
        ...
    
    def is_valid(self) -> bool:
        """Check if stream is valid."""
        ...
    
    def get_errors(self) -> List[LexerError]:
        """Get validation errors."""
        ...

@dataclass
class LexerOutput:
    """Output from lexer to parser."""
    tokens: List[EnhancedToken]
    validation_result: ValidationResult
    metadata: Dict[str, Any]

class LexerParserContract(ABC):
    """Contract between lexer and parser."""
    
    @abstractmethod
    def validate_lexer_output(
        self,
        output: LexerOutput
    ) -> List[Issue]:
        """Validate lexer output meets parser requirements."""
        pass
    
    @abstractmethod
    def transform_tokens(
        self,
        tokens: List[EnhancedToken]
    ) -> List[Token]:
        """Transform enhanced tokens for parser consumption."""
        pass

class StandardLexerParserContract(LexerParserContract):
    """Standard implementation of lexer-parser contract."""
    
    def validate_lexer_output(
        self,
        output: LexerOutput
    ) -> List[Issue]:
        """Validate lexer output."""
        issues = []
        
        # Check for lexer errors
        if not output.validation_result.is_valid:
            for error in output.validation_result.errors:
                issues.append(Issue(
                    message=error.message,
                    severity=Severity.ERROR,
                    source="lexer"
                ))
        
        # Check token stream integrity
        if not output.tokens:
            issues.append(Issue(
                message="Empty token stream",
                severity=Severity.ERROR,
                source="contract"
            ))
        
        # Check EOF token
        if output.tokens and output.tokens[-1].type != TokenType.EOF:
            issues.append(Issue(
                message="Token stream must end with EOF",
                severity=Severity.ERROR,
                source="contract"
            ))
        
        return issues
    
    def transform_tokens(
        self,
        tokens: List[EnhancedToken]
    ) -> List[Token]:
        """Transform enhanced tokens to basic tokens."""
        # Can optionally strip metadata for backward compatibility
        return [Token(
            type=t.type,
            value=t.value,
            position=t.position,
            end_position=t.end_position,
            quote_type=t.quote_type,
            line=t.line,
            column=t.column
        ) for t in tokens]
```

2. **Contract Adapter** (`contracts/contract_adapter.py`)
```python
class ContractAdapter:
    """Adapts between lexer and parser using contract."""
    
    def __init__(
        self,
        contract: LexerParserContract = None
    ):
        self.contract = contract or StandardLexerParserContract()
    
    def process_lexer_output(
        self,
        lexer_output: LexerOutput,
        parser_config: ParserConfig
    ) -> 'ProcessedTokens':
        """Process lexer output for parser."""
        # Validate output
        issues = self.contract.validate_lexer_output(lexer_output)
        
        if issues and parser_config.error_handling == ErrorHandlingMode.STRICT:
            raise ParseError(f"Lexer output validation failed: {issues[0].message}")
        
        # Transform tokens if needed
        if parser_config.use_enhanced_tokens:
            tokens = lexer_output.tokens
        else:
            tokens = self.contract.transform_tokens(lexer_output.tokens)
        
        return ProcessedTokens(
            tokens=tokens,
            errors=lexer_output.validation_result.errors,
            warnings=lexer_output.validation_result.warnings,
            issues=issues
        )
```

## Phase 4: Integration and Migration (2 weeks)

### 4.1 Enhanced Lexer Integration (Week 1)

#### Implementation Steps:

1. **Enhanced Modular Lexer** (`lexer/enhanced_modular_lexer.py`)
```python
class EnhancedModularLexer(ModularLexer):
    """Enhanced lexer with validation and context tracking."""
    
    def __init__(
        self,
        input_string: str,
        config: Optional[LexerConfig] = None
    ):
        super().__init__(input_string, config)
        
        # Enhanced context
        self.enhanced_context = EnhancedLexerContext()
        
        # Validators
        self.expansion_validator = ExpansionValidator()
        self.bracket_tracker = BracketTracker()
        
        # Enhanced recognizers
        self._setup_enhanced_recognizers()
    
    def _setup_enhanced_recognizers(self):
        """Set up enhanced recognizers."""
        # Add assignment recognizer with high priority
        self.registry.register(
            AssignmentRecognizer(),
            priority=90  # High priority
        )
        
        # Add context-aware operator recognizer
        self.registry.register(
            ContextAwareOperatorRecognizer(),
            priority=80
        )
    
    def tokenize(self) -> LexerOutput:
        """Tokenize with validation."""
        tokens = []
        
        while self.position < len(self.input):
            # Get token with context
            token = self._next_token_with_context()
            
            if token:
                # Track brackets
                self.bracket_tracker.process_token(
                    token,
                    len(tokens)
                )
                
                tokens.append(token)
                
                # Update context based on token
                self._update_context(token)
        
        # Add EOF token
        eof_token = EnhancedToken(
            type=TokenType.EOF,
            value='',
            position=self.position,
            end_position=self.position
        )
        tokens.append(eof_token)
        
        # Finalize bracket tracking
        bracket_errors = self.bracket_tracker.finalize(tokens)
        
        # Validate token stream
        validator = TokenStreamValidator()
        validation_result = validator.validate(tokens)
        
        # Add bracket errors
        validation_result.errors.extend(bracket_errors)
        
        return LexerOutput(
            tokens=tokens,
            validation_result=validation_result,
            metadata={
                'source_length': len(self.input),
                'token_count': len(tokens),
                'has_errors': not validation_result.is_valid
            }
        )
    
    def _next_token_with_context(self) -> Optional[EnhancedToken]:
        """Get next token with context information."""
        # Skip whitespace
        self._skip_whitespace()
        
        if self.position >= len(self.input):
            return None
        
        # Try recognizers with context
        for recognizer in self.registry.get_recognizers():
            if isinstance(recognizer, ContextAwareRecognizer):
                token = recognizer.recognize_with_context(
                    self.input,
                    self.position,
                    self.enhanced_context
                )
            else:
                # Fallback for non-context-aware recognizers
                token = recognizer.recognize(
                    self.input,
                    self.position,
                    self.context
                )
                
                # Enhance basic token
                if token:
                    token = self._enhance_basic_token(token)
            
            if token:
                self.position = token.end_position
                return token
        
        # Fallback: create error token
        char = self.input[self.position]
        error_token = create_error_token(
            position=self.position,
            value=char,
            error_type="unrecognized_character",
            message=f"Unrecognized character: '{char}'"
        )
        self.position += 1
        
        return error_token
    
    def _enhance_basic_token(
        self,
        token: Token
    ) -> EnhancedToken:
        """Enhance a basic token with metadata."""
        enhanced = EnhancedToken(
            type=token.type,
            value=token.value,
            position=token.position,
            end_position=token.end_position,
            quote_type=token.quote_type,
            line=token.line,
            column=token.column
        )
        
        # Add context metadata
        enhanced.metadata.contexts = self.enhanced_context.get_current_contexts()
        
        # Add semantic type
        if token.type in {TokenType.IF, TokenType.THEN, TokenType.ELSE,
                         TokenType.FI, TokenType.WHILE, TokenType.DO,
                         TokenType.DONE, TokenType.FOR, TokenType.IN}:
            enhanced.metadata.semantic_type = SemanticType.KEYWORD
        elif token.type in {TokenType.PIPE, TokenType.AND_AND,
                           TokenType.OR_OR, TokenType.SEMICOLON}:
            enhanced.metadata.semantic_type = SemanticType.OPERATOR
        
        return enhanced
    
    def _update_context(self, token: EnhancedToken):
        """Update context based on token."""
        # Track command position
        if token.type in {TokenType.PIPE, TokenType.AND_AND,
                         TokenType.OR_OR, TokenType.SEMICOLON,
                         TokenType.NEWLINE}:
            self.enhanced_context.command_position = True
        elif token.type not in {TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                               TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR}:
            self.enhanced_context.command_position = False
        
        # Track test expressions
        if token.type == TokenType.DOUBLE_LBRACKET:
            self.enhanced_context.enter_test_expression()
        elif token.type == TokenType.DOUBLE_RBRACKET:
            self.enhanced_context.exit_test_expression()
        
        # Track arithmetic expressions
        if token.type == TokenType.DOUBLE_LPAREN:
            self.enhanced_context.arithmetic_depth += 1
        elif token.type == TokenType.DOUBLE_RPAREN:
            self.enhanced_context.arithmetic_depth -= 1
```

### 4.2 Parser Integration (Week 1)

#### Implementation Steps:

1. **Enhanced Parser Base** (`parser/enhanced_base.py`)
```python
class EnhancedContextBaseParser(ContextBaseParser):
    """Enhanced base parser that works with enhanced tokens."""
    
    def __init__(
        self,
        ctx: ParserContext,
        use_enhanced_tokens: bool = True
    ):
        super().__init__(ctx)
        self.use_enhanced_tokens = use_enhanced_tokens
        
        # Contract adapter
        self.contract_adapter = ContractAdapter()
    
    def setup_from_lexer_output(
        self,
        lexer_output: LexerOutput
    ):
        """Set up parser from lexer output."""
        # Process through contract
        processed = self.contract_adapter.process_lexer_output(
            lexer_output,
            self.ctx.config
        )
        
        # Update context with processed tokens
        self.ctx.tokens = processed.tokens
        self.ctx.current = 0
        
        # Add lexer errors to context
        for error in processed.errors:
            self.ctx.add_lexer_error(error)
        
        # Add warnings
        for warning in processed.warnings:
            self.ctx.add_warning(warning)
    
    def peek_enhanced(self) -> Optional[EnhancedToken]:
        """Peek at current token as enhanced token."""
        token = self.peek()
        
        if isinstance(token, EnhancedToken):
            return token
        
        # Convert basic token to enhanced for compatibility
        return EnhancedToken(
            type=token.type,
            value=token.value,
            position=token.position,
            end_position=token.end_position,
            quote_type=token.quote_type,
            line=token.line,
            column=token.column
        )
    
    def expect_with_context(
        self,
        token_type: TokenType,
        context: TokenContext,
        message: Optional[str] = None
    ) -> Token:
        """Expect token with specific context."""
        token = self.peek_enhanced()
        
        if token and context not in token.metadata.contexts:
            # Token type matches but context is wrong
            actual_contexts = ', '.join(c.value for c in token.metadata.contexts)
            error_msg = message or f"Expected {token_type} in {context.value} context, but found it in {actual_contexts}"
            raise self._error(error_msg)
        
        return self.expect(token_type, message)
```

2. **Migration Utilities** (`parser/migration.py`)
```python
class ParserMigration:
    """Utilities for migrating to enhanced lexer-parser interface."""
    
    @staticmethod
    def create_compatible_lexer(
        input_string: str,
        config: Optional[LexerConfig] = None,
        enhanced: bool = True
    ) -> Union[ModularLexer, EnhancedModularLexer]:
        """Create lexer with compatibility mode."""
        if enhanced:
            return EnhancedModularLexer(input_string, config)
        else:
            return ModularLexer(input_string, config)
    
    @staticmethod
    def adapt_tokens(
        tokens: List[Token],
        enhance: bool = True
    ) -> List[Union[Token, EnhancedToken]]:
        """Adapt tokens between basic and enhanced formats."""
        if not enhance:
            # Downgrade enhanced to basic
            return [Token(
                type=t.type,
                value=t.value,
                position=t.position,
                end_position=t.end_position,
                quote_type=t.quote_type,
                line=t.line,
                column=t.column
            ) for t in tokens]
        else:
            # Upgrade basic to enhanced
            enhanced_tokens = []
            for token in tokens:
                if isinstance(token, EnhancedToken):
                    enhanced_tokens.append(token)
                else:
                    enhanced_tokens.append(EnhancedToken(
                        type=token.type,
                        value=token.value,
                        position=token.position,
                        end_position=token.end_position,
                        quote_type=token.quote_type,
                        line=token.line,
                        column=token.column
                    ))
            return enhanced_tokens
```

### 4.3 Backward Compatibility (Week 2)

#### Implementation Steps:

1. **Compatibility Layer** (`compatibility/lexer_parser_compat.py`)
```python
from typing import List, Union

class LexerParserCompatibility:
    """Ensures backward compatibility during migration."""
    
    @staticmethod
    def tokenize_compatible(
        input_string: str,
        strict: bool = True,
        use_enhanced: bool = False
    ) -> List[Token]:
        """Tokenize with compatibility mode."""
        # Determine configuration
        if strict:
            config = LexerConfig.create_batch_config()
        else:
            config = LexerConfig.create_interactive_config()
        
        if use_enhanced:
            # Use enhanced lexer but return basic tokens
            lexer = EnhancedModularLexer(input_string, config)
            output = lexer.tokenize()
            
            # Convert to basic tokens
            adapter = ContractAdapter()
            return adapter.transform_tokens(output.tokens)
        else:
            # Use original lexer
            from ..lexer import tokenize
            return tokenize(input_string, strict)
    
    @staticmethod
    def create_parser_compatible(
        tokens: List[Token],
        config: Optional[ParserConfig] = None,
        use_enhanced: bool = False
    ) -> Parser:
        """Create parser with compatibility mode."""
        if use_enhanced and config and config.use_enhanced_tokens:
            # Enhance tokens if needed
            enhanced_tokens = ParserMigration.adapt_tokens(tokens, enhance=True)
            
            # Create enhanced parser
            ctx = ParserContextFactory.create(
                tokens=enhanced_tokens,
                config=config
            )
            
            # Use enhanced base
            from .enhanced_base import EnhancedParser
            return EnhancedParser(ctx)
        else:
            # Use standard parser
            return Parser(tokens, config=config)
```

2. **Feature Flags** (`config/feature_flags.py`)
```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class LexerParserFeatureFlags:
    """Feature flags for lexer-parser improvements."""
    
    # Enhanced tokens
    use_enhanced_tokens: bool = False
    
    # Validation features
    enable_lexer_validation: bool = False
    validate_quotes: bool = True
    validate_expansions: bool = True
    validate_brackets: bool = True
    
    # Context features
    track_token_context: bool = False
    track_semantic_types: bool = False
    
    # Assignment detection
    detect_assignments: bool = False
    
    # Error handling
    collect_lexer_errors: bool = False
    max_lexer_errors: int = 50
    
    @classmethod
    def create_legacy(cls) -> 'LexerParserFeatureFlags':
        """Create flags for legacy mode."""
        return cls(
            use_enhanced_tokens=False,
            enable_lexer_validation=False,
            track_token_context=False,
            track_semantic_types=False,
            detect_assignments=False,
            collect_lexer_errors=False
        )
    
    @classmethod
    def create_progressive(cls) -> 'LexerParserFeatureFlags':
        """Create flags for progressive enhancement."""
        return cls(
            use_enhanced_tokens=True,
            enable_lexer_validation=True,
            track_token_context=True,
            track_semantic_types=False,  # Optional
            detect_assignments=True,
            collect_lexer_errors=True
        )
    
    @classmethod
    def create_full(cls) -> 'LexerParserFeatureFlags':
        """Create flags with all features enabled."""
        return cls(
            use_enhanced_tokens=True,
            enable_lexer_validation=True,
            track_token_context=True,
            track_semantic_types=True,
            detect_assignments=True,
            collect_lexer_errors=True
        )
```

## Phase 5: Testing and Documentation (1 week)

### 5.1 Comprehensive Testing (Week 1)

#### Test Categories:

1. **Token Enhancement Tests**
```python
# tests/test_enhanced_tokens.py
def test_token_context_tracking():
    """Test that tokens track their context correctly."""
    lexer = EnhancedModularLexer("echo hello | grep world")
    output = lexer.tokenize()
    
    tokens = output.tokens
    
    # First token should be in command position
    assert TokenContext.COMMAND_POSITION in tokens[0].metadata.contexts
    
    # Token after pipe should be in command position
    pipe_index = next(i for i, t in enumerate(tokens) if t.type == TokenType.PIPE)
    assert TokenContext.COMMAND_POSITION in tokens[pipe_index + 1].metadata.contexts

def test_assignment_detection():
    """Test assignment pattern detection."""
    lexer = EnhancedModularLexer("VAR=value arr[0]=elem")
    output = lexer.tokenize()
    
    tokens = output.tokens
    
    assert tokens[0].type == TokenType.ASSIGNMENT_WORD
    assert tokens[0].metadata.semantic_type == SemanticType.ASSIGNMENT
    
    assert tokens[1].type == TokenType.ARRAY_ASSIGNMENT_WORD
```

2. **Validation Tests**
```python
# tests/test_lexer_validation.py
def test_unclosed_expansion_detection():
    """Test detection of unclosed expansions."""
    lexer = EnhancedModularLexer("echo ${VAR")
    output = lexer.tokenize()
    
    assert not output.validation_result.is_valid
    assert any(e.error_type == LexerErrorType.UNCLOSED_EXPANSION 
              for e in output.validation_result.errors)

def test_bracket_pairing():
    """Test bracket pairing validation."""
    lexer = EnhancedModularLexer("echo $((1 + 2)")
    output = lexer.tokenize()
    
    assert not output.validation_result.is_valid
    assert any(e.error_type == LexerErrorType.UNMATCHED_BRACKET
              for e in output.validation_result.errors)
```

3. **Contract Tests**
```python
# tests/test_lexer_parser_contract.py
def test_contract_validation():
    """Test lexer-parser contract validation."""
    lexer = EnhancedModularLexer("echo hello")
    output = lexer.tokenize()
    
    contract = StandardLexerParserContract()
    issues = contract.validate_lexer_output(output)
    
    assert len(issues) == 0
    assert output.tokens[-1].type == TokenType.EOF
```

4. **Compatibility Tests**
```python
# tests/test_compatibility.py
def test_backward_compatibility():
    """Test backward compatibility with existing code."""
    # Old way
    from psh.lexer import tokenize
    old_tokens = tokenize("echo hello", strict=True)
    
    # New way with compatibility
    new_tokens = LexerParserCompatibility.tokenize_compatible(
        "echo hello",
        strict=True,
        use_enhanced=False
    )
    
    assert len(old_tokens) == len(new_tokens)
    for old, new in zip(old_tokens, new_tokens):
        assert old.type == new.type
        assert old.value == new.value
```

### 5.2 Documentation

#### User Documentation:
1. Migration guide for existing code
2. Feature flag documentation
3. New token type reference
4. Validation error reference

#### Developer Documentation:
1. Architecture overview of enhancements
2. Contract specification
3. Extension points for custom recognizers
4. Performance considerations

## Phase 6: Cleanup and Finalization (1 week)

### 6.1 Remove Compatibility Code (Days 1-3)

#### Implementation Steps:

1. **Remove Feature Flags** (`config/feature_flags.py`)
```python
# DELETE THIS FILE - No longer needed after full migration
```

2. **Remove Compatibility Layer** (`compatibility/lexer_parser_compat.py`)
```python
# DELETE THIS FILE - All code now uses enhanced interface
```

3. **Clean Up Lexer Code**
   - Remove `ModularLexer` class (keep only `EnhancedModularLexer`)
   - Rename `EnhancedModularLexer` to `ModularLexer`
   - Remove all compatibility checks and fallback code
   - Remove `use_enhanced_tokens` parameters

```python
# lexer/__init__.py - Simplified after cleanup
def tokenize(input_string: str, strict: bool = True) -> LexerOutput:
    """
    Tokenize a shell command string using the enhanced lexer.
    
    Args:
        input_string: The shell command string to tokenize
        strict: If True, use strict mode; if False, use interactive mode
        
    Returns:
        LexerOutput with validated tokens
    """
    # Create appropriate lexer config
    if strict:
        config = LexerConfig.create_batch_config()
    else:
        config = LexerConfig.create_interactive_config()
    
    # Always use enhanced lexer
    lexer = ModularLexer(input_string, config=config)
    return lexer.tokenize()
```

4. **Clean Up Parser Code**
   - Remove `ContextBaseParser` (merge necessary code into `EnhancedContextBaseParser`)
   - Rename `EnhancedContextBaseParser` to `ContextBaseParser`
   - Remove all token type conversion code
   - Remove backward compatibility checks in `base_context.py`

```python
# parser/base_context.py - Simplified after cleanup
class ContextBaseParser:
    """Base parser with ParserContext for centralized state management."""
    
    def __init__(self, ctx: ParserContext):
        self.ctx = ctx
        self.contract_adapter = ContractAdapter()
    
    def peek(self, offset: int = 0) -> EnhancedToken:
        """Look at current token + offset without consuming."""
        return self.ctx.peek(offset)
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        # No more compatibility checks needed
        return self.ctx.match(*token_types)
    
    def expect(self, token_type: TokenType, message: Optional[str] = None) -> EnhancedToken:
        """Consume token of expected type or raise error."""
        # Direct implementation, no compatibility layer
        return self.ctx.consume(token_type, message)
```

5. **Remove Migration Utilities** (`parser/migration.py`)
```python
# DELETE THIS FILE - Migration complete
```

6. **Simplify Token Classes**
   - Make `EnhancedToken` the default `Token` class
   - Move enhanced functionality into base `Token`
   - Remove redundant token conversion methods

```python
# token_types.py - Unified token class
@dataclass
class Token:
    """A lexical token with type, value, position, and metadata."""
    type: TokenType
    value: str
    position: int
    end_position: int
    quote_type: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    metadata: TokenMetadata = field(default_factory=TokenMetadata)
    parts: List[TokenPart] = field(default_factory=list)
    
    @property
    def is_error(self) -> bool:
        return self.metadata.error_info is not None
    
    @property
    def in_test_context(self) -> bool:
        return TokenContext.TEST_EXPRESSION in self.metadata.contexts

# Remove EnhancedToken class - functionality merged into Token
```

### 6.2 Update Dependencies (Days 4-5)

#### Implementation Steps:

1. **Update All Imports**
```python
# Update all files that import token classes
# Before:
from psh.token_types import Token, EnhancedToken
from psh.lexer import ModularLexer, EnhancedModularLexer

# After:
from psh.token_types import Token  # EnhancedToken is now just Token
from psh.lexer import ModularLexer  # Enhanced is now the default
```

2. **Update Parser Constructors**
```python
# Before:
parser = Parser(tokens, use_enhanced_tokens=True, config=config)

# After:
parser = Parser(tokens, config=config)  # Always uses enhanced tokens
```

3. **Update Tests**
   - Remove all compatibility tests
   - Remove feature flag tests
   - Update assertions to expect enhanced token behavior
   - Remove tests for basic token conversion

4. **Update Documentation**
   - Remove migration guide (move to archive)
   - Update API documentation to reflect simplified interface
   - Remove feature flag documentation
   - Update architecture diagrams

### 6.3 Final Validation (Days 6-7)

#### Validation Steps:

1. **Run Full Test Suite**
```bash
# Ensure all tests pass with cleaned up code
python -m pytest tests/ -v

# Run performance benchmarks
python -m pytest tests/performance/ -v --benchmark
```

2. **Code Coverage Check**
```bash
# Ensure no dead code remains
python -m pytest tests/ --cov=psh --cov-report=html
# Review coverage report for unused code paths
```

3. **Static Analysis**
```bash
# Check for unused imports and dead code
flake8 psh/ --select=F401,F841
mypy psh/ --strict
```

4. **Documentation Review**
   - Ensure all examples use new API
   - Check that migration notes are archived
   - Verify no references to compatibility flags

5. **Performance Validation**
   - Compare performance before and after cleanup
   - Ensure no regression in tokenization speed
   - Verify memory usage is reasonable

## Implementation Timeline

- **Phase 1**: Enhanced Token Infrastructure (2 weeks)
  - Week 1: Token types and enhanced classes
  - Week 2: Context tracking and assignment detection

- **Phase 2**: Syntax Validation in Lexer (2 weeks)
  - Week 1: Expansion and quote validation
  - Week 2: Bracket pairing and integrated validation

- **Phase 3**: Lexer-Parser Contract (1 week)
  - Week 1: Contract definition and implementation

- **Phase 4**: Integration and Migration (2 weeks)
  - Week 1: Enhanced lexer and parser integration
  - Week 2: Backward compatibility

- **Phase 5**: Testing and Documentation (1 week)
  - Week 1: Comprehensive testing and documentation

- **Phase 6**: Cleanup and Finalization (1 week)
  - Days 1-3: Remove compatibility code
  - Days 4-5: Update dependencies
  - Days 6-7: Final validation

**Total Duration**: 9 weeks

## Success Metrics

1. **Error Detection**: 90% of syntax errors detected in lexer phase
2. **Performance**: No more than 10% overhead for enhanced processing
3. **Compatibility**: 100% backward compatibility with existing code
4. **Test Coverage**: 95% coverage of new code
5. **Parser Simplification**: 30% reduction in parser error handling code

## Risk Mitigation

1. **Performance Impact**: Use feature flags to enable/disable enhancements
2. **Compatibility Issues**: Maintain parallel implementations during migration
3. **Complexity**: Incremental rollout with monitoring
4. **Testing Burden**: Automated test generation for edge cases

## Future Extensions

1. **Semantic Analysis**: Add more semantic understanding to tokens
2. **IDE Integration**: Provide rich token information for IDE features
3. **Incremental Lexing**: Support for real-time editing
4. **Custom Token Types**: Plugin system for domain-specific tokens
5. **Performance Optimization**: Specialized fast paths for common patterns

This plan provides a structured approach to enhancing the lexer-parser interface while maintaining the system's educational value and architectural clarity.