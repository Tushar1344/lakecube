"""Emit UC row filters + ABAC policies from Cube security blocks.

Member-level filter expressions (`descendants(US)`, `uda:KEY_CUSTOMER`, etc.)
are authored in business terms. The compiler lowers them to:

  - A SQL UDF per filter that evaluates a hierarchy predicate using
    the shared `lakecube.closure` table (see `lakecube.emitters.closure`)
  - A row filter attached to the fact table via
    `ALTER TABLE ... SET ROW FILTER`

The hierarchy-expression parser is shared with `lakecube.fn.member_filter` —
this module just adds the UDA predicate (which needs its own table) and
falls back to literal equality for unrecognized expressions.
"""

from __future__ import annotations

import re

from lakecube.emitters.base import Artifact
from lakecube.fn import member_filter
from lakecube.spec import Cube, SecurityFilter

_UDA = re.compile(r"^\s*uda:(\S+)\s*$")


def _predicate_sql(expr: str, dim: str, key_col: str) -> str:
    if m := _UDA.match(expr):
        tag = m.group(1).replace("'", "''")
        # UDA predicate — P1 adds a proper lakecube.udas table. For now we
        # emit a placeholder subquery against a conventional table name.
        return (
            f"({key_col} IN (SELECT descendant FROM lakecube.udas "
            f"WHERE dimension = '{dim}' AND uda = '{tag}'))"
        )
    return member_filter(expr, dim, key_col=key_col)


def _filter_to_sql(flt: SecurityFilter, cube: Cube) -> str:
    fn_name = f"lakecube_{cube.name}__rf_{flt.name}"
    key_col = cube.fact.dimension_keys.get(flt.dimension, f"{flt.dimension}_key")
    pred = _predicate_sql(flt.members, flt.dimension, key_col)
    principals = flt.principal
    return (
        f"-- Row filter: {flt.name}\n"
        f"-- Access: {flt.access} for {principals}\n"
        f"-- Members: {flt.members}\n"
        f"CREATE OR REPLACE FUNCTION {fn_name}({key_col} STRING)\n"
        f"RETURNS BOOLEAN\n"
        f"RETURN IS_ACCOUNT_GROUP_MEMBER('{principals}') AND ({pred});\n"
        f"\n"
        f"ALTER TABLE {cube.fact.table} SET ROW FILTER {fn_name} ON ({key_col});\n"
    )


def emit_security(cube: Cube) -> list[Artifact]:
    if not cube.security:
        return []
    body = "\n".join(_filter_to_sql(f, cube) for f in cube.security)
    header = (
        f"-- Generated security filters for cube {cube.name}.\n"
        "-- Hierarchy predicates reference the shared lakecube.closure table.\n\n"
    )
    return [
        Artifact(
            path=f"security/{cube.name}_row_filters.sql",
            content=header + body,
            kind="sql",
        )
    ]
