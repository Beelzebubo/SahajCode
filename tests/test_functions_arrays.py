"""Tests for user-defined functions (garu/firta) and arrays."""
import pytest
from sahajcode.lexer import tokenize, TokenType
from sahajcode.parser import parse, Parser
from sahajcode.symbol_table import analyze_types
from sahajcode.codegen import generate_c
from sahajcode.ast_nodes import NodeType


def _compile(source):
    tokens = tokenize(source)
    ast = parse(tokens)
    symtab, errors = analyze_types(ast)
    assert not errors, errors
    return generate_c(ast, symtab)


def _run(source):
    import subprocess
    import sys
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        np_path = Path(tmpdir) / 'prog.np'
        np_path.write_text(source)
        result = subprocess.run([sys.executable, '-m', 'sahajcode.cli', 'run', str(np_path)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()


# --- Lexer ---

def test_function_keywords_lexed():
    tokens = tokenize('garu firta')
    assert tokens[0].type == TokenType.GARU
    assert tokens[1].type == TokenType.FIRTA


def test_devanagari_function_keywords_lexed():
    tokens = tokenize('गर्नु फर्क')
    assert tokens[0].type == TokenType.GARU
    assert tokens[1].type == TokenType.FIRTA


def test_array_token_lexed():
    tokens = tokenize('[ ]')
    assert tokens[0].type == TokenType.LBRACKET
    assert tokens[1].type == TokenType.RBRACKET


# --- Parser ---

def test_parse_function_def():
    src = 'garu add(a, b)\n    rakha x = a + b\n    firta x\nantya\n'
    ast = parse(tokenize(src)).statements
    assert ast[0].node_type == NodeType.FUNCTION_DEF
    assert ast[0].name == 'add'
    assert ast[0].params == ['a', 'b']
    assert ast[0].body[1].node_type == NodeType.RETURN


def test_parse_array_literal():
    ast = parse(tokenize('rakha a = [1, 2, 3]\n')).statements
    assert ast[0].value.node_type == NodeType.ARRAY_LITERAL
    assert ast[0].value.size == 3


def test_parse_index_assignment():
    ast = parse(tokenize('a[0] = 5\n')).statements
    assert ast[0].node_type == NodeType.ASSIGNMENT
    assert ast[0].target.node_type == NodeType.INDEX


# --- Symbol table ---

def test_function_registered():
    src = 'garu add(a, b)\n    rakha x = a + b\n    firta x\nantya\n'
    symtab, errors = analyze_types(parse(tokenize(src)))
    assert not errors
    fn = symtab.lookup_function('add')
    assert fn is not None
    assert fn.params == ['a', 'b']


# --- Code generation ---

def test_function_in_c_output():
    c = _compile('garu double(n)\n    rakha x = n * 2\n    firta x\nantya\n'
                 'rakha r = double(21)\nbhana r\n')
    assert 'int double(int n)' in c


# --- Integration (compile + run) ---

def test_function_call_returns():
    out = _run('garu add(a, b)\n    rakha x = a + b\n    firta x\nantya\n'
               'rakha r = add(3, 4)\nbhana r\n')
    assert out == '7'


def test_array_sum_loop():
    out = _run('rakha nums = [10, 20, 30, 40]\n'
               'rakha sum = 0\nrakha i = 0\n'
               'jaba i < 4 samma\n    sum = sum + nums[i]\n    i = i + 1\nantya\n'
               'bhana sum\n')
    assert out == '100'


def test_array_index_assignment():
    out = _run('rakha nums = [1, 2, 3]\nnums[0] = 99\nbhana nums[0]\n')
    assert out == '99'


def test_function_and_array_together():
    out = _run('garu add(a, b)\n    rakha x = a + b\n    firta x\nantya\n'
               'rakha nums = [10, 20, 30, 40]\n'
               'rakha sum = 0\nrakha i = 0\n'
               'jaba i < 4 samma\n    sum = sum + nums[i]\n    i = i + 1\nantya\n'
               'rakha r = add(sum, 5)\nbhana r\n'
               'nums[0] = 99\nbhana nums[0]\n')
    assert out == '105\n99'


def test_string_function():
    out = _run('garu greet(n)\n    firta "hello"\nantya\n'
               'bhana greet(1)\n')
    assert out == 'hello'
