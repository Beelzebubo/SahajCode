import pytest
from src.lexer import tokenize
from src.parser import parse
from src.symbol_table import analyze_types
from src.codegen import generate_c


def test_generate_c_simple():
    source = 'rakha x = 7\nbhana x\n'
    tokens = tokenize(source)
    ast = parse(tokens)
    symtab, errors = analyze_types(ast)
    assert not errors
    c_code = generate_c(ast, symtab)
    # Verify variable declaration and print statement in generated C
    # Variables are declared at top with default value, then assigned
    assert 'int x = 0;' in c_code   # declaration with default
    assert 'x = 7;' in c_code       # actual assignment
    assert 'printf("%d\\n", x);' in c_code
