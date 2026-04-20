"""Compiler entry point.

Stub — the real implementation lands in P0. Current behavior is to parse a spec
and return a structured "emission plan" describing what artifacts would be
produced. No Databricks calls yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lakecube.spec import Cube


@dataclass
class EmissionPlan:
    """What the compiler would deploy — inspection target before anything touches Databricks."""

    metric_views: list[str] = field(default_factory=list)
    lakeflow_pipelines: list[str] = field(default_factory=list)
    abac_policies: list[str] = field(default_factory=list)
    delta_branches: list[str] = field(default_factory=list)
    lakebase_schemas: list[str] = field(default_factory=list)


def load_spec(path: str | Path) -> Cube:
    """Load and validate a `cube.yaml` into a Cube model."""
    raw = yaml.safe_load(Path(path).read_text())
    return Cube.model_validate(raw)


def compile_cube(cube: Cube) -> EmissionPlan:
    """Produce an emission plan from a validated Cube.

    TODO(P0): actually emit DDL / YAML / policies. Right now, return named
    placeholders so the CLI can show the user what *would* be deployed.
    """
    plan = EmissionPlan()
    plan.metric_views.append(f"{cube.name}__metric_view")
    for dim in cube.dimensions:
        plan.lakeflow_pipelines.append(f"{cube.name}__dim_{dim.name}")
    plan.lakeflow_pipelines.append(f"{cube.name}__fact")
    for sec in cube.security:
        plan.abac_policies.append(f"{cube.name}__filter_{sec.name}")
    for scenario in cube.scenarios:
        plan.delta_branches.append(f"{cube.name}__scenario_{scenario.name}")
    if cube.scenarios:
        plan.lakebase_schemas.append(f"{cube.name}__writeback")
    return plan
