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

VERSION = "0.2.9"

HELP = """
Kuda v0.2.9 - Fast ML language that compiles to C

Usage:
  kuda <file.kuda>            Run file (compiles to C, super fast!)
  kuda py <file.kuda>         Run with Python libraries (numpy, etc.)
  kuda build <file.kuda>      Build a standalone binary
  kuda interp <file.kuda>     Interpreter mode (for debugging)
  kuda repl                   Interactive REPL
  kuda version                Show version
  kuda help                   Show this help

Examples:
  kuda hello.kuda             # Just run it!
  kuda py ml.kuda             # Run with Python libraries
  kuda build game.kuda        # Creates ./game binary
  kuda interp debug.kuda      # Debug mode
  kuda repl                   # Interactive console
"""

def parse_source(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()

def run_interpreted(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    interpreter = Interpreter()
    try:
        ast = parse_source(source)
        interpreter.run(ast)
    except LexerError as e:
        print(str(e)); sys.exit(1)
    except ParseError as e:
        print(str(e)); sys.exit(1)
    except RuntimeError_ as e:
        print(str(e)); sys.exit(1)
    except Exception as e:
        line = interpreter.current_line
        prefix = f"[Kuda] Line {line}: " if line else "[Kuda] Error: "
        print(f"{prefix}{e}"); sys.exit(1)

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
        c_code = gen.generate(ast, source_file=os.path.abspath(path))
    except Exception as e:
        print(f"[Kuda CompileError] {e}"); sys.exit(1)

    c_file = tempfile.NamedTemporaryFile(suffix='.c', delete=False, mode='w', encoding='utf-8')
    c_file.write(c_code)
    c_file.close()

    if output is None:
        output = os.path.splitext(path)[0]

    cmd = ['gcc', '-O2', '-o', output, c_file.name]
    # Add extra .c files from extern "file.c" statements
    src_dir = os.path.dirname(os.path.abspath(path))
    for cf in gen.extra_c_files:
        if not os.path.isabs(cf):
            cf = os.path.join(src_dir, cf)
        cmd.append(cf)
    cmd += ['-lm'] + gen.link_flags
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(c_file.name)

    if result.returncode != 0:
        if not silent:
            print(f"[Kuda] Compilation error:\n{result.stderr}")
        return None

    return output

def run_fast(path):
    # Sprawdź czy używa DataBuilder — jeśli tak, od razu interpreter
    try:
        with open(path) as _f: _src = _f.read()
        from lexer import Lexer
        from parser import Parser
        _tokens = Lexer(_src).tokenize()
        _ast = Parser(_tokens).parse()
        from codegen import CGenerator
        _cg = CGenerator()
        # Fallback do interpretera tylko jeśli używa DataBuilder bez net
        from parser import NetNode, YieldNode, TryNode
        _has_net = any(isinstance(s, NetNode) for s in _ast.statements)
        if _cg._uses_data_builder(_ast) and not _has_net:
            run_interpreted(path)
            return
        # Fallback do interpretera jeśli kod używa yield lub try/fail
        def _ast_has_node(stmts, node_type):
            for s in stmts:
                if isinstance(s, node_type):
                    return True
                for attr in ('body', 'else_body', 'statements', 'try_body', 'fail_body'):
                    sub = getattr(s, attr, None)
                    if isinstance(sub, list) and _ast_has_node(sub, node_type):
                        return True
                if hasattr(s, 'cases'):
                    for _, body in s.cases:
                        if _ast_has_node(body, node_type):
                            return True
                if hasattr(s, 'fail_clauses'):
                    for _, _, body in s.fail_clauses:
                        if _ast_has_node(body, node_type):
                            return True
            return False
        if _ast_has_node(_ast.statements, YieldNode):
            run_interpreted(path)
            return
        if _ast_has_node(_ast.statements, TryNode):
            run_interpreted(path)
            return
    except Exception:
        pass

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

def run_repl():
    from lexer import Lexer, LexerError
    from parser import Parser, ParseError
    from interpreter import Interpreter, RuntimeError_

    interp = Interpreter()
    print(f"Kuda v{VERSION} REPL — type 'exit' or Ctrl+C to quit")

    buf = []  # bufor na wieloliniowe bloki (fun, if, each itp.)

    while True:
        try:
            prompt = '... ' if buf else '>>> '
            try:
                line = input(prompt)
            except EOFError:
                print()
                break

            if line.strip() in ('exit', 'quit'):
                break

            buf.append(line)
            source = '\n'.join(buf)

            # Sprawdź czy blok jest niekompletny (ostatnia niepusta linia kończy się ':')
            stripped = line.rstrip()
            if stripped.endswith(':') or (buf and stripped == ''):
                # Jeśli pusta linia i mamy bufor — próbuj wykonać
                if stripped == '' and len(buf) > 1:
                    pass  # spróbujemy wykonać poniżej
                else:
                    continue  # czekaj na więcej linii

            # Spróbuj sparsować i wykonać
            try:
                tokens = Lexer(source).tokenize()
                ast    = Parser(tokens).parse()
                interp.run(ast)
                buf = []  # sukces — wyczyść bufor
            except ParseError as e:
                msg = str(e)
                # Niekompletny blok — czekaj na więcej linii
                if 'INDENT' in msg or 'EOF' in msg or 'expected' in msg.lower():
                    continue
                print(msg)
                buf = []
            except LexerError as e:
                print(str(e))
                buf = []
            except RuntimeError_ as e:
                print(str(e))
                buf = []
            except Exception as e:
                line_no = interp.current_line
                prefix  = f'[Kuda] Line {line_no}: ' if line_no else '[Kuda] '
                print(f'{prefix}{e}')
                buf = []

        except KeyboardInterrupt:
            print()
            if buf:
                buf = []  # anuluj bufor, nie wychodzi z REPL
            else:
                break


def main():
    args = sys.argv[1:]

    if not args or args[0] in ('help', '--help', '-h'):
        print(HELP); return

    if args[0] in ('version', '--version', '-v'):
        print(f"Kuda v{VERSION}"); return

    # kuda repl
    if args[0] == 'repl':
        run_repl(); return

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