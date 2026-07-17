"""
SahajCode CLI
Command-line interface for SahajCode transpiler.
Commands: run, build, init
"""

import argparse
import os
import sys
import subprocess
from .error_reporter import ErrorReporter, ERROR_MESSAGES
from .lexer import TokenType
import tempfile
from pathlib import Path
from . import __version__


def report_lexical_errors(tokens, reporter: ErrorReporter, source: str = ""):
    """Map lexical ERROR tokens to the PRD E001/E005 catalog messages."""
    lines = source.split('\n') if source else []
    for token in tokens:
        if token.type != TokenType.ERROR:
            continue
        # Show the user's actual source line (not the internal token text)
        src_line = lines[token.line - 1] if 1 <= token.line <= len(lines) else token.value
        # Caret points at the exact offending column (PRD §9.2)
        caret = ' ' * max(token.column - 1, 0) + '^'
        if token.value == 'unterminated_string':
            cat = ERROR_MESSAGES['E001']
            nepali = f"[ERROR] Line {token.line}: {cat['nepali']}"
            english = f"[ENGLISH] Line {token.line}: {cat['english']}"
            reporter.add_error(nepali, english, token.line, src_line, cat['suggestion'], caret)
        else:
            cat = ERROR_MESSAGES['E005']
            char = token.value
            nepali = f"[ERROR] Line {token.line}: {cat['nepali'].format(char=char)}"
            english = f"[ENGLISH] Line {token.line}: {cat['english'].format(char=char)}"
            reporter.add_error(nepali, english, token.line, src_line, cat['suggestion'], caret)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='sahaj',
        description='SahajCode - Nepali Programming Language Transpiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument('--version', action='store_true', help='Show version')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show transpilation steps')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run command
    run_parser = subparsers.add_parser('run', help='Transpile, compile, and run a SahajCode program')
    run_parser.add_argument('file', help='Path to .np source file')
    run_parser.add_argument('--keep-c', '-k', action='store_true', help='Preserve generated .c file')
    run_parser.add_argument('--output', '-o', default='a.out', help='Name of output binary')
    
    # build command
    build_parser = subparsers.add_parser('build', help='Transpile to C without compiling')
    build_parser.add_argument('file', help='Path to .np source file')
    build_parser.add_argument('--output', '-o', help='Name of output C file')
    build_parser.add_argument('--show', '-s', action='store_true', help='Print C code to stdout')
    
    # init command
    init_parser = subparsers.add_parser('init', help='Create a new project skeleton')
    init_parser.add_argument('project', nargs='?', default='.', help='Project directory name')
    
    args = parser.parse_args()
    
    if args.version:
        print(f"SahajCode v{__version__} — Nepali Programming Language")
        return 0
    
    if args.command == 'run':
        return cmd_run(args)
    elif args.command == 'build':
        return cmd_build(args)
    elif args.command == 'init':
        return cmd_init(args)
    else:
        parser.print_help()
        return 6  # No input (system error) - per PRD


def _transpile(args, file_path, source):
    """Shared lex → parse → analyze pipeline. Returns (c_code, None) or (None, exit_code)."""
    error_reporter = ErrorReporter()
    
    from .lexer import tokenize
    tokens = tokenize(source)
    report_lexical_errors(tokens, error_reporter, source)
    if error_reporter.has_errors():
        print(error_reporter.format_report())
        return None, 1
    
    from .parser import Parser
    parser = Parser(tokens)
    ast = parser.parse()
    if parser.errors:
        for line, nepali_msg, english_msg, token, suggestion in parser.errors:
            error_reporter.add_error(nepali_msg, english_msg, token.line, token.value, suggestion)
        print(error_reporter.format_report())
        return None, 2
    
    from .symbol_table import analyze_types
    symtab, errors = analyze_types(ast)
    if errors:
        for line, msg, var in errors:
            error_reporter.add_error(msg, msg, line, var)
        print(error_reporter.format_report())
        return None, 3
    
    from .codegen import generate_c
    return generate_c(ast, symtab, source), 0


def cmd_run(args):
    """Execute: sahaj run <file.np>"""
    file_path = Path(args.file).resolve()
    
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return 7
    
    if args.verbose:
        print(f"[1/4] Reading {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read file: {e}")
        return 6
    
    if args.verbose:
        print("[2/4] Transpiling...")
    
    c_code, code = _transpile(args, file_path, source)
    if code:
        return code
    
    # Write C to temp file
    c_path = file_path.with_suffix('.c')
    with open(c_path, 'w', encoding='utf-8') as f:
        f.write(c_code)
    
    if args.verbose and not args.keep_c:
        print(f"[5/4] Compiling with gcc...")
    
    # Compile
    binary_path = file_path.parent / args.output
    try:
        result = subprocess.run(
            ['gcc', '-std=c99', '-o', str(binary_path), str(c_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Map C errors back to source if possible
            print("[ERROR] Compilation failed:")
            print(result.stderr)
            return 4  # C compilation error
    except FileNotFoundError:
        print("[ERROR] gcc not found. Please install gcc or MinGW.")
        return 6  # System error
    
    # Run
    if args.verbose:
        print("[6/4] Running binary...")
    
    try:
        result = subprocess.run([str(binary_path)], capture_output=True, text=True, timeout=10)
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        if result.returncode != 0:
            return 5  # Runtime error
    except Exception as e:
        print(f"[ERROR] Runtime error: {e}", file=sys.stderr)
        return 5
    finally:
        # Cleanup
        if binary_path.exists():
            if not args.keep_c:
                os.remove(binary_path)
            else:
                print(f"\n[Info] Binary saved to: {binary_path}")
        if c_path.exists() and not args.keep_c:
            os.remove(c_path)
    
    return 0


def cmd_build(args):
    """Execute: sahaj build <file.np>"""
    file_path = Path(args.file).resolve()
    
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return 7
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"[ERROR] Could not read file: {e}")
        return 6
    
    c_code, code = _transpile(args, file_path, source)
    if code:
        return code
    
    if args.show:
        print(c_code)
        return 0
    
    output_path = Path(args.output).resolve() if args.output else file_path.with_suffix('.c')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(c_code)
    
    print(f"[Info] C code written to: {output_path}")
    return 0


def cmd_init(args):
    """Execute: sahaj init <project>"""
    project_path = Path(args.project)
    
    if project_path.exists() and project_path != Path('.'):
        print(f"[ERROR] Directory already exists: {project_path}")
        return 6
    
    if project_path != Path('.'):
        project_path.mkdir(parents=True, exist_ok=True)
    
    # Create sample .np file
    sample = '''# Mero pahilo SahajCode program
bhana "Namaste Sathi"
'''
    
    sample_path = project_path / 'hello.np'
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(sample)
    
    print(f"[Info] Created project in: {project_path.resolve()}")
    print(f"[Info] Sample file: {sample_path}")
    # Create README.md
    readme_path = project_path / 'README.md'
    readme_content = "# SahajCode Project\n\nThis project was generated by `sahaj init`.\n"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    # Create .sahaj config directory and placeholder config.yaml
    sahaj_dir = project_path / '.sahaj'
    sahaj_dir.mkdir(exist_ok=True)
    config_path = sahaj_dir / 'config.yaml'
    config_path.write_text('# Configuration placeholder\n')
    
    return 0


if __name__ == '__main__':
    sys.exit(main())