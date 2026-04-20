"""Essbase .rul → Lakeflow Declarative Pipeline converter (stub)."""

from __future__ import annotations

from pathlib import Path


def import_rules_file(rul_path: str | Path) -> str:
    """Convert an Essbase data-load rules file to a Lakeflow pipeline YAML.

    TODO(P3): column mappings, aggregation rules, selection criteria →
    pipeline sources, transforms, and sinks.
    """
    raise NotImplementedError("rules importer lands in P3")
