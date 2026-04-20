"""Emit Delta branch operations for declared scenarios.

Each Scenario in `cube.yaml` becomes a named Delta branch forked from the
scenario's `fork_from` branch. Approvers are captured as a metadata table
row (for the future approval workflow).

Delta branches in Databricks/Iceberg use the `CREATE BRANCH` syntax:

  ALTER TABLE catalog.schema.fact CREATE BRANCH IF NOT EXISTS budget_fy26
    FROM BRANCH main;

For P0 we emit SQL. A future `lakecube apply` step dispatches it.
"""

from __future__ import annotations

from lakecube.emitters.base import Artifact
from lakecube.spec import Cube


def emit_scenarios(cube: Cube) -> list[Artifact]:
    if not cube.scenarios:
        return []
    lines = [f"-- Scenario branches for cube {cube.name}.\n"]
    approvers_rows: list[str] = []
    for s in cube.scenarios:
        lines.append(
            f"ALTER TABLE {cube.fact.table} CREATE BRANCH IF NOT EXISTS "
            f"{s.name.replace('-', '_')} FROM BRANCH {s.fork_from};"
        )
        for who in s.approvers:
            approvers_rows.append(f"  ('{s.name}', '{who}', '{'write' if s.writable else 'read'}')")
    if approvers_rows:
        lines.append("")
        lines.append(
            "INSERT INTO lakecube.scenario_approvers (scenario, approver, access) VALUES\n"
            + ",\n".join(approvers_rows)
            + ";"
        )
    return [
        Artifact(
            path=f"scenarios/{cube.name}_branches.sql",
            content="\n".join(lines) + "\n",
            kind="scenario",
        )
    ]
