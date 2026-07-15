import pytest
from src.lexer import tokenize
from src.parser import parse
from src.ast_nodes import NodeType

def test_parse_var_decl_and_print():
    source = 'rakha x = 5\nbhana x\n'
    tokens = tokenize(source)
    ast = parse(tokens)
    assert len(ast.statements) == 2
    var_decl, print_stmt = ast.statements
    assert var_decl.node_type == NodeType.VAR_DECL
    assert var_decl.name == 'x'
    assert print_stmt.node_type == NodeType.PRINT
    assert print_stmt.expr.node_type.name == 'IDENTIFIER' or print_stmt.expr.node_type == NodeType.IDENTIFIER
