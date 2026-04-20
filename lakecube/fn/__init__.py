"""Cube-aware SQL helpers — the only "DSL" Lakecube exposes.

Each helper returns a SQL expression. They compose into measure formulas,
security predicates, Metric View filters, and the compiler's lowered output.

Essbase analogs:
  parent / children / descendants / ancestors / level  ← member navigation
  member_filter                                         ← parse an Essbase-style
                                                           member predicate and
                                                           produce SQL
  ytd / qtd / mat / prior_period                        ← Dynamic Time Series
                                                           (P1 — stubs below)
  uda                                                   ← UDA predicate (P1)
  allocate / spread                                     ← allocation helpers (P2)
"""

from lakecube.fn.hierarchy import (
    ancestors,
    children,
    descendants,
    level,
    member_filter,
    parent,
)

__all__ = [
    "parent",
    "children",
    "descendants",
    "ancestors",
    "level",
    "member_filter",
]
