# This is the main file for the pymath CLI.
import argparse

def add(a, b):
    """Adds two numbers."""
    return a + b

def subtract(a, b):
    """Subtracts two numbers."""
    return a - b

def multiply(a, b):
    """Multiplies two numbers."""
    return a * b

def divide(a, b):
    """Divides two numbers. Handles division by zero."""
    if b == 0:
        return "Error: Cannot divide by zero."
    return a / b

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple CLI calculator.")
    parser.add_argument("operation", choices=["add", "subtract", "multiply", "divide"], help="The operation to perform.")
    parser.add_argument("a", type=float, help="The first number.")
    parser.add_argument("b", type=float, help="The second number.")

    args = parser.parse_args()

    if args.operation == "add":
        result = add(args.a, args.b)
    elif args.operation == "subtract":
        result = subtract(args.a, args.b)
    elif args.operation == "multiply":
        result = multiply(args.a, args.b)
    elif args.operation == "divide":
        result = divide(args.a, args.b)
    else:
        result = "Error: Invalid operation."

    print(result)
