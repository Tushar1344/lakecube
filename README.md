# Lakecube

**A thin cube contract over Databricks.**

Lakecube is a modern, Databricks-native replacement for Oracle Essbase — built on the principle that most of Essbase's surface area is 1990s implementation detail, while a small, timeless core (cubes, hierarchies, driver-based calc, scenario write-back, member-level security) is worth preserving and reimagining.

It is not a new OLAP engine. It is a compiler and a client surface over primitives the Lakehouse already provides: Delta Lake, Unity Catalog Metric Views, Lakeflow Declarative Pipelines, Lakebase, AI/BI + Genie, and Databricks Apps.

## Why

Finance and EPM workloads still run on Essbase because the alternatives have either been too rigid (modern MOLAP), too read-only (BI-only semantic layers), or too greenfield (modern EPM rewrites). The best "modern" Essbase story as of 2026 is still to [containerize Oracle's binaries](https://github.com/appliedolap/docker-essbase). Lakecube delivers the Essbase *contract* — not the implementation — on the Lakehouse you already own.

## What it is

- A **spec** (`cube.yaml` + optional Python): dimensions, hierarchies, measures, calc, security, scenarios — authored as code, version-controlled.
- A **compiler** (`lakecube compile`): emits Unity Catalog Metric Views, Lakeflow pipelines, UC ABAC policies, Delta branch operations, Lakebase schemas. Writes no runtime of its own.
- A **CLI** (`lakecube`): compile, deploy, diff, scenario fork/merge, calc run, parity test, import legacy artifacts.
- A **Workbench** (Databricks App): pivot grid with Essbase-familiar gestures (zoom, keep-only, pivot), visual outline editor, form designer, approval inbox.
- An **Excel plugin**: Smart-View-fidelity ad-hoc + write-back.
- **Migration tooling**: import existing Essbase outlines (`.otl`), calc scripts (`.csc`), rules files (`.rul`), and MaxL scripts — don't force rewrites.

## Timelessness test

Everything in Lakecube passes two tests:

1. **Does an Essbase user recognize the gesture?** (zoom, keep-only, POV, run business rule, drill through, scenarios) — if yes, the vocabulary and ergonomics survive.
2. **Is the implementation already a Databricks primitive?** — if yes, we use it unchanged. If no, we earn the right to build.

Things we drop: BSO/ASO/Hybrid storage labels, dense/sparse jargon, MaxL as a *language* (kept as an import format), MDX as the *primary* query language (kept via optional legacy bridge), outline binary files (replaced by git-versioned YAML). Things we keep: every capability, every gesture, every verb.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full blueprint and the Essbase-user migration parity matrix.

## Status

**Pre-P0**: scaffold only. The first working milestone is P0 — a compiler MVP that takes `cube.yaml` and produces a deployed Unity Catalog Metric View for Essbase's canonical [Sample.Basic](examples/sample_basic/) cube.

See [docs/ARCHITECTURE.md §6](docs/ARCHITECTURE.md) for the phased roadmap.

## Quickstart (when P0 lands)

```bash
pip install lakecube
git clone https://github.com/Tushar1344/lakecube
cd lakecube/examples/sample_basic

lakecube compile                        # validate + preview
lakecube deploy --catalog main          # emit UC Metric View + Lakeflow
lakecube scenario new budget-v2         # fork a Delta branch
lakecube scenario merge budget-v2       # merge approved changes
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome — particularly from anyone with Essbase experience who can pressure-test the migration parity matrix.

## License

Apache-2.0. See [LICENSE](LICENSE).
