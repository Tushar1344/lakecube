"""Emit a Lakeflow Declarative Pipeline for dimension conformance + fact aggregation.

Lakeflow handles:
  - Dimension SCD (Type 2 via AUTO CDC) — one streaming table per dimension
  - Fact table materialization / incremental refresh — one MV per cube
  - Aggregate materialized views (one per hot measure × dimension slice) — P2

For P0 scaffolding we emit a minimal pipeline YAML covering dim conformance
and a single "all-measures" MV. Richer aggregate routing comes later.
"""

from __future__ import annotations

import yaml

from lakecube.emitters.base import Artifact
from lakecube.spec import Cube


def _dim_table(cube: Cube, dim_name: str) -> str:
    return f"lakecube.{cube.name}__dim_{dim_name}"


def emit_lakeflow(cube: Cube) -> list[Artifact]:
    tables: list[dict] = []

    # One streaming table per dimension (SCD Type 2 scaffold).
    # Real source mapping comes from `rules:` or the outline importer.
    for dim in cube.dimensions:
        if dim.is_measures:
            continue
        tables.append(
            {
                "name": _dim_table(cube, dim.name),
                "kind": "streaming_table",
                "comment": f"Conformed dimension: {dim.name}",
                "cluster_by": ["member_key"],
                # AUTO CDC placeholder — the importer/rules converter fills this in.
                "auto_cdc_from": f"TODO_source_for_{dim.name}",
                "scd_type": 2,
            }
        )

    # One materialized view over the fact with all measures pre-joined.
    tables.append(
        {
            "name": f"lakecube.{cube.name}__fact_mv",
            "kind": "materialized_view",
            "comment": f"Canonical fact MV for {cube.name}",
            "source": cube.fact.table,
            "refresh": "incremental",
        }
    )

    pipeline = {
        "name": f"lakecube_{cube.name}",
        "edition": "advanced",
        "continuous": False,
        "catalog": "lakecube",
        "target": cube.name,
        "tables": tables,
    }

    return [
        Artifact(
            path=f"lakeflow/{cube.name}.yaml",
            content=yaml.safe_dump(pipeline, sort_keys=False, default_flow_style=False),
            kind="lakeflow",
        )
    ]
