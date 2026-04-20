"""Cube-aware helpers — the only "DSL" Lakecube exposes.

These functions compose into measure formulas, calc scripts, and security
expressions. Each compiles to SQL (via UDF or inline expression) when
deployed, so the authoring surface and the runtime stay in sync.

Essbase analogs:
  - parent / children / descendants / ancestors  ← member navigation
  - ytd / qtd / mat / prior_period               ← Dynamic Time Series
  - uda                                          ← UDA predicate
  - allocate / spread                            ← allocation primitives
"""

from lakecube.fn.hierarchy import ancestors, children, descendants, parent

__all__ = ["parent", "children", "descendants", "ancestors"]
