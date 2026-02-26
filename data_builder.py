import random as _random
import math as _math

class DataBuilder:
    """
    Generator datasetów dla Kuda.

    data.binary.sequential.xor
    data.binary(3).sequential.parity
    data.binary(4).random(100).parity
    data.numeric.sequential(0.0, 5.0, 1.0).square
    data.numeric.random(100, 0.0, 10.0).sin
    """

    TARGETS = ['xor', 'kand', 'kor', 'nand', 'nor', 'parity',
               'sum', 'square', 'sqrt', 'sin', 'cos', 'identity']

    def __init__(self, dtype=None, mode=None, mode_args=None, n_bits=2):
        self._dtype     = dtype
        self._mode      = mode
        self._mode_args = mode_args
        self._n_bits    = n_bits

    def __call__(self, *args):
        # data.binary(3) — ustaw n_bits
        if self._dtype == 'binary' and self._mode is None:
            return DataBuilder(dtype='binary', n_bits=int(args[0]))
        # data.binary.random(200) — ustaw liczbę próbek
        if self._dtype == 'binary' and self._mode == 'random' and self._mode_args is None:
            return DataBuilder(dtype='binary', mode='random',
                               mode_args=(int(args[0]),), n_bits=self._n_bits)
        # data.numeric.sequential(start, stop, step)
        if self._dtype == 'numeric' and self._mode == 'sequential':
            return DataBuilder(dtype='numeric', mode='sequential',
                               mode_args=(float(args[0]), float(args[1]), float(args[2])))
        # data.numeric.random(n, min, max)
        if self._dtype == 'numeric' and self._mode == 'random':
            return DataBuilder(dtype='numeric', mode='random',
                               mode_args=(int(args[0]), float(args[1]), float(args[2])))
        return self

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        # Typ danych
        if name == 'binary':
            return DataBuilder(dtype='binary', n_bits=self._n_bits)
        if name == 'numeric':
            return DataBuilder(dtype='numeric')

        # Tryb
        if name == 'sequential':
            return DataBuilder(dtype=self._dtype, mode='sequential',
                               mode_args=self._mode_args, n_bits=self._n_bits)
        if name == 'random':
            return DataBuilder(dtype=self._dtype, mode='random',
                               mode_args=self._mode_args, n_bits=self._n_bits)

        # Target — generuj
        if name in self.TARGETS:
            return self._generate(name)

        raise AttributeError(f"[data] Nieznany atrybut: '{name}'. Dostępne targety: {', '.join(self.TARGETS)}")

    def _generate(self, target):
        if self._dtype == 'binary':
            return self._gen_binary(target)
        elif self._dtype == 'numeric':
            return self._gen_numeric(target)
        raise ValueError(f"[data] Najpierw wybierz typ: data.binary lub data.numeric")

    def _gen_binary(self, target):
        n = self._n_bits

        if self._mode == 'random':
            count = self._mode_args[0] if self._mode_args else 100
            inputs_list = [
                [float(_random.randint(0, 1)) for _ in range(n)]
                for _ in range(count)
            ]
        else:  # sequential (domyślne)
            inputs_list = []
            for i in range(2 ** n):
                bits = [float((i >> (n - 1 - b)) & 1) for b in range(n)]
                inputs_list.append(bits)

        return [(bits, self._calc_target(bits, target)) for bits in inputs_list]

    def _gen_numeric(self, target):
        if self._mode == 'sequential':
            if not self._mode_args:
                raise ValueError("[data] sequential wymaga: data.numeric.sequential(start, stop, step).target")
            start, stop, step = self._mode_args
            inputs_list = []
            x = start
            while x <= stop + 1e-9:
                inputs_list.append([x])
                x += step
        elif self._mode == 'random':
            if not self._mode_args:
                raise ValueError("[data] random wymaga: data.numeric.random(n, min, max).target")
            n, lo, hi = self._mode_args
            inputs_list = [[_random.uniform(lo, hi)] for _ in range(n)]
        else:
            raise ValueError("[data] Wybierz tryb: sequential lub random")

        return [([round(inp[0], 8)], self._calc_target(inp, target)) for inp in inputs_list]

    def _calc_target(self, inputs, target):
        x = inputs[0]
        bits = inputs

        if target == 'xor':
            result = 0
            for b in bits: result ^= int(b)
            return float(result)
        elif target == 'kand':
            return 1.0 if all(b == 1.0 for b in bits) else 0.0
        elif target == 'kor':
            return 1.0 if any(b == 1.0 for b in bits) else 0.0
        elif target == 'nand':
            return 0.0 if all(b == 1.0 for b in bits) else 1.0
        elif target == 'nor':
            return 0.0 if any(b == 1.0 for b in bits) else 1.0
        elif target == 'parity':
            return 1.0 if sum(int(b) for b in bits) % 2 == 0 else 0.0
        elif target == 'sum':
            return float(sum(inputs))
        elif target == 'square':
            return float(x * x)
        elif target == 'sqrt':
            return float(_math.sqrt(abs(x)))
        elif target == 'sin':
            return float(_math.sin(x))
        elif target == 'cos':
            return float(_math.cos(x))
        elif target == 'identity':
            return float(x)
        else:
            raise ValueError(f"[data] Nieznany target: '{target}'")

    def __repr__(self):
        return f"DataBuilder(dtype={self._dtype}, mode={self._mode}, n_bits={self._n_bits})"