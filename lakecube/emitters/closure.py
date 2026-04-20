"""Emit the shared closure table + per-cube seed INSERTs for hierarchy navigation.

Closure table schema:

    CREATE TABLE lakecube.closure (
        dimension   STRING,
        ancestor    STRING,
        descendant  STRING,
        depth       INT
    ) USING DELTA;

One row per (dimension, ancestor, descendant, depth) tuple. A reflexive row
(depth=0) exists for every member so `descendants(X, include_self=True)` and
`ancestors(X, include_self=True)` are cheap equality joins.

For P0 the closure is populated by SQL INSERTs derived directly from the
`cube.yaml` hierarchy. For cubes with millions of members (P2+) the same
rows come from a Lakeflow pipeline over the real dim table; the emitted
schema is identical so callers don't notice the swap.

Only non-measures dimensions get closure rows — the measures dimension's
hierarchy is a presentation concept, not a fact-joinable key.
"""

from __future__ import annotations

from lakecube.emitters.base import Artifact
from lakecube.spec import Cube, Member


def _walk_closure(
    root: Member,
    dim: str,
    rows: list[tuple[str, str, str, int]],
    ancestors: list[str],
) -> None:
    """Emit closure rows for `root` against its ancestor path, then recurse."""
    # Reflexive row (depth=0) for every member.
    rows.append((dim, root.name, root.name, 0))
    # Pairs with every ancestor already on the stack.
    for i, anc in enumerate(reversed(ancestors), start=1):
        rows.append((dim, anc, root.name, i))
    # Recurse with `root` pushed as an ancestor.
    for child in root.children:
        _walk_closure(child, dim, rows, ancestors + [root.name])


def _values_literal(row: tuple[str, str, str, int]) -> str:
    dim, anc, desc, depth = row
    esc_anc = anc.replace("'", "''")
    esc_desc = desc.replace("'", "''")
    return f"  ('{dim}', '{esc_anc}', '{esc_desc}', {depth})"


def emit_closure(cube: Cube) -> list[Artifact]:
    rows: list[tuple[str, str, str, int]] = []
    dim_names: list[str] = []
    for dim in cube.dimensions:
        if dim.is_measures:
            continue
        dim_names.append(dim.name)
        for hierarchy in dim.hierarchies:
            for top in hierarchy.members:
                _walk_closure(top, dim.name, rows, ancestors=[])

    if not rows:
        return []

    # Deduplicate (a member reachable through multiple paths — shared members).
    rows = sorted(set(rows))

    header = (
        "-- Closure table + seed rows for hierarchy navigation.\n"
        "-- Used by lakecube.fn.parent / children / descendants / ancestors / level.\n"
        "\n"
        "CREATE TABLE IF NOT EXISTS lakecube.closure (\n"
        "    dimension  STRING,\n"
        "    ancestor   STRING,\n"
        "    descendant STRING,\n"
        "    depth      INT\n"
        ") USING DELTA;\n\n"
    )

    dim_list = ", ".join(f"'{d}'" for d in dim_names)
    clear = f"DELETE FROM lakecube.closure WHERE dimension IN ({dim_list});\n\n"

    insert = (
        "INSERT INTO lakecube.closure (dimension, ancestor, descendant, depth) VALUES\n"
        + ",\n".join(_values_literal(r) for r in rows)
        + ";\n"
    )

    return [
        Artifact(
            path=f"closure/{cube.name}_closure.sql",
            content=header + clear + insert,
            kind="sql",
        )
    ]
