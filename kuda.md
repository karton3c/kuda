# Kuda Language Reference
**Version 0.2.5**

Kuda is my own programming language with Python-like syntax that compiles to C for fast execution. This document covers everything you need to write Kuda programs.

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
11. [Functions](#functions)
12. [Models (Classes)](#models-classes)
13. [Math Functions](#math-functions)
14. [File I/O](#file-io)
15. [Time](#time)
16. [Matrix Operations](#matrix-operations)
17. [ML Functions](#ml-functions)
18. [Python Libraries](#python-libraries)
19. [Error Handling](#error-handling)
20. [Full Examples](#full-examples)

---

## Running Kuda

```bash
kuda file.kuda              # Run a file (fast, compiles to C)
kuda py file.kuda           # Run with Python libraries
kuda build file.kuda        # Build a standalone binary
kuda interp file.kuda       # Interpreter mode (for debugging)
kuda version                # Show version
kuda help                   # Show help
```

---

## Basic Syntax

Kuda uses **indentation** to define blocks, just like Python. Use 4 spaces (or 1 tab) consistently.

```kuda
# This is a comment

# Indentation defines blocks
if x > 0:
    out("positive")   # inside the if block
out("always runs")    # outside the if block
```

Comments start with `#` and go to the end of the line. There are no multi-line comments.

---

## Variables & Types

Variables are created by assigning a value. No need to declare types — Kuda figures it out automatically.

```kuda
# Numbers
x = 10
y = 3.14
z = -42

# Strings
name = "Kuda"
greeting = 'Hello!'

# Booleans
flag = True
other = False

# None
empty = None
```

### Augmented Assignment

You can use shorthand operators to update variables:

```kuda
x = 10
x += 5    # x is now 15
x -= 3    # x is now 12
x *= 2    # x is now 24
x /= 4    # x is now 6.0
```

### Types in Kuda

| Type | Example | Notes |
|------|---------|-------|
| number | `42`, `3.14` | All numbers are doubles internally |
| string | `"hello"` | Single or double quotes |
| bool | `True`, `False` | Capital T and F |
| list | `[1, 2, 3]` | Dynamic, grows automatically |
| tuple | `(1, "hello")` | Fixed pair or group of values |
| dict | `{"key": "val"}` | Key-value pairs |
| matrix | `Matrix(3, 3)` | For ML/math operations |
| None | `None` | Empty/null value |

---

## Output

Use `out()` to print anything to the screen.

```kuda
out("Hello, World!")
out(42)
out(3.14)
out(True)
out([1, 2, 3])

# Combine with str() to mix types
name = "Kuda"
version = 2
out("Welcome to " + name + " v" + str(version))
```

---

## Operators

### Math Operators
```kuda
x = 10 + 5     # 15  addition
x = 10 - 5     # 5   subtraction
x = 10 * 5     # 50  multiplication
x = 10 / 5     # 2   division
x = 10 % 3     # 1   modulo (remainder)
```

### Augmented Assignment
```kuda
x += 5    # same as x = x + 5
x -= 3    # same as x = x - 3
x *= 2    # same as x = x * 2
x /= 4    # same as x = x / 4
```

### Comparison Operators
```kuda
x == y    # equal
x != y    # not equal
x > y     # greater than
x < y     # less than
x >= y    # greater than or equal
x <= y    # less than or equal
```

### Logical Operators
```kuda
x and y   # both must be true
x or y    # at least one must be true
not x     # opposite
```

### String Concatenation
```kuda
result = "Hello" + " " + "World"

# Always convert numbers to string first
age = 25
out("Age: " + str(age))
```

---

## Strings

### Creating Strings
```kuda
a = "double quotes"
b = 'single quotes'
c = "it's fine"
```

### String Methods
Call methods directly on a string using `.`:

```kuda
text = "  Hello World  "

text.caps()                  # "  HELLO WORLD  "
text.small()                 # "  hello world  "
text.trim()                  # "Hello World"
text.swap("World", "Kuda")   # "  Hello Kuda  "
text.cut(" ")                # split by space
len(text)                    # 15
```

### Type Conversion
```kuda
str(42)         # "42"
str(3.14)       # "3.14"
str(True)       # "True"
int("42")       # 42
float("3.14")   # 3.14
```

---

## Lists

Lists hold multiple values and grow automatically.

### Creating Lists
```kuda
empty = []
nums = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True]
nested = [[1, 2], [3, 4]]
```

### Multiline Lists

Lists can span multiple lines — Kuda ignores indentation inside `[...]`:

```kuda
data = [
    1, 2, 3,
    4, 5, 6,
    7, 8, 9
]
```

### Accessing Elements
```kuda
nums = [10, 20, 30, 40]

x = nums[0]         # 10  (direct index)
x = nums[-1]        # 40  (negative index from end)
x = nums.grab(2)    # 30  (grab by index)
x = nums.grab()     # pop last element
```

### Assigning to Index
```kuda
nums = [1, 2, 3]
nums[0] = 99        # [99, 2, 3]
```

### List Methods
```kuda
nums = [3, 1, 4, 1, 5]

nums.add(9)         # add to end
nums.del(1)         # remove first 1
nums.sort()         # sort in place
nums.rev()          # reverse in place
nums.grab(0)        # get at index 0
nums.grab()         # pop last
nums.fd(4)          # find index of 4
nums.cnt(5)         # count 5s
len(nums)           # length
sum(nums)           # sum of all elements
```

### List Comprehension

Create a new list by transforming another:

```kuda
nums = [1, 2, 3, 4, 5]
squares = [x * x each x in nums]    # [1, 4, 9, 16, 25]
```

### Looping Over Lists
```kuda
fruits = ["apple", "banana", "cherry"]

each fruit in fruits:
    out(fruit)
```

---

## Tuples

Tuples are fixed pairs or groups of values, created with `()`.

```kuda
point = (10, 20)
person = ("Artur", 21)
```

### Tuple Unpacking in `each`

You can unpack tuples directly in a loop:

```kuda
data = [
    ([0, 0], 0),
    ([0, 1], 1),
    ([1, 0], 1),
    ([1, 1], 0)
]

each x, t in data:
    out(str(x) + " -> " + str(t))
```

### Lists of Tuples

Useful for training data in ML:

```kuda
dataset = [
    ([0, 0, 0], 0),
    ([0, 0, 1], 1),
    ([0, 1, 0], 1),
    ([1, 1, 1], 1)
]

each inputs, label in dataset:
    out("inputs: " + str(inputs) + " label: " + str(label))
```

---

## Dictionaries

Dictionaries store key-value pairs.

### Creating Dictionaries
```kuda
person = {"name": "Artur", "age": 21}

# Multiline is fine too
config = {
    "lr": 0.01,
    "epochs": 1000,
    "hidden": 16
}
```

### Accessing Values
```kuda
out(person["name"])     # Artur
out(str(person["age"])) # 21
```

### Adding and Updating
```kuda
person["city"] = "Krakow"   # add new key
person["age"] = 22           # update existing key
```

---

## Control Flow

### If / Else

```kuda
x = 10

if x > 10:
    out("big")
othif x == 10:
    out("exactly ten")
other:
    out("small")
```

### Repeat (loop N times)

```kuda
repeat 5:
    out("hello")

n = 10
repeat n:
    out("looping")
```

### Each (for each item)

```kuda
# Loop over a list
each item in [1, 2, 3, 4, 5]:
    out(str(item))

# Loop over a range
each i in range(10):
    out(str(i))

# Range with start and end
each i in range(5, 10):
    out(str(i))

# Tuple unpacking
each x, y in [(1, 2), (3, 4)]:
    out(str(x) + " + " + str(y) + " = " + str(x + y))
```

### Til (while loop)

```kuda
i = 0
til i < 10:
    out(str(i))
    i += 1
```

### Break and Continue

```kuda
# break - exit the loop immediately
each i in range(10):
    if i == 5:
        break
    out(str(i))   # prints 0 1 2 3 4

# continue - skip to next iteration
each i in range(10):
    if i % 2 == 0:
        continue
    out(str(i))   # prints 1 3 5 7 9
```

---

## Functions

### Defining Functions

```kuda
fun greet(name):
    out("Hello, " + name + "!")

greet("World")
```

### Returning Values

Use `give` to return a value:

```kuda
fun add(a, b):
    give a + b

result = add(10, 20)
out(str(result))    # 30
```

### Recursion

```kuda
fun factorial(n):
    if n <= 1:
        give 1
    give n * factorial(n - 1)

out(str(factorial(5)))   # 120
```

---

## Models (Classes)

Models let you group data and functions together.

### Defining a Model

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
abs(-42)            # absolute value: 42
round(3.14159, 2)   # round: 3.14
max(10, 20)         # 20
min(10, 20)         # 10
rand(1, 100)        # random integer
rand_float()        # random float 0.0-1.0
log(2.71828)        # natural log: ~1.0
exp(1)              # e^1: ~2.71828
sum([1,2,3,4,5])    # 15
pi                  # 3.14159...
```

---

## File I/O

```kuda
# Read
content = read("myfile.txt")
out(content)

# Write
write("output.txt", "Hello from Kuda!")

# Append
existing = read("log.txt")
write("log.txt", existing + "\nNew line")
```

---

## Time

```kuda
wait(2)         # wait 2 seconds
wait(0.5)       # wait half a second
t = time()      # seconds since epoch
```

---

## Matrix Operations

### Creating Matrices

```kuda
m = Matrix(3, 3)        # empty matrix
w = mat_rand(4, 3)      # random matrix
z = mat_zeros(2, 2)     # zero matrix
```

### Operations

```kuda
c = mat_mul(a, b)           # multiply
c = mat_add(a, b)           # add
c = mat_sub(a, b)           # subtract
c = mat_hadamard(a, b)      # element-wise multiply
c = mat_scale(a, 0.5)       # scale
t = mat_T(a)                # transpose
c = mat_copy(a)             # copy
```

### Access

```kuda
val = mat_get(m, 0, 1)      # get row 0, col 1
mat_set(m, 1, 2, 99.0)      # set row 1, col 2
out(str(m.rows))             # number of rows
out(str(m.cols))             # number of cols
```

### Stats

```kuda
total = mat_sum(m)
avg   = mat_mean(m)
mat_print(m)
```

---

## ML Functions

### Scalar Activation Functions

```kuda
sigmoid(0.5)        # 0.622
relu(5.0)           # 5.0
relu(-3.0)          # 0.0
```

### Matrix Activation Functions

```kuda
mat_sigmoid(m)          # sigmoid on every element
mat_relu(m)             # relu on every element
mat_tanh(m)             # tanh on every element
mat_sigmoid_deriv(m)    # sigmoid derivative
mat_relu_deriv(m)       # relu derivative
```

### Loss Functions

```kuda
# Works with both scalars and matrices
loss = mse(prediction, target)
grad = mse_grad(predictions, targets)   # matrix only
```

---

## Python Libraries

Use `kuda py file.kuda` to access any installed Python library.

```kuda
use numpy as np
use pandas as pd

arr = np.array([1, 2, 3, 4, 5])
out("Mean: " + str(np.mean(arr)))
```

> **Note:** `kuda py` runs through the interpreter, not compiled to C. Slower but gives access to the full Python ecosystem.

---

## Error Handling

```kuda
try:
    result = int("not a number")
fail:
    out("Something went wrong!")
```

---

## Full Examples

### Example 1: FizzBuzz

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

### Example 2: Fibonacci

```kuda
fun fib(n):
    if n <= 1:
        give n
    give fib(n - 1) + fib(n - 2)

each i in range(10):
    out(str(fib(i)))
```

### Example 3: List Comprehension

```kuda
nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
squares = [x * x each x in nums]
out(str(squares))
```

### Example 4: Tuple Unpacking

```kuda
data = [
    ([0, 0], 0),
    ([0, 1], 1),
    ([1, 0], 1),
    ([1, 1], 0)
]

each inputs, label in data:
    out(str(inputs) + " -> " + str(label))
```

### Example 5: Dictionary

```kuda
scores = {"Alice": 95, "Bob": 87, "Carol": 92}
scores["Dave"] = 78

each name in ["Alice", "Bob", "Carol", "Dave"]:
    out(name + ": " + str(scores[name]))
```

### Example 6: Neural Network Layer

```kuda
fun forward(inputs, weights, bias):
    result = mat_mul(inputs, weights)
    result = mat_add(result, bias)
    give mat_sigmoid(result)

inputs  = mat_rand(1, 4)
weights = mat_rand(4, 3)
bias    = mat_zeros(1, 3)

output = forward(inputs, weights, bias)
mat_print(output)
```

---

## Quick Reference Card

### Control Flow
| Keyword | Meaning |
|---------|---------|
| `if` | if condition |
| `othif` | else if |
| `other` | else |
| `repeat n` | loop n times |
| `each x in list` | for each |
| `each x, y in list` | for each with tuple unpacking |
| `til condition` | while |
| `break` | exit loop |
| `continue` | next iteration |

### Functions & Models
| Keyword | Meaning |
|---------|---------|
| `fun name(args)` | define function |
| `give value` | return value |
| `model Name` | define class |
| `self` | current instance |

### Operators
| Operator | Meaning |
|----------|---------|
| `+= -= *= /=` | augmented assignment |
| `%` | modulo |
| `and or not` | logical |

### Built-in Functions
| Function | What it does |
|----------|-------------|
| `out(x)` | print to screen |
| `str(x)` | convert to string |
| `int(x)` | convert to integer |
| `float(x)` | convert to float |
| `len(x)` | length of string or list |
| `input(prompt)` | read from keyboard |
| `range(n)` | numbers 0 to n-1 |
| `range(a, b)` | numbers a to b-1 |
| `sum(list)` | sum of list |
| `max(a, b)` | larger of two |
| `min(a, b)` | smaller of two |
| `abs(x)` | absolute value |
| `round(x, n)` | round to n decimals |
| `rand(lo, hi)` | random integer |
| `rand_float()` | random 0.0 to 1.0 |
| `read(file)` | read file |
| `write(file, text)` | write file |
| `wait(seconds)` | sleep |
| `time()` | current time |

### Math Functions
| Function | What it does |
|----------|-------------|
| `prw(x)` | square root |
| `pot(x, y)` | x to the power of y |
| `dwn(x)` | floor (round down) |
| `up(x)` | ceil (round up) |
| `log(x)` | natural log |
| `exp(x)` | e to the power of x |
| `pi` | 3.14159... |

### String Methods
| Method | What it does |
|--------|-------------|
| `.caps()` | uppercase |
| `.small()` | lowercase |
| `.trim()` | remove edge spaces |
| `.swap(a, b)` | replace a with b |
| `.cut(sep)` | split into list |

### List Methods
| Method | What it does |
|--------|-------------|
| `.add(x)` | add to end |
| `.del(x)` | remove first x |
| `.sort()` | sort in place |
| `.rev()` | reverse in place |
| `.grab(i)` | get at index i |
| `.grab()` | pop last element |
| `.fd(x)` | find index of x |
| `.cnt(x)` | count x |

### ML Functions
| Function | What it does |
|----------|-------------|
| `sigmoid(x)` | sigmoid activation |
| `relu(x)` | relu activation |
| `mat_rand(r, c)` | random matrix |
| `mat_zeros(r, c)` | zero matrix |
| `mat_mul(a, b)` | matrix multiply |
| `mat_add(a, b)` | matrix add |
| `mat_sub(a, b)` | matrix subtract |
| `mat_scale(m, s)` | scale matrix |
| `mat_T(m)` | transpose |
| `mat_sigmoid(m)` | sigmoid on matrix |
| `mat_relu(m)` | relu on matrix |
| `mat_tanh(m)` | tanh on matrix |
| `mat_sum(m)` | sum all elements |
| `mat_mean(m)` | average all elements |
| `mat_print(m)` | print matrix |
| `mse(pred, target)` | mean squared error (scalar or matrix) |

---

*Kuda v0.2.5 — open source, contributions welcome!*