"""Parser error catalog and enhanced error handling."""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """Severity levels for parser errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class ErrorTemplate:
    """Template for parser error messages."""
    code: str
    message: str
    suggestion: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    is_recoverable: bool = True


class ParserErrorCatalog:
    """Catalog of common parser errors with helpful suggestions."""
    
    # Control structure errors
    MISSING_SEMICOLON_BEFORE_THEN = ErrorTemplate(
        code="E001",
        message="Missing ';' or newline before 'then'",
        suggestion="Add a semicolon after the condition: if condition; then",
        severity=ErrorSeverity.ERROR
    )
    
    MISSING_DO_AFTER_FOR = ErrorTemplate(
        code="E002", 
        message="Missing 'do' in for loop",
        suggestion="Add 'do' after the loop variable list: for var in list; do"
    )
    
    MISSING_DO_AFTER_WHILE = ErrorTemplate(
        code="E003",
        message="Missing 'do' in while loop", 
        suggestion="Add 'do' after the condition: while condition; do"
    )
    
    UNCLOSED_IF_STATEMENT = ErrorTemplate(
        code="E004",
        message="Unclosed 'if' statement",
        suggestion="Add 'fi' to close the if statement"
    )
    
    UNCLOSED_FOR_LOOP = ErrorTemplate(
        code="E005",
        message="Unclosed 'for' loop",
        suggestion="Add 'done' to close the for loop"
    )
    
    UNCLOSED_WHILE_LOOP = ErrorTemplate(
        code="E006", 
        message="Unclosed 'while' loop",
        suggestion="Add 'done' to close the while loop"
    )
    
    UNCLOSED_CASE_STATEMENT = ErrorTemplate(
        code="E007",
        message="Unclosed 'case' statement",
        suggestion="Add 'esac' to close the case statement"
    )
    
    # Command structure errors
    EMPTY_COMMAND = ErrorTemplate(
        code="E010",
        message="Empty command",
        suggestion="Add a command name or remove the empty line",
        severity=ErrorSeverity.WARNING
    )
    
    INVALID_COMMAND_NAME = ErrorTemplate(
        code="E011",
        message="Invalid command name",
        suggestion="Command names cannot start with numbers or contain spaces"
    )
    
    MISSING_COMMAND_AFTER_PIPE = ErrorTemplate(
        code="E012",
        message="Missing command after pipe '|'",
        suggestion="Add a command after the pipe operator"
    )
    
    MISSING_COMMAND_AFTER_AND = ErrorTemplate(
        code="E013", 
        message="Missing command after '&&'",
        suggestion="Add a command after the && operator"
    )
    
    MISSING_COMMAND_AFTER_OR = ErrorTemplate(
        code="E014",
        message="Missing command after '||'", 
        suggestion="Add a command after the || operator"
    )
    
    # Redirection errors
    MISSING_REDIRECT_TARGET = ErrorTemplate(
        code="E020",
        message="Missing redirection target",
        suggestion="Add a filename after the redirection operator: > filename"
    )
    
    INVALID_FILE_DESCRIPTOR = ErrorTemplate(
        code="E021",
        message="Invalid file descriptor",
        suggestion="File descriptors must be numbers 0-9"
    )
    
    UNCLOSED_HERE_DOCUMENT = ErrorTemplate(
        code="E022",
        message="Unclosed here document",
        suggestion="Add the here document delimiter to close it"
    )
    
    # Function errors
    INVALID_FUNCTION_NAME = ErrorTemplate(
        code="E030",
        message="Invalid function name",
        suggestion="Function names must be valid identifiers (letters, numbers, underscore)"
    )
    
    MISSING_FUNCTION_BODY = ErrorTemplate(
        code="E031",
        message="Missing function body",
        suggestion="Add braces with commands: function_name() { commands; }"
    )
    
    UNCLOSED_FUNCTION_BODY = ErrorTemplate(
        code="E032",
        message="Unclosed function body",
        suggestion="Add '}' to close the function body"
    )
    
    # Loop control errors
    BREAK_OUTSIDE_LOOP = ErrorTemplate(
        code="E040",
        message="'break' used outside of loop",
        suggestion="Use 'break' only inside for, while, or until loops"
    )
    
    CONTINUE_OUTSIDE_LOOP = ErrorTemplate(
        code="E041",
        message="'continue' used outside of loop", 
        suggestion="Use 'continue' only inside for, while, or until loops"
    )
    
    # Quote and expansion errors
    UNCLOSED_SINGLE_QUOTE = ErrorTemplate(
        code="E050",
        message="Unclosed single quote",
        suggestion="Add a closing single quote: 'text'"
    )
    
    UNCLOSED_DOUBLE_QUOTE = ErrorTemplate(
        code="E051",
        message="Unclosed double quote",
        suggestion="Add a closing double quote: \"text\""
    )
    
    UNCLOSED_COMMAND_SUBSTITUTION = ErrorTemplate(
        code="E052", 
        message="Unclosed command substitution",
        suggestion="Add closing parenthesis: $(command)"
    )
    
    UNCLOSED_ARITHMETIC_EXPANSION = ErrorTemplate(
        code="E053",
        message="Unclosed arithmetic expansion", 
        suggestion="Add closing parentheses: $((expression))"
    )
    
    UNCLOSED_PARAMETER_EXPANSION = ErrorTemplate(
        code="E054",
        message="Unclosed parameter expansion",
        suggestion="Add closing brace: ${variable}"
    )
    
    # Array errors
    INVALID_ARRAY_INDEX = ErrorTemplate(
        code="E060",
        message="Invalid array index",
        suggestion="Array indices must be numbers or valid expressions"
    )
    
    UNCLOSED_ARRAY_SUBSCRIPT = ErrorTemplate(
        code="E061",
        message="Unclosed array subscript",
        suggestion="Add closing bracket: array[index]"
    )
    
    # Test command errors
    UNCLOSED_TEST_EXPRESSION = ErrorTemplate(
        code="E070",
        message="Unclosed test expression",
        suggestion="Add closing bracket: [ expression ] or [[ expression ]]"
    )
    
    INVALID_TEST_OPERATOR = ErrorTemplate(
        code="E071",
        message="Invalid test operator",
        suggestion="Use valid test operators like -eq, -ne, -lt, -gt, etc."
    )
    
    # General syntax errors
    UNEXPECTED_TOKEN = ErrorTemplate(
        code="E080",
        message="Unexpected token",
        suggestion="Check syntax around this token"
    )
    
    UNEXPECTED_EOF = ErrorTemplate(
        code="E081",
        message="Unexpected end of input",
        suggestion="Complete the command or statement"
    )
    
    INVALID_SYNTAX = ErrorTemplate(
        code="E082",
        message="Invalid syntax",
        suggestion="Check the command syntax"
    )


class ErrorSuggester:
    """Provides intelligent error suggestions based on context."""
    
    @staticmethod
    def suggest_for_missing_token(expected_token: str, context: str) -> Optional[str]:
        """Suggest fix for missing token based on context."""
        suggestions = {
            # Control structure suggestions
            ("then", "if"): "Add ';' before 'then': if condition; then",
            ("do", "for"): "Add ';' before 'do': for var in list; do", 
            ("do", "while"): "Add ';' before 'do': while condition; do",
            ("fi", "if"): "Close if statement with 'fi'",
            ("done", "for"): "Close for loop with 'done'",
            ("done", "while"): "Close while loop with 'done'",
            ("esac", "case"): "Close case statement with 'esac'",
            
            # Punctuation suggestions
            (";", "command"): "Add ';' to separate commands",
            (")", "("): "Add closing parenthesis",
            ("}", "{"): "Add closing brace", 
            ("]", "["): "Add closing bracket",
            ("]]", "[["): "Add closing double bracket",
            
            # Redirection suggestions
            ("filename", ">"): "Add filename after redirection: > filename",
            ("filename", ">>"): "Add filename after redirection: >> filename",
            ("filename", "<"): "Add filename after redirection: < filename",
        }
        
        return suggestions.get((expected_token, context))
    
    @staticmethod
    def suggest_for_typo(expected: str, actual: str) -> Optional[str]:
        """Suggest fix for common typos."""
        # Common typos mapping
        typos = {
            # Control structure typos
            "fi": ["if", "fii", "fi;", "fi.", "fi,"],
            "done": ["don", "doen", "dnoe", "odne", "done;"],
            "then": ["hten", "tehn", "then;", "then,"],
            "else": ["esle", "esle", "lese", "else;"],
            "elif": ["elfi", "eliif", "elif;"],
            "esac": ["esca", "easc", "caes", "esac;"],
            
            # Command typos
            "echo": ["ehco", "ecoh", "echo;"],
            "exit": ["exti", "eixt", "exit;"],
            "grep": ["grpe", "gerp", "grpe"],
            "cat": ["cta", "act", "cat;"],
        }
        
        for correct, wrong_variants in typos.items():
            if actual.lower() in wrong_variants:
                return f"Did you mean '{correct}'?"
        
        # Check for simple edit distance
        if len(expected) > 2 and len(actual) > 2:
            if abs(len(expected) - len(actual)) <= 1:
                # Simple character substitution/insertion/deletion
                diff_count = sum(1 for a, b in zip(expected, actual) if a != b)
                if diff_count <= 2:
                    return f"Did you mean '{expected}'?"
        
        return None
    
    @staticmethod
    def suggest_for_context(token_value: str, preceding_tokens: List[str]) -> Optional[str]:
        """Suggest fixes based on surrounding context."""
        if not preceding_tokens:
            return None
        
        last_token = preceding_tokens[-1] if preceding_tokens else ""
        
        # Context-based suggestions
        context_suggestions = {
            # After control keywords
            ("if", "then"): "Add condition before 'then': if condition; then",
            ("for", "do"): "Add variable and list: for var in list; do",
            ("while", "do"): "Add condition before 'do': while condition; do",
            ("case", "in"): "Add expression: case expression in",
            
            # After operators
            ("|", ""): "Add command after pipe",
            ("&&", ""): "Add command after &&",
            ("||", ""): "Add command after ||",
            (">", ""): "Add filename after redirection",
            (">>", ""): "Add filename after redirection",
            ("<", ""): "Add filename after redirection",
        }
        
        key = (last_token, token_value)
        result = context_suggestions.get(key)
        
        # If no exact match, try some pattern matching
        if not result:
            # Check for 'then' token after if-like words
            if token_value == "then" and any("if" in token for token in preceding_tokens):
                return "Add condition before 'then': if condition; then"
            # Check for missing commands after operators
            elif token_value == "" and last_token in ["|", "&&", "||"]:
                return f"Add command after {last_token}"
        
        return result


def get_error_template(error_code: str) -> Optional[ErrorTemplate]:
    """Get error template by code."""
    for attr_name in dir(ParserErrorCatalog):
        if not attr_name.startswith('_'):
            template = getattr(ParserErrorCatalog, attr_name)
            if isinstance(template, ErrorTemplate) and template.code == error_code:
                return template
    return None


def find_similar_error_templates(message: str) -> List[ErrorTemplate]:
    """Find error templates with similar messages."""
    similar = []
    message_lower = message.lower()
    
    for attr_name in dir(ParserErrorCatalog):
        if not attr_name.startswith('_'):
            template = getattr(ParserErrorCatalog, attr_name)
            if isinstance(template, ErrorTemplate):
                if any(word in template.message.lower() for word in message_lower.split()):
                    similar.append(template)
    
    return similar