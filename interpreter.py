from parser import *
import sys
import random
import numpy as np
from data_builder import DataBuilder

# === Sygnały kontroli przepływu ===

class GiveSignal(Exception):
    def __init__(self, value): self.value = value

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass


# === Środowisko (zmienne) ===

class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError(f"Undefined variable: '{name}'")

    def set(self, name, value):
        self.vars[name] = value

    def assign(self, name, value):
        """Przypisuje do istniejącej zmiennej w odpowiednim zakresie"""
        if name in self.vars:
            self.vars[name] = value
            return True
        if self.parent:
            return self.parent.assign(name, value)
        return False

    def set_or_assign(self, name, value):
        if not self.assign(name, value):
            self.set(name, value)


# === Klasy Kuda ===

class KudaFunction:
    def __init__(self, name, params, body, env):
        self.name = name
        self.params = params
        self.body = body
        self.env = env  # domknięcie

    def __repr__(self):
        return f'<fun {self.name}>'


class KudaInstance:
    def __init__(self, model_name, env):
        self.model_name = model_name
        self.env = env
        self.attrs = {}

    def get_attr(self, name):
        if name in self.attrs:
            return self.attrs[name]
        # Szukaj metody w klasie
        try:
            method = self.env.get(name)
            if isinstance(method, KudaFunction):
                return BoundMethod(self, method)
        except:
            pass
        raise AttributeError(f"'{self.model_name}' has no attribute '{name}'")

    def set_attr(self, name, value):
        self.attrs[name] = value

    def __repr__(self):
        return f'<{self.model_name} instance>'


class BoundMethod:
    def __init__(self, instance, func):
        self.instance = instance
        self.func = func

    def __repr__(self):
        return f'<bound method {self.func.name}>'


class KudaModel:
    def __init__(self, name, body, env):
        self.name = name
        self.body = body
        self.env = env

    def __repr__(self):
        return f'<model {self.name}>'


# === Interpreter ===

