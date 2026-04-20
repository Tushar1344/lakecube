"""Compiler — takes a `cube.yaml` spec and emits deployable Databricks artifacts.

The compiler is the heart of Lakecube. It must:
  1. Validate the spec against the Pydantic schema.
  2. Emit Unity Catalog Metric View DDL (the primary semantic layer).
  3. Emit Lakeflow Declarative Pipeline YAML (for dimension conformance, SCD,
     and materialized aggregations that serve as the ASO / IVM calc engine).
  4. Emit UC ABAC policies + row-filter UDFs from `security:` blocks.
  5. Emit Delta branch ops for `scenarios:` blocks.
  6. Emit Lakebase schema DDL for write-back forms + cell comments.

It writes no runtime of its own — every emission is configuration for
existing Databricks primitives.
"""

from lakecube.compiler.compile import compile_cube

__all__ = ["compile_cube"]
