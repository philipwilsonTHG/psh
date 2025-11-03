"""Control structure parsers for the shell parser combinator.

This module provides parsers for all control flow structures including
if/elif/else, loops, case statements, and function definitions.
"""

from typing import List, Optional, Tuple, Union
from ...token_types import Token, TokenType
from ...ast_nodes import (
    # Control structures
    IfConditional, WhileLoop, UntilLoop, ForLoop, CaseConditional, SelectLoop,
    CStyleForLoop, CaseItem, CasePattern, FunctionDef,
    # Compound commands
    SubshellGroup, BraceGroup,
    # Other AST nodes
    CommandList, StatementList, ASTNode,
    # Break/continue
    BreakStatement, ContinueStatement
)
from ..config import ParserConfig
from .core import (
    Parser, ParseResult, ForwardParser,
    between, lazy, skip, keyword
)
from .tokens import TokenParsers
from .commands import CommandParsers


class ControlStructureParsers:
    """Parsers for shell control structures.
    
    This class provides parsers for all control flow structures:
    - If/elif/else conditionals
    - While loops
    - For loops (traditional and C-style)
    - Case statements
    - Select loops
    - Function definitions
    - Subshell and brace groups
    - Break and continue statements
    """
    
    def __init__(self, config: Optional[ParserConfig] = None,
                 token_parsers: Optional[TokenParsers] = None,
                 command_parsers: Optional[CommandParsers] = None):
        """Initialize control structure parsers.
        
        Args:
            config: Parser configuration
            token_parsers: Token parsers to use
            command_parsers: Command parsers for parsing bodies
        """
        self.config = config or ParserConfig()
        self.tokens = token_parsers or TokenParsers()
        self.commands = command_parsers  # May be None initially
        
        # Forward declaration for statement lists
        self.statement_list_forward = ForwardParser[CommandList]()
        
        self._initialize_parsers()
    
    def set_command_parsers(self, command_parsers: CommandParsers):
        """Set command parsers after initialization.
        
        This breaks the circular dependency between command and control parsers.
        
        Args:
            command_parsers: Command parsers to use
        """
        self.commands = command_parsers
        # Re-initialize parsers that depend on commands
        self._initialize_dependent_parsers()
    
    def _initialize_parsers(self):
        """Initialize parsers that don't depend on command parsers."""
        # Keywords
        self.if_kw = keyword('if')
        self.then_kw = keyword('then')
        self.elif_kw = keyword('elif')
        self.else_kw = keyword('else')
        self.fi_kw = keyword('fi')
        self.while_kw = keyword('while')
        self.for_kw = keyword('for')
        self.in_kw = keyword('in')
        self.do_kw = keyword('do')
        self.done_kw = keyword('done')
        self.case_kw = keyword('case')
        self.esac_kw = keyword('esac')
        self.select_kw = keyword('select')
        self.function_kw = keyword('function')
        
        # Statement terminators
        self.statement_terminator = self.tokens.semicolon.or_else(self.tokens.newline)
        
        # Helper parsers for control structures
        self.do_separator = Parser(lambda tokens, pos: self._parse_do_separator(tokens, pos))
        self.then_separator = Parser(lambda tokens, pos: self._parse_then_separator(tokens, pos))
    
    def _initialize_dependent_parsers(self):
        """Initialize parsers that depend on command parsers."""
        if not self.commands:
            return
        
        # Control structure parsers
        self.if_statement = self._build_if_statement()
        self.while_loop = self._build_while_loop()
        self.until_loop = self._build_until_loop()
        self.for_loop = self._build_for_loops()
        self.case_statement = self._build_case_statement()
        self.select_loop = self._build_select_loop()
        
        # Function definitions
        self.function_def = self._build_function_def()
        
        # Compound commands
        self.subshell_group = self._build_subshell_group()
        self.brace_group = self._build_brace_group()
        
        # Break and continue
        self.break_statement = self._build_break_statement()
        self.continue_statement = self._build_continue_statement()
        
        # Combined control structure parser
        self.control_structure = (
            self.if_statement
            .or_else(self.while_loop)
            .or_else(self.until_loop)
            .or_else(self.for_loop)
            .or_else(self.case_statement)
            .or_else(self.select_loop)
            .or_else(self.subshell_group)
            .or_else(self.brace_group)
            .or_else(self.break_statement)
            .or_else(self.continue_statement)
        )
    
    def _parse_do_separator(self, tokens: List[Token], pos: int) -> ParseResult[None]:
        """Parse separator followed by 'do' keyword."""
        # Skip optional separator
        if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
            pos += 1
        
        # Expect 'do'
        if pos >= len(tokens) or tokens[pos].value != 'do':
            return ParseResult(success=False, error="Expected 'do'", position=pos)
        
        return ParseResult(success=True, value=None, position=pos + 1)
    
    def _parse_then_separator(self, tokens: List[Token], pos: int) -> ParseResult[None]:
        """Parse separator followed by 'then' keyword."""
        # Skip optional separator
        if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
            pos += 1
        
        # Expect 'then'
        if pos >= len(tokens) or tokens[pos].value != 'then':
            return ParseResult(success=False, error="Expected 'then'", position=pos)
        
        return ParseResult(success=True, value=None, position=pos + 1)
    
    def _collect_tokens_until_keyword(self, tokens: List[Token], start_pos: int,
                                     end_keyword: str, start_keyword: Optional[str] = None) -> Tuple[List[Token], int]:
        """Collect tokens until end keyword, handling nested structures.
        
        If start_keyword is provided, counts nesting levels.
        
        Args:
            tokens: List of tokens
            start_pos: Starting position
            end_keyword: Keyword that ends collection
            start_keyword: Optional keyword that increases nesting
            
        Returns:
            Tuple of (collected_tokens, position_after_end_keyword)
        """
        collected = []
        pos = start_pos
        nesting_level = 0
        
        while pos < len(tokens):
            token = tokens[pos]
            
            # Check for start keyword (increases nesting)
            if start_keyword and token.value == start_keyword:
                nesting_level += 1
                collected.append(token)
                pos += 1
                continue
            
            # Check for end keyword
            if token.value == end_keyword:
                if nesting_level == 0:
                    # Found our end keyword
                    return collected, pos
                else:
                    # This ends a nested structure
                    nesting_level -= 1
                    collected.append(token)
                    pos += 1
                    continue
            
            # Regular token
            collected.append(token)
            pos += 1
        
        # Reached end without finding end keyword
        return collected, pos
    
    def _build_if_statement(self) -> Parser[IfConditional]:
        """Build parser for if/then/elif/else/fi statements."""
        def parse_condition_then(tokens: List[Token], pos: int) -> ParseResult[Tuple[CommandList, CommandList]]:
            """Parse a condition-then pair."""
            # Parse condition (statement list until 'then')
            condition_tokens = []
            current_pos = pos
            
            # Collect tokens until we see 'then'
            saw_separator = False
            while current_pos < len(tokens):
                token = tokens[current_pos]
                
                # Check if this is 'then' keyword
                if token.value == 'then' and token.type.name in ['THEN', 'WORD']:
                    # 'then' must be preceded by a separator
                    if condition_tokens and not saw_separator:
                        return ParseResult(success=False, 
                                         error="Syntax error: expected ';' or newline before 'then'", 
                                         position=current_pos)
                    break
                
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    saw_separator = True
                    # Check if next token is 'then'
                    if (current_pos + 1 < len(tokens) and 
                        tokens[current_pos + 1].value == 'then'):
                        # Don't include the separator in condition tokens
                        break
                
                condition_tokens.append(token)
                current_pos += 1
            
            if current_pos >= len(tokens):
                return ParseResult(success=False, 
                                 error="Unexpected end of input: expected 'then' in if statement", 
                                 position=pos)
            
            # Skip separator if we're at one
            if tokens[current_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                current_pos += 1
            
            # Verify we actually found 'then'
            if current_pos >= len(tokens) or tokens[current_pos].value != 'then':
                return ParseResult(success=False, 
                                 error=f"Expected 'then' in if statement", 
                                 position=current_pos)
            
            # Parse the condition
            condition_result = self.commands.statement_list.parse(condition_tokens, 0)
            if not condition_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse condition: {condition_result.error}", 
                                 position=pos)
            
            current_pos += 1  # Skip 'then'
            
            # Skip optional separator after 'then'
            if current_pos < len(tokens) and tokens[current_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                current_pos += 1
            
            # Parse the body (until elif/else/fi, handling nested if statements)
            body_tokens = []
            nesting_level = 0
            
            while current_pos < len(tokens):
                token = tokens[current_pos]
                
                # Track nested if statements
                if token.value == 'if':
                    nesting_level += 1
                    body_tokens.append(token)
                    current_pos += 1
                    continue
                
                # Check for keywords that might end this body
                if token.value in ['elif', 'else', 'fi']:
                    if nesting_level == 0:
                        # This ends our current body
                        break
                    elif token.value == 'fi':
                        # This ends a nested if
                        nesting_level -= 1
                    body_tokens.append(token)
                    current_pos += 1
                    continue
                
                body_tokens.append(token)
                current_pos += 1
            
            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse then body: {body_result.error}", 
                                 position=current_pos)
            
            return ParseResult(
                success=True,
                value=(condition_result.value, body_result.value),
                position=current_pos
            )
        
        # Main if statement parser
        def parse_if_statement(tokens: List[Token], pos: int) -> ParseResult[IfConditional]:
            """Parse complete if statement."""
            # Check for 'if' keyword
            if pos >= len(tokens) or tokens[pos].value != 'if':
                return ParseResult(success=False, error="Expected 'if'", position=pos)
            
            pos += 1  # Skip 'if'
            
            # Parse main condition and then part
            main_result = parse_condition_then(tokens, pos)
            if not main_result.success:
                return ParseResult(success=False, error=main_result.error, position=pos)
            
            condition, then_part = main_result.value
            pos = main_result.position
            
            # Parse elif parts
            elif_parts = []
            while pos < len(tokens) and tokens[pos].value == 'elif':
                pos += 1  # Skip 'elif'
                elif_result = parse_condition_then(tokens, pos)
                if not elif_result.success:
                    return ParseResult(success=False, error=elif_result.error, position=pos)
                elif_parts.append(elif_result.value)
                pos = elif_result.position
            
            # Parse optional else part
            else_part = None
            if pos < len(tokens) and tokens[pos].value == 'else':
                pos += 1  # Skip 'else'
                
                # Skip optional separator after 'else'
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Parse else body (until 'fi', handling nested if statements)
                else_tokens = []
                nesting_level = 0
                
                while pos < len(tokens):
                    token = tokens[pos]
                    
                    if token.value == 'if':
                        nesting_level += 1
                    elif token.value == 'fi':
                        if nesting_level == 0:
                            break
                        else:
                            nesting_level -= 1
                    
                    else_tokens.append(token)
                    pos += 1
                
                else_result = self.commands.statement_list.parse(else_tokens, 0)
                if not else_result.success:
                    return ParseResult(success=False, 
                                     error=f"Failed to parse else body: {else_result.error}", 
                                     position=pos)
                else_part = else_result.value
            
            # Expect 'fi'
            if pos >= len(tokens):
                return ParseResult(success=False, 
                                 error="Unexpected end of input: expected 'fi' to close if statement", 
                                 position=pos)
            if tokens[pos].value != 'fi':
                return ParseResult(success=False, 
                                 error=f"Expected 'fi' to close if statement, got '{tokens[pos].value}'", 
                                 position=pos)
            
            pos += 1  # Skip 'fi'
            
            return ParseResult(
                success=True,
                value=IfConditional(
                    condition=condition,
                    then_part=then_part,
                    elif_parts=elif_parts,
                    else_part=else_part
                ),
                position=pos
            )
        
        return Parser(parse_if_statement)
    
    def _build_while_loop(self) -> Parser[WhileLoop]:
        """Build parser for while/do/done loops."""
        def parse_while_loop(tokens: List[Token], pos: int) -> ParseResult[WhileLoop]:
            """Parse while loop."""
            # Check for 'while' keyword
            if pos >= len(tokens) or tokens[pos].value != 'while':
                return ParseResult(success=False, error="Expected 'while'", position=pos)
            
            pos += 1  # Skip 'while'
            
            # Parse condition (until 'do')
            condition_tokens = []
            while pos < len(tokens):
                token = tokens[pos]
                # Check for 'do' keyword (either DO token type or WORD with value 'do')
                if (token.type.name == 'DO' and token.value == 'do') or \
                   (token.type.name == 'WORD' and token.value == 'do'):
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    # Check if next token is 'do'
                    if pos + 1 < len(tokens):
                        next_token = tokens[pos + 1]
                        if (next_token.type.name == 'DO' and next_token.value == 'do') or \
                           (next_token.type.name == 'WORD' and next_token.value == 'do'):
                            break
                condition_tokens.append(token)
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'do' in while loop", position=pos)
            
            # Parse the condition
            condition_result = self.commands.statement_list.parse(condition_tokens, 0)
            if not condition_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse while condition: {condition_result.error}", 
                                 position=pos)
            
            # Skip separator and 'do'
            if tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' after while condition", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close while loop", position=pos)
            
            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse while body: {body_result.error}", 
                                 position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            return ParseResult(
                success=True,
                value=WhileLoop(
                    condition=condition_result.value,
                    body=body_result.value
                ),
                position=pos
            )
        
        return Parser(parse_while_loop)

    def _build_until_loop(self) -> Parser[UntilLoop]:
        """Build parser for until/do/done loops."""
        def parse_until_loop(tokens: List[Token], pos: int) -> ParseResult[UntilLoop]:
            """Parse until loop."""
            if pos >= len(tokens) or tokens[pos].value != 'until':
                return ParseResult(success=False, error="Expected 'until'", position=pos)
            
            pos += 1  # Skip 'until'

            # Parse condition until 'do'
            condition_tokens = []
            while pos < len(tokens):
                token = tokens[pos]
                if (token.type.name == 'DO' and token.value == 'do') or \
                   (token.type.name == 'WORD' and token.value == 'do'):
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    if pos + 1 < len(tokens):
                        next_token = tokens[pos + 1]
                        if (next_token.type.name == 'DO' and next_token.value == 'do') or \
                           (next_token.type.name == 'WORD' and next_token.value == 'do'):
                            break
                condition_tokens.append(token)
                pos += 1

            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'do' in until loop", position=pos)

            condition_result = self.commands.statement_list.parse(condition_tokens, 0)
            if not condition_result.success:
                return ParseResult(success=False,
                                   error=f"Failed to parse until condition: {condition_result.error}",
                                   position=pos)

            if tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' after until condition", position=pos)
            pos += 1

            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1

            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')

            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close until loop", position=pos)

            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False,
                                   error=f"Failed to parse until body: {body_result.error}",
                                   position=pos)

            pos = done_pos + 1

            return ParseResult(
                success=True,
                value=UntilLoop(
                    condition=condition_result.value,
                    body=body_result.value
                ),
                position=pos
            )

        return Parser(parse_until_loop)
    
    def _build_for_loops(self) -> Parser[Union[ForLoop, CStyleForLoop]]:
        """Build parser for both traditional and C-style for loops."""
        # Try C-style first, then traditional
        return self._build_c_style_for_loop().or_else(self._build_traditional_for_loop())
    
    def _build_traditional_for_loop(self) -> Parser[ForLoop]:
        """Build parser for traditional for/in loops."""
        def parse_for_loop(tokens: List[Token], pos: int) -> ParseResult[ForLoop]:
            """Parse traditional for loop."""
            # Check for 'for' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'FOR' and tokens[pos].value != 'for'):
                return ParseResult(success=False, error="Expected 'for'", position=pos)
            
            pos += 1  # Skip 'for'
            
            # Parse variable name
            if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
                return ParseResult(success=False, error="Expected variable name after 'for'", position=pos)
            
            var_name = tokens[pos].value
            pos += 1

            # Skip optional newlines before checking for 'in'
            while pos < len(tokens) and tokens[pos].type.name == 'NEWLINE':
                pos += 1

            has_in_clause = False
            if pos < len(tokens) and (tokens[pos].type.name == 'IN' or tokens[pos].value == 'in'):
                has_in_clause = True
                pos += 1  # Skip 'in'
                while pos < len(tokens) and tokens[pos].type.name == 'NEWLINE':
                    pos += 1

            items: List[str]
            item_quote_types: List[Optional[str]]
            if has_in_clause:
                items = []
                item_quote_types = []
                # Parse items (words until 'do' or separator+do)
                while pos < len(tokens):
                    token = tokens[pos]
                    if token.type.name == 'DO' and token.value == 'do':
                        break
                    if token.type.name in ['SEMICOLON', 'NEWLINE']:
                        # Check if next token is 'do'
                        if (pos + 1 < len(tokens) and 
                            tokens[pos + 1].type.name == 'DO'):
                            break
                    if token.type.name in ['WORD', 'STRING', 'VARIABLE', 'COMPOSITE']:
                        items.append(self._format_token_value(token))
                        quote_type = getattr(token, 'quote_type', None)
                        item_quote_types.append(quote_type)
                        pos += 1
                    else:
                        break
            else:
                # No explicit list - default to positional parameters ("$@")
                items = ['$@']
                item_quote_types = ['"']
            
            # Skip optional separator before 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1

            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' in for loop", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close for loop", position=pos)
            
            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse for body: {body_result.error}", 
                                 position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            return ParseResult(
                success=True,
                value=ForLoop(
                    variable=var_name,
                    items=items,
                    body=body_result.value,
                    item_quote_types=item_quote_types
                ),
                position=pos
            )
        
        return Parser(parse_for_loop)
    
    def _build_c_style_for_loop(self) -> Parser[CStyleForLoop]:
        """Build parser for C-style for loops."""
        def parse_c_style_for(tokens: List[Token], pos: int) -> ParseResult[CStyleForLoop]:
            """Parse C-style for loop."""
            # Check for 'for' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'FOR' and tokens[pos].value != 'for'):
                return ParseResult(success=False, error="Expected 'for'", position=pos)
            
            # Check for '((' after 'for'
            if pos + 1 >= len(tokens) or (tokens[pos + 1].type.name != 'DOUBLE_LPAREN' and tokens[pos + 1].value != '(('):
                return ParseResult(success=False, error="Not a C-style for loop", position=pos)
            
            pos += 2  # Skip 'for' and '(('
            
            # Parse init expression (until ';')
            init_tokens = []
            while pos < len(tokens) and tokens[pos].value != ';':
                init_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected ';' after init expression", position=pos)
            pos += 1  # Skip ';'
            
            # Parse condition expression (until ';')
            cond_tokens = []
            while pos < len(tokens) and tokens[pos].value != ';':
                cond_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected ';' after condition expression", position=pos)
            pos += 1  # Skip ';'
            
            # Parse update expression (until '))')
            update_tokens = []
            while pos < len(tokens) and tokens[pos].type.name != 'DOUBLE_RPAREN' and tokens[pos].value != '))':
                update_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected '))' to close C-style for", position=pos)
            pos += 1  # Skip '))'
            
            # Skip separator and 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' after C-style for header", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close C-style for loop", position=pos)
            
            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse for body: {body_result.error}", 
                                 position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            # Convert token lists to strings
            init_expr = ' '.join(t.value for t in init_tokens) if init_tokens else None
            cond_expr = ' '.join(t.value for t in cond_tokens) if cond_tokens else None
            update_expr = ' '.join(t.value for t in update_tokens) if update_tokens else None
            
            return ParseResult(
                success=True,
                value=CStyleForLoop(
                    init_expr=init_expr,
                    condition_expr=cond_expr,
                    update_expr=update_expr,
                    body=body_result.value
                ),
                position=pos
            )
        
        return Parser(parse_c_style_for)
    
    def _build_case_statement(self) -> Parser[CaseConditional]:
        """Build parser for case/esac statements."""
        def parse_case_statement(tokens: List[Token], pos: int) -> ParseResult[CaseConditional]:
            """Parse case statement."""
            # Check for 'case' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'CASE' and tokens[pos].value != 'case'):
                return ParseResult(success=False, error="Expected 'case'", position=pos)
            
            pos += 1  # Skip 'case'
            
            # Parse expression (usually a variable or word)
            if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'VARIABLE', 'STRING']:
                return ParseResult(success=False, error="Expected expression after 'case'", position=pos)
            
            # Format the expression appropriately
            expr = self._format_token_value(tokens[pos])
            pos += 1
            
            # Expect 'in'
            if pos >= len(tokens) or (tokens[pos].type.name != 'IN' and tokens[pos].value != 'in'):
                return ParseResult(success=False, error="Expected 'in' after case expression", position=pos)
            
            pos += 1  # Skip 'in'
            
            # Skip optional separator
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse case items until 'esac'
            items = []
            while pos < len(tokens) and tokens[pos].value != 'esac':
                # Parse pattern(s)
                patterns = []
                
                # Parse first pattern
                if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'STRING']:
                    break
                
                patterns.append(CasePattern(tokens[pos].value))
                pos += 1
                
                # Parse additional patterns separated by '|'
                while pos < len(tokens) and tokens[pos].value == '|':
                    pos += 1  # Skip '|'
                    if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'STRING']:
                        return ParseResult(success=False, error="Expected pattern after '|'", position=pos)
                    patterns.append(CasePattern(tokens[pos].value))
                    pos += 1
                
                # Expect ')'
                if pos >= len(tokens) or tokens[pos].value != ')':
                    return ParseResult(success=False, error="Expected ')' after case pattern(s)", position=pos)
                
                pos += 1  # Skip ')'
                
                # Skip optional separator
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Parse commands until case terminator
                command_tokens = []
                while pos < len(tokens):
                    token = tokens[pos]
                    # Check for case terminators
                    if token.type.name == 'DOUBLE_SEMICOLON' or token.value == ';;':
                        break
                    if token.value == ';&' or token.value == ';;&':
                        break
                    # Check if next token is a pattern (word followed by ')')
                    if (pos + 1 < len(tokens) and 
                        token.type.name in ['WORD', 'STRING'] and 
                        tokens[pos + 1].value == ')'):
                        break
                    # Check for 'esac'
                    if token.value == 'esac':
                        break
                    command_tokens.append(token)
                    pos += 1
                
                # Parse the commands
                if command_tokens:
                    commands_result = self.commands.statement_list.parse(command_tokens, 0)
                    if not commands_result.success:
                        return ParseResult(success=False, 
                                         error=f"Failed to parse case commands: {commands_result.error}", 
                                         position=pos)
                    commands = commands_result.value
                else:
                    commands = CommandList(statements=[])
                
                # Get terminator
                terminator = ';;'  # Default
                if pos < len(tokens):
                    if tokens[pos].type.name == 'DOUBLE_SEMICOLON' or tokens[pos].value == ';;':
                        terminator = ';;'
                        pos += 1
                    elif tokens[pos].value == ';&':
                        terminator = ';&'
                        pos += 1
                    elif tokens[pos].value == ';;&':
                        terminator = ';;&'
                        pos += 1
                
                # Skip optional separator after terminator
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Create case item
                items.append(CaseItem(
                    patterns=patterns,
                    commands=commands,
                    terminator=terminator
                ))
            
            # Expect 'esac'
            if pos >= len(tokens) or tokens[pos].value != 'esac':
                return ParseResult(success=False, error="Expected 'esac' to close case statement", position=pos)
            
            pos += 1  # Skip 'esac'
            
            return ParseResult(
                success=True,
                value=CaseConditional(
                    expr=expr,
                    items=items
                ),
                position=pos
            )
        
        return Parser(parse_case_statement)
    
    def _build_select_loop(self) -> Parser[SelectLoop]:
        """Build parser for select/do/done loops."""
        def parse_select_loop(tokens: List[Token], pos: int) -> ParseResult[SelectLoop]:
            """Parse select loop."""
            # Check for 'select' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'SELECT' and tokens[pos].value != 'select'):
                return ParseResult(success=False, error="Expected 'select'", position=pos)
            
            pos += 1  # Skip 'select'
            
            # Parse variable name
            if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
                return ParseResult(success=False, error="Expected variable name after 'select'", position=pos)
            
            var_name = tokens[pos].value
            pos += 1
            
            # Expect 'in'
            if pos >= len(tokens) or (tokens[pos].type.name != 'IN' and tokens[pos].value != 'in'):
                return ParseResult(success=False, error="Expected 'in' after variable name", position=pos)
            
            pos += 1  # Skip 'in'
            
            # Parse items (words until 'do' or separator+do)
            items = []
            item_quote_types = []
            while pos < len(tokens):
                token = tokens[pos]
                if token.type.name == 'DO' and token.value == 'do':
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    # Check if next token is 'do'
                    if (pos + 1 < len(tokens) and 
                        tokens[pos + 1].type.name == 'DO'):
                        break
                if token.type.name in ['WORD', 'STRING', 'VARIABLE', 'COMMAND_SUB', 
                                      'COMMAND_SUB_BACKTICK', 'ARITH_EXPANSION', 'PARAM_EXPANSION']:
                    items.append(self._format_token_value(token))
                    
                    # Track quote type for strings
                    quote_type = getattr(token, 'quote_type', None)
                    item_quote_types.append(quote_type)
                    
                    pos += 1
                else:
                    break
            
            # Skip separator and 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' in select loop", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close select loop", position=pos)
            
            body_result = self.commands.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, 
                                 error=f"Failed to parse select body: {body_result.error}", 
                                 position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            return ParseResult(
                success=True,
                value=SelectLoop(
                    variable=var_name,
                    items=items,
                    item_quote_types=item_quote_types,
                    body=body_result.value,
                    redirects=[],  # TODO: Parse redirections if needed
                    background=False
                ),
                position=pos
            )
        
        return Parser(parse_select_loop)
    
    def _build_function_name(self) -> Parser[str]:
        """Parse a valid function name."""
        def parse_function_name(tokens: List[Token], pos: int) -> ParseResult[str]:
            """Parse and validate function name."""
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected function name", position=pos)
            
            token = tokens[pos]
            if token.type.name != 'WORD':
                return ParseResult(success=False, error="Expected function name", position=pos)
            
            # Validate function name (must start with letter or underscore)
            name = token.value
            if not name:
                return ParseResult(success=False, error="Empty function name", position=pos)
            
            # First character must be letter or underscore
            if not (name[0].isalpha() or name[0] == '_'):
                return ParseResult(success=False, 
                                 error=f"Invalid function name: {name} (must start with letter or underscore)", 
                                 position=pos)
            
            # Rest must be alphanumeric, underscore, or hyphen
            for char in name[1:]:
                if not (char.isalnum() or char in '_-'):
                    return ParseResult(success=False, 
                                     error=f"Invalid function name: {name} (contains invalid character '{char}')", 
                                     position=pos)
            
            # Check it's not a reserved word
            reserved = {'if', 'then', 'else', 'elif', 'fi', 'while', 'do', 'done', 
                       'for', 'case', 'esac', 'function', 'in', 'select'}
            if name in reserved:
                return ParseResult(success=False, 
                                 error=f"Reserved word cannot be function name: {name}", 
                                 position=pos)
            
            return ParseResult(success=True, value=name, position=pos + 1)
        
        return Parser(parse_function_name)
    
    def _parse_function_body(self, tokens: List[Token], pos: int) -> ParseResult[StatementList]:
        """Parse function body between { }."""
        # Expect {
        if pos >= len(tokens) or tokens[pos].value != '{':
            return ParseResult(success=False, error="Expected '{' to start function body", position=pos)
        outer_pos = pos + 1  # Track position in outer token stream
        
        # Skip optional newline after {
        if outer_pos < len(tokens) and tokens[outer_pos].type.name == 'NEWLINE':
            outer_pos += 1
        
        # Collect tokens until }
        body_tokens = []
        brace_count = 1
        
        while outer_pos < len(tokens) and brace_count > 0:
            token = tokens[outer_pos]
            if token.value == '{':
                brace_count += 1
            elif token.value == '}':
                brace_count -= 1
                if brace_count == 0:
                    break
            body_tokens.append(token)
            outer_pos += 1
        
        if brace_count > 0:
            return ParseResult(success=False, error="Unclosed function body", position=outer_pos)
        
        # Parse the body as a statement list
        if body_tokens:
            # For function bodies, we need stricter parsing
            statements = []
            inner_pos = 0  # Position within body_tokens
            
            # Skip leading separators
            while inner_pos < len(body_tokens) and body_tokens[inner_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                inner_pos += 1
            
            # Parse statements
            while inner_pos < len(body_tokens):
                # Try to parse a statement
                stmt_result = self.commands.statement.parse(body_tokens, inner_pos)
                if not stmt_result.success:
                    # Check if this is a real error or just end of statements
                    if inner_pos < len(body_tokens):
                        error = stmt_result.error
                        if "expected 'fi'" in error.lower():
                            error = "Syntax error in function body: missing 'fi' to close if statement"
                        elif "expected 'done'" in error.lower():
                            error = "Syntax error in function body: missing 'done' to close loop"
                        elif "expected 'esac'" in error.lower():
                            error = "Syntax error in function body: missing 'esac' to close case statement"
                        elif "expected 'then'" in error.lower():
                            error = "Syntax error in function body: missing 'then' in if statement"
                        else:
                            error = f"Invalid function body: {error}"
                        return ParseResult(success=False, error=error, position=outer_pos)
                    break
                
                statements.append(stmt_result.value)
                inner_pos = stmt_result.position
                
                # Skip separators
                while inner_pos < len(body_tokens) and body_tokens[inner_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    inner_pos += 1
            
            body_result = ParseResult(success=True, value=StatementList(statements=statements), position=inner_pos)
        else:
            # Empty body
            body_result = ParseResult(success=True, value=StatementList(statements=[]), position=0)
        
        outer_pos += 1  # Skip closing }
        
        return ParseResult(
            success=True,
            value=body_result.value,
            position=outer_pos
        )
    
    def _build_posix_function(self) -> Parser[FunctionDef]:
        """Parse POSIX-style function: name() { body }"""
        def parse_posix_function(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            """Parse POSIX function."""
            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Not a function definition", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Expect ()
            if pos + 1 >= len(tokens) or tokens[pos].value != '(' or tokens[pos + 1].value != ')':
                return ParseResult(success=False, error="Expected () after function name", position=pos)
            pos += 2
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_posix_function)
    
    def _build_function_keyword_style(self) -> Parser[FunctionDef]:
        """Parse function keyword style: function name { body }"""
        def parse_function_keyword(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            """Parse function with keyword."""
            # Check for 'function' keyword
            if pos >= len(tokens) or tokens[pos].value != 'function':
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1
            
            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Expected function name after 'function'", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_function_keyword)
    
    def _build_function_keyword_with_parens(self) -> Parser[FunctionDef]:
        """Parse function keyword with parentheses: function name() { body }"""
        def parse_function_with_parens(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            """Parse function with keyword and parentheses."""
            # Check for 'function' keyword
            if pos >= len(tokens) or tokens[pos].value != 'function':
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1
            
            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Expected function name after 'function'", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Expect ()
            if pos + 1 >= len(tokens) or tokens[pos].value != '(' or tokens[pos + 1].value != ')':
                return ParseResult(success=False, error="Expected () after function name", position=pos)
            pos += 2
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_function_with_parens)
    
    def _build_function_def(self) -> Parser[FunctionDef]:
        """Build parser for function definitions."""
        # Try all three forms: POSIX first (most specific), then keyword variants
        return (
            self._build_posix_function()
            .or_else(self._build_function_keyword_with_parens())
            .or_else(self._build_function_keyword_style())
        )
    
    def _build_break_statement(self) -> Parser[BreakStatement]:
        """Build parser for break statement."""
        def parse_break(tokens: List[Token], pos: int) -> ParseResult[BreakStatement]:
            """Parse break statement."""
            # Check for 'break' keyword
            if pos >= len(tokens) or tokens[pos].value != 'break':
                return ParseResult(success=False, error="Expected 'break'", position=pos)
            
            pos += 1  # Skip 'break'
            
            # Parse optional level (number)
            level = 1  # Default
            if pos < len(tokens) and tokens[pos].type.name == 'WORD':
                # Check if it's a number
                try:
                    level = int(tokens[pos].value)
                    pos += 1
                except ValueError:
                    pass  # Not a number, leave level as 1
            
            return ParseResult(
                success=True,
                value=BreakStatement(level=level),
                position=pos
            )
        
        return Parser(parse_break)
    
    def _build_continue_statement(self) -> Parser[ContinueStatement]:
        """Build parser for continue statement."""
        def parse_continue(tokens: List[Token], pos: int) -> ParseResult[ContinueStatement]:
            """Parse continue statement."""
            # Check for 'continue' keyword
            if pos >= len(tokens) or tokens[pos].value != 'continue':
                return ParseResult(success=False, error="Expected 'continue'", position=pos)
            
            pos += 1  # Skip 'continue'
            
            # Parse optional level (number)
            level = 1  # Default
            if pos < len(tokens) and tokens[pos].type.name == 'WORD':
                # Check if it's a number
                try:
                    level = int(tokens[pos].value)
                    pos += 1
                except ValueError:
                    pass  # Not a number, leave level as 1
            
            return ParseResult(
                success=True,
                value=ContinueStatement(level=level),
                position=pos
            )
        
        return Parser(parse_continue)
    
    def _build_subshell_group(self) -> Parser[SubshellGroup]:
        """Build parser for subshell group (...) syntax."""
        return between(
            self.tokens.lparen,
            self.tokens.rparen,
            lazy(lambda: self.commands.statement_list)
        ).map(lambda statements: SubshellGroup(statements=statements))
    
    def _build_brace_group(self) -> Parser[BraceGroup]:
        """Build parser for brace group {...} syntax."""
        return between(
            self.tokens.lbrace,
            self.tokens.rbrace,
            lazy(lambda: self.commands.statement_list)
        ).map(lambda statements: BraceGroup(statements=statements))
    
    def _format_token_value(self, token: Token) -> str:
        """Format token value appropriately based on token type."""
        if token.type.name == 'VARIABLE':
            # Variables need the $ prefix
            return f"${token.value}"
        elif token.type.name in ['COMMAND_SUB', 'COMMAND_SUB_BACKTICK', 
                                 'ARITH_EXPANSION', 'PARAM_EXPANSION']:
            # These already include their delimiters
            return token.value
        else:
            # Everything else uses raw value
            return token.value


# Convenience functions

def create_control_structure_parsers(config: Optional[ParserConfig] = None,
                                    token_parsers: Optional[TokenParsers] = None,
                                    command_parsers: Optional[CommandParsers] = None) -> ControlStructureParsers:
    """Create and return a ControlStructureParsers instance.
    
    Args:
        config: Optional parser configuration
        token_parsers: Optional token parsers
        command_parsers: Optional command parsers
        
    Returns:
        Initialized ControlStructureParsers object
    """
    return ControlStructureParsers(config, token_parsers, command_parsers)
