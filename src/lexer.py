"""
SahajCode Lexer (Tokenizer)
Implements a DFA-based single-pass scanner for SahajCode source code.
Supports Unicode Nepali identifiers and bilingual keywords.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    # Keywords
    RAKHA = auto()      # rakha (keep/put) - declare/assign
    BHANA = auto()      # bhana (say/speak) - print
    SUNA = auto()       # suna (listen) - input
    YEDI = auto()       # yedi (if)
    BHANE = auto()      # bhane (then)
    NATRA = auto()      # natra (else)
    JABA = auto()       # jaba (while)
    SAMMA = auto()      # samma (until)
    GUMA = auto()       # guma (loop/turn) - for
    DEKHI = auto()      # dekhi (from)
    ANTYA = auto()      # antya (end)
    THIK = auto()       # thik (true)
    GALAT = auto()      # galat (false)
    
    # Literals and identifiers
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    
    # Operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %
    EQUAL_EQUAL = auto() # ==
    NOT_EQUAL = auto()  # !=
    LESS = auto()       # <
    GREATER = auto()    # >
    LESS_EQUAL = auto()  # <=
    GREATER_EQUAL = auto() # >=
    EQUAL = auto()      # =
    
    # Structure
    COMMENT = auto()
    NEWLINE = auto()
    EOF = auto()
    
    # Error
    ERROR = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, Line {self.line})"


# All 13 reserved keywords (English transliteration)
KEYWORDS = {
    'rakha': TokenType.RAKHA,
    'bhana': TokenType.BHANA,
    'suna': TokenType.SUNA,
    'yedi': TokenType.YEDI,
    'bhane': TokenType.BHANE,
    'natra': TokenType.NATRA,
    'jaba': TokenType.JABA,
    'samma': TokenType.SAMMA,
    'guma': TokenType.GUMA,
    'dekhi': TokenType.DEKHI,
    'antya': TokenType.ANTYA,
    'thik': TokenType.THIK,
    'galat': TokenType.GALAT,
}

# Nepali script keywords (Unicode Devanagari - U+0900 to U+097F)
NEPALI_KEYWORDS = {
    'राख': TokenType.RAKHA,
    'भन': TokenType.BHANA,
    'सुन': TokenType.SUNA,
    'यदि': TokenType.YEDI,
    'भने': TokenType.BHANE,
    'नत्र': TokenType.NATRA,
    'जब': TokenType.JABA,
    'सम्म': TokenType.SAMMA,
    'गुमा': TokenType.GUMA,
    'देखि': TokenType.DEKHI,
    'अन्त्य': TokenType.ANTYA,
    'ठीक': TokenType.THIK,
    'गलत': TokenType.GALAT,
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """Convert source string to token list."""
        while self.pos < len(self.source):
            char = self.source[self.pos]
            
            # Skip whitespace (but not newlines)
            if char in ' \t':
                self.pos += 1
                self.column += 1
                continue
            
            # Newline
            if char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.pos += 1
                self.line += 1
                self.column = 1
                continue
            
            # Windows newline
            if char == '\r' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.column))
                self.pos += 2
                self.line += 1
                self.column = 1
                continue
            
            # Comment
            if char == '#':
                self._scan_comment()
                continue
            
            # String
            if char == '"':
                self._scan_string()
                continue
            
            # Operators (check multi-char first)
            if self.pos + 1 < len(self.source):
                two_char = self.source[self.pos:self.pos + 2]
                if two_char == '==':
                    self.tokens.append(Token(TokenType.EQUAL_EQUAL, '==', self.line, self.column))
                    self.pos += 2
                    self.column += 2
                    continue
                if two_char == '!=':
                    self.tokens.append(Token(TokenType.NOT_EQUAL, '!=', self.line, self.column))
                    self.pos += 2
                    self.column += 2
                    continue
                if two_char == '<=':
                    self.tokens.append(Token(TokenType.LESS_EQUAL, '<=', self.line, self.column))
                    self.pos += 2
                    self.column += 2
                    continue
                if two_char == '>=':
                    self.tokens.append(Token(TokenType.GREATER_EQUAL, '>=', self.line, self.column))
                    self.pos += 2
                    self.column += 2
                    continue
            
            # Single-char operators
            single_ops = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '<': TokenType.LESS,
                '>': TokenType.GREATER,
                '=': TokenType.EQUAL,
            }
            
            if char in single_ops:
                self.tokens.append(Token(single_ops[char], char, self.line, self.column))
                self.pos += 1
                self.column += 1
                continue
            
            # Numbers
            if char.isdigit():
                self._scan_number()
                continue
            
            # Identifiers and keywords (including Unicode Nepali)
            if char.isalpha() or char == '_' or self._is_devanagari(char):
                self._scan_identifier()
                continue
            
            # Unknown character
            self.tokens.append(Token(TokenType.ERROR, char, self.line, self.column))
            self.pos += 1
            self.column += 1
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens
    
    def _scan_comment(self):
        """Scan a line comment starting with #."""
        start = self.pos
        start_col = self.column
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            self.pos += 1
        self.tokens.append(Token(TokenType.COMMENT, self.source[start:self.pos], self.line, start_col))
    
    def _scan_string(self):
        """Scan a double-quoted string."""
        start_col = self.column
        self.pos += 1  # skip opening quote
        start = self.pos
        
        while self.pos < len(self.source):
            if self.source[self.pos] == '"':
                value = self.source[start:self.pos]
                self.tokens.append(Token(TokenType.STRING, value, self.line, start_col))
                self.pos += 1
                self.column = self.pos - self.line_start() + 1
                return
            if self.source[self.pos] == '\n':
                # Unterminated string
                self.tokens.append(Token(TokenType.ERROR, 'unterminated_string', self.line, start_col))
                self.line += 1
                self.pos += 1
                self.column = 1
                return
            self.pos += 1
        
        # Reached EOF without closing quote
        self.tokens.append(Token(TokenType.ERROR, 'unterminated_string', self.line, start_col))
    
    def _scan_number(self):
        """Scan an integer number."""
        start = self.pos
        start_col = self.column
        
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self.pos += 1
        
        value = self.source[start:self.pos]
        self.tokens.append(Token(TokenType.NUMBER, value, self.line, start_col))
    
    def _scan_identifier(self):
        """Scan an identifier or keyword."""
        start = self.pos
        start_col = self.column
        
        while self.pos < len(self.source):
            char = self.source[self.pos]
            # Accept alphanumeric, underscore, and Devanagari chars for identifiers
            if char.isalnum() or char == '_' or self._is_devanagari(char):
                self.pos += 1
                continue
            break
        
        value = self.source[start:self.pos]
        
        # Check English keywords
        if value in KEYWORDS:
            self.tokens.append(Token(KEYWORDS[value], value, self.line, start_col))
        # Check Nepali keywords
        elif value in NEPALI_KEYWORDS:
            self.tokens.append(Token(NEPALI_KEYWORDS[value], value, self.line, start_col))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, value, self.line, start_col))
    
    def line_start(self) -> int:
        """Return the starting position of the current line."""
        end = self.source.rfind('\n', 0, self.pos)
        return end + 1 if end >= 0 else 0
    
    def _is_devanagari(self, char: str) -> bool:
        """Check if character is Devanagari Unicode (Nepali script)."""
        if len(char) != 1:
            return False
        code = ord(char)
        return 0x0900 <= code <= 0x097F


def tokenize(source: str) -> List[Token]:
    """Convenience function to tokenize source code."""
    lexer = Lexer(source)
    return lexer.tokenize()


if __name__ == '__main__':
    # Quick test
    test_code = '''# Test program
bhana "Namaste"
rakha x = 10
yedi x > 5 bhane
    bhana x
natra
    bhana "Thulo"
antya
'''
    for tok in tokenize(test_code):
        print(tok)