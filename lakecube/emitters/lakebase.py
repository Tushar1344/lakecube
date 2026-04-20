"""Emit Lakebase (Postgres) schema for write-back form state, cell comments, and LROs.

Write-back flow:
  1. User edits cells in Excel/Workbench.
  2. Edits land in `lakecube_writeback.<cube>_cells` keyed by scenario + intersection.
  3. On submit, Postgres advisory locks serialize concurrent writes.
  4. Approved edits flow into the scenario's Delta branch via a Lakeflow job.
  5. The branch merges to main when the approval workflow completes.

We also create tables for cell comments and linked reporting objects (LROs),
so Essbase users' cell-attached metadata survives the migration.
"""

from __future__ import annotations

from lakecube.emitters.base import Artifact
from lakecube.spec import Cube


def emit_lakebase(cube: Cube) -> list[Artifact]:
    if not cube.scenarios:
        return []
    schema = f"lakecube_writeback_{cube.name}"
    non_measure_dims = [d for d in cube.dimensions if d.type != "measures"]
    dim_cols = ",\n    ".join(f"{dim.name}_key TEXT NOT NULL" for dim in non_measure_dims)
    unique_keys = ", ".join(f"{d.name}_key" for d in non_measure_dims)
    ddl = f"""-- Lakebase write-back schema for cube {cube.name}.
-- Apply to the Postgres endpoint associated with this cube.

CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.cells (
    id BIGSERIAL PRIMARY KEY,
    scenario TEXT NOT NULL,
    measure TEXT NOT NULL,
    {dim_cols},
    value DOUBLE PRECISION,
    submitted_by TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'draft',  -- draft | submitted | approved | rejected
    UNIQUE (scenario, measure, {unique_keys})
);

CREATE TABLE IF NOT EXISTS {schema}.cell_comments (
    id BIGSERIAL PRIMARY KEY,
    cell_id BIGINT REFERENCES {schema}.cells(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.cell_lros (
    id BIGSERIAL PRIMARY KEY,
    cell_id BIGINT REFERENCES {schema}.cells(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,  -- 'url' | 'file'
    target TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cells_scenario_idx ON {schema}.cells(scenario);
CREATE INDEX IF NOT EXISTS cells_status_idx ON {schema}.cells(status);
"""
    return [
        Artifact(
            path=f"lakebase/{cube.name}_writeback.sql",
            content=ddl,
            kind="ddl",
        )
    ]
