"""Essbase .csc → Lakeflow / `lakecube.fn` transpiler (stub)."""

from __future__ import annotations

from pathlib import Path


def import_calc_script(csc_path: str | Path) -> str:
    """Transpile a calc script to a Python calc function + Lakeflow dependencies.

    TODO(P2): cover the common verbs — FIX/ENDFIX, CALC ALL, CALC DIM, AGG,
    SET commands. Unsupported constructs become stubs with the original
    script preserved as a comment for manual review.
    """
    raise NotImplementedError("calc transpiler lands in P2")
