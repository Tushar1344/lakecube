"""Hierarchy navigation helpers — produce real SQL predicates.

Every helper returns a SQL boolean expression that evaluates `key_col` (the
fact table's dimension key) against a closure table populated by the compiler.

Backing schema (emitted by `lakecube.emitters.closure.emit_closure`):

    CREATE TABLE IF NOT EXISTS lakecube.closure (
        dimension   STRING,  -- e.g., "market"
        ancestor    STRING,  -- member key higher in the hierarchy
        descendant  STRING,  -- member key lower in the hierarchy
        depth       INT      -- 0 = self; 1 = immediate parent/child; N = transitive
    );

A reflexive row exists for every member (depth=0) so `descendants(X)` naturally
includes X itself when `include_self=True`.

Usage (inline in a measure formula, security predicate, or Metric View filter):

    >>> descendants("market", "East")
    "(market_key IN (SELECT descendant FROM lakecube.closure ...))"

Key convention: if `key_col` is omitted, it defaults to `<dim>_key`. Pass
explicitly when your fact uses a different column name.
"""

from __future__ import annotations

_CLOSURE = "lakecube.closure"


def _default_key(dim: str) -> str:
    return f"{dim}_key"


def _quote(s: str) -> str:
    """Single-quote a SQL literal, escaping embedded quotes."""
    return "'" + s.replace("'", "''") + "'"


def parent(dim: str, member: str, *, key_col: str | None = None) -> str:
    """SQL predicate: `key_col` is the immediate parent of `member`."""
    kc = key_col or _default_key(dim)
    return (
        f"({kc} IN (SELECT ancestor FROM {_CLOSURE} "
        f"WHERE dimension = {_quote(dim)} "
        f"AND descendant = {_quote(member)} AND depth = 1))"
    )


def children(dim: str, member: str, *, key_col: str | None = None) -> str:
    """SQL predicate: `key_col` is an immediate child of `member`."""
    kc = key_col or _default_key(dim)
    return (
        f"({kc} IN (SELECT descendant FROM {_CLOSURE} "
        f"WHERE dimension = {_quote(dim)} "
        f"AND ancestor = {_quote(member)} AND depth = 1))"
    )


def ancestors(
    dim: str,
    member: str,
    *,
    key_col: str | None = None,
    include_self: bool = False,
) -> str:
    """SQL predicate: `key_col` is any ancestor of `member` (optionally incl. self)."""
    kc = key_col or _default_key(dim)
    min_depth = 0 if include_self else 1
    return (
        f"({kc} IN (SELECT ancestor FROM {_CLOSURE} "
        f"WHERE dimension = {_quote(dim)} "
        f"AND descendant = {_quote(member)} AND depth >= {min_depth}))"
    )


def descendants(
    dim: str,
    member: str,
    *,
    key_col: str | None = None,
    include_self: bool = False,
) -> str:
    """SQL predicate: `key_col` is any descendant of `member` (optionally incl. self).

    `include_self=True` is the typical Essbase "rollup" interpretation —
    'descendants(US)' in Essbase includes US itself. Default is False so
    callers that need strict descendants get them.
    """
    kc = key_col or _default_key(dim)
    min_depth = 0 if include_self else 1
    return (
        f"({kc} IN (SELECT descendant FROM {_CLOSURE} "
        f"WHERE dimension = {_quote(dim)} "
        f"AND ancestor = {_quote(member)} AND depth >= {min_depth}))"
    )


def level(dim: str, depth: int, *, key_col: str | None = None) -> str:
    """SQL predicate: `key_col` is at the given depth below the top of the hierarchy.

    Essbase-style "level 0" (leaves) is a common need; Lakecube models it as
    "members with no descendants at depth 1".
    """
    kc = key_col or _default_key(dim)
    if depth == 0:
        return (
            f"({kc} NOT IN (SELECT ancestor FROM {_CLOSURE} "
            f"WHERE dimension = {_quote(dim)} AND depth = 1))"
        )
    return (
        f"({kc} IN (SELECT descendant FROM {_CLOSURE} c1 "
        f"JOIN (SELECT MIN(descendant) AS root FROM {_CLOSURE} "
        f"WHERE dimension = {_quote(dim)} AND depth = 0) r "
        f"ON c1.ancestor = r.root "
        f"WHERE c1.dimension = {_quote(dim)} AND c1.depth = {depth}))"
    )


def member_filter(expr: str, dim: str, *, key_col: str | None = None) -> str:
    """Lower a member-filter expression (as authored in cube.yaml) to SQL.

    Supports:
      descendants(X), descendants_self(X), ancestors(X), ancestors_self(X),
      children(X), parent(X), level(N), <literal member name>

    Everything else returns a literal-equality predicate against `key_col`.
    Callers should `lakecube.emitters.security` for the wider member-filter
    language; this function is the canonical dispatcher.
    """
    import re

    expr = expr.strip()

    patterns = [
        (r"^descendants\(\s*(.+?)\s*\)$",
            lambda m: descendants(dim, m.group(1), key_col=key_col)),
        (r"^descendants_self\(\s*(.+?)\s*\)$",
            lambda m: descendants(dim, m.group(1), key_col=key_col, include_self=True)),
        (r"^ancestors\(\s*(.+?)\s*\)$",
            lambda m: ancestors(dim, m.group(1), key_col=key_col)),
        (r"^ancestors_self\(\s*(.+?)\s*\)$",
            lambda m: ancestors(dim, m.group(1), key_col=key_col, include_self=True)),
        (r"^children\(\s*(.+?)\s*\)$",
            lambda m: children(dim, m.group(1), key_col=key_col)),
        (r"^parent\(\s*(.+?)\s*\)$",
            lambda m: parent(dim, m.group(1), key_col=key_col)),
        (r"^level\(\s*(\d+)\s*\)$",
            lambda m: level(dim, int(m.group(1)), key_col=key_col)),
    ]
    for pat, builder in patterns:
        if m := re.match(pat, expr):
            return builder(m)

    kc = key_col or _default_key(dim)
    return f"({kc} = {_quote(expr)})"
