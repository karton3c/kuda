# Kuda v0.2.1 - Python Bridge
# Handles 'kuda py file.kuda' mode
# Lets Kuda code use Python libraries like numpy, pandas, etc.

import sys
import os

KUDA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KUDA_DIR)

from lexer import Lexer, LexerError
from parser import Parser, ParseError, UseNode
from interpreter import Interpreter, RuntimeError_


class PythonBridge:
    """
    Runs Kuda in Python mode.
    - 'use numpy as np' imports Python's numpy and makes it available
    - 'use pandas as pd' imports Python's pandas
    - All standard Kuda features still work
    - Slower than pure C mode but has access to all Python libraries
    """

    def run(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
        except LexerError as e:
            print(str(e)); sys.exit(1)
        except ParseError as e:
            print(str(e)); sys.exit(1)

        # Scan for 'use' statements and import Python libraries
        interpreter = Interpreter()
        for stmt in ast.statements:
            if isinstance(stmt, UseNode):
                self._import_library(stmt, interpreter)

        # Run the program with interpreter (Python libraries accessible)
        try:
            interpreter.run(ast)
        except RuntimeError_ as e:
            print(str(e)); sys.exit(1)
        except Exception as e:
            print(f"[Kuda] Error: {e}"); sys.exit(1)

    def _import_library(self, node, interpreter):
        module_name = node.module
        alias = node.alias or module_name

        try:
            module = __import__(module_name)
            # Handle submodules like 'sklearn.linear_model'
            # by importing the full module
            parts = module_name.split('.')
            for part in parts[1:]:
                module = getattr(module, part)

            # Register module in interpreter's global environment
            # This lets Kuda code call things like np.array(), pd.DataFrame()
            interpreter.global_env.set(alias, _PyModuleWrapper(module, alias))
            print(f"[Kuda py] Loaded: {module_name} as {alias}")

        except ImportError:
            print(f"[Kuda py] Warning: Could not import '{module_name}'")
            print(f"[Kuda py] Try: pip install {module_name}")


class _PyModuleWrapper:
    """
    Wraps a Python module so Kuda can call its functions.
    When Kuda does: np.array([1,2,3])
    This wrapper intercepts the call and delegates to numpy.
    """

    def __init__(self, module, name):
        self._module = module
        self._name = name

    def get_attr(self, attr_name):
        if hasattr(self._module, attr_name):
            attr = getattr(self._module, attr_name)
            if callable(attr):
                return _PyFuncWrapper(attr)
            return attr
        raise AttributeError(f"'{self._name}' has no attribute '{attr_name}'")

    def __repr__(self):
        return f'<kuda py module: {self._name}>'


class _PyFuncWrapper:
    """
    Wraps a Python function so Kuda's interpreter can call it.
    """

    def __init__(self, func):
        self._func = func

    def __call__(self, args):
        return self._func(*args)

    def __repr__(self):
        return f'<kuda py function: {self._func.__name__}>'