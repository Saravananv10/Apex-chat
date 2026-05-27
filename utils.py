# utils.py
"""Utility functions for the project.

This module currently provides a simple factorial calculation.
"""

__all__ = ["factorial"]


def factorial(n: int) -> int:
    """Return the factorial of a non‑negative integer ``n``.

    Parameters
    n : int
        A non‑negative integer whose factorial is to be computed.

    Returns
    int
        The factorial of ``n``.

    Raises
    ValueError
        If ``n`` is negative.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative integers")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


# Simple test block
if __name__ == "__main__":
    test_values = [0, 1, 5, 10]
    for val in test_values:
        print(f"factorial({val}) = {factorial(val)}")