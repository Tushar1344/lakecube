"""Hierarchy navigation helpers.

At author time these are Python functions returning SQL expressions. At compile
time they become SQL UDFs or inline predicates over the dimension's hierarchy
column (either nested STRUCT or parent/child closure, picked per cube).

Stubs for scaffolding. Real SQL emission lands in P0.
"""

from __future__ import annotations


def parent(member: str, dimension: str) -> str:
    """SQL predicate: immediate parent of `member` in `dimension`."""
    return f"__lc_parent('{dimension}', '{member}')"


def children(member: str, dimension: str) -> str:
    """SQL predicate: immediate children of `member` in `dimension`."""
    return f"__lc_children('{dimension}', '{member}')"


def descendants(member: str, dimension: str) -> str:
    """SQL predicate: all descendants (recursive) of `member` in `dimension`."""
    return f"__lc_descendants('{dimension}', '{member}')"


def ancestors(member: str, dimension: str) -> str:
    """SQL predicate: all ancestors (recursive) of `member` in `dimension`."""
    return f"__lc_ancestors('{dimension}', '{member}')"
