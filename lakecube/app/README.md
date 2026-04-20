# Lakecube Workbench

A Databricks App that serves as the web client for Lakecube cubes. Four modes, one shell:

- **Analyze** — AG Grid pivot with Essbase-familiar ad-hoc gestures (zoom, keep-only, pivot, POV, drill-through, Genie sidekick).
- **Design** — visual outline editor for admins who don't want to edit `cube.yaml` directly. Saves emit git PRs.
- **Forms** — Hyperion-Planning-style form designer + runner for guided data entry.
- **Govern** — approval inbox (side-by-side scenario diff), rule audit, substitution-variable editor, security-filter manager.

**Status**: lands in P1 (Analyze mode) → P3 (Forms/Govern) → P4 (Design mode).
