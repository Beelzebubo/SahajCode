import pytest
from src.lexer import tokenize, TokenType

def test_simple_tokens():
    source = 'rakha x = 10\nbhana x\n'
    tokens = tokenize(source)
    # Filter out NEWLINE and EOF for simplicity
    filtered = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    types = [t.type for t in filtered]
    assert types == [TokenType.RAKHA, TokenType.IDENTIFIER, TokenType.EQUAL, TokenType.NUMBER,
                    TokenType.BHANA, TokenType.IDENTIFIER]
