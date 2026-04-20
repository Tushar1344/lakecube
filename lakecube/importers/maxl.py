"""MaxL compatibility layer (stub).

Two modes:
  - run:     interpret a .mxl script and dispatch to Lakecube operations
  - convert: translate a .mxl script into equivalent `lakecube` CLI calls
"""

from __future__ import annotations

from pathlib import Path


def run_maxl(mxl_path: str | Path) -> None:
    """Execute a MaxL script against Lakecube. TODO(P2)."""
    raise NotImplementedError("maxl runner lands in P2")


def convert_maxl(mxl_path: str | Path) -> str:
    """Translate a MaxL script into native `lakecube` CLI invocations. TODO(P2)."""
    raise NotImplementedError("maxl converter lands in P2")
