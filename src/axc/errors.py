"""Exceptions, with the exit code each one means carried by the class."""

from __future__ import annotations

__all__ = ["ClassificationError", "UnusableAssortment"]


class ClassificationError(Exception):
    """A question this data cannot answer. Exit code 1."""


class UnusableAssortment(ClassificationError, ValueError):
    """An assortment that is malformed rather than merely uninformative. Exit code 2."""
