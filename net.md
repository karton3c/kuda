# Kuda — Neural Networks & DataBuilder
**Version 0.2.6**

This document covers the `net` block, all training parameters, activations, DataBuilder datasets, and `data.cust`.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [net block syntax](#net-block-syntax)
3. [Parameters reference](#parameters-reference)
4. [Activations](#activations)
5. [Weight initialization](#weight-initialization)
6. [predict()](#predict)
7. [Multiple nets](#multiple-nets)
8. [DataBuilder](#databuilder)
9. [data.cust — custom targets](#datacust--custom-targets)
10. [Manual datasets (~inputs / ~targets)](#manual-datasets-inputs--targets)
11. [Tips & troubleshooting](#tips--troubleshooting)
12. [Examples](#examples)

---

## Quick Start

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 3000
    ~stop = 0.001
    ~log = 1000

out(str(round(xor.predict([0.0, 1.0]))))   # 1
out(str(round(xor.predict([1.0, 1.0]))))   # 0
```

The `net` block defines, trains, and exposes a neural network. Training happens automatically when you run the file. After training, use `.predict()` to get results.

---

## net block syntax

```kuda
net <name>:
    ~param = value
    ~param = value
    ...
```

- Name must be a valid identifier (e.g. `xor`, `mynet`, `classifier`)
- Parameters are prefixed with `~`
- You need at minimum: a dataset (`~data`, or `~inputs`+`~targets`) and `~layers`
- Multiple nets can exist in the same file — they train in order

---

## Parameters reference

### ~data

Provide a dataset from DataBuilder:

```kuda
~data = data.binary(2).sequential.xor
~data = data.binary(4).sequential.parity
~data = data.binary(8).sequential.cust
~data = data.numeric.sequential(0.0, 6.28, 0.1).sin
```

See [DataBuilder](#databuilder) for all options.

### ~inputs and ~targets

Provide data manually as lists:

```kuda
~inputs = [
    [0.0, 0.0],
    [0.0, 1.0],
    [1.0, 0.0],
    [1.0, 1.0]
]
~targets = [
    [0.0],
    [1.0],
    [1.0],
    [0.0]
]
```

Each input is a list, each target is a list. Both must have the same number of rows.

### ~layers

Define the architecture. `auto` means the input layer size is taken from the dataset automatically.

```kuda
~layers = [auto, 8, 1]          # input, 1 hidden (8), output (1)
~layers = [auto, 16, 8, 1]      # input, 2 hidden, output
~layers = [auto, 32, 64, 16, 1] # input, 3 hidden, output
~layers = [3, 8, 1]             # explicit input size
```

The last number is the output size. For binary classification use `1`. For multi-class use the number of classes.

### ~lr — learning rate

```kuda
~lr = 0.1     # fast but may overshoot
~lr = 0.01    # balanced
~lr = 0.001   # slow but stable for deep nets
```

### ~epochs

```kuda
~epochs = 1000    # quick test
~epochs = 5000    # standard
~epochs = 20000   # hard problems (parity 8-bit etc.)
```

### ~act — hidden layer activation

```kuda
~act = tanh       # default, works for most problems
~act = relu       # good for deep networks
~act = sigmoid    # if you need 0-1 range in hidden layers
~act = leaky      # like relu but no dead neurons
~act = linear     # usually only for output
```

### ~act_out — output layer activation

If not set, uses the same as `~act`.

```kuda
~act_out = sigmoid   # binary classification output (0-1)
~act_out = linear    # regression output (any value)
~act_out = tanh      # output in range -1 to 1
```

### ~init — weight initialization

```kuda
~init = xav    # Xavier — default, good for tanh/sigmoid
~init = he     # He — better for relu/leaky
```

### ~log — logging interval

```kuda
~log = 100      # print loss every 100 epochs
~log = 1000     # print less often
~log = 9999999  # effectively silent (only early stop prints)
```

### ~stop — early stopping

Stop training when average loss goes below this value:

```kuda
~stop = 0.01     # loose
~stop = 0.001    # standard
~stop = 0.0001   # tight
```

If not set, trains for all `~epochs`.

---

## Activations

| Name | Formula | Best for |
|------|---------|---------|
| `tanh` | (e^x - e^-x) / (e^x + e^-x) | Binary classification, most problems |
| `sigmoid` | 1 / (1 + e^-x) | Output layer for probability |
| `relu` | max(0, x) | Deep networks, fast training |
| `leaky` | x if x>0 else 0.01*x | Deep networks, avoids dead neurons |
| `linear` | x | Regression output layer |

**Recommended combinations:**

| Problem | ~act | ~act_out |
|---------|------|---------|
| Binary classification (0/1) | `tanh` | `tanh` or `sigmoid` |
| Regression (any value) | `tanh` | `linear` |
| Deep network | `relu` | `sigmoid` |
| XOR, parity | `tanh` | `tanh` |

---

## Weight initialization

| Name | Formula | Best with |
|------|---------|----------|
| `xav` | std = sqrt(2 / (n_in + n_out)) | tanh, sigmoid |
| `he` | std = sqrt(2 / n_in) | relu, leaky |

---

## predict()

After training, call `.predict()` with an input list:

```kuda
result = mynet.predict([1.0, 0.0, 1.0])
out(str(result))             # raw float
out(str(round(result)))      # rounded to 0 or 1
```

For multi-output nets, `.predict()` returns the first output. Full multi-output support coming in a future version.

**The input list must match the input layer size.** If you used `data.binary(4)` then inputs are 4 floats.

---

## Multiple nets

You can have multiple nets in one file. They train in the order they appear:

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 2000
    ~stop = 0.001
    ~log = 9999

net parity:
    ~data = data.binary(4).sequential.parity
    ~layers = [auto, 16, 8, 1]
    ~lr = 0.05
    ~epochs = 5000
    ~stop = 0.001
    ~log = 9999

out("XOR 1,0 = " + str(round(xor.predict([1.0, 0.0]))))
out("parity 0101 = " + str(round(parity.predict([0.0,1.0,0.0,1.0]))))
```

Each net must have a unique name.

---

## DataBuilder

DataBuilder generates training datasets. Access it through the built-in `data` object.

### Binary datasets

Generate all 2^N combinations of N bits:

```kuda
data = data.binary(N).sequential.<target>
```

Or generate M random combinations:

```kuda
data = data.binary(N).random(M).<target>
```

### Binary targets

| Target | Description | Example |
|--------|-------------|---------|
| `xor` | XOR of all bits | `[1,0]` → 1, `[1,1]` → 0 |
| `parity` | 1 if even number of 1s | `[0,0]` → 1, `[1,0]` → 0 |
| `kand` | 1 only if all bits are 1 | `[1,1,1]` → 1 |
| `kor` | 1 if any bit is 1 | `[0,0,1]` → 1 |
| `nand` | opposite of kand | `[1,1,1]` → 0 |
| `nor` | opposite of kor | `[0,0,0]` → 1 |
| `cust` | user-defined function | see below |

> **Note:** `and` and `or` are Kuda keywords, so the targets are called `kand` and `kor`.

### Numeric datasets

```kuda
data = data.numeric.sequential(start, stop, step).<target>
data = data.numeric.random(n, min, max).<target>
```

| Target | Description |
|--------|-------------|
| `sin` | sin(x) |
| `cos` | cos(x) |
| `square` | x² |
| `sqrt` | √x |
| `identity` | x |
| `sum` | sum of inputs |

Example — learn to approximate sin(x):

```kuda
net sinus:
    ~data = data.numeric.sequential(0.0, 6.28, 0.1).sin
    ~layers = [auto, 16, 8, 1]
    ~lr = 0.01
    ~epochs = 10000
    ~act = tanh
    ~act_out = linear
    ~log = 2000

out("sin(0) = " + str(mynet.predict([0.0])))
out("sin(1.57) = " + str(mynet.predict([1.5707])))
```

---

## data.cust — custom targets

`data.cust` lets you define any target function using Kuda code.

### Syntax

```kuda
data.cust = fun(bits):
    # bits is a list of floats (0.0 or 1.0 for binary)
    # must return a float
    give <value>

dataset = data.binary(N).sequential.cust
```

`data.cust` is stored on the `data` object — it does not conflict with regular variables named `cust`.

### Rules

- The function receives `bits` — a list of floats
- Must return a float (use `float(...)` for conversions if needed)
- Works with both `sequential` and `random`
- Works in both C mode and interpreter mode

### Examples

**Bit at position 3:**
```kuda
data.cust = fun(bits):
    give bits[3]
```

**Two bits equal:**
```kuda
data.cust = fun(bits):
    if bits[0] == bits[3]:
        give 1.0
    give 0.0
```

**Sum greater than threshold:**
```kuda
data.cust = fun(bits):
    s = bits[0] + bits[1] + bits[2] + bits[3]
    if s > 2.0:
        give 1.0
    give 0.0
```

**XOR of specific positions:**
```kuda
data.cust = fun(bits):
    a = bits[0]
    b = bits[2]
    give float((a + b) % 2.0)
```

**Combining multiple conditions:**
```kuda
data.cust = fun(bits):
    # 1 if first bit XOR last bit AND middle bit is 1
    xor = float((bits[0] + bits[4]) % 2.0)
    if xor == 1.0:
        if bits[2] == 1.0:
            give 1.0
    give 0.0
```

### Full example with net

```kuda
data.cust = fun(bits):
    if bits[2] == 1.0:
        if bits[4] == 1.0:
            give 1.0
    give 0.0

net mynet:
    ~data = data.binary(8).sequential.cust
    ~layers = [auto, 16, 8, 1]
    ~lr = 0.05
    ~epochs = 5000
    ~stop = 0.001
    ~log = 1000

out("00101000 -> 1? " + str(round(mynet.predict([0.0,0.0,1.0,0.0,1.0,0.0,0.0,0.0]))))
out("00100000 -> 0? " + str(round(mynet.predict([0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0]))))
```

---

## Manual datasets (~inputs / ~targets)

Use `~inputs` and `~targets` when you want full control over the data:

```kuda
net classifier:
    ~inputs = [
        [0.0, 0.0],
        [0.0, 1.0],
        [1.0, 0.0],
        [1.0, 1.0]
    ]
    ~targets = [
        [0.0],
        [1.0],
        [1.0],
        [0.0]
    ]
    ~layers = [2, 8, 1]
    ~lr = 0.1
    ~epochs = 3000
    ~stop = 0.001
    ~log = 1000
```

The input layer size must match the length of each input row. You cannot use `auto` with manual inputs.

---

## Tips & troubleshooting

### Network not learning

- Try increasing `~epochs`
- Lower `~lr` (e.g. `0.01` instead of `0.1`)
- Add more neurons or layers
- Switch activation: try `relu` + `~init = he`

### Loss stuck

- Problem may be too hard for the architecture — add more hidden neurons
- Parity 8-bit needs at least `[auto, 32, 64, 16, 1]` and `~epochs = 20000`
- Try different `~lr` values

### Parity problems by size

| Bits | Recommended architecture |
|------|--------------------------|
| 2 | `[auto, 4, 1]` |
| 4 | `[auto, 16, 8, 1]` |
| 6 | `[auto, 32, 16, 1]` |
| 8 | `[auto, 32, 64, 16, 1]` |

### predict() gives wrong results

- Check that input values are floats: `1.0` not `1`
- Check that input length matches `~layers[0]` (or `auto` input size)
- Make sure training converged (loss should be low)

### C vs interpreter

- Files with `net` blocks always compile to C
- `data.cust` works in both modes
- Use `kuda interp file.kuda` if you want to force interpreter (slower but easier to debug)

---

## Examples

### XOR

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 3000
    ~stop = 0.001
    ~log = 1000

out("0,0 = " + str(round(xor.predict([0.0, 0.0]))))
out("0,1 = " + str(round(xor.predict([0.0, 1.0]))))
out("1,0 = " + str(round(xor.predict([1.0, 0.0]))))
out("1,1 = " + str(round(xor.predict([1.0, 1.0]))))
```

### Parity 6-bit

```kuda
net parity:
    ~data = data.binary(6).sequential.parity
    ~layers = [auto, 32, 16, 1]
    ~lr = 0.05
    ~epochs = 10000
    ~stop = 0.001
    ~log = 2000

out("000000 -> 1? " + str(round(parity.predict([0.0,0.0,0.0,0.0,0.0,0.0]))))
out("100000 -> 0? " + str(round(parity.predict([1.0,0.0,0.0,0.0,0.0,0.0]))))
out("110000 -> 1? " + str(round(parity.predict([1.0,1.0,0.0,0.0,0.0,0.0]))))
out("111111 -> 1? " + str(round(parity.predict([1.0,1.0,1.0,1.0,1.0,1.0]))))
```

### sin(x) approximation

```kuda
net sinus:
    ~data = data.numeric.sequential(0.0, 6.28, 0.2).sin
    ~layers = [auto, 16, 8, 1]
    ~lr = 0.01
    ~epochs = 10000
    ~act = tanh
    ~act_out = linear
    ~stop = 0.0001
    ~log = 2000

out("sin(0)    = " + str(sinus.predict([0.0])))
out("sin(1.57) = " + str(sinus.predict([1.5707])))
out("sin(3.14) = " + str(sinus.predict([3.1415])))
```

### Custom: first bit equals last bit

```kuda
data.cust = fun(bits):
    if bits[0] == bits[3]:
        give 1.0
    give 0.0

net mynet:
    ~data = data.binary(4).sequential.cust
    ~layers = [auto, 8, 1]
    ~lr = 0.05
    ~epochs = 3000
    ~stop = 0.001
    ~log = 1000

out("0001 -> 0? " + str(round(mynet.predict([0.0,0.0,0.0,1.0]))))
out("1001 -> 1? " + str(round(mynet.predict([1.0,0.0,0.0,1.0]))))
out("0000 -> 1? " + str(round(mynet.predict([0.0,0.0,0.0,0.0]))))
out("1111 -> 1? " + str(round(mynet.predict([1.0,1.0,1.0,1.0]))))
```

### Two nets in one file

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 2000
    ~stop = 0.001
    ~log = 9999

net kor:
    ~data = data.binary(2).sequential.kor
    ~layers = [auto, 4, 1]
    ~lr = 0.1
    ~epochs = 1000
    ~stop = 0.0001
    ~log = 9999

out("XOR 1,0 = " + str(round(xor.predict([1.0, 0.0]))))
out("OR  0,0 = " + str(round(kor.predict([0.0, 0.0]))))
out("OR  1,0 = " + str(round(kor.predict([1.0, 0.0]))))
```

---

*Kuda v0.2.6 — open source*