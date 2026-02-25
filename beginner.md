# Kuda for Beginners 🚀
**Your first steps in programming with Kuda**

Welcome! This guide will teach you programming from scratch using the Kuda language. No experience needed — we'll go step by step, with lots of examples and exercises along the way.

---

## Chapter 1: Hello, World!

Every programmer starts here. Let's make Kuda say something.

```kuda
out("Hello, World!")
```

Run it with:
```bash
kuda hello.kuda
```

You should see:
```
Hello, World!
```

That's it — your first Kuda program! `out()` is the function that prints things to the screen. Anything you put inside the quotes gets printed.

### Try it yourself:
```kuda
out("Hello!")
out("My name is Kuda.")
out("I am learning to code.")
```

### 🏋️ Exercise 1
Write a program that prints these three lines:
```
I love coding!
Kuda is awesome.
Let's go!
```

---

## Chapter 2: Variables

A variable is like a box where you store information. You give the box a name, and put something inside it.

```kuda
name = "Artur"
out(name)
```

Output:
```
Artur
```

You can store different kinds of things:

```kuda
# A name (text)
name = "Artur"

# An age (number)
age = 17

# A height (decimal number)
height = 1.82

# True or False
is_cool = True
```

### Using variables in sentences

To mix text and variables, use `+` and `str()`:

```kuda
name = "Artur"
age = 17

out("My name is " + name)
out("I am " + str(age) + " years old")
```

Output:
```
My name is Artur
I am 17 years old
```

> **Why str()?** Numbers and text are different things in Kuda. `str()` converts a number into text so you can join it with `+`.

### Changing variables

Variables can change — that's why they're called *vari*ables!

```kuda
score = 0
out("Score: " + str(score))

score = 10
out("Score: " + str(score))

score = 25
out("Score: " + str(score))
```

Output:
```
Score: 0
Score: 10
Score: 25
```

### 🏋️ Exercise 2
Create variables for:
- Your name
- Your age
- Your favourite number

Then print a sentence using all three, like:
```
My name is Artur, I am 17 and my favourite number is 7.
```

---

## Chapter 3: Math

Kuda can do math just like a calculator.

```kuda
out(str(2 + 3))     # 5
out(str(10 - 4))    # 6
out(str(3 * 5))     # 15
out(str(20 / 4))    # 5
out(str(10 % 3))    # 1  (remainder after dividing)
```

### Math with variables

```kuda
price = 10
quantity = 5
total = price * quantity

out("Total: " + str(total))
```

Output:
```
Total: 50
```

### Updating variables with math

```kuda
score = 100

score = score + 50    # add 50
out(str(score))       # 150

score += 25           # shortcut for score = score + 25
out(str(score))       # 175

score -= 30           # subtract 30
out(str(score))       # 145

score *= 2            # multiply by 2
out(str(score))       # 290
```

### What is modulo (%)?

Modulo gives you the **remainder** after division:

```kuda
out(str(10 % 3))   # 1  (10 divided by 3 = 3 remainder 1)
out(str(15 % 5))   # 0  (15 divided by 5 = 3 remainder 0)
out(str(7 % 2))    # 1  (7 divided by 2 = 3 remainder 1)
```

A very common use: checking if a number is even or odd:
```kuda
number = 8
if number % 2 == 0:
    out(str(number) + " is even")
other:
    out(str(number) + " is odd")
```

### 🏋️ Exercise 3
Write a program that:
1. Creates a variable `price` with the value `25`
2. Creates a variable `discount` with the value `5`
3. Calculates the final price after the discount
4. Prints: `Final price: 20`

---

## Chapter 4: Getting Input from the User

You can ask the user to type something:

```kuda
name = input("What is your name? ")
out("Hello, " + name + "!")
```

When you run this, it will wait for you to type. Whatever you type becomes the value of `name`.

### Converting input to a number

Input always gives you text. If you need a number, convert it:

```kuda
age_text = input("How old are you? ")
age = int(age_text)

next_year = age + 1
out("Next year you will be " + str(next_year))
```

### A complete example

```kuda
out("=== Simple Calculator ===")

a_text = input("Enter first number: ")
b_text = input("Enter second number: ")

a = float(a_text)
b = float(b_text)

out("Sum: " + str(a + b))
out("Difference: " + str(a - b))
out("Product: " + str(a * b))
out("Division: " + str(a / b))
```

### 🏋️ Exercise 4
Write a program that:
1. Asks the user for their name
2. Asks the user for their birth year
3. Calculates their age (current year is 2025)
4. Prints something like: `Hello Artur! You are 17 years old.`

---

## Chapter 5: Making Decisions (if / othif / other)

Programs need to make decisions. In Kuda, you use `if`.

```kuda
age = 18

if age >= 18:
    out("You are an adult.")
other:
    out("You are a minor.")
```

### Multiple conditions with othif

```kuda
score = 75

if score >= 90:
    out("Grade: A")
othif score >= 80:
    out("Grade: B")
othif score >= 70:
    out("Grade: C")
othif score >= 60:
    out("Grade: D")
other:
    out("Grade: F")
```

### Comparing things

```kuda
x = 10
y = 20

if x == y:
    out("They are equal")

if x != y:
    out("They are different")

if x < y:
    out("x is smaller")

if x > y:
    out("x is bigger")
```

### Combining conditions

```kuda
age = 20
has_ticket = True

if age >= 18 and has_ticket:
    out("You can enter!")
other:
    out("Sorry, you cannot enter.")
```

```kuda
is_raining = True
has_umbrella = False

if is_raining or has_umbrella:
    out("You should be okay")
other:
    out("You might get wet!")
```

### 🏋️ Exercise 5
Write a program that:
1. Asks the user to enter a number
2. Prints whether it is positive, negative, or zero

**Hint:** You'll need `int(input(...))` and three conditions.

---

## Chapter 6: Loops

Loops let you repeat things without copy-pasting code.

### Repeat — do something N times

```kuda
repeat 5:
    out("Hello!")
```

Output:
```
Hello!
Hello!
Hello!
Hello!
Hello!
```

### Each — loop over a list of things

```kuda
each number in [1, 2, 3, 4, 5]:
    out(str(number))
```

Output:
```
1
2
3
4
5
```

### Range — loop a specific number of times with a counter

```kuda
each i in range(5):
    out("Step " + str(i))
```

Output:
```
Step 0
Step 1
Step 2
Step 3
Step 4
```

Range starts at 0 by default. You can give it a start and end:

```kuda
each i in range(1, 6):
    out(str(i))
```

Output:
```
1
2
3
4
5
```

### Til — repeat while something is true

```kuda
count = 1
til count <= 5:
    out(str(count))
    count += 1
```

Output:
```
1
2
3
4
5
```

> ⚠️ **Warning:** Always make sure the condition eventually becomes False, otherwise your program will run forever!

### Loops with math

```kuda
# Multiplication table for 3
each i in range(1, 11):
    result = 3 * i
    out("3 x " + str(i) + " = " + str(result))
```

Output:
```
3 x 1 = 3
3 x 2 = 6
3 x 3 = 9
...
3 x 10 = 30
```

### Break and Continue

Sometimes you want to exit a loop early or skip an iteration:

```kuda
# Stop when we find 5
each i in range(10):
    if i == 5:
        break
    out(str(i))
# prints 0 1 2 3 4
```

```kuda
# Skip even numbers
each i in range(10):
    if i % 2 == 0:
        continue
    out(str(i))
# prints 1 3 5 7 9
```

### 🏋️ Exercise 6
Write a program that prints the multiplication table for a number chosen by the user:
```
Enter a number: 7
7 x 1 = 7
7 x 2 = 14
...
7 x 10 = 70
```

---

## Chapter 7: Lists

A list is a collection of values stored together.

```kuda
fruits = ["apple", "banana", "cherry"]
numbers = [10, 20, 30, 40, 50]
empty = []
```

### Accessing items

Items in a list are numbered starting from 0:

```kuda
fruits = ["apple", "banana", "cherry"]

out(fruits[0])   # apple
out(fruits[1])   # banana
out(fruits[2])   # cherry
```

Use `-1` to get the last item:
```kuda
out(fruits[-1])  # cherry
```

### Adding items

```kuda
fruits = ["apple", "banana"]
fruits.add("cherry")
fruits.add("mango")

out(str(len(fruits)))   # 4
```

### Changing items

```kuda
fruits = ["apple", "banana", "cherry"]
fruits[1] = "blueberry"

each fruit in fruits:
    out(fruit)
# apple, blueberry, cherry
```

### Looping over a list

```kuda
scores = [85, 92, 78, 96, 88]
total = 0

each score in scores:
    total += score

average = total / len(scores)
out("Average score: " + str(average))
```

### Useful list operations

```kuda
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

numbers.sort()                          # sort: [1, 1, 2, 3, 4, 5, 6, 9]
out("Sorted: " + str(numbers))

numbers.rev()                           # reverse
out("Reversed: " + str(numbers))

out("Length: " + str(len(numbers)))     # 8
out("Sum: " + str(sum(numbers)))        # 31
out("Count of 1s: " + str(numbers.cnt(1)))   # 2
```

### Building a list with a loop

```kuda
squares = []

each i in range(1, 6):
    squares.add(i * i)

out(str(squares))   # [1, 4, 9, 16, 25]
```

Or with list comprehension (shortcut):

```kuda
squares = [i * i each i in range(1, 6)]
out(str(squares))   # [1, 4, 9, 16, 25]
```

### 🏋️ Exercise 7
Write a program that:
1. Creates a list of 5 numbers
2. Finds the biggest number (use a loop and a variable `biggest`)
3. Finds the smallest number
4. Calculates the average
5. Prints all three results

---

## Chapter 8: Functions

Functions let you write code once and use it many times.

### Defining a function

```kuda
fun say_hello():
    out("Hello!")

say_hello()   # call it
say_hello()   # call it again
say_hello()   # and again
```

### Functions with parameters

Parameters are inputs you pass to the function:

```kuda
fun greet(name):
    out("Hello, " + name + "!")

greet("Artur")
greet("World")
greet("Kuda")
```

Output:
```
Hello, Artur!
Hello, World!
Hello, Kuda!
```

### Functions that return a value

Use `give` to send a value back:

```kuda
fun add(a, b):
    give a + b

result = add(3, 7)
out(str(result))   # 10
```

```kuda
fun square(x):
    give x * x

out(str(square(4)))    # 16
out(str(square(10)))   # 100
```

### A real example

```kuda
fun is_even(n):
    if n % 2 == 0:
        give True
    give False

each i in range(1, 11):
    if is_even(i):
        out(str(i) + " is even")
    other:
        out(str(i) + " is odd")
```

### Functions calling other functions

```kuda
fun celsius_to_fahrenheit(c):
    give c * 9.0 / 5.0 + 32.0

fun print_temperature(city, temp_c):
    temp_f = celsius_to_fahrenheit(temp_c)
    out(city + ": " + str(temp_c) + "°C = " + str(temp_f) + "°F")

print_temperature("Warsaw", 20)
print_temperature("London", 15)
print_temperature("New York", 28)
```

### 🏋️ Exercise 8
Write a function `max_of_three(a, b, c)` that takes three numbers and returns the biggest one. Test it with a few different inputs.

---

## Chapter 9: Strings in Depth

You've been using strings since Chapter 1. Let's look at what you can do with them.

### String methods

```kuda
text = "Hello, World!"

out(text.caps())          # HELLO, WORLD!
out(text.small())         # hello, world!
out(text.swap("World", "Kuda"))   # Hello, Kuda!
out(str(len(text)))       # 13
```

### Splitting strings

```kuda
sentence = "the quick brown fox"
words = sentence.cut(" ")

each word in words:
    out(word)
```

Output:
```
the
quick
brown
fox
```

### Building strings in a loop

```kuda
result = ""
each i in range(1, 6):
    result = result + str(i) + " "

out(result)   # 1 2 3 4 5
```

### Checking string content

```kuda
name = input("Enter your name: ")

if len(name) == 0:
    out("You didn't enter anything!")
othif len(name) < 3:
    out("That's a very short name!")
other:
    out("Hello, " + name + "!")
```

### 🏋️ Exercise 9
Write a program that:
1. Asks the user to enter a sentence
2. Splits it into words
3. Prints how many words there are
4. Prints each word on a new line with its length

Example:
```
Enter a sentence: hello world kuda
Words: 3
hello (5 letters)
world (5 letters)
kuda (4 letters)
```

---

## Chapter 10: Putting It All Together

Let's build some real programs using everything you've learned!

### Project 1: Number Guessing Game

```kuda
secret = rand(1, 100)
attempts = 0
won = False

out("=== Guess the Number ===")
out("I'm thinking of a number between 1 and 100.")
out("")

til not won:
    guess_text = input("Your guess: ")
    guess = int(guess_text)
    attempts += 1

    if guess < secret:
        out("Too low! Try higher.")
    othif guess > secret:
        out("Too high! Try lower.")
    other:
        won = True

out("")
out("Correct! The number was " + str(secret))
out("You got it in " + str(attempts) + " attempts!")
```

