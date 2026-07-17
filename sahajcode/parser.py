"""
SahajCode Parser
Recursive descent LL(1) parser for SahajCode language.
Converts token stream into an Abstract Syntax Tree.
"""

from typing import List, Optional, Tuple
from .ast_nodes import (
    NodeType, Program, VarDecl, Assignment, Print, Input,
    If, While, For, BinaryOp, UnaryOp, Number, String, Identifier, Comment, ASTNode
)
from .lexer import Token, TokenType
from .error_reporter import ERROR_MESSAGES


class ParseError(Exception):
    """Exception raised for syntax errors."""
    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        if token:
            super().__init__(f"{message} at line {token.line}")
        else:
            super().__init__(message)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[Tuple[int, str, str, Token]] = []
    
    def parse(self) -> Program:
        """Parse tokens into AST."""
        statements, _ = self._parse_program()
        return Program(statements=statements, node_type=NodeType.PROGRAM)
    
    def _parse_program(self) -> Tuple[List[ASTNode], bool]:
        """Parse program: statement* EOF"""
        statements = []
        
        while self._current().type != TokenType.EOF:
            stmt, ok = self._parse_statement()
            if ok and stmt is not None:
                statements.append(stmt)
        
        return statements, True
    
    def _parse_statement(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse a single statement."""
        tok = self._current()
        
        if tok.type == TokenType.RAKHA:
            return self._parse_var_decl()
        elif tok.type == TokenType.BHANA:
            return self._parse_print()
        elif tok.type == TokenType.SUNA:
            return self._parse_input()
        elif tok.type == TokenType.YEDI:
            return self._parse_if()
        elif tok.type == TokenType.JABA:
            return self._parse_while()
        elif tok.type == TokenType.GUMA:
            return self._parse_for()
        elif tok.type == TokenType.IDENTIFIER:
            return self._parse_assignment()
        elif tok.type == TokenType.COMMENT:
            comment = Comment(text=tok.value, line=tok.line, node_type=NodeType.COMMENT)
            self._advance()
            return comment, True
        elif tok.type == TokenType.NEWLINE:
            self._advance()
            return None, True
        
        # NATRA (else) is handled specially by _parse_if, return False without advancing
        # to signal that we're at an else clause
        if tok.type == TokenType.NATRA:
            return None, False
        
        # Unhandled token (e.g., ANTYA at statement level, operators, etc.)
        # Skip it and return True to keep parsing
        self._advance()
        return None, True
    
    def _parse_var_decl(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: rakha IDENTIFIER = expression NEWLINE"""
        rakha_tok = self._current()
        self._consume(TokenType.RAKHA)
        
        name_tok = self._current()
        if name_tok.type != TokenType.IDENTIFIER:
            self._error("परिभाषित गर्न वेरिएबलको नाम चाहिन्छ", "'rakha x = ...' ढाँचामा नाम राख्नुहोस्", name_tok)
            return None, False
        name = name_tok.value
        self._advance()
        
        if not self._consume(TokenType.EQUAL):
            self._error("'rakha' लाई '=' चाहिन्छ", "'rakha x = मान' ढाँचा प्रयोग गर्नुहोस्", name_tok)
            return None, False
        
        expr, ok = self._parse_expression()
        if not ok:
            return None, False
        
        self._consume_newline()
        
        return VarDecl(name=name, value=expr, line=rakha_tok.line, node_type=NodeType.VAR_DECL), True
    
    def _parse_print(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: bhana expression NEWLINE"""
        bhana_tok = self._current()
        self._consume(TokenType.BHANA)
        
        expr, ok = self._parse_expression()
        if not ok:
            return None, False
        
        self._consume_newline()
        
        return Print(expr=expr, line=bhana_tok.line, node_type=NodeType.PRINT), True
    
    def _parse_input(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: suna IDENTIFIER NEWLINE"""
        suna_tok = self._current()
        self._consume(TokenType.SUNA)
        
        name_tok = self._current()
        if name_tok.type != TokenType.IDENTIFIER:
            self._error("'suna' लाई वेरिएबलको नाम चाहिन्छ", "'suna x' ढाँचा प्रयोग गर्नुहोस्", name_tok)
            return None, False
        
        name = name_tok.value
        self._advance()
        
        self._consume_newline()
        
        return Input(name=name, line=suna_tok.line, node_type=NodeType.INPUT), True
    
    def _parse_if(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: yedi expression bhane NEWLINE statement+ [natra NEWLINE statement+] antya NEWLINE"""
        yedi_tok = self._current()
        self._consume(TokenType.YEDI)
        
        condition, ok = self._parse_expression()
        if not ok:
            return None, False
        
        if not self._consume(TokenType.BHANE):
            cat = ERROR_MESSAGES['E002']
            self._error(cat['nepali'], cat['english'], self._prev(), cat['suggestion'])
            self._recover_to_antya()
            return None, False
        
        self._consume_newline()
        
        then_branch, _ = self._parse_block(TokenType.ANTYA)
        
        else_branch = []
        if self._current().type == TokenType.NATRA:
            self._advance()
            self._consume_newline()
            else_branch, _ = self._parse_block(TokenType.ANTYA)
        
        if self._current().type != TokenType.ANTYA:
            cat = ERROR_MESSAGES['E004']
            self._error(cat['nepali'].format(keyword='yedi'),
                       cat['english'].format(keyword='yedi'), yedi_tok,
                       cat['suggestion'].format(keyword='yedi'))
            return None, False
        
        self._consume(TokenType.ANTYA)
        self._consume_newline()
        
        return If(condition=condition, then_branch=then_branch, else_branch=else_branch, line=yedi_tok.line, node_type=NodeType.IF), True
    
    def _parse_while(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: jaba expression samma NEWLINE statement+ antya NEWLINE"""
        jaba_tok = self._current()
        self._consume(TokenType.JABA)
        
        condition, ok = self._parse_expression()
        if not ok:
            return None, False
        
        if not self._consume(TokenType.SAMMA):
            self._error("'jaba' लाई 'samma' (until) चाहिन्छ", "'jaba cond samma' ढाँचा प्रयोग गर्नुहोस्", self._prev())
            self._recover_to_antya()
            return None, False
        
        self._consume_newline()
        
        body, _ = self._parse_block(TokenType.ANTYA)
        
        if self._current().type != TokenType.ANTYA:
            cat = ERROR_MESSAGES['E004']
            self._error(cat['nepali'].format(keyword='jaba'),
                       cat['english'].format(keyword='jaba'), jaba_tok,
                       cat['suggestion'].format(keyword='jaba'))
            return None, False
        
        self._consume(TokenType.ANTYA)
        self._consume_newline()
        
        return While(condition=condition, body=body, line=jaba_tok.line, node_type=NodeType.WHILE), True
    
    def _parse_for(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: guma IDENTIFIER = NUMBER dekhi NUMBER NEWLINE statement+ antya NEWLINE"""
        guma_tok = self._current()
        self._consume(TokenType.GUMA)
        
        var_tok = self._current()
        if var_tok.type != TokenType.IDENTIFIER:
            self._error("'guma' लाई वेरिएबलको नाम चाहिन्छ", "'guma i = ...' ढाँचा प्रयोग गर्नुहोस्", var_tok)
            return None, False
        var = var_tok.value
        self._advance()
        
        if not self._consume(TokenType.EQUAL):
            self._error("'guma' लाई '=' चाहिन्छ", "'guma i = मान' ढाँचा प्रयोग गर्नुहोस्", guma_tok)
            return None, False
        
        start_tok = self._current()
        if start_tok.type != TokenType.NUMBER:
            self._error("'dekhi' (from) अगाडि संख्या चाहिन्छ", "'guma i = 1 dekhi 10' ढाँचा प्रयोग गर्नुहोस्", start_tok)
            return None, False
        start = Number(value=int(start_tok.value), line=start_tok.line, node_type=NodeType.NUMBER)
        self._advance()
        
        if not self._consume(TokenType.DEKHI):
            self._error("'dekhi' (from) चाहिन्छ", "'guma i = 1 dekhi 10' ढाँचा प्रयोग गर्नुहोस्", self._prev())
            return None, False
        
        end_tok = self._current()
        if end_tok.type != TokenType.NUMBER:
            self._error("'dekhi' (from) पछि संख्या चाहिन्छ", "'guma i = 1 dekhi 10' ढाँचा प्रयोग गर्नुहोस्", end_tok)
            return None, False
        end = Number(value=int(end_tok.value), line=end_tok.line, node_type=NodeType.NUMBER)
        self._advance()
        
        self._consume_newline()
        
        body, _ = self._parse_block(TokenType.ANTYA)
        
        if self._current().type != TokenType.ANTYA:
            cat = ERROR_MESSAGES['E004']
            self._error(cat['nepali'].format(keyword='guma'),
                       cat['english'].format(keyword='guma'), guma_tok,
                       cat['suggestion'].format(keyword='guma'))
            return None, False
        
        self._consume(TokenType.ANTYA)
        self._consume_newline()
        
        return For(var=var, start=start, end=end, body=body, line=guma_tok.line, node_type=NodeType.FOR), True
    
    def _parse_assignment(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse: IDENTIFIER = expression NEWLINE"""
        name_tok = self._current()
        if name_tok.type != TokenType.IDENTIFIER:
            return None, False
        name = name_tok.value
        self._advance()
        
        if self._current().type != TokenType.EQUAL:
            return None, False
        self._advance()
        
        expr, ok = self._parse_expression()
        if not ok:
            return None, False
        
        self._consume_newline()
        
        return Assignment(name=name, value=expr, line=name_tok.line, node_type=NodeType.ASSIGNMENT), True
    
    # Expression parsing with precedence
    def _parse_expression(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse expression: comparison (('<'|'>'|'=='|'!='|'<='|'>=') comparison)*"""
        return self._parse_comparison()
    
    def _parse_comparison(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse comparison: additive (('>='|'<='|'=='|'!='|'<'|'>') additive)*"""
        left, ok = self._parse_additive()
        if not ok:
            return None, False
        
        while self._match_type([TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL, 
                               TokenType.EQUAL_EQUAL, TokenType.NOT_EQUAL,
                               TokenType.LESS, TokenType.GREATER]):
            op = self._prev().value
            right, ok = self._parse_additive()
            if not ok:
                return None, False
            left = BinaryOp(op=op, left=left, right=right, line=left.line, node_type=NodeType.BINARY_OP)
        
        return left, True
    
    def _parse_additive(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse additive: term (('+'|'-') term)*"""
        left, ok = self._parse_term()
        if not ok:
            return None, False
        
        while self._match_type([TokenType.PLUS, TokenType.MINUS]):
            op = self._prev().value
            right, ok = self._parse_term()
            if not ok:
                return None, False
            left = BinaryOp(op=op, left=left, right=right, line=left.line, node_type=NodeType.BINARY_OP)
        
        return left, True
    
    def _parse_term(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse term: factor (('*'|'/'|'%') factor)*"""
        left, ok = self._parse_factor()
        if not ok:
            return None, False
        
        while self._match_type([TokenType.STAR, TokenType.SLASH, TokenType.PERCENT]):
            op = self._prev().value
            right, ok = self._parse_factor()
            if not ok:
                return None, False
            left = BinaryOp(op=op, left=left, right=right, line=left.line, node_type=NodeType.BINARY_OP)
        
        return left, True
    
    def _parse_factor(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse factor: ('+'|'-') factor | primary"""
        if self._match_type([TokenType.MINUS]):
            op = self._prev().value
            operand, ok = self._parse_factor()
            if not ok:
                return None, False
            return UnaryOp(op=op, operand=operand, line=self._prev().line, node_type=NodeType.UNARY_OP), True
        
        return self._parse_primary()
    
    def _parse_primary(self) -> Tuple[Optional[ASTNode], bool]:
        """Parse primary: NUMBER | STRING | IDENTIFIER"""
        tok = self._current()
        
        if self._match_type([TokenType.NUMBER]):
            return Number(value=int(self._prev().value), line=tok.line, node_type=NodeType.NUMBER), True
        
        if self._match_type([TokenType.STRING]):
            return String(value=self._prev().value, line=tok.line, node_type=NodeType.STRING), True
        
        if self._match_type([TokenType.THIK]):
            return Number(value=1, line=tok.line, node_type=NodeType.NUMBER), True
        
        if self._match_type([TokenType.GALAT]):
            return Number(value=0, line=tok.line, node_type=NodeType.NUMBER), True
        
        if self._match_type([TokenType.IDENTIFIER]):
            return Identifier(name=self._prev().value, line=tok.line, node_type=NodeType.IDENTIFIER), True
        
        return None, False
    
    def _parse_block(self, terminator: TokenType) -> Tuple[List[ASTNode], bool]:
        """Parse statements until terminator (antya)."""
        statements = []
        
        while self._current().type != terminator and self._current().type != TokenType.EOF:
            # NATRA indicates the start of an else-branch in an if-statement
            if self._current().type == TokenType.NATRA:
                break
            stmt, ok = self._parse_statement()
            if ok and stmt is not None:
                statements.append(stmt)
        
        return statements, True
    
    # Utility methods
    def _current(self) -> Token:
        return self.tokens[self.pos]
    
    def _prev(self) -> Token:
        return self.tokens[self.pos - 1] if self.pos > 0 else self.tokens[0]
    
    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok
    
    def _consume(self, expected: TokenType) -> bool:
        if self._current().type == expected:
            self._advance()
            return True
        return False
    
    def _consume_newline(self) -> bool:
        return self._consume(TokenType.NEWLINE)
    
    def _match_type(self, types: List[TokenType]) -> bool:
        for t in types:
            if self._current().type == t:
                self._advance()
                return True
        return False
    
    def _error(self, nepali_msg: str, english_msg: str, token: Token, suggestion: str = ""):
        """Record a parse error."""
        self.errors.append((token.line, nepali_msg, english_msg, token, suggestion))
    
    def _recover_to_antya(self):
        """Panic-mode recovery: skip tokens until NEWLINE or ANTYA."""
        while self._current().type not in [TokenType.ANTYA, TokenType.NEWLINE, TokenType.EOF]:
            self._advance()


def parse(tokens: List[Token]) -> Program:
    """Parse tokens into an AST."""
    parser = Parser(tokens)
    return parser.parse()


if __name__ == '__main__':
    from lexer import tokenize
    test = '''bhana "Namaste"
rakha x = 10
yedi x > 5 bhane
    bhana x
antya
'''
    tokens = tokenize(test)
    ast = parse(tokens)
    for stmt in ast.statements:
        print(stmt)