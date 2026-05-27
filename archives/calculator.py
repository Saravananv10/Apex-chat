# calculator.py
"""A simple calculator module.

This module provides four basic arithmetic operations that can be used
by other parts of the application or tested independently.
"""

from __future__ import annotations


def add(a: float | int, b: float | int) -> float:
    """Return the sum of *a* and *b*.

    Parameters
    ----------
    a, b: int | float
        Operands.

    Returns
    -------
    float
        The result of ``a + b``.
    """
    return a + b


def subtract(a: float | int, b: float | int) -> float:
    """Return the difference of *a* and *b* (a - b)."""
    return a - b


def multiply(a: float | int, b: float | int) -> float:
    """Return the product of *a* and *b*."""
    return a * b


def divide(a: float | int, b: float | int) -> float:
    """Return the quotient of *a* divided by *b*.

    Raises
    ------
    ZeroDivisionError
        If *b* is zero.
    """
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


if __name__ == "__main__":
    # Simple manual test when running the file directly.
    import sys

    try:
        a, b = map(float, sys.argv[1:3])
    except ValueError:
        print("Usage: python calculator.py <a> <b>")
        sys.exit(1)

    print(f"{a} + {b} = {add(a, b)}")
    print(f"{a} - {b} = {subtract(a, b)}")
    print(f"{a} * {b} = {multiply(a, b)}")
    try:
        print(f"{a} / {b} = {divide(a, b)}")
    except ZeroDivisionError as e:
        print(e)