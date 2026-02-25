#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile

KUDA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KUDA_DIR)

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from interpreter import Interpreter, RuntimeError_

VERSION = "0.2.3"
    
HELP = """
Kuda v0.2.2 - Fast ML language that compiles to C

Usage:
  kuda <file.kuda>            Run file (compiles to C, super fast!)
  kuda py <file.kuda>         Run with Python libraries (numpy, etc.)
  kuda build <file.kuda>      Build a standalone binary
  kuda interp <file.kuda>     Interpreter mode (for debugging)
  kuda version                Show version
  kuda help                   Show this help

Examples:
  kuda hello.kuda             # Just run it!
  kuda py ml.kuda             # Run with Python libraries
  kuda build game.kuda        # Creates ./game binary
  kuda interp debug.kuda      # Debug mode
"""

def parse_source(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()

def run_interpreted(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    try:
        ast = parse_source(source)
        interpreter = Interpreter()
        interpreter.run(ast)
    except LexerError as e:
        print(str(e)); sys.exit(1)
    except ParseError as e:
        print(str(e)); sys.exit(1)
    except RuntimeError_ as e:
        print(str(e)); sys.exit(1)
    except Exception as e:
        print(f"[Kuda] Error: {e}"); sys.exit(1)

def compile_to_binary(path, output=None, silent=False):
    from codegen import CGenerator, CompileError

    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        ast = parse_source(source)
    except (LexerError, ParseError) as e:
        print(str(e)); sys.exit(1)

    try:
        gen = CGenerator()
        c_code = gen.generate(ast)
    except Exception as e:
        print(f"[Kuda CompileError] {e}"); sys.exit(1)

    c_file = tempfile.NamedTemporaryFile(suffix='.c', delete=False, mode='w', encoding='utf-8')
    c_file.write(c_code)
    c_file.close()

    if output is None:
        output = os.path.splitext(path)[0]

    cmd = ['gcc', '-O2', '-o', output, c_file.name, '-lm']
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(c_file.name)

    if result.returncode != 0:
        if not silent:
            print(f"[Kuda] Compilation error:\n{result.stderr}")
        return None

    return output

def run_fast(path):
    tmp_bin = tempfile.NamedTemporaryFile(delete=False, suffix='')
    tmp_bin.close()

    binary = compile_to_binary(path, output=tmp_bin.name, silent=False)

    if binary is None:
        try: os.unlink(tmp_bin.name)
        except: pass
        print("[Kuda] Falling back to interpreter...")
        run_interpreted(path)
        return

    result = subprocess.run([binary])
    try: os.unlink(binary)
    except: pass
    sys.exit(result.returncode)

def run_python_mode(path):
    from python_bridge import PythonBridge
    bridge = PythonBridge()
    bridge.run(path)

def check_file(path):
    if not path.endswith('.kuda'):
        print(f"[Kuda] Expected a .kuda file, got: '{path}'")
        sys.exit(1)
    if not os.path.exists(path):
        print(f"[Kuda] File not found: '{path}'")
        sys.exit(1)

def main():
    args = sys.argv[1:]

    if not args or args[0] in ('help', '--help', '-h'):
        print(HELP); return

    if args[0] in ('version', '--version', '-v'):
        print(f"Kuda v{VERSION}"); return

    # kuda py <file.kuda>
    if args[0] == 'py':
        if len(args) < 2:
            print("[Kuda] Missing file. Usage: kuda py <file.kuda>"); sys.exit(1)
        check_file(args[1])
        run_python_mode(args[1]); return

    # kuda build <file.kuda>
    if args[0] == 'build':
        if len(args) < 2:
            print("[Kuda] Missing file. Usage: kuda build <file.kuda>"); sys.exit(1)
        check_file(args[1])
        out = compile_to_binary(args[1])
        if out:
            print(f"[Kuda] Built: {out}")
        return

    # kuda interp <file.kuda>
    if args[0] == 'interp':
        if len(args) < 2:
            print("[Kuda] Missing file. Usage: kuda interp <file.kuda>"); sys.exit(1)
        check_file(args[1])
        run_interpreted(args[1]); return

    # kuda run <file.kuda> - old style still supported
    if args[0] == 'run':
        if len(args) < 2:
            print("[Kuda] Missing file. Usage: kuda <file.kuda>"); sys.exit(1)
        check_file(args[1])
        run_fast(args[1]); return

    # kuda <file.kuda> - default simplest usage
    if args[0].endswith('.kuda'):
        check_file(args[0])
        run_fast(args[0]); return

    print(f"[Kuda] Unknown command: '{args[0]}'. Run 'kuda help'.")
    sys.exit(1)

if __name__ == '__main__':
    main()