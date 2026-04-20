"""Compiler entry point.

Takes a `cube.yaml`, validates it, runs each emitter, and returns the full set
of artifacts that would be applied to Databricks. No SDK calls yet — the apply
step lands in a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lakecube.emitters import (
    Artifact,
    emit_lakebase,
    emit_lakeflow,
    emit_metric_view,
    emit_scenarios,
    emit_security,
)
from lakecube.spec import Cube


@dataclass
class EmissionPlan:
    """Full set of artifacts a deploy would write."""

    artifacts: list[Artifact] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[Artifact]:
        return [a for a in self.artifacts if a.kind == kind]

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.artifacts:
            counts[a.kind] = counts.get(a.kind, 0) + 1
        return counts


def load_spec(path: str | Path) -> Cube:
    raw = yaml.safe_load(Path(path).read_text())
    return Cube.model_validate(raw)


def compile_cube(cube: Cube) -> EmissionPlan:
    plan = EmissionPlan()
    plan.artifacts.append(emit_metric_view(cube))
    plan.artifacts.extend(emit_lakeflow(cube))
    plan.artifacts.extend(emit_security(cube))
    plan.artifacts.extend(emit_scenarios(cube))
    plan.artifacts.extend(emit_lakebase(cube))
    return plan


def write_plan(plan: EmissionPlan, out_dir: str | Path) -> list[Path]:
    """Write every artifact into `out_dir`, returning the written paths."""
    out = Path(out_dir)
    written: list[Path] = []
    for art in plan.artifacts:
        target = out / art.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(art.content)
        written.append(target)
    return written