### Project 2: Grade Calculator

```kuda
fun get_grade(score):
    if score >= 90:
        give "A"
    othif score >= 80:
        give "B"
    othif score >= 70:
        give "C"
    othif score >= 60:
        give "D"
    other:
        give "F"

scores = []
names = []

out("=== Grade Calculator ===")
out("Enter student scores (type 'done' to finish)")
out("")

running = True
til running:
    name = input("Student name (or 'done'): ")
    if name == "done":
        running = False
    other:
        score_text = input("Score for " + name + ": ")
        score = int(score_text)
        names.add(name)
        scores.add(score)

out("")
out("=== Results ===")

i = 0
each score in scores:
    grade = get_grade(score)
    out(names[i] + ": " + str(score) + " → " + grade)
    i += 1

total = sum(scores)
avg = total / len(scores)
out("")
out("Class average: " + str(round(avg)))
```

### Project 3: Simple Shopping Cart

```kuda
fun show_menu():
    out("")
    out("=== Shop ===")
    out("1. Apple   - $1")
    out("2. Banana  - $0.5")
    out("3. Orange  - $1.5")
    out("4. Checkout")
    out("")

prices = [1.0, 0.5, 1.5]
item_names = ["Apple", "Banana", "Orange"]
cart = []
total = 0.0

running = True
til running:
    show_menu()
    choice_text = input("Choose: ")
    choice = int(choice_text)

    if choice == 1 or choice == 2 or choice == 3:
        item = item_names[choice - 1]
        price = prices[choice - 1]
        cart.add(choice - 1)
        total += price
        out("Added " + item + " ($" + str(price) + ")")
        out("Cart total: $" + str(total))
    othif choice == 4:
        running = False
    other:
        out("Invalid choice!")

out("")
out("=== Receipt ===")
each item_idx in cart:
    out("- " + item_names[item_idx] + ": $" + str(prices[item_idx]))
out("Total: $" + str(total))
out("Thanks for shopping!")
```

---

## 🎯 Final Challenges

You've made it through all the chapters! Here are some bigger challenges to test your skills:

### Challenge 1: FizzBuzz
Print numbers from 1 to 100. But:
- If the number is divisible by 3, print "Fizz"
- If divisible by 5, print "Buzz"
- If divisible by both, print "FizzBuzz"
- Otherwise print the number

### Challenge 2: Temperature Converter
Write a program that:
- Asks the user if they want to convert C→F or F→C
- Asks for the temperature
- Prints the result

Formulas:
- C to F: `(c * 9/5) + 32`
- F to C: `(f - 32) * 5/9`

### Challenge 3: Word Counter
Write a program that:
- Asks the user to type a sentence
- Counts how many times each unique word appears
- Prints the results sorted

### Challenge 4: Number Statistics
Write a program that:
- Keeps asking the user for numbers until they type "stop"
- Then prints: count, sum, average, min, and max of all entered numbers

### Challenge 5: Simple Encryption
Write a program that:
- Asks the user for a message
- Shifts every letter by 1 (a→b, b→c, z→a)
- Prints the encrypted message

---

## Quick Cheat Sheet

```kuda
# Output
out("Hello!")
out("Value: " + str(x))

# Variables
name = "Artur"
age = 17
score = 9.5
is_cool = True

# Math
x = 10 + 5      # add
x = 10 - 5      # subtract
x = 10 * 5      # multiply
x = 10 / 5      # divide
x = 10 % 3      # remainder
x += 5          # shortcut add
x -= 3          # shortcut subtract

# Input
name = input("Your name: ")
age = int(input("Your age: "))

# Decisions
if x > 0:
    out("positive")
othif x < 0:
    out("negative")
other:
    out("zero")

# Loops
repeat 5:
    out("hello")

each item in [1, 2, 3]:
    out(str(item))

each i in range(10):
    out(str(i))

i = 0
til i < 10:
    out(str(i))
    i += 1

# Lists
nums = [1, 2, 3]
nums.add(4)
nums[0] = 99
out(str(len(nums)))

# Functions
fun add(a, b):
    give a + b

result = add(3, 7)
```

---

*Good luck and have fun coding in Kuda! 🎉*