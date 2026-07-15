"""Comprehensive tests covering all features and edge cases."""
import pytest
import tempfile
import subprocess
import sys
from pathlib import Path

from src.lexer import tokenize, TokenType
from src.parser import parse, Parser
from src.symbol_table import analyze_types
from src.codegen import generate_c
from src.ast_nodes import NodeType


def run_cli(args):
    """Run the sahaj CLI as a subprocess and return (rc, output)."""
    result = subprocess.run([sys.executable, '-m', 'src.cli'] + args,
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


class TestLexer:
    def test_all_keywords_recognized(self):
        for kw in ['rakha', 'bhana', 'suna', 'yedi', 'bhane', 'natra',
                   'jaba', 'samma', 'guma', 'dekhi', 'antya', 'thik', 'galat']:
            tokens = tokenize(kw)
            assert tokens[0].type != TokenType.ERROR, f"Keyword {kw} not recognized"

    def test_devanagari_keywords(self):
        for kw in ['राख', 'भन', 'सुन', 'यदि', 'भने', 'नत्र', 'जब', 'सम्म',
                   'गुमा', 'देखि', 'अन्त्य', 'ठीक', 'गलत']:
            tokens = tokenize(kw)
            assert tokens[0].type != TokenType.ERROR, f"Devanagari keyword {kw} not recognized"

    def test_unterminated_string(self):
        tokens = tokenize('bhana "unterminated\n')
        assert any(t.type == TokenType.ERROR for t in tokens)

    def test_invalid_character(self):
        tokens = tokenize('rakha x = @5')
        assert any(t.type == TokenType.ERROR for t in tokens)


class TestParser:
    def test_simple_program(self):
        tokens = tokenize('rakha x = 5\nbhana x\n')
        ast = parse(tokens)
        assert len(ast.statements) == 2
        assert ast.statements[0].node_type == NodeType.VAR_DECL
        assert ast.statements[1].node_type == NodeType.PRINT

    def test_addition_increment(self):
        source = 'rakha i = 1\ni = i + 1\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        assignment = ast.statements[1]
        assert assignment.node_type == NodeType.ASSIGNMENT
        # The value should be a BinaryOp with op '+'
        assert assignment.value.node_type == NodeType.BINARY_OP
        assert assignment.value.op == '+'

    def test_if_else(self):
        source = 'yedi 1 bhane\n    bhana 1\nnatra\n    bhana 0\nantya\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        if_stmt = ast.statements[0]
        assert if_stmt.node_type == NodeType.IF
        assert len(if_stmt.then_branch) == 1
        assert len(if_stmt.else_branch) == 1

    def test_while_loop(self):
        source = 'jaba 1 samma\n    bhana 1\nantya\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        assert ast.statements[0].node_type == NodeType.WHILE

    def test_for_loop(self):
        source = 'guma i = 1 dekhi 3\n    bhana i\nantya\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        for_stmt = ast.statements[0]
        assert for_stmt.node_type == NodeType.FOR
        assert for_stmt.start.value == 1
        assert for_stmt.end.value == 3

    def test_syntax_error_detected(self):
        source = 'yedi 1 bhana 1\nantya\n'  # bhana instead of bhane
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = parser.parse()
        assert len(parser.errors) > 0


class TestSymbolTable:
    def test_redeclaration_error(self):
        source = 'rakha x = 5\nrakha x = 10\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        assert any('पहिले' in str(e) for e in errors)

    def test_undeclared_variable(self):
        source = 'x = 5\n'  # x not declared
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        assert len(errors) > 0


class TestCodegen:
    def test_simple_print(self):
        source = 'rakha x = 7\nbhana x\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'int x = 0;' in c_code
        assert 'x = 7;' in c_code
        assert 'printf("%d\\n", x);' in c_code

    def test_if_else_c_code(self):
        source = 'yedi 1 bhane\n    bhana 1\nnatra\n    bhana 0\nantya\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'if (1) {' in c_code
        assert 'else {' in c_code

    def test_addition_c_code(self):
        source = 'rakha x = 5\nx = x + 1\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'x = (x + 1);' in c_code

    def test_string_assignment(self):
        source = 'rakha s = "hello"\nbhana s\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'char s[256] = {0};' in c_code
        assert 'strcpy(s, "hello");' in c_code

    def test_string_comparison_uses_strcmp(self):
        source = 'rakha s = "hi"\nyedi s == "hi" bhane\n    bhana 1\nantya\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'strcmp(s, "hi") == 0' in c_code
        assert '(s == "hi")' not in c_code

    def test_string_concat_in_var_decl(self):
        source = 'rakha g = "Namaste " + "Sahaj"\nbhana g\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'strcpy(g, "Namaste ");' in c_code
        assert 'strcat(g, "Sahaj");' in c_code
        assert 'g = ("Namaste " + "Sahaj")' not in c_code

    def test_string_int_concat_coerces(self):
        source = 'rakha age = 25\nrakha info = "age " + age\nbhana info\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'sprintf(' in c_code
        assert 'strcat(info' in c_code

    def test_string_concat_in_print(self):
        source = 'rakha age = 25\nbhana "Value: " + age\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        assert 'sprintf(' in c_code

    def test_source_line_comments_f3_1(self):
        source = 'rakha x = 5\nbhana x\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab, source)
        assert '/* Line 1: rakha x = 5 */' in c_code
        assert '/* Line 2: bhana x */' in c_code

    def test_source_line_comments_fallback_without_source(self):
        source = 'rakha x = 5\n'
        tokens = tokenize(source)
        ast = parse(tokens)
        symtab, errors = analyze_types(ast)
        c_code = generate_c(ast, symtab)
        # Without source text, comment has no ': <code>' suffix
        assert '/* Line 1 */' in c_code
        assert '/* Line 1: rakha' not in c_code


class TestCLI:
    def test_run_simple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'hello.np'
            np_path.write_text('bhana "Namaste"\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 0
            assert 'Namaste' in out

    def test_run_with_arithmetic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha x = 1\nx = x + 2\nbhana x\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 0
            assert '3' in out

    def test_run_with_if_else(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('yedi 1 bhane\n    bhana "yes"\nnatra\n    bhana "no"\nantya\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 0
            assert 'yes' in out
            assert 'no' not in out

    def test_invalid_character_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha x = @5\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 1

    def test_run_string_comparison(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha nam = "Ram"\nyedi nam == "Ram" bhane\n    bhana "Milne"\nnatra\n    bhana "Na Milne"\nantya\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 0
            assert 'Milne' in out

    def test_run_string_concat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha name = "Ram"\nrakha age = 25\nbhana name + " is " + age\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 0
            assert 'Ram is 25' in out

    def test_run_division_by_zero_literal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha x = 10\nrakha y = x / 0\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 5
            assert 'Cannot divide by zero' in out

    def test_run_unterminated_string_e001(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('bhana "oops\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 1
            assert 'Unterminated string' in out

    def test_run_invalid_character_e005(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha x = @5\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 1
            assert 'Invalid character' in out

    def test_caret_points_at_column(self):
        """PRD §9.2: caret marks the exact column, not the whole line (E005)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            # '@' is at column 11 of "rakha x = @5"
            np_path.write_text('rakha x = @5\n')
            rc, out = run_cli(['run', str(np_path)])
            caret_line = next(l for l in out.split('\n') if l.strip().startswith('^'))
            # A whole-line caret would sit right after the 10-space indent (index 10)
            assert caret_line.index('^') > 10

    def test_run_division_by_variable_zero_e006(self):
        """PRD E006: division by a variable divisor is caught at runtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('rakha x = 10\nrakha y = 0\nrakha z = x / y\nbhana z\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 5
            assert 'Cannot divide by zero' in out

    def test_syntax_error_e002_catalog(self):
        """PRD E002: missing 'bhane' uses the catalog message + suggestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('yedi x > 5\n    bhana "hi"\nantya\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 2
            assert "'yedi' (if) requires 'bhane' (then)" in out
            assert 'Did you mean: yedi x > 5 bhane' in out

    def test_syntax_error_e004_catalog(self):
        """PRD E004: missing 'antya' uses the catalog message + suggestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('yedi 1 bhane\n    bhana "hi"\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 2
            assert "Missing 'antya' (end) for 'yedi'" in out
            assert "Every 'yedi' must be closed with 'antya'" in out

    def test_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            np_path.write_text('yedi 1 bhana 1\nantya\n')
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 2

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'nonexistent.np'
            rc, out = run_cli(['run', str(np_path)])
            assert rc == 7

    def test_build_generates_c(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            np_path = Path(tmpdir) / 'test.np'
            c_path = Path(tmpdir) / 'test.c'
            np_path.write_text('bhana "hello"\n')
            rc, out = run_cli(['build', str(np_path), '-o', str(c_path)])
            assert rc == 0
            assert c_path.exists()

    def test_version(self):
        rc, out = run_cli(['--version'])
        assert rc == 0
        assert 'SahajCode' in out
