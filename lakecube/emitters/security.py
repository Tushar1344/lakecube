"""Emit UC row filters + ABAC policies from Cube security blocks.

Member-level filter expressions (e.g. `descendants(US)`, `uda:KEY_CUSTOMER`)
are authored in business terms. The compiler lowers them to:

  - A SQL UDF per filter that evaluates the hierarchy predicate using the
    dimension's closure/STRUCT column
  - A row filter attached to the fact table via `ALTER TABLE ... SET ROW FILTER`
  - An ABAC policy granting/denying the principal

For P0 we emit the SQL text; the actual SDK apply is a future step.
Member-expression parsing is stubbed — P0 handles `descendants(X)` and
`ancestors(X)` literal forms; richer predicates land in P1.
"""

from __future__ import annotations

import re

from lakecube.emitters.base import Artifact
from lakecube.spec import Cube, SecurityFilter

_DESCENDANTS = re.compile(r"^\s*descendants\(\s*(\S+?)\s*\)\s*$")
_ANCESTORS = re.compile(r"^\s*ancestors\(\s*(\S+?)\s*\)\s*$")
_UDA = re.compile(r"^\s*uda:(\S+)\s*$")


def _predicate_sql(expr: str, dim: str) -> str:
    """Lower a member-filter expression to a SQL boolean predicate."""
    if m := _DESCENDANTS.match(expr):
        return f"lakecube_fn.descendants('{dim}', '{m.group(1)}', {dim}_key)"
    if m := _ANCESTORS.match(expr):
        return f"lakecube_fn.ancestors('{dim}', '{m.group(1)}', {dim}_key)"
    if m := _UDA.match(expr):
        return f"lakecube_fn.has_uda('{dim}', '{m.group(1)}', {dim}_key)"
    # Fallback: treat as literal member name match.
    return f"{dim}_key = '{expr.strip()}'"


def _filter_to_sql(flt: SecurityFilter, cube: Cube) -> str:
    fn_name = f"lakecube_{cube.name}__rf_{flt.name}"
    pred = _predicate_sql(flt.members, flt.dimension)
    principals = flt.principal
    key_col = cube.fact.dimension_keys.get(flt.dimension, flt.dimension)
    return (
        f"-- Row filter: {flt.name}\n"
        f"-- Access: {flt.access} for {principals}\n"
        f"-- Members: {flt.members}\n"
        f"CREATE OR REPLACE FUNCTION {fn_name}({flt.dimension}_key STRING)\n"
        f"RETURNS BOOLEAN\n"
        f"RETURN IS_ACCOUNT_GROUP_MEMBER('{principals}') AND ({pred});\n"
        f"\n"
        f"ALTER TABLE {cube.fact.table} SET ROW FILTER {fn_name} ON ({key_col});\n"
    )


def emit_security(cube: Cube) -> list[Artifact]:
    if not cube.security:
        return []
    body = "\n".join(_filter_to_sql(f, cube) for f in cube.security)
    header = f"-- Generated security filters for cube {cube.name}\n-- Uses UC row filter UDFs.\n\n"
    return [
        Artifact(
            path=f"security/{cube.name}_row_filters.sql",
            content=header + body,
            kind="sql",
        )
    ]