class RuntimeError_(Exception):
    def __init__(self, msg, line=None):
        if line:
            super().__init__(f'[Kuda RuntimeError] Line {line}: {msg}')
        else:
            super().__init__(f'[Kuda RuntimeError] {msg}')


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self._setup_builtins()

    def _setup_builtins(self):
        """Wbudowane funkcje Kuda"""
        env = self.global_env

        import random, math, time as _time

        # Podstawowe
        env.set('len',   lambda args: len(args[0]))
        env.set('range', lambda args: list(range(*[int(a) for a in args])))
        env.set('int',   lambda args: int(args[0]))
        env.set('float', lambda args: float(args[0]))
        env.set('str',   lambda args: str(args[0]))
        env.set('type',  lambda args: type(args[0]).__name__)
        env.set('input', lambda args: input(args[0] if args else ''))
        env.set('abs',   lambda args: abs(args[0]))
        env.set('max',   lambda args: max(args) if len(args) > 1 else max(args[0]))
        env.set('min',   lambda args: min(args) if len(args) > 1 else min(args[0]))
        env.set('sum',   lambda args: sum(args[0]))
        env.set('round', lambda args: round(args[0], int(args[1]) if len(args) > 1 else 0))
        env.set('rand',        lambda args: random.randint(int(args[0]), int(args[1])))
        env.set('rand_float',  lambda args: random.random())
        env.set('rand_normal', lambda args: random.gauss(args[0], args[1]))
        env.set('shuffle',     lambda args: random.shuffle(args[0]) or args[0])

        # Stringi
        env.set('cut',   lambda args: args[0].split(args[1] if len(args) > 1 else None))
        env.set('swap',  lambda args: args[0].replace(args[1], args[2]))
        env.set('caps',  lambda args: args[0].upper())
        env.set('small', lambda args: args[0].lower())
        env.set('trim',  lambda args: args[0].strip())
        env.set('merge', lambda args: args[0].join(args[1]))

        # Listy
        env.set('add',   lambda args: args[0].append(args[1]))
        env.set('del',   lambda args: args[0].remove(args[1]))
        env.set('sort',  lambda args: args[0].sort())
        env.set('rev',   lambda args: args[0].reverse())
        env.set('grab',  lambda args: args[0].pop())
        env.set('fd',    lambda args: args[0].index(args[1]))
        env.set('cnt',   lambda args: args[0].count(args[1]))

        # Matematyka
        env.set('prw',   lambda args: math.sqrt(args[0]))
        env.set('pot',   lambda args: math.pow(args[0], args[1]))
        env.set('dwn',   lambda args: math.floor(args[0]))
        env.set('up',    lambda args: math.ceil(args[0]))
        env.set('pi',    math.pi)

        # Pliki
        env.set('read',  lambda args: open(args[0], 'r', encoding='utf-8').read())
        env.set('write', lambda args: open(args[0], 'w', encoding='utf-8').write(args[1]))

        # Time
        env.set('wait',  lambda args: _time.sleep(args[0]))
        env.set('time',  lambda args: _time.time())

        # DataBuilder
        env.set('data', DataBuilder())

        # Matrix i ML
        env.set('Matrix', lambda args: np.random.randn(int(args[0]), int(args[1])) * 0.1 if len(args)==2 else np.zeros((int(args[0]), int(args[1]))))
        env.set('mat_rand', lambda args: np.random.randn(int(args[0]), int(args[1])) * np.sqrt(2.0/(args[0]+args[1])))
        env.set('mat_zeros', lambda args: np.zeros((int(args[0]), int(args[1]))))
        env.set('mat_mul', lambda args: np.dot(args[0], args[1]))
        env.set('sigmoid', lambda args: 1.0 / (1.0 + np.exp(-args[0])))
        env.set('relu', lambda args: np.maximum(0, args[0]))
        env.set('mat_sigmoid', lambda args: 1.0 / (1.0 + np.exp(-args[0])))
        env.set('mat_relu', lambda args: np.maximum(0, args[0]))
        env.set('mat_sigmoid_deriv', lambda args: args[0] * (1 - args[0]))
        env.set('mat_T', lambda args: args[0].T)

    def run(self, ast):
        self.exec_block(ast.statements, self.global_env)

    def exec_block(self, statements, env):
        for stmt in statements:
            self.exec(stmt, env)

    def exec(self, node, env):
        # Importy
        if isinstance(node, UseNode):
            return self.exec_use(node, env)

        # Przypisanie
        if isinstance(node, AssignNode):
            return self.exec_assign(node, env)

        # Skrócone przypisanie += -= *= /=
        if isinstance(node, AugAssignNode):
            current = env.get(node.name)
            value = self.eval(node.value, env)
            if node.op == '+': result = current + value
            elif node.op == '-': result = current - value
            elif node.op == '*': result = current * value
            elif node.op == '/': result = current / value
            env.set_or_assign(node.name, result)
            return

        # Przypisanie do indeksu d["klucz"] = x
        if isinstance(node, IndexAssignNode):
            obj = self.eval(node.target.obj, env)
            idx = self.eval(node.target.index, env)
            val = self.eval(node.value, env)
            obj[idx] = val
            return

        # out()
        if isinstance(node, OutNode):
            val = self.eval(node.value, env)
            print(self._to_str(val))
            return

        # if/othif/other
        if isinstance(node, IfNode):
            return self.exec_if(node, env)

        # repeat
        if isinstance(node, RepeatNode):
            return self.exec_repeat(node, env)

        # each z unpackingiem
        if isinstance(node, EachUnpackNode):
            return self.exec_each_unpack(node, env)

        # each
        if isinstance(node, EachNode):
            return self.exec_each(node, env)

        # til
        if isinstance(node, TilNode):
            return self.exec_til(node, env)

        # fun
        if isinstance(node, FunNode):
            func = KudaFunction(node.name, node.params, node.body, env)
            env.set(node.name, func)
            return

        # model
        if isinstance(node, ModelNode):
            return self.exec_model(node, env)

        # give
        if isinstance(node, GiveNode):
            value = self.eval(node.value, env)
            raise GiveSignal(value)

        # try/fail
        if isinstance(node, TryNode):
            return self.exec_try(node, env)

        # break/continue
        if isinstance(node, BreakNode):
            raise BreakSignal()

        if isinstance(node, ContinueNode):
            raise ContinueSignal()

        # Wyrażenia jako instrukcje (np. wywołania funkcji)
        self.eval(node, env)

    def exec_use(self, node, env):
        try:
            import importlib
            mod = importlib.import_module(node.module)
            env.set(node.module, mod)
        except ImportError:
            raise RuntimeError_(f"Nie możon zaimportować: '{node.module}'")

    def exec_assign(self, node, env):
        value = self.eval(node.value, env)
        if isinstance(node.name, str):
            env.set_or_assign(node.name, value)
        elif isinstance(node.name, AttrNode):
            # np. self.x = 5
            obj = self.eval(node.name.obj, env)
            if isinstance(obj, KudaInstance):
                obj.set_attr(node.name.attr, value)
            else:
                setattr(obj, node.name.attr, value)

    def exec_if(self, node, env):
        for cond, body in node.cases:
            if self.eval(cond, env):
                child_env = Environment(env)
                self.exec_block(body, child_env)
                return
        if node.else_body:
            child_env = Environment(env)
            self.exec_block(node.else_body, child_env)

    def exec_repeat(self, node, env):
        count = int(self.eval(node.count, env))
        for _ in range(count):
            child_env = Environment(env)
            try:
                self.exec_block(node.body, child_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_each_unpack(self, node, env):
        iterable = self.eval(node.iterable, env)
        for item in iterable:
            child_env = Environment(env)
            if len(node.vars) == 2 and isinstance(item, (list, tuple)) and len(item) == 2:
                child_env.set(node.vars[0], item[0])
                child_env.set(node.vars[1], item[1])
            else:
                for i, var in enumerate(node.vars):
                    child_env.set(var, item[i] if isinstance(item, (list, tuple)) else item)
            try:
                self.exec_block(node.body, child_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_each(self, node, env):
        iterable = self.eval(node.iterable, env)
        for item in iterable:
            child_env = Environment(env)
            child_env.set(node.var, item)
            try:
                self.exec_block(node.body, child_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_til(self, node, env):
        while self.eval(node.condition, env):
            child_env = Environment(env)
            try:
                self.exec_block(node.body, child_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_model(self, node, env):
        model_env = Environment(env)
        # Zarejestruj model
        model = KudaModel(node.name, node.body, model_env)

        # Wykonaj ciało modelu żeby załadować metody
        for stmt in node.body:
            if isinstance(stmt, FunNode):
                func = KudaFunction(stmt.name, stmt.params, stmt.body, model_env)
                model_env.set(stmt.name, func)

        # Stwórz konstruktor
        def constructor(args):
            instance = KudaInstance(node.name, model_env)
            # Wywołaj init jeśli istnieje
            try:
                init_func = model_env.get('init')
                self._call_function(init_func, [instance] + args)
            except:
                pass
            return instance

        env.set(node.name, constructor)

    def exec_try(self, node, env):
        try:
            self.exec_block(node.try_body, env)
        except (GiveSignal, BreakSignal, ContinueSignal):
            raise
        except Exception:
            self.exec_block(node.fail_body, env)

    # === Ewaluacja wyrażeń ===

    def eval(self, node, env):
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, StringNode):
            return node.value

        if isinstance(node, BoolNode):
            return node.value

        if isinstance(node, NoneNode):
            return None

        if isinstance(node, ListNode):
            return [self.eval(e, env) for e in node.elements]

        if isinstance(node, TupleNode):
            return tuple(self.eval(e, env) for e in node.elements)

        if isinstance(node, DictNode):
            return {self.eval(k, env): self.eval(v, env) for k, v in node.pairs}

        if isinstance(node, ListCompNode):
            iterable = self.eval(node.iterable, env)
            result = []
            for item in iterable:
                child_env = Environment(env)
                child_env.set(node.var, item)
                result.append(self.eval(node.expr, child_env))
            return result

        if isinstance(node, IdentNode):
            return env.get(node.name)

        if isinstance(node, BinOpNode):
            return self.eval_binop(node, env)

        if isinstance(node, UnaryOpNode):
            return self.eval_unary(node, env)

        if isinstance(node, AttrNode):
            obj = self.eval(node.obj, env)
            if isinstance(obj, KudaInstance):
                return obj.get_attr(node.attr)
            elif hasattr(obj, 'get_attr'):
                # Handles _PyModuleWrapper from python_bridge
                return obj.get_attr(node.attr)
            elif hasattr(obj, node.attr):
                return getattr(obj, node.attr)
            else:
                raise RuntimeError_(f"No attribute '{node.attr}'")

        if isinstance(node, IndexNode):
            obj = self.eval(node.obj, env)
            idx = self.eval(node.index, env)
            return obj[idx]

        if isinstance(node, CallNode):
            return self.eval_call(node, env)

        raise RuntimeError_(f"Unknown AST node: {type(node)}")

    def eval_binop(self, node, env):
        op = node.op

        # Leniwi operatorzy logiczni
        if op == 'and':
            return self.eval(node.left, env) and self.eval(node.right, env)
        if op == 'or':
            return self.eval(node.left, env) or self.eval(node.right, env)

        left = self.eval(node.left, env)
        right = self.eval(node.right, env)

        if op == '+': return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/': return left / right
        if op == '%': return left % right
        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '<': return left < right
        if op == '>': return left > right
        if op == '<=': return left <= right
        if op == '>=': return left >= right

        raise RuntimeError_(f"Unknown operator: '{op}'")

    def eval_unary(self, node, env):
        val = self.eval(node.operand, env)
        if node.op == '-': return -val
        if node.op == 'not': return not val
        raise RuntimeError_(f"Unknown unary operator: '{node.op}'")

    # Mapowanie metod Kuda on operacje Pythona
    STRING_METHODS = {
        'cut':   lambda obj, args: obj.split(args[0] if args else None),
        'swap':  lambda obj, args: obj.replace(args[0], args[1]),
        'caps':  lambda obj, args: obj.upper(),
        'small': lambda obj, args: obj.lower(),
        'trim':  lambda obj, args: obj.strip(),
        'merge': lambda obj, args: obj.join(args[0]),
        'len':   lambda obj, args: len(obj),
        'fd':    lambda obj, args: obj.find(args[0]),
        'cnt':   lambda obj, args: obj.count(args[0]),
    }

    LIST_METHODS = {
        'add':   lambda obj, args: obj.append(args[0]),
        'del':   lambda obj, args: obj.remove(args[0]),
        'sort':  lambda obj, args: obj.sort(),
        'rev':   lambda obj, args: obj.reverse(),
        'grab':  lambda obj, args: obj.pop(),
        'fd':    lambda obj, args: obj.index(args[0]),
        'cnt':   lambda obj, args: obj.count(args[0]),
        'len':   lambda obj, args: len(obj),
    }

    def eval_call(self, node, env):
        args = [self.eval(a, env) for a in node.args]

        if isinstance(node.func, AttrNode):
            obj = self.eval(node.func.obj, env)
            method_name = node.func.attr

            if isinstance(obj, str) and method_name in self.STRING_METHODS:
                return self.STRING_METHODS[method_name](obj, args)

            if isinstance(obj, list) and method_name in self.LIST_METHODS:
                return self.LIST_METHODS[method_name](obj, args)

            if isinstance(obj, KudaInstance):
                method = obj.get_attr(method_name)
                if isinstance(method, BoundMethod):
                    return self._call_function(method.func, [method.instance] + args)

            # Python module wrapper (from python_bridge.py)
            if hasattr(obj, 'get_attr'):
                method = obj.get_attr(method_name)
                if callable(method):
                    return method(args)
                return method

            # Native Python method
            if hasattr(obj, method_name):
                return getattr(obj, method_name)(*args)

            raise RuntimeError_(f"No method '{method_name}' on {type(obj).__name__}")

        func = self.eval(node.func, env)

        # Wbudowane funkcje (lambdy)
        if callable(func) and not isinstance(func, (KudaFunction, BoundMethod)):
            return func(args)

        # Metoda przypisaon do instancji
        if isinstance(func, BoundMethod):
            return self._call_function(func.func, [func.instance] + args)

        # Funkcja Kuda
        if isinstance(func, KudaFunction):
            return self._call_function(func, args)

        # Metoda Pythona
        if callable(func):
            return func(*args)

        raise RuntimeError_(f"'{func}' is not callable")

    def _call_function(self, func, args):
        call_env = Environment(func.env)

        # Mapuj parametry on argumenty
        for i, param in enumerate(func.params):
            if i < len(args):
                call_env.set(param, args[i])
            else:
                call_env.set(param, None)

        try:
            self.exec_block(func.body, call_env)
            return None
        except GiveSignal as g:
            return g.value

    def _to_str(self, val):
        if val is None:
            return 'None'
        if isinstance(val, bool):
            return 'True' if val else 'False'
        if isinstance(val, list):
            return '[' + ', '.join(self._to_str(v) for v in val) + ']'
        return str(val)