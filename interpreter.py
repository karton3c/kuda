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

class KudaNet:
    """Wbudowana sieć neuronowa Kuda."""
    def __init__(self, name, params):
        self.name = name
        self.params = params  # dict: key -> wartość
        self.weights = []     # lista list wag
        self.biases = []      # lista list biasów
        self.trained = False

    def get_attr(self, name):
        if name == 'train':
            return BoundNetMethod(self, 'train')
        if name == 'predict':
            return BoundNetMethod(self, 'predict')
        if name == 'loss':
            return BoundNetMethod(self, 'loss')
        if name == 'write':
            return BoundNetMethod(self, 'write')
        if name == 'load':
            return BoundNetMethod(self, 'load')
        raise AttributeError(f"Net '{self.name}' has no attribute '{name}'")

    def __repr__(self):
        return f'<net {self.name}>'

class BoundNetMethod:
    def __init__(self, net, method):
        self.net = net
        self.method = method

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
        self.current_line = 0
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
        env.set('str',   lambda args: (str(int(args[0])) if isinstance(args[0], float) and args[0] == int(args[0]) and abs(args[0]) < 1e15 else str(args[0])))
        env.set('type',  lambda args: type(args[0]).__name__)
        env.set('input', lambda args: input(args[0] if args else ''))
        env.set('abs',   lambda args: abs(args[0]))
        env.set('max',   lambda args: max(args) if len(args) > 1 else max(args[0]))
        env.set('min',   lambda args: min(args) if len(args) > 1 else min(args[0]))
        env.set('sum',   lambda args: sum(args[0]))
        env.set('round', lambda args: (lambda r: float(int(r)) if r == int(r) else r)(round(args[0], int(args[1])) if len(args) > 1 else float(round(args[0]))))
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

        # AI - funkcje aktywacji (skalarne, dla list)
        env.set('sigmoid',  lambda args: 1.0 / (1.0 + math.exp(-args[0])))
        env.set('sigmoid_d',lambda args: args[0] * (1.0 - args[0]))
        env.set('tanh',     lambda args: math.tanh(args[0]))
        env.set('tanh_d',   lambda args: 1.0 - args[0] * args[0])
        env.set('relu',     lambda args: max(0.0, args[0]))
        env.set('relu_d',   lambda args: 1.0 if args[0] > 0.0 else 0.0)
        env.set('leaky',    lambda args: args[0] if args[0] > 0.0 else 0.01 * args[0])
        env.set('leaky_d',  lambda args: 1.0 if args[0] > 0.0 else 0.01)
        env.set('softmax',  lambda args: (lambda lst: (lambda s: [math.exp(x)/s for x in lst])(sum(math.exp(x) for x in lst)))(args[0]))

        # AI - operacje na listach
        env.set('dot',      lambda args: sum(a*b for a,b in zip(args[0], args[1])))
        env.set('argmax',   lambda args: args[0].index(max(args[0])))
        env.set('argmin',   lambda args: args[0].index(min(args[0])))
        env.set('clip',     lambda args: max(args[1], min(args[2], args[0])))
        env.set('mean',     lambda args: sum(args[0]) / len(args[0]))
        env.set('norm',     lambda args: math.sqrt(sum(x*x for x in args[0])))

        # AI - inicjalizacja wag
        env.set('xav',  lambda args: [random.gauss(0, (2.0/(args[0]+args[1]))**0.5) for _ in range(int(args[0]*args[1]))])
        env.set('he',   lambda args: [random.gauss(0, (2.0/args[0])**0.5) for _ in range(int(args[0]))])

        # AI - metryki
        def _acc(args):
            pred, target = args[0], args[1]
            correct = sum(1 for p,t in zip(pred,target) if round(p)==round(t))
            return correct / len(target)
        env.set('acc', _acc)

        def _crent(args):
            pred, target = args[0], args[1]
            eps = 1e-15
            return -sum(t * math.log(max(p, eps)) for p,t in zip(pred,target)) / len(target)
        env.set('crent', _crent)

        # AI - wycinek listy
        def _snip(args):
            lst, start, end = args[0], int(args[1]), int(args[2])
            return lst[start:end]
        env.set('snip', _snip)

        # AI - batch/pack
        def _pack(args):
            lst, n = args[0], int(args[1])
            return [lst[i:i+n] for i in range(0, len(lst), n)]
        env.set('pack', _pack)

        # AI - zapis/odczyt wag
        def _save_weights(args):
            import json
            path, *lists = args
            data = [[float(x) for x in lst] for lst in lists]
            open(path, 'w').write(json.dumps(data))
        def _load_weights(args):
            import json
            data = json.loads(open(args[0]).read())
            return data  # lista list
        env.set('save_weights', _save_weights)
        env.set('load_weights', _load_weights)

        # Time
        env.set('wait',  lambda args: _time.sleep(args[0]))
        env.set('time',  lambda args: _time.time())

        # DataBuilder
        env.set('data', DataBuilder())
        env.set('auto', None)  # special value for net ~layers

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
        if isinstance(node, AnonFunNode):
            return KudaFunction(None, node.params, node.body, env)
        if isinstance(node, FunNode):
            func = KudaFunction(node.name, node.params, node.body, env)
            env.set(node.name, func)
            return

        # model
        if isinstance(node, ModelNode):
            return self.exec_model(node, env)
        if isinstance(node, NetNode):
            return self.exec_net(node, env)
        if isinstance(node, NetLoadNode):
            return self.exec_net_load(node, env)

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
            # Zawsze przypisuj lokalnie — nie wyciekaj do zewnętrznego scope
            env.set(node.name, value)
        elif isinstance(node.name, AttrNode):
            # np. self.x = 5
            obj = self.eval(node.name.obj, env)
            if isinstance(obj, KudaInstance):
                obj.set_attr(node.name.attr, value)
            elif isinstance(obj, __import__('data_builder').DataBuilder) and node.name.attr == 'cust':
                # Wrap KudaFunction so DataBuilder can call it
                def make_call(fn, interp_self):
                    def call(f, args): return interp_self._call_function(f, args)
                    return (fn, call)
                setattr(obj, '_cust_fn', make_call(value, self))
            else:
                setattr(obj, node.name.attr, value)

    def exec_if(self, node, env):
        for cond, body in node.cases:
            if self.eval(cond, env):
                self.exec_block(body, env)
                return
        if node.else_body:
            self.exec_block(node.else_body, env)

    def exec_repeat(self, node, env):
        count = int(self.eval(node.count, env))
        for _ in range(count):
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_each_unpack(self, node, env):
        iterable = self.eval(node.iterable, env)
        for item in iterable:
            if len(node.vars) == 2 and isinstance(item, (list, tuple)) and len(item) == 2:
                env.set(node.vars[0], item[0])
                env.set(node.vars[1], item[1])
            else:
                for i, var in enumerate(node.vars):
                    env.set(var, item[i] if isinstance(item, (list, tuple)) else item)
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_each(self, node, env):
        iterable = self.eval(node.iterable, env)
        for item in iterable:
            env.set(node.var, item)
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_til(self, node, env):
        while self.eval(node.condition, env):
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_net(self, node, env):
        import math, random as _random
        # Ewaluuj parametry
        params = {}
        for key, val_node in node.params.items():
            try:
                params[key] = self.eval(val_node, env)
            except Exception:
                # Może być 'auto' lub inna specjalna wartość
                params[key] = None

        net = KudaNet(node.name, params)

        # Pobierz dane
        raw_data = None
        if 'data' in params:
            raw_data = params['data']
        elif 'inputs' in params and 'targets' in params:
            raw_data = list(zip(params['inputs'], params['targets']))

        if raw_data is None:
            raise RuntimeError_("net: brak danych (~data lub ~inputs + ~targets)")

        # Normalizuj format danych -> lista (inputs, target)
        dataset = []
        for item in raw_data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                inp, tgt = item
                if not isinstance(inp, list): inp = [inp]
                if not isinstance(tgt, list): tgt = [tgt]
                dataset.append((inp, tgt))

        # Parametry sieci
        n_inputs = len(dataset[0][0]) if dataset else 1
        layers_raw = params.get('layers', [n_inputs, 8, 1])
        layers = []
        for l in layers_raw:
            if isinstance(l, str) and l == 'auto':
                layers.append(n_inputs)
            elif l is None:
                layers.append(n_inputs)
            else:
                layers.append(int(l))
        if layers[0] != n_inputs:
            layers[0] = n_inputs  # auto-fix

        lr        = float(params.get('lr', 0.01))
        epochs    = int(params.get('epochs', 1000))
        act_name  = params.get('act', 'tanh')
        out_name  = params.get('act_out', act_name)
        loss_name = params.get('loss', 'mse')
        init_name = params.get('init', 'xav')
        pack_size = params.get('pack', None)
        log_every = int(params.get('log', 100))
        stop_loss = float(params.get('stop', -1.0))

        # Funkcje aktywacji
        def get_act(name):
            if name == 'tanh':     return math.tanh, lambda x: 1.0 - x*x
            if name == 'sigmoid':  return (lambda x: 1/(1+math.exp(-x))), lambda x: x*(1-x)
            if name == 'relu':     return (lambda x: max(0.0,x)), lambda x: 1.0 if x>0 else 0.0
            if name == 'leaky':    return (lambda x: x if x>0 else 0.01*x), lambda x: 1.0 if x>0 else 0.01
            if name == 'linear':   return (lambda x: x), lambda x: 1.0
            return math.tanh, lambda x: 1.0 - x*x

        act_f, act_d = get_act(act_name)
        out_f, out_d = get_act(out_name)

        # Inicjalizacja wag
        def init_weights(n_in, n_out, method):
            if method == 'he':
                std = math.sqrt(2.0/n_in)
            else:  # xav
                std = math.sqrt(2.0/(n_in+n_out))
            return [_random.gauss(0, std) for _ in range(n_in*n_out)]

        net.layers   = layers
        net.act_name = act_name
        net.out_name = out_name
        net.weights = []
        net.biases  = []
        for i in range(len(layers)-1):
            net.weights.append(init_weights(layers[i], layers[i+1], init_name))
            net.biases.append([0.0]*layers[i+1])

        # Forward pass
        def forward(inputs):
            a = inputs[:]
            activations = [a]
            for li in range(len(net.weights)):
                n_in  = layers[li]
                n_out = layers[li+1]
                w = net.weights[li]
                b = net.biases[li]
                is_last = (li == len(net.weights)-1)
                f = out_f if is_last else act_f
                new_a = []
                for j in range(n_out):
                    z = b[j]
                    for k in range(n_in):
                        z += a[k] * w[j*n_in+k]
                    new_a.append(f(z))
                a = new_a
                activations.append(a)
            return activations

        # Backward pass
        def backward(activations, target):
            n_layers = len(layers)
            deltas = [None] * (n_layers-1)
            # Output layer delta
            li = n_layers-2
            is_last = True
            f_d = out_d
            out_a = activations[-1]
            deltas[li] = [(out_a[j]-target[j]) * f_d(out_a[j]) for j in range(len(out_a))]
            # Hidden layers
            for li in range(n_layers-3, -1, -1):
                n_in  = layers[li+1]
                n_out_next = layers[li+2]
                w_next = net.weights[li+1]
                a = activations[li+1]
                d_next = deltas[li+1]
                d = []
                for j in range(n_in):
                    err = sum(d_next[k]*w_next[k*n_in+j] for k in range(n_out_next))
                    d.append(err * act_d(a[j]))
                deltas[li] = d
            return deltas

        # Update weights
        def update(activations, deltas):
            for li in range(len(net.weights)):
                n_in  = layers[li]
                n_out = layers[li+1]
                d = deltas[li]
                a_in = activations[li]
                for j in range(n_out):
                    net.biases[li][j]  -= lr * d[j]
                    for k in range(n_in):
                        net.weights[li][j*n_in+k] -= lr * d[j] * a_in[k]

        # Trening
        data_list = dataset[:]
        for epoch in range(epochs):
            _random.shuffle(data_list)
            batches = [data_list]
            if pack_size:
                ps = int(pack_size)
                batches = [data_list[i:i+ps] for i in range(0, len(data_list), ps)]

            total_loss = 0.0
            for batch in batches:
                for inputs, target in batch:
                    acts = forward(inputs)
                    out_a = acts[-1]
                    total_loss += sum((o-t)**2 for o,t in zip(out_a,target)) / len(target)
                    deltas = backward(acts, target)
                    update(acts, deltas)

            avg_loss = total_loss / len(data_list)
            if log_every > 0 and epoch % log_every == 0:
                print(f"Epoch {epoch} | Loss: {round(avg_loss, 6)}")
            if stop_loss > 0 and avg_loss < stop_loss:
                print(f"Early stop epoch {epoch} | Loss: {round(avg_loss, 6)}")
                break

        net.trained = True
        net._forward = forward
        net._layers  = layers

        # Zarejestruj net w env
        env.set(node.name, net)

    def exec_net_load(self, node, env):
        import json as _json, math as _math
        path = self.eval(node.path_node, env)

        try:
            with open(path) as _f:
                data = _json.load(_f)
        except FileNotFoundError:
            raise RuntimeError_(f"net.load: nie mozna otworzyc '{path}'")

        layers   = data['layers']
        W_flat   = data['W']
        B_flat   = data['B']
        act_name = data.get('act', 'tanh')
        out_name = data.get('act_out', act_name)

        # Rebuild weights/biases as lists of lists
        weights = []; biases = []
        idx_w = 0; idx_b = 0
        for i in range(len(layers) - 1):
            n_in, n_out = layers[i], layers[i+1]
            weights.append(W_flat[idx_w:idx_w + n_in*n_out]); idx_w += n_in*n_out
            biases.append(B_flat[idx_b:idx_b + n_out]);        idx_b += n_out

        def _get_act(aname):
            if aname == 'tanh':    return _math.tanh
            if aname == 'sigmoid': return lambda x: 1/(1+_math.exp(-x))
            if aname == 'relu':    return lambda x: max(0.0, x)
            if aname == 'leaky':   return lambda x: x if x>0 else 0.01*x
            if aname == 'linear':  return lambda x: x
            return _math.tanh

        act_f = _get_act(act_name)
        out_f = _get_act(out_name)

        def _make_forward(w_ref, b_ref, af, of, ls):
            def _fwd(inputs):
                a = inputs[:]
                activations = [a]
                for li in range(len(w_ref)):
                    n_in  = ls[li]; n_out = ls[li+1]
                    w = w_ref[li]; b = b_ref[li]
                    is_last = (li == len(w_ref)-1)
                    f = of if is_last else af
                    new_a = []
                    for j in range(n_out):
                        z = b[j]
                        for k in range(n_in): z += a[k] * w[j*n_in+k]
                        new_a.append(f(z))
                    a = new_a; activations.append(a)
                return activations
            return _fwd

        net = KudaNet(node.name, {})
        net.weights  = weights
        net.biases   = biases
        net.layers   = layers
        net.act_name = act_name
        net.out_name = out_name
        net.trained  = True
        net._forward = _make_forward(net.weights, net.biases, act_f, out_f, layers)
        net._layers  = layers

        env.set(node.name, net)
        print(f"Wagi wczytane z {path}")

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
        # Track current line for error messages
        if hasattr(node, 'line') and node.line:
            self.current_line = node.line

        if isinstance(node, AnonFunNode):
            return KudaFunction(None, node.params, node.body, env)

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
            try:
                return env.get(node.name)
            except RuntimeError as e:
                raise RuntimeError_(str(e).replace("Undefined variable: ", "Undefined variable: "), self.current_line)

        if isinstance(node, BinOpNode):
            return self.eval_binop(node, env)

        if isinstance(node, UnaryOpNode):
            return self.eval_unary(node, env)

        if isinstance(node, AttrNode):
            obj = self.eval(node.obj, env)
            if isinstance(obj, KudaInstance):
                return obj.get_attr(node.attr)
            elif hasattr(obj, 'get_attr'):
                return obj.get_attr(node.attr)
            elif hasattr(obj, node.attr):
                return getattr(obj, node.attr)
            else:
                raise RuntimeError_(f"No attribute '{node.attr}'", self.current_line)

        if isinstance(node, IndexNode):
            obj = self.eval(node.obj, env)
            idx = self.eval(node.index, env)
            try:
                return obj[int(idx) if isinstance(idx, float) and idx == int(idx) else idx]
            except (IndexError, KeyError, TypeError) as e:
                raise RuntimeError_(f"Index error: {e}", self.current_line)

        if isinstance(node, CallNode):
            return self.eval_call(node, env)

        raise RuntimeError_(f"Unknown AST node: {type(node)}", self.current_line)

    def eval_binop(self, node, env):
        op = node.op
        line = getattr(node, 'line', 0) or self.current_line

        # Leniwi operatorzy logiczni
        if op == 'and':
            return self.eval(node.left, env) and self.eval(node.right, env)
        if op == 'or':
            return self.eval(node.left, env) or self.eval(node.right, env)

        left = self.eval(node.left, env)
        right = self.eval(node.right, env)

        try:
            if op == '+': return left + right
            if op == '-': return left - right
            if op == '*': return left * right
            if op == '/':
                if right == 0: raise RuntimeError_(f"Division by zero", line)
                return left / right
            if op == '%': return left % right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<': return left < right
            if op == '>': return left > right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
        except RuntimeError_:
            raise
        except Exception as e:
            raise RuntimeError_(f"Type error on '{op}': {e}", line)

        raise RuntimeError_(f"Unknown operator: '{op}'", line)

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

            # KudaNet
            if isinstance(obj, KudaNet):
                method = obj.get_attr(method_name)
                if isinstance(method, BoundNetMethod):
                    net = method.net
                    if method.method == 'predict':
                        if not net.trained:
                            raise RuntimeError_(f"Net '{net.name}' nie jest wytrenowana!")
                        inputs = args[0] if args else []
                        if not isinstance(inputs, list): inputs = [inputs]
                        acts = net._forward(inputs)
                        result = acts[-1]
                        return result[0] if len(result) == 1 else result
                    if method.method == 'write':
                        import json as _json
                        path = args[0] if args else f"{net.name}_weights.json"
                        layers = getattr(net, 'layers', [])
                        W_flat = [w for layer in net.weights for w in layer]
                        B_flat = [b for layer in net.biases  for b in layer]
                        data = {
                            'net':    net.name,
                            'layers': layers,
                            'act':    getattr(net, 'act_name', 'tanh'),
                            'act_out':getattr(net, 'out_name', 'tanh'),
                            'W':      W_flat,
                            'B':      B_flat,
                        }
                        with open(path, 'w') as _f:
                            _json.dump(data, _f, indent=2)
                        print(f"Wagi zapisane do {path}")
                        return None
                    if method.method == 'load':
                        import json as _json
                        path = args[0] if args else f"{net.name}_weights.json"
                        try:
                            with open(path) as _f:
                                data = _json.load(_f)
                        except FileNotFoundError:
                            print(f"Blad: nie mozna otworzyc {path}")
                            return None
                        layers = data.get('layers', getattr(net, 'layers', []))
                        W_flat = data.get('W', [])
                        B_flat = data.get('B', [])
                        net.weights = []
                        net.biases  = []
                        idx_w = 0
                        idx_b = 0
                        for i in range(len(layers) - 1):
                            n_in, n_out = layers[i], layers[i+1]
                            net.weights.append(W_flat[idx_w:idx_w + n_in*n_out])
                            idx_w += n_in * n_out
                            net.biases.append(B_flat[idx_b:idx_b + n_out])
                            idx_b += n_out
                        net.layers   = layers
                        net.act_name = data.get('act',     getattr(net, 'act_name', 'tanh'))
                        net.out_name = data.get('act_out', getattr(net, 'out_name', 'tanh'))
                        net.trained  = True
                        # Rebuild _forward with correct activations
                        import math as _math
                        def _get_act(aname):
                            if aname == 'tanh':    return _math.tanh
                            if aname == 'sigmoid': return lambda x: 1/(1+_math.exp(-x))
                            if aname == 'relu':    return lambda x: max(0.0, x)
                            if aname == 'leaky':   return lambda x: x if x>0 else 0.01*x
                            if aname == 'linear':  return lambda x: x
                            return _math.tanh
                        _act_f = _get_act(net.act_name)
                        _out_f = _get_act(net.out_name)
                        _layers = layers[:]
                        def _make_forward(n, w_ref, b_ref, af, of, ls):
                            def _fwd(inputs):
                                a = inputs[:]
                                activations = [a]
                                for li in range(len(w_ref)):
                                    n_in  = ls[li]
                                    n_out = ls[li+1]
                                    w = w_ref[li]
                                    b = b_ref[li]
                                    is_last = (li == len(w_ref)-1)
                                    f = of if is_last else af
                                    new_a = []
                                    for j in range(n_out):
                                        z = b[j]
                                        for k in range(n_in):
                                            z += a[k] * w[j*n_in+k]
                                        new_a.append(f(z))
                                    a = new_a
                                    activations.append(a)
                                return activations
                            return _fwd
                        net._forward = _make_forward(net.name, net.weights, net.biases, _act_f, _out_f, _layers)
                        print(f"Wagi wczytane z {path}")
                        return None
                    return None
                return method

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

        # Metoda sieci neuronowej
        if isinstance(func, BoundNetMethod):
            net = func.net
            if func.method == 'train':
                # trening już wykonany w exec_net, tu nic nie robimy
                return None
            if func.method == 'predict':
                if not net.trained:
                    raise RuntimeError_(f"Net '{net.name}' nie jest wytrenowana!")
                inputs = args[0] if args else []
                if not isinstance(inputs, list): inputs = [inputs]
                acts = net._forward(inputs)
                result = acts[-1]
                return result[0] if len(result) == 1 else result
            if func.method == 'write':
                import json as _json
                path = args[0] if args else f"{net.name}_weights.json"
                layers = getattr(net, 'layers', [])
                W_flat = [w for layer in net.weights for w in layer]
                B_flat = [b for layer in net.biases  for b in layer]
                data = {
                    'net':     net.name,
                    'layers':  layers,
                    'act':     getattr(net, 'act_name', 'tanh'),
                    'act_out': getattr(net, 'out_name', 'tanh'),
                    'W':       W_flat,
                    'B':       B_flat,
                }
                with open(path, 'w') as _f:
                    _json.dump(data, _f, indent=2)
                print(f"Wagi zapisane do {path}")
                return None
            if func.method == 'load':
                import json as _json, math as _math
                path = args[0] if args else f"{net.name}_weights.json"
                try:
                    with open(path) as _f:
                        data = _json.load(_f)
                except FileNotFoundError:
                    print(f"Blad: nie mozna otworzyc {path}")
                    return None
                layers = data.get('layers', getattr(net, 'layers', []))
                W_flat = data.get('W', [])
                B_flat = data.get('B', [])
                net.weights = []
                net.biases  = []
                idx_w = 0; idx_b = 0
                for i in range(len(layers) - 1):
                    n_in, n_out = layers[i], layers[i+1]
                    net.weights.append(W_flat[idx_w:idx_w + n_in*n_out])
                    idx_w += n_in * n_out
                    net.biases.append(B_flat[idx_b:idx_b + n_out])
                    idx_b += n_out
                net.layers   = layers
                net.act_name = data.get('act',     getattr(net, 'act_name', 'tanh'))
                net.out_name = data.get('act_out', getattr(net, 'out_name', 'tanh'))
                net.trained  = True
                def _get_act(aname):
                    if aname == 'tanh':    return _math.tanh
                    if aname == 'sigmoid': return lambda x: 1/(1+_math.exp(-x))
                    if aname == 'relu':    return lambda x: max(0.0, x)
                    if aname == 'leaky':   return lambda x: x if x>0 else 0.01*x
                    if aname == 'linear':  return lambda x: x
                    return _math.tanh
                _act_f = _get_act(net.act_name)
                _out_f = _get_act(net.out_name)
                _lys = layers[:]
                def _make_forward(w_ref, b_ref, af, of, ls):
                    def _fwd(inputs):
                        a = inputs[:]
                        activations = [a]
                        for li in range(len(w_ref)):
                            n_in  = ls[li]
                            n_out = ls[li+1]
                            w = w_ref[li]; b = b_ref[li]
                            is_last = (li == len(w_ref)-1)
                            f = of if is_last else af
                            new_a = []
                            for j in range(n_out):
                                z = b[j]
                                for k in range(n_in): z += a[k] * w[j*n_in+k]
                                new_a.append(f(z))
                            a = new_a
                            activations.append(a)
                        return activations
                    return _fwd
                net._forward = _make_forward(net.weights, net.biases, _act_f, _out_f, _lys)
                print(f"Wagi wczytane z {path}")
                return None
            if func.method == 'loss':
                return None
            return None

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
        if isinstance(val, float) and val == int(val) and abs(val) < 1e15:
            return str(int(val))
        if isinstance(val, list):
            return '[' + ', '.join(self._to_str(v) for v in val) + ']'
        return str(val)