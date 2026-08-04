"""Public API for the `well` package."""

from __future__ import annotations

__all__ = ["greet", "hello"]


def hello() -> str:
    return "hello from well"


def greet(name: str = "world") -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"

