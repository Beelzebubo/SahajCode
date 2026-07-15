import os
import tempfile
import subprocess
import sys
from pathlib import Path


def run_cli(args):
    """Run the sahaj CLI as a subprocess and return exit code and output."""
    # Ensure the module can be executed via python -m
    result = subprocess.run([sys.executable, '-m', 'src.cli'] + args,
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def test_run_simple_program():
    with tempfile.TemporaryDirectory() as tmpdir:
        np_path = Path(tmpdir) / 'hello.np'
        np_path.write_text('bhana "Namaste"\n')
        rc, out = run_cli(['run', str(np_path)])
        assert rc == 0
        assert 'Namaste' in out
