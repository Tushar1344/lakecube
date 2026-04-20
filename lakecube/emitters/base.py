"""Common types for emitters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Artifact:
    """A single file Lakecube would write to apply a cube to Databricks.

    `kind` is informational — it lets the CLI group/display artifacts by type
    and lets downstream tooling (e.g., a future `lakecube apply`) dispatch to
    the right Databricks SDK call.
    """

    path: str     # repo-relative, e.g., "metric_views/sample_basic.yaml"
    content: str  # the file body
    kind: str     # "metric_view" | "lakeflow" | "sql" | "ddl" | "scenario"
