def hello_world():
    """Simple function that prints Hello World"""
    print("Hello, World!")

def add_numbers(a, b):
    """Add two numbers and return the result"""
    return a + b

# This is a test file
if __name__ == "__main__":
    hello_world()
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")