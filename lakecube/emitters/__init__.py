"""Artifact emitters — turn a validated Cube into deployable Databricks artifacts.

Each emitter takes a Cube and returns one or more Artifact objects that name
the target file path and carry the content Lakecube would apply to Databricks.
The compiler orchestrates the emitters; the CLI writes them to `build/`.

No emitter talks to Databricks directly. Every emission is pure text —
inspection, diff-ability, and version control come free.
"""

from lakecube.emitters.base import Artifact
from lakecube.emitters.closure import emit_closure
from lakecube.emitters.lakebase import emit_lakebase
from lakecube.emitters.lakeflow import emit_lakeflow
from lakecube.emitters.metric_view import emit_metric_view
from lakecube.emitters.scenarios import emit_scenarios
from lakecube.emitters.security import emit_security

__all__ = [
    "Artifact",
    "emit_metric_view",
    "emit_lakeflow",
    "emit_closure",
    "emit_security",
    "emit_scenarios",
    "emit_lakebase",
]
