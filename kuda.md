# Kuda Language Reference
**Version 0.2.9**

Kuda is a programming language with Python-like syntax that compiles to C for fast execution. This document covers everything you need to write Kuda programs.

---

## Table of Contents

1. [Running Kuda](#running-kuda)
2. [Basic Syntax](#basic-syntax)
3. [Variables & Types](#variables--types)
4. [Output](#output)
5. [Operators](#operators)
6. [Strings](#strings)
7. [Lists](#lists)
8. [Tuples](#tuples)
9. [Dictionaries](#dictionaries)
10. [Control Flow](#control-flow)
11. [check / is](#check--is)
12. [Functions](#functions)
13. [Generators (yield)](#generators-yield)
14. [Anonymous Functions](#anonymous-functions)
15. [Models (Classes)](#models-classes)
16. [Math Functions](#math-functions)
17. [File I/O](#file-io)
18. [Time](#time)
19. [Matrix Operations](#matrix-operations)
20. [ML Functions](#ml-functions)
21. [Neural Networks (net block)](#neural-networks-net-block)
22. [DataBuilder](#databuilder)
23. [Importing Files](#importing-files)
24. [Python Libraries](#python-libraries)
25. [C Libraries & extern](#c-libraries--extern)
26. [Error Handling](#error-handling)
27. [REPL](#repl)
28. [Full Examples](#full-examples)

---

## Running Kuda

```bash
kuda file.kuda              # Run a file (compiles to C, fast)
kuda interp file.kuda       # Interpreter mode (for debugging)
kuda py file.kuda           # Run with Python libraries
kuda build file.kuda        # Build a standalone binary
kuda version                # Show version
kuda help                   # Show help
```

**When does it use C vs interpreter?**
- Files with `net` blocks → compiles to C automatically
- Files with only `data.binary/numeric` (no net) → uses interpreter
- `kuda interp` → always interpreter

---

## Basic Syntax

Kuda uses **indentation** to define blocks, just like Python. Use 4 spaces consistently.

```kuda
# This is a comment

if x > 0:
    out("positive")   # inside the if block
out("always runs")    # outside the if block
```

---

## Variables & Types

```kuda
x = 10
y = 3.14
name = "Kuda"
flag = True
empty = None
```

### Augmented Assignment

```kuda
x += 5
x -= 3
x *= 2
x /= 4
```

### Types

| Type | Example | Notes |
|------|---------|-------|
| number | `42`, `3.14` | All numbers are doubles internally |
| string | `"hello"` | Single or double quotes |
| bool | `True`, `False` | Capital T and F |
| list | `[1, 2, 3]` | Dynamic |
| tuple | `(1, "hello")` | Fixed pair |
| dict | `{"key": "val"}` | Key-value pairs |
| matrix | `Matrix(3, 3)` | For ML/math |
| None | `None` | Empty/null value |

---

## Output

```kuda
out("Hello, World!")
out(42)
out("Value: " + str(42))
```

---

## Operators

```kuda
# Math
x = 10 + 5
x = 10 - 5
x = 10 * 5
x = 10 / 5
x = 10 % 3     # modulo

# Comparison
x == y
x != y
x > y
x < y
x >= y
x <= y

# Logical
x and y
x or y
not x
```

---

## Strings

```kuda
text = "  Hello World  "

text.caps()                  # "  HELLO WORLD  "
text.small()                 # "  hello world  "
text.trim()                  # "Hello World"
text.swap("World", "Kuda")   # "  Hello Kuda  "
text.cut(" ")                # split by space -> list
len(text)                    # 15

str(42)       # "42"
int("42")     # 42
float("3.14") # 3.14

" ".merge(["a", "b", "c"])   # "a b c"  — join list with separator
```

---

## Lists

```kuda
nums = [1, 2, 3, 4, 5]

# Access
x = nums[0]
x = nums[-1]
x = nums.grab(2)
x = nums.grab()     # pop last

# Modify
nums[0] = 99
nums.add(9)
nums.del(1)
nums.sort()
nums.rev()

# Concatenate
a = [1, 2, 3]
b = [4, 5, 6]
c = a + b           # [1, 2, 3, 4, 5, 6]

# Info
nums.fd(4)
nums.cnt(5)
len(nums)
sum(nums)

# Comprehension
squares = [x * x each x in nums]

# Loop
each item in nums:
    out(str(item))
```

---

## Tuples

```kuda
point = (10, 20)

# Unpack in each
data = [([0, 0], 0), ([0, 1], 1)]
each inputs, label in data:
    out(str(inputs) + " -> " + str(label))
```

---

## Dictionaries

```kuda
config = {
    "lr": 0.01,
    "epochs": 1000
}

out(str(config["lr"]))
config["hidden"] = 16
```

---

## Control Flow

```kuda
# if / othif / other
if x > 10:
    out("big")
othif x == 10:
    out("ten")
other:
    out("small")

# repeat N times
repeat 5:
    out("hello")

# each (for each)
# each (for each)
each i in range(10):         # 0..9
    out(str(i))

each i in range(2, 8):       # 2..7
    out(str(i))

each i in range(0, 10, 2):   # 0, 2, 4, 6, 8
    out(str(i))

each x, y in [(1, 2), (3, 4)]:
    out(str(x + y))

# til (while)
i = 0
til i < 10:
    i += 1

# break / continue
each i in range(10):
    if i == 5:
        break
```

---

## check / is

Match expression against values — like a switch statement:

```kuda
check x:
    is 1:
        out("one")
    is 2:
        out("two")
    other:
        out("no match")
```

Works with numbers **and** strings:

```kuda
lang = "kuda"
check lang:
    is "python":
        out("python!")
    is "kuda":
        out("kuda!")
    other:
        out("unknown language")
```

`other` is optional. If no `is` matches and there is no `other`, nothing happens.

```kuda
check x:
    is 0:
        out("zero")
    is 1:
        out("one")
```

`check` compiles to a series of `if/else if` in C — full speed.


---

## Functions

```kuda
fun greet(name):
    out("Hello, " + name + "!")

fun add(a, b):
    give a + b

result = add(10, 20)
```

### Recursion

```kuda
fun factorial(n):
    if n <= 1:
        give 1
    give n * factorial(n - 1)
```

---

## Generators (yield)

A function with `yield` returns a generator — values are produced lazily, one at a time:

```kuda
fun numbers(n):
    i = 0
    til i < n:
        yield i
        i += 1

each x in numbers(5):
    out(str(x))   # 0 1 2 3 4
```

Generators can be **infinite** — stop them with `break`:

```kuda
fun fibonacci():
    a = 0
    b = 1
    til True:
        yield a
        tmp = a + b
        a = b
        b = tmp

each f in fibonacci():
    out(str(f))
    if f > 100:
        break
```

Use `.collect()` to gather all values into a list:

```kuda
fun squares(n):
    each i in range(1, n + 1):
        yield i * i

lista = squares(5).collect()   # [1, 4, 9, 16, 25]
```

Works with `if`, `each`, `til`, `repeat`, `break` and `continue` inside the generator body.

> **Note:** generators run in interpreter mode. Code using `yield` automatically falls back from C compilation to the interpreter.


---

## Anonymous Functions

Functions can be used as values without a name:

```kuda
double = fun(x):
    give x * 2.0

result = double(5.0)
```

Anonymous functions are mainly used with `data.cust` — see [DataBuilder](#databuilder).

---

## Models (Classes)

```kuda
model Dog:
    fun init(self, name, breed):
        self.name = name
        self.breed = breed

    fun bark(self):
        out(self.name + " says: Woof!")

dog = Dog("Rex", "Labrador")
dog.bark()
```

---

## Math Functions

```kuda
prw(16)             # square root: 4.0
pot(2, 8)           # power: 256.0
dwn(3.7)            # floor: 3
up(3.2)             # ceil: 4
abs(-42)            # 42
round(3.7)          # 4  (returns int)
round(3.14159, 2)   # 3.14 (with precision)
max(10, 20)         # 20
min(10, 20)         # 10
rand(1, 100)        # random integer
rand_float()        # random float 0.0-1.0
rand_normal(0, 1)   # random float from normal distribution (mean, std)
log(2.71828)        # natural log
exp(1)              # e^1
sum([1,2,3])        # 6
pi                  # 3.14159...
```

---

## File I/O

```kuda
content = read("myfile.txt")         # read entire file as string
write("output.txt", "Hello!")        # write file (overwrites)
append("log.txt", "new line\n")     # append to file
lines = readlines("myfile.txt")      # read file as list of lines
```

Example — simple file-based log:

```kuda
write("log.txt", "start\n")
append("log.txt", "step 1\n")
append("log.txt", "step 2\n")

lines = readlines("log.txt")
out("Lines: " + str(len(lines)))
each line in lines:
    out("> " + line)
```

`append` and `readlines` work in both interpreter and C mode.

---

## Time

```kuda
wait(2)
t = time()
```

---

## Matrix Operations

```kuda
m = Matrix(3, 3)
w = mat_rand(4, 3)
z = mat_zeros(2, 2)

c = mat_mul(a, b)
c = mat_add(a, b)
c = mat_sub(a, b)
c = mat_hadamard(a, b)
c = mat_scale(a, 0.5)
t = mat_T(a)

val = mat_get(m, 0, 1)
mat_set(m, 1, 2, 99.0)
mat_print(m)
mat_sum(m)
mat_mean(m)
```

---

## ML Functions

```kuda
# Activations (scalar)
sigmoid(x)
relu(x)
tanh(x)
leaky(x)        # leaky relu: x if x > 0 else 0.01 * x

# Activation derivatives (scalar) — for manual backprop
sigmoid_d(x)    # sigmoid derivative: x * (1 - x)
tanh_d(x)       # tanh derivative: 1 - x * x
relu_d(x)       # relu derivative: 1 if x > 0 else 0
leaky_d(x)      # leaky relu derivative: 1 if x > 0 else 0.01

# Activations (matrix)
mat_sigmoid(m)
mat_relu(m)
mat_tanh(m)
mat_sigmoid_deriv(m)
mat_relu_deriv(m)

# Loss
mse(pred, target)
mse_grad(preds, targets)

# Weight init
xav(n_in, n_out)
he(n_in, n_out)

# Utilities
dot(a, b)
mean(list)
norm(list)
softmax(list)
argmax(list)
argmin(list)
clip(x, lo, hi)
acc(preds, targets)
crent(pred, target)
snip(list, start, end)
pack(list, size)
shuffle(list)
save_weights(net, path)
load_weights(net, path)
```

---

## Neural Networks (net block)

See [net.md](net.md) for the full reference.

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 3000
    ~act = tanh
    ~stop = 0.001
    ~log = 1000

out(str(round(xor.predict([1.0, 0.0]))))
```

### Parameters

| Parameter | Example | Default | Description |
|-----------|---------|---------|-------------|
| `~data` | `data.binary(3).sequential.xor` | — | Dataset from DataBuilder |
| `~inputs` | `[[0,0],[0,1]]` | — | Manual inputs |
| `~targets` | `[[0],[1]]` | — | Manual targets |
| `~layers` | `[auto, 16, 8, 1]` | — | Layer sizes |
| `~lr` | `0.01` | `0.01` | Learning rate |
| `~epochs` | `5000` | `1000` | Training epochs |
| `~act` | `tanh` | `tanh` | Hidden activation |
| `~act_out` | `linear` | same as `~act` | Output activation |
| `~init` | `xav` | `xav` | Weight init (`xav` or `he`) |
| `~log` | `500` | `100` | Print loss every N epochs |
| `~stop` | `0.001` | — | Early stop threshold |

---

## DataBuilder

See [net.md](net.md) for the full reference.

```kuda
# Binary
data = data.binary(3).sequential.xor
data = data.binary(4).sequential.parity
data = data.binary(4).random(200).kor

# Numeric
data = data.numeric.sequential(0.0, 10.0, 0.5).sin
data = data.numeric.random(100, 0.0, 10.0).square

# Custom target
data.cust = fun(bits):
    if bits[0] == bits[3]:
        give 1.0
    give 0.0

data = data.binary(4).sequential.cust
```

---

## Importing Files

Split your code across multiple files using `use`:

```kuda
use "utils.kuda"          # relative to current file
use "libs/math.kuda"      # subfolder relative to current file
use @"src/helpers.kuda"   # relative to CWD / project root
use @"/abs/path/to/file.kuda"  # absolute path
```

All functions, variables and models from the imported file become available immediately. Imports are resolved at both compile time (C mode) and run time (interpreter). Nested imports work — a file can `use` other files.

**Example:**

```kuda
# mathlib.kuda
fun square(x):
    give x * x

PI = 3.14159265
```

```kuda
# main.kuda
use "mathlib.kuda"

out(str(square(5.0)))   # 25
out(str(PI))            # 3.14159265
```

---

## Python Libraries

```kuda
use numpy as np

arr = np.array([1, 2, 3])
out(str(np.mean(arr)))
```

> Requires `kuda py file.kuda`.

---

## C Libraries & extern

Link system C libraries with `use`:

```kuda
use sdl2      # adds -lSDL2 to gcc
use gl        # adds -lGL
use pthread   # adds -lpthread
use curl      # adds -lcurl
use sqlite3   # adds -lsqlite3
```

Include external C source files with `extern`:

```kuda
extern "wrapper.c"   # compile this .c file alongside your program
```

Declare C functions for use in Kuda:

```kuda
extern void   SDL_Init(double flags)
extern void   SDL_Delay(double ms)
extern str    SDL_GetError()
extern double my_compute(double x, double y)
```

**Full example — calling C from Kuda:**

```kuda
use sdl2
extern "sdl_wrapper.c"
extern void   kuda_window_open(double w, double h)
extern void   kuda_window_close()

kuda_window_open(800.0, 600.0)
kuda_window_close()
```

---

## Error Handling

```kuda
# basic — catch any error
try:
    result = int("not a number")
fail:
    out("Something went wrong!")

# with error message
try:
    x = int("abc")
fail e:
    out("Error: " + e)

# with error type
try:
    y = 1.0 / 0.0
fail ZeroDivision e:
    out("Division by zero: " + e)

# multiple clauses
try:
    lista = [1.0, 2.0]
    z = lista[10]
fail IndexError e:
    out("Bad index: " + e)
fail e:
    out("Other error: " + e)
```

**Available error types:**

| Type | Catches |
|------|---------|
| `TypeError` | wrong type in operation |
| `ValueError` | invalid value conversion |
| `IndexError` | list index out of range |
| `KeyError` | dict key not found |
| `ZeroDivision` | division by zero |
| `FileError` | file not found / IO error |
| `RuntimeError` | general runtime error |
| `AttributeError` | attribute not found |

Runtime errors include the line number:

```
[Kuda RuntimeError] Line 3: Type error on '+': ...
[Kuda RuntimeError] Line 7: Undefined variable: 'x'
[Kuda RuntimeError] Line 12: Division by zero
[Kuda RuntimeError] Line 5: Index error: list index out of range
```
## REPL

Interactive console — type code and see results immediately:

```bash
kuda repl
```

```
Kuda v0.2.9 REPL — type 'exit' or Ctrl+C to quit
>>> x = 10
>>> y = 20
>>> out(str(x + y))
30
>>> fun square(n):
...     give n * n
>>> out(str(square(7)))
49
>>> exit
```

- Variables and functions persist between lines
- Multi-line blocks (`fun`, `if`, `each`, etc.) work normally
- `exit` or `Ctrl+C` to quit
- `Ctrl+C` while typing a block cancels the buffer without exiting


---

## Full Examples

### FizzBuzz

```kuda
each i in range(1, 101):
    if i % 15 == 0:
        out("FizzBuzz")
    othif i % 3 == 0:
        out("Fizz")
    othif i % 5 == 0:
        out("Buzz")
    other:
        out(str(i))
```

### XOR Neural Network

```kuda
net xor:
    ~data = data.binary(2).sequential.xor
    ~layers = [auto, 8, 1]
    ~lr = 0.1
    ~epochs = 3000
    ~stop = 0.001
    ~log = 1000

out("0,1 = " + str(round(xor.predict([0.0, 1.0]))))
out("1,1 = " + str(round(xor.predict([1.0, 1.0]))))
```

### Custom Target

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

out(str(round(mynet.predict([0.0,0.0,1.0,0.0,1.0,0.0,0.0,0.0]))))
```

---

*Kuda v0.2.9 — open source*