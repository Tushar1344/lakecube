"""Essbase .otl → cube.yaml importer (stub)."""

from __future__ import annotations

from pathlib import Path


def import_outline(otl_path: str | Path) -> dict:
    """Parse an Essbase outline export and return a cube.yaml-compatible dict.

    TODO(P0): real XML parse. Essbase exports dimensions, members, hierarchies,
    consolidation operators, aliases, UDAs, attribute dimensions, and member
    formulas. Map each to the Cube spec.
    """
    raise NotImplementedError("outline importer lands in P0")
