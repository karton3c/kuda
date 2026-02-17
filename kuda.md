# Kuda Language Reference
**Version 0.2.1**

Kuda is my own programming language with Python-like syntax that compiles to C for fast execution. This document covers everything you need to write Kuda programs

---

## Table of Contents

1. [Running Kuda](#running-kuda)
2. [Basic Syntax](#basic-syntax)
3. [Variables & Types](#variables--types)
4. [Output](#output)
5. [Operators](#operators)
6. [Strings](#strings)
7. [Lists](#lists)
8. [Control Flow](#control-flow)
9. [Functions](#functions)
10. [Models (Classes)](#models-classes)
11. [Math Functions](#math-functions)
12. [File I/O](#file-io)
13. [Time](#time)
14. [Matrix Operations](#matrix-operations)
15. [ML Functions](#ml-functions)
16. [Python Libraries](#python-libraries)
17. [Error Handling](#error-handling)
18. [Full Examples](#full-examples)

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

### Types in Kuda

| Type | Example | Notes |
|------|---------|-------|
| number | `42`, `3.14` | All numbers are doubles internally |
| string | `"hello"` | Single or double quotes |
| bool | `True`, `False` | Capital T and F |
| list | `[1, 2, 3]` | Dynamic, grows automatically |
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

text.caps()             # "  HELLO WORLD  "
text.small()            # "  hello world  "
text.trim()             # "Hello World"    (removes spaces from edges)
text.swap("World", "Kuda")  # "  Hello Kuda  "
text.cut(" ")           # ["", "", "Hello", "World", "", ""]  (split)
len(text)               # 15  (length)
```

### String Functions
These work the same way but as standalone calls:

```kuda
caps("hello")           # "HELLO"
small("HELLO")          # "hello"
trim("  hi  ")          # "hi"
swap("hello", "l", "r") # "herro"
cut("a,b,c", ",")       # ["a", "b", "c"]
merge("-", ["a","b","c"])# "a-b-c"
len("hello")            # 5
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

### Accessing Elements
```kuda
nums = [10, 20, 30, 40]

# By index (starts at 0)
x = nums.grab(0)    # 10
x = nums.grab(2)    # 30

# Pop last element
x = nums.grab()     # 40, list is now [10, 20, 30]
```

### List Methods
```kuda
nums = [3, 1, 4, 1, 5]

nums.add(9)         # add to end:    [3, 1, 4, 1, 5, 9]
nums.del(1)         # remove first 1: [3, 4, 1, 5, 9]
nums.sort()         # sort:           [1, 3, 4, 5, 9]
nums.rev()          # reverse:        [9, 5, 4, 3, 1]
nums.grab(0)        # get at index 0: 9
nums.grab()         # pop last:       1, list shrinks
nums.fd(4)          # find index of 4: 2
nums.cnt(5)         # count 5s: 1
len(nums)           # length
```

### Looping Over Lists
```kuda
fruits = ["apple", "banana", "cherry"]

each fruit in fruits:
    out(fruit)
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

You can have as many `othif` blocks as you need. `other` is optional.

```kuda
# Simple if with no else
if flag:
    out("flag is true")

# Multiple conditions
if x > 0 and y > 0:
    out("both positive")

if x == 0 or y == 0:
    out("at least one is zero")
```

### Repeat (loop N times)

```kuda
# Repeat exactly 5 times
repeat 5:
    out("hello")

# Use a variable
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
```

### Til (while loop)

```kuda
# Loop while condition is true
i = 0
til i < 10:
    out(str(i))
    i = i + 1

# Infinite loop with break
til True:
    x = input("Enter number: ")
    if x == "quit":
        break
    out("You entered: " + x)
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

Use `give` to return a value from a function:

```kuda
fun add(a, b):
    give a + b

result = add(10, 20)
out(str(result))    # 30
```

### Multiple Parameters

```kuda
fun power(base, exp):
    give pot(base, exp)

out(str(power(2, 8)))   # 256
```

### Functions Calling Functions

```kuda
fun square(x):
    give x * x

fun sum_of_squares(a, b):
    give square(a) + square(b)

out(str(sum_of_squares(3, 4)))   # 25
```

### Recursion

```kuda
fun factorial(n):
    if n <= 1:
        give 1
    give n * factorial(n - 1)

out(str(factorial(5)))   # 120
```

### Default-style Pattern (no default args yet, use if)

```kuda
fun greet(name, loud):
    if loud:
        out(name.caps() + "!!!")
    other:
        out("Hello, " + name)

greet("kuda", True)    # KUDA!!!
greet("kuda", False)   # Hello, kuda
```

---

## Models (Classes)

Models let you group data and functions together, like classes in Python.

### Defining a Model

```kuda
model Dog:
    fun init(self, name, breed):
        self.name = name
        self.breed = breed

    fun bark(self):
        out(self.name + " says: Woof!")

    fun info(self):
        out("Name: " + self.name)
        out("Breed: " + self.breed)
```

### Creating Instances

```kuda
dog = Dog("Rex", "Labrador")
dog.bark()      # Rex says: Woof!
dog.info()      # Name: Rex / Breed: Labrador
```

### Accessing Attributes

```kuda
out(dog.name)   # Rex
out(dog.breed)  # Labrador
```

### Model with Calculations

```kuda
model Circle:
    fun init(self, radius):
        self.radius = radius

    fun area(self):
        give pi * self.radius * self.radius

    fun perimeter(self):
        give 2 * pi * self.radius

c = Circle(5)
out("Area: " + str(c.area()))
out("Perimeter: " + str(c.perimeter()))
```

---

## Math Functions

```kuda
# Square root
prw(16)         # 4.0
prw(2)          # 1.41421

# Power
pot(2, 8)       # 256.0
pot(3, 3)       # 27.0

# Floor and Ceil
dwn(3.7)        # 3  (round down)
up(3.2)         # 4  (round up)

# Absolute value
abs(-42)        # 42
abs(42)         # 42

# Round
round(3.14159, 2)   # 3.14

# Min and Max
max(10, 20)     # 20
min(10, 20)     # 10

# Random integer between lo and hi (inclusive)
rand(1, 100)    # e.g. 47

# Random float between 0 and 1
rand_float()    # e.g. 0.731

# Constants
pi              # 3.14159...

# Log and Exp
log(2.71828)    # ~1.0
exp(1)          # ~2.71828

# Sum of a list
sum([1, 2, 3, 4, 5])   # 15
```

---

## File I/O

### Reading Files

```kuda
content = read("myfile.txt")
out(content)
```

### Writing Files

```kuda
write("output.txt", "Hello from Kuda!")
```

### Appending (read then write)

```kuda
existing = read("log.txt")
write("log.txt", existing + "\nNew line added")
```

---

## Time

```kuda
# Pause execution
wait(2)         # wait 2 seconds
wait(0.5)       # wait half a second

# Get current time (seconds since epoch)
t = time()
out(str(t))
```

---

## Matrix Operations

Matrices are used for fast math, especially in machine learning.

### Creating Matrices

```kuda
# New empty matrix (rows x cols)
m = Matrix(3, 3)

# Random matrix (good for neural network weights)
w = mat_rand(4, 3)

# Zero matrix
z = mat_zeros(2, 2)
```

### Basic Operations

```kuda
a = mat_rand(3, 3)
b = mat_rand(3, 3)

# Multiply (dot product)
c = mat_mul(a, b)

# Element-wise operations
c = mat_add(a, b)       # add
c = mat_sub(a, b)       # subtract
c = mat_hadamard(a, b)  # element-wise multiply

# Scale by a number
c = mat_scale(a, 0.5)

# Transpose
t = mat_T(a)
```

### Accessing Elements

```kuda
m = mat_rand(3, 3)

# Get value at row 0, col 1
val = mat_get(m, 0, 1)

# Set value at row 1, col 2
mat_set(m, 1, 2, 99.0)
```

### Stats

```kuda
m = mat_rand(4, 4)

total = mat_sum(m)      # sum of all elements
avg = mat_mean(m)       # average of all elements
```

### Matrix Properties

```kuda
m = mat_rand(3, 4)

out(str(m.rows))    # 3
out(str(m.cols))    # 4
```

### Printing

```kuda
m = mat_rand(2, 2)
mat_print(m)
# or
m.print()
```

### Copy

```kuda
original = mat_rand(3, 3)
copy = mat_copy(original)
```

### Dot Product (vectors)

```kuda
a = mat_rand(1, 3)
b = mat_rand(3, 1)
result = dot(a, b)
```

---

## ML Functions

These are built-in functions for machine learning.

### Activation Functions

```kuda
# Sigmoid: squashes any number to 0-1
y = sigmoid(0.5)        # 0.622459
y = sigmoid(-2.0)       # 0.119203

# ReLU: keeps positives, zeros out negatives
y = relu(5.0)           # 5.0
y = relu(-3.0)          # 0.0
```

### Matrix Activation Functions

Apply activation functions to entire matrices at once:

```kuda
m = mat_rand(3, 3)

activated = mat_sigmoid(m)          # sigmoid on every element
activated = mat_relu(m)             # relu on every element
activated = mat_tanh(m)             # tanh on every element

# Derivatives (for backpropagation)
d = mat_sigmoid_deriv(m)            # sigmoid derivative
d = mat_relu_deriv(m)               # relu derivative
```

### Loss Functions

```kuda
predictions = mat_rand(4, 1)
targets = mat_rand(4, 1)

# Mean Squared Error
loss = mse(predictions, targets)

# MSE Gradient (for backpropagation)
grad = mse_grad(predictions, targets)
```

---

## Python Libraries

Use `kuda py file.kuda` to run in Python mode, which gives access to any installed Python library.

### Importing Libraries

```kuda
use numpy as np
use pandas as pd
```

### Using Numpy

```kuda
use numpy as np

arr = np.array([1, 2, 3, 4, 5])
out("Sum: " + str(np.sum(arr)))
out("Mean: " + str(np.mean(arr)))
out("Std: " + str(np.std(arr)))

m = np.zeros([3, 3])
out(str(np.dot(m, m)))
```

### Using Any Library

```kuda
use requests as req
use sklearn as sk
use matplotlib as plt
```

> **Note:** `kuda py` mode runs through the interpreter, not compiled to C. It's slower than regular `kuda` but gives you access to the entire Python ecosystem.

---

## Error Handling

### Try / Fail

Use `try` and `fail` to handle errors gracefully:

```kuda
try:
    result = int("not a number")
    out(str(result))
fail:
    out("Something went wrong!")
```

### Common Errors and How to Fix Them

#### ParseError
```
[Kuda ParseError] Line 5: Expected 'INDENT', got 'NEWLINE'
```
**Cause:** Missing indentation after `if`, `fun`, `model`, `repeat`, etc.
**Fix:** Add 4 spaces before the code inside the block.

```kuda
# Wrong:
if x > 0:
out("positive")

# Correct:
if x > 0:
    out("positive")
```

---

```
[Kuda ParseError] Line 3: Expected ')', got 'NEWLINE'
```
**Cause:** Missing closing bracket.
**Fix:** Check all your `(`, `[` are properly closed.

```kuda
# Wrong:
out("hello"

# Correct:
out("hello")
```

---

#### RuntimeError
```
[Kuda RuntimeError] Undefined variable: 'x'
```
**Cause:** Using a variable before it's created.
**Fix:** Make sure you assign the variable first.

```kuda
# Wrong:
out(str(x))
x = 10

# Correct:
x = 10
out(str(x))
```

---

```
[Kuda RuntimeError] No method 'xyz' on str
```
**Cause:** Calling a method that doesn't exist on that type.
**Fix:** Check the method name in this document.

---

#### LexerError
```
[Kuda LexerError] Line 7: Unknown character: '@'
```
**Cause:** Using a character Kuda doesn't understand.
**Fix:** Remove the unknown character. Kuda supports: `+ - * / % = < > ! ( ) [ ] : , . # " '`

---

### Tips for Debugging

Use `kuda interp file.kuda` — the interpreter gives more detailed error messages and is easier to debug than compiled mode.

Add `out()` statements to see what your variables contain:

```kuda
x = some_calculation()
out("DEBUG x = " + str(x))   # check the value
```

Wrap risky code in `try/fail`:

```kuda
try:
    data = read("file.txt")
    process(data)
fail:
    out("Error reading or processing file")
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

### Example 2: Simple Calculator

```kuda
fun calculate(a, op, b):
    if op == "+":
        give a + b
    othif op == "-":
        give a - b
    othif op == "*":
        give a * b
    othif op == "/":
        if b == 0:
            out("Error: divide by zero")
            give 0
        give a / b
    other:
        out("Unknown operator: " + op)
        give 0

out(str(calculate(10, "+", 5)))   # 15
out(str(calculate(10, "*", 3)))   # 30
out(str(calculate(10, "/", 2)))   # 5
```

### Example 3: Fibonacci

```kuda
fun fib(n):
    if n <= 1:
        give n
    give fib(n - 1) + fib(n - 2)

each i in range(10):
    out(str(fib(i)))
```

### Example 4: Working with Lists

```kuda
# Read numbers, find max, min, average
numbers = [23, 7, 45, 12, 67, 3, 89, 34]

numbers.sort()
out("Sorted: ")
out(numbers)

out("Min: " + str(numbers.grab(0)))
out("Max: " + str(numbers.grab(len(numbers) - 1)))
out("Sum: " + str(sum(numbers)))
```

### Example 5: Simple Neural Network Layer

```kuda
# A single neural network layer
fun forward(inputs, weights, bias):
    result = mat_mul(inputs, weights)
    result = mat_add(result, bias)
    give mat_sigmoid(result)

# Create random weights and bias
inputs  = mat_rand(1, 4)   # 1 sample, 4 features
weights = mat_rand(4, 3)   # 4 inputs, 3 outputs
bias    = mat_zeros(1, 3)  # 1 sample, 3 outputs

output = forward(inputs, weights, bias)
out("Layer output:")
mat_print(output)
```

### Example 6: Using Python Libraries

```kuda
# Run with: kuda py example.kuda
use numpy as np

# Generate some data
data = np.random.randn(100)

out("Mean: " + str(np.mean(data)))
out("Std Dev: " + str(np.std(data)))
out("Min: " + str(np.min(data)))
out("Max: " + str(np.max(data)))
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
| `mse(pred, target)` | mean squared error |

---

*Kuda v0.2.1 — open source, contributions welcome!*