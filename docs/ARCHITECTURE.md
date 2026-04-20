# Lakecube Architecture

The full architecture blueprint, including the Essbase user migration parity matrix,
lives in [`blueprint.md`](blueprint.md). This file is a short recap.

## TL;DR

Lakecube delivers the Essbase **contract** — cubes, hierarchies, driver-based calc,
scenario write-back, member-level security, Smart-View-style ad-hoc gestures —
through a thin shim over Databricks primitives. The runtime is entirely new;
the daily user experience is not.

## What's new code

1. **Spec** — `cube.yaml` + optional Python. Author cubes as code.
2. **Compiler** — emits UC Metric Views, Lakeflow pipelines, UC ABAC policies, Delta branch ops, Lakebase schemas.
3. **CLI** — `lakecube` (MaxL replacement) with migration importers for `.otl`, `.csc`, `.rul`, `.mxl`.
4. **Workbench App** — Databricks App with Analyze / Design / Forms / Govern modes.
5. **Excel plugin** — Databricks Excel Add-in with Smart-View-parity ad-hoc + write-back.
6. **XMLA bridge** (optional, migration aid) — legacy MDX clients keep working.

## What's not new code

Everything else. Explicitly out of scope — because Databricks already provides these:

- Calc scheduler → Lakeflow Jobs
- Query engine → Photon
- Data catalog → Unity Catalog
- Semantic layer → UC Metric Views
- ACL system → UC ABAC + RLS/CLS
- Materialized view / IVM runtime → Lakeflow MVs
- Transactional write substrate → Lakebase
- BI tool → AI/BI Dashboards
- Natural-language interface → Genie
- ML / agent platform → Mosaic AI / Agent Bricks
- Data loader → Lakeflow Declarative Pipelines
- Governance layer → UC

## Phases

| Phase | Scope | Duration |
|---|---|---|
| **P0** | Compiler MVP + outline importer + Sample.Basic compiles | 5 wks |
| **P1** | Read analytics parity: hierarchies, security → ABAC, AI/BI + Genie + Workbench Analyze mode | 8 wks |
| **P2** | Smart-View-parity Excel plugin + driver calc + MaxL/calc-script importers | 14 wks |
| **P3** | Forms + write-back + scenarios + rules importer | 14 wks |
| **P4** | XMLA bridge + Workbench Design mode + agents | 10 wks |
| **P5** | Long-tail parity | ongoing |

P0+P1 ship in 13 weeks as "modern cube analytics on Databricks." Full parity at ~12 months.

## Essbase migration parity

Every daily Essbase workflow — ad-hoc zoom/keep-only/pivot, forms, business rules,
approvals, drill-through, MaxL automation — has a named Lakecube equivalent.
The "retain the verbs" principle: where Essbase users know a term (Retrieve, POV,
Outline, Scenario, Business Rule, Substitution Variable), the Lakecube UI uses
the same term even if the underlying tech is entirely different.

See the full parity matrix in the design note (to be imported into `docs/blueprint.md`).
