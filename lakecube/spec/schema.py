"""Pydantic models for the `cube.yaml` spec.

Scaffold — field set will grow as the compiler matures. Current shape covers
the minimum needed to model Essbase's Sample.Basic cube end-to-end.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Member(_Base):
    name: str
    alias: str | None = None
    consolidation: str = "+"  # +, -, ~, ^, %, *, / — Essbase operator semantics preserved
    storage: str | None = None  # stored | dynamic | label-only
    formula: str | None = None  # SQL or `lakecube.fn` expression
    udas: list[str] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)
    children: list[Member] = Field(default_factory=list)


class Hierarchy(_Base):
    name: str
    default: bool = False
    members: list[Member] = Field(default_factory=list)


class Dimension(_Base):
    name: str
    type: str = "standard"  # standard | attribute | time
    hierarchies: list[Hierarchy] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)  # alias_table_name -> source column
    time_grain: str | None = None  # for type=time: day|month|quarter|year
    dynamic_time_series: list[str] = Field(default_factory=list)  # e.g. ["YTD", "QTD", "MAT"]


class Measure(_Base):
    name: str
    aggregation: str = "sum"  # sum | avg | min | max | count | formula
    source: str | None = None  # column or SQL expression
    formula: str | None = None  # composition over other measures
    solve_order: int = 0
    format: str | None = None


class Fact(_Base):
    table: str  # Delta table in UC (catalog.schema.table)
    dimension_keys: dict[str, str] = Field(default_factory=dict)  # dim_name -> fk column


class Scenario(_Base):
    name: str
    fork_from: str = "main"  # Delta branch to fork from
    approvers: list[str] = Field(default_factory=list)
    writable: bool = True


class SecurityFilter(_Base):
    name: str
    principal: str  # group or user
    dimension: str
    members: str  # expression, e.g. "descendants(US)" or "uda:KEY_CUSTOMER"
    access: str = "read"  # read | write | none


class Cube(_Base):
    name: str
    version: str = "1"
    description: str | None = None
    fact: Fact
    dimensions: list[Dimension] = Field(default_factory=list)
    measures: list[Measure] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    security: list[SecurityFilter] = Field(default_factory=list)
    params: dict[str, str] = Field(default_factory=dict)  # substitution variables
