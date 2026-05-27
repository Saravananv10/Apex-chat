def factorial(n: int) -> int:
    """Return the factorial of a non‑negative integer ``n``.

    Parameters:
    n : int
        The number to compute the factorial of. Must be non‑negative.

    Returns:
    int
        The factorial of ``n``.

    Raises:
    ValueError
        If ``n`` is negative.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative integers")

    result = 1
    for i in range(2, n + 1):
        result *= i
    return result