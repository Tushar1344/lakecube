# Re-engineering Essbase — A Thin Cube Contract Over Databricks

## 1. Context

Oracle Essbase still anchors thousands of Finance/EPM workloads, and the fact that the best modern answer is to containerize Oracle's binaries ([appliedolap/docker-essbase](https://github.com/appliedolap/docker-essbase)) exposes the real opportunity. But "re-engineering Essbase" is a trap if it means re-implementing Essbase. Most of Essbase's surface area is an artifact of 1990s constraints — scarce RAM, slow disks, no columnar stores, no git, no Lakehouse, no semantic layer standards. The timeless ideas are small.

This blueprint re-scopes the project from *"rebuild Essbase"* to *"deliver the Essbase **contract** — cubes, hierarchies, driver-based planning, write-back, member security — through a thin shim over Databricks primitives."* The goal is the smallest possible new codebase that honors the timeless 20% of Essbase and borrows aggressively from modern engines (atoti, Pinot, ClickHouse, Druid, Malloy, dbt Semantic Layer, RisingWave, Iceberg). Anything that can be delivered by an existing Databricks abstraction **must** be delivered by that abstraction, unchanged.

Codename: **Lakecube**. Deliverable in this session: blueprint only. Audience spans read-only analytics → BI self-serve → EPM write-back, phased in that order.

## 2. What Essbase Got Right (Keep) vs. What Was Legacy (Drop)

### Timeless ideas worth preserving
*Data-model concepts*
| Idea | Why timeless |
|---|---|
| **Cube-as-contract** (named dimensions, measures, hierarchies) | Business model, not a storage model |
| **Hierarchies as first-class** (with level/ancestor/descendant ops) | Maps directly to how finance reasons about rollups |
| **Point of View (POV)** as the navigation primitive | Right UX for ad-hoc multidim analysis |
| **Driver-based calc** (`Margin = Revenue − COGS`) | Composable, auditable, re-used by every modern planner |
| **Member-level semantic security** ("you can see US + children") | Security expressed in business terms, not table predicates |
| **Write-back with scenario isolation + approval** | The reason EPM exists; read-only BI is a different product |
| **Time intelligence** (YTD, QTD, MAT, prior-year) | Universal, not Essbase-specific |
| **Solve order / calc dependencies** | Real, declarable DAG of metrics |
| **Attribute dimensions + UDAs** | Slicing by free-form tags without fact-table bloat |
| **Drill-through to source** | Analyst always wants to know "what transactions made this number" |

*Daily-workflow concepts (the muscle memory we must not break)*
| Idea | Why timeless |
|---|---|
| **Ad-hoc grid semantics** — zoom in/out, keep-only, remove-only, pivot, free-form member entry | Essbase users do this thousands of times a week; any "modern" UI that drops these feels broken |
| **Session POV** that persists across sheets | Set once, work for hours |
| **Data forms** (guided input with fixed layouts) | Primary planning UX — budgeters live in forms, not pivot grids |
| **Business rules triggered from the grid** (right-click → run) | Consolidation, allocation, currency conversion on demand |
| **Cell comments / linked reporting objects** | Why a number is what it is — audit trail in-place |
| **Aliases / locale toggling** | Same number, different member name per user |
| **Interactive calc test / preview** | "Run this calc, show me what changes, don't commit" |
| **Approval inbox with side-by-side diff** | Manager reviews the delta before it lands |
| **Substitution variables** (rename, don't remove) | Finance relies on `&CurrYear`, `&CurrMonth`; we call them parameters, keep the feel |

### 1990s baggage to **drop**
| Essbase concept | What replaces it | Why drop |
|---|---|---|
| BSO / ASO / Hybrid storage modes | Delta + Liquid Clustering + Photon | Physical-layer concerns the platform handles |
| Dense/sparse dimension labels | Planner chooses; Photon handles skew | Not a user concept |
| Two-pass calc (dense → sparse) | Query planner / DAG | Mechanical detail |
| Calc scripts as a proprietary DSL | Python UDFs + Lakeflow Pipelines + SQL | Better languages now exist |
| MDX as the query language | SQL + Metric View queries + Genie NL | Legacy client protocol only |
| MaxL scripting | `lakecube` CLI + IaC | CLI beats a bespoke language |
| Outlines as a binary file | Git-versioned YAML | Version control is table stakes |
| Restructure as a distinct operation | Schema migration via compiler + Lakeflow | Online evolution for free |
| Substitution variables | Jinja / dbt-style params | Every modern templating system does this |
| Transparent/replicated/linked partitions | UC + Delta Sharing + Lakehouse Federation | Generic federation exists |
| Rules files | Lakeflow Declarative Pipelines | Declarative ETL is solved |
| Block-level cache | Photon + disk cache | Platform concern |
| Alias tables | UC translation tables / column comments | Catalog concern |

**Important distinction**: the "drop" column is about *implementation and jargon*, not capability. A user who wrote MaxL scripts still gets CLI-driven automation with a MaxL-to-`lakecube` translator for their existing code. A user who wrote calc scripts still gets their calc logic — transpiled or wrapped — running on Lakeflow instead of BSO. The outline binary is gone; the *visual outline editor* is not. See **Section 11: Essbase User Migration Parity** for the full coverage matrix.

Net effect: Lakecube is ~10% of the Essbase surface area, doing the 100% of the work that matters — and every daily workflow an Essbase user relies on has a named equivalent, not a shrug.

## 3. Borrowed Ideas from Modern Engines

| Idea | Source | How we use it |
|---|---|---|
| **Compositional metric DSL** | [atoti](https://www.atoti.activeviam.com/) (Python), [Malloy](https://www.malloydata.dev/), [dbt MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow) | Cube authored as YAML + optional Python; metrics reference other metrics |
| **Optimizer-routed projections** | [ClickHouse](https://clickhouse.com/) | UC Metric Views already do this; we don't reinvent it |
| **Ingest-time rollup** | [Druid](https://druid.apache.org/), [Pinot](https://pinot.apache.org/) star-tree | Lakeflow AUTO CDC + MVs gives us this for free |
| **Incremental view maintenance** | [RisingWave](https://risingwave.com/), [Materialize](https://materialize.com/) | This **is** what Lakeflow MVs are; use them as the calc engine |
| **Branch-per-scenario** | Iceberg branches, git | Scenario = Delta branch. Approval = merge. Fork/commit/reject come free |
| **Driver-based planning** | Anaplan, Pigment, Causal | Metrics form an explicit DAG; change an input, IVM cascades |
| **Metrics-as-code + OSI** | dbt Semantic Layer, [Open Semantic Interchange](https://semanticinterchange.org/) | Author once, surface in Genie, AI/BI, Tableau, Excel, Power BI — no XMLA lock-in |
| **Nested structures as first-class** | Malloy, BigQuery | Hierarchies modeled as nested `STRUCT`s on Delta, not closure tables |
| **Approval as merge request** | GitHub | PR flow = planning flow. Free auditability |

What we explicitly **don't** borrow: proprietary query DSLs (MDX, DAX), rigid pre-materialized cube schemas (Kylin), in-memory-only engines (SSAS Tabular).

## 4. Architecture — What's Actually New

Lakecube is **a contract, a compiler, and two thin apps**. Everything else is existing Databricks.

```
┌─────────────────────────────────────────────────────────────────┐
│  Author:  cube.yaml (+ optional calc.py)  ── git                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ lakecube compile
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  NEW:  Lakecube Compiler  (~5k LoC Python)                      │
│        Emits artifacts — writes NO runtime of its own           │
└──┬─────────┬─────────┬─────────┬─────────┬─────────┬────────────┘
   │         │         │         │         │         │
   ▼         ▼         ▼         ▼         ▼         ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│ UC     ││Lakeflow││ UC     ││ Delta  ││Lakebase││ App    │
│ Metric ││ Decl.  ││ ABAC + ││ Branch ││ schema ││ config │
│ Views  ││Pipelines│ RLS    ││ ops    ││(forms) ││(forms) │
└────────┘└────────┘└────────┘└────────┘└────────┘└────────┘
 semantic  calc/IVM   security  scenarios write-back  UX
 layer     engine     filters   isolation state
```

### 4.1 Storage & Calc — use what exists, unchanged

- Facts and dimensions live in **Delta** with **Liquid Clustering**. Predictive Optimization runs compaction. Hierarchies are either a `STRUCT` column (nested model) or a standard `parent_member/level` closure — the compiler supports both; neither is a new primitive.
- Every aggregation is a **Lakeflow Materialized View** with AUTO CDC + incremental refresh. This is the ASO analog and the IVM calc engine at the same time. *There is no custom calc DAG.*
- Procedural multi-step calc (what Essbase expressed as calc scripts — e.g. allocations, consolidation with elimination, what-if overrides) is a **chain of Lakeflow pipelines** whose dependencies are declared in `cube.yaml`. Lakeflow already does topological execution, retries, lineage. We inherit it.
- A small **Python UDF library** (`lakecube.fn`) exposes cube-aware helpers: `parent()`, `children()`, `ytd()`, `prior_period()`, `allocate()`. These compile to SQL window/aggregate expressions where possible; fall back to Python UDF otherwise. This is the *only* concession to a "DSL" — and it's just a library.

### 4.2 Semantic Layer — extend, don't replace

- **Unity Catalog Metric Views** are the semantic layer. Full stop. We do **not** build a parallel outline.
- The compiler emits a Metric View per measure set, annotating hierarchies, attribute dimensions, DTS calendar members as UC properties + tags.
- Where Metric Views lack something (today: member formulas, attribute dims), we contribute the pattern as a **compiler-emitted SQL view** tagged for discovery — not a new catalog object. When UC closes the gap, the compiler switches emit targets; users don't change anything.
- OSI-compatible YAML is the source format. Means dbt users, Genie, AI/BI, Tableau/Power BI (via BI compat mode), and future OSI-compliant tools all see the same metrics.

### 4.3 Security — translate, don't duplicate

- Member-level filters (`Entity IN descendants(US)`) are authored in the cube YAML. Compiler lowers them to **UC ABAC policies** + row filter UDFs over the dimension's hierarchy column. UC governance handles enforcement — we don't invent a filter engine.
- Attribute-based security becomes UC ABAC tag policies directly.
- Hierarchy-aware filtering (descendants, ancestors) is a library of standard SQL predicates the compiler emits.

### 4.4 Scenarios & Write-back — Delta branches + Lakebase

- A **scenario is a named Delta branch**. Forking is instant; merging is atomic; approval workflow is a pull request in a git-tracked `scenarios/` directory.
- Cell edits from Excel or the Workbench land in **Lakebase** (per-scenario form state + row-level locking via Postgres advisory locks). A Lakeflow job promotes approved edits into the scenario's Delta branch and merges to `main`.
- Business rules (`@cube.rule`) are Python functions run pre/post submit — hosted in a Databricks job, not a custom runtime.
- This replaces Essbase's cell-locking + approval workflow + audit trail with three existing, generic, battle-tested systems.

### 4.5 Clients — cover every Essbase daily workflow, then add the new capabilities

Three client surfaces. Each covers a persona fully so nobody is told "go use a different tool."

**A. Excel — "Smart View parity" plugin (this is where migration risk is highest)**

Built as a Databricks Excel Add-in extension. Must support the full Smart View muscle-memory set, not just "POV + submit":

- *Ad-hoc grid*: connect, default POV, zoom-in (expand children), zoom-out (collapse to parent), zoom-to-bottom/level, keep-only, remove-only, pivot row↔column, swap dimension, remove dimension
- *Free-form mode*: type member names (with alias/partial-match resolution) anywhere on the sheet; refresh resolves and aggregates
- *Member selector*: hierarchy tree dialog with search, attribute filters, UDA filters — identical ergonomics to Smart View's
- *POV toolbar*: persistent across workbook tabs; alias-table switcher dropdown
- *Drill-through*: right-click cell → "Drill Through" → opens source rows in a new sheet
- *Cell comments & LROs*: right-click → attach note/URL/file; stored in Lakebase, visible on hover
- *Submit*: submit-selected-range, submit-without-refresh, validate-before-submit
- *Run Business Rule*: right-click → pick rule → prompt for parameters → execute → refresh
- *Grid formulas* (local, non-persisted): `=$Sales*1.05` for what-if without writing to the cube
- *Keyboard shortcuts*: mirror Smart View defaults (Alt+S,Z,I for zoom-in, etc.) — muscle memory preserved
- *Formatting & comments preserved on refresh* (this is the #1 Smart View complaint about competitors that fail it)
- *Query designer / report designer*: build a parameterized report, save, re-run

VBA/macro compatibility is **explicitly scoped-down**: we expose a Python/JS API via Excel add-in, not a VBA shim. Customers with VBA-heavy books use the XMLA bridge temporarily while we help them port.

**B. Lakecube Workbench — Databricks App (~8-10k LoC, not 2k)**

The web client. Four modes, one shell:

- **Analyze mode** — AG Grid pivot with full ad-hoc semantics (same ops as Excel above), scenario picker, POV panel, drill-through drawer, Genie sidekick for NL questions
- **Design mode** — visual outline/cube editor: dimension tree with drag-drop reparent, member property panel (consolidation operator, storage, alias, UDAs, formula), formula editor with autocomplete + inline validation, "Preview calc" button that runs a dry-run against a Delta branch. Saves emit a git PR on `cube.yaml`; admins who don't want git get a "Save & Deploy" button that commits on their behalf
- **Forms mode** — form designer (grid with rows/columns of members, fixed text, data/formula cells, read-only vs. writable, validation rules) + form runner for end users. Mirrors Hyperion Planning forms
- **Govern mode** — approval inbox with side-by-side diff of scenario vs. `main`, rule execution audit, substitution-variable editor, security-filter manager

**C. AI/BI Dashboards + Genie — zero-build surface**

A cube = a metric view, so AI/BI and Genie work out of the box. We add:
- A **"Lakecube lens"** — a pre-built AI/BI dashboard template per cube (variance, trend, top-N) that a user gets with `lakecube deploy`
- **Genie agent pack** — cube-aware skills: "explain variance", "allocate overhead", "compare scenarios", "find outliers in dimension X"
- **Agent Bricks** for the "why did this move" workflow — pure additive capability that Essbase never had

**D. Legacy bridge — XMLA/MDX → SQL translator (Phase 4, migration aid)**

Thin service so existing Smart View (classic), Excel OLAP pivots, Power BI Premium, and third-party MDX clients connect unchanged while we migrate workbooks. Built on [olap4j](http://www.olap4j.org/) / [Mondrian](https://mondrian.pentaho.com/) parser. Supports the 80/20 of Essbase MDX; flags unsupported constructs. Not a core plane — a ramp.

### 4.6 CLI & authoring loop

- `lakecube compile | deploy | diff | scenario new|merge|reject | calc run | test | rule run | maxl run` — Click wrapper. Replaces MaxL for new work and runs MaxL for legacy.
- Cube repo has the same shape as a dbt project: `models/`, `scenarios/`, `forms/`, `rules/`, `tests/` (data-parity tests).
- Schema evolution: edit YAML, commit, CI runs `lakecube diff` → applies Delta/UC/Lakeflow changes idempotently. No "restructure" event.

### 4.7 Migration & authoring tooling — inherit existing artifacts, don't force rewrites

Users have 10–20 years of MaxL scripts, calc scripts, rules files, and outlines. We inherit them.

- **Outline importer** (`lakecube import outline app.db.otl`) — parses Essbase XML outline export; emits `cube.yaml` with dimensions, hierarchies, aliases, UDAs, attribute dims, consolidation operators, member formulas. Member-formula syntax is translated where 1:1 mappings exist; others wrapped in a Python UDF with the original formula preserved as a comment for manual review.
- **Calc script transpiler** (`lakecube import calc script.csc`) — parses FIX/ENDFIX, AGG, CALC DIM, CALC ALL, SET commands; emits a Lakeflow pipeline (for set-based ops) or a Python calc function using `lakecube.fn` (for procedural ops). Best-effort: expect 70–80% clean translation; the rest get a stub + a `# TODO: manual` with the original script embedded. Critical: the transpiler is **idempotent and re-runnable** as the transpiler matures, users can re-import with improvements.
- **Rules file converter** (`lakecube import rules load.rul`) — parses Essbase data load rules (column mappings, aggregation rules, selection criteria); emits a Lakeflow Declarative Pipeline YAML.
- **MaxL translator** (`lakecube maxl run script.mxl` or `lakecube maxl convert`) — parses MaxL; either executes against Lakecube (runtime mode) or emits equivalent `lakecube` CLI invocations (convert mode). Covers the common verbs: create/alter/drop app|db|filter|user, import/export data, execute calc, display filter row. Legacy ops automation keeps working unchanged on day one.
- **Substitution variable adapter** — reads Essbase substitution variable exports; writes Lakecube parameter manifest (`params.yaml`). Jinja-style `{{ params.curr_year }}` in authoring; `&CurrYear` syntax still accepted in imported scripts for compatibility.
- **Smart View workbook inventory** (`lakecube inventory workbooks /path`) — scans Excel files for Smart View connections and flags which ones depend on features our plugin does / doesn't support yet. Gives migration PMs a quantified backlog.
- **Data parity tester** (`lakecube parity test`) — runs a battery of queries against both Essbase (via MaxL export) and Lakecube; produces a diff report with tolerance bands. CI-friendly.

## 5. What We Are NOT Building

Explicitly out of scope — because Databricks already has these:

- A calc scheduler (Lakeflow Jobs)
- A query engine (Photon)
- A data catalog (Unity Catalog)
- A semantic layer (UC Metric Views)
- An ACL system (UC ABAC + RLS/CLS)
- A materialized view / IVM runtime (Lakeflow MVs)
- A transactional write substrate (Lakebase)
- A BI tool (AI/BI Dashboards)
- A natural-language interface (Genie)
- An ML / agent platform (Mosaic AI / Agent Bricks)
- A data loader (Lakeflow Declarative Pipelines + AUTO CDC)
- A governance layer (UC)

Anything built is a bug.

## 6. Phased Rollout — Compressed

Because most of the plumbing is reused, timelines are tight — but **user-experience parity has its own cost**, and we're not cutting that.

| Phase | Scope | Duration | Exit |
|---|---|---|---|
| **P0 — Compiler MVP** | `cube.yaml` spec (OSI-compat superset), compiler emits UC Metric View + Lakeflow pipelines, `lakecube` CLI, Sample.Basic example, **outline importer** (Essbase .otl → cube.yaml) | 5 wks | `lakecube import outline Sample.Basic.otl && lakecube deploy` → queryable metric view |
| **P1 — Read analytics parity** | Hierarchies, attribute dims, UDAs, DTS, aliases, security compiler → ABAC, AI/BI + Genie over the cube, **Workbench Analyze mode** (ad-hoc grid with zoom/keep/pivot), **drill-through** | 8 wks | Analyst reproduces Sample.Basic Essbase reports in AI/BI *and* in Workbench with familiar ad-hoc gestures |
| **P2 — Excel parity + driver calc** | **Full Smart-View-fidelity Excel plugin** (zoom, keep-only, free-form, member selector, POV, aliases, grid formulas, cell comments), `lakecube.fn` library, multi-step Lakeflow calc chains, **calc script transpiler**, **MaxL translator** | 14 wks | Essbase analyst opens Excel, uses ad-hoc against Lakecube with no retraining. Variance/allocation calcs match within tolerance |
| **P3 — Forms + write-back + rules** | **Workbench Form Designer & Runner** (Hyperion-Planning-style forms), Delta branch scenarios, Lakebase write-back, approval workflow with diff inbox, business rules (right-click in grid), substitution-variable adapter, **rules-file importer** | 14 wks | End-to-end planning cycle on a reference tenant; budget cycle completed by a real finance user without Essbase fallback |
| **P4 — Legacy bridge + design mode + agents** | XMLA/MDX translator (Smart View classic, Power BI Premium), **Workbench Design mode** (visual outline editor for non-git admins), Agent Bricks cube assistant, Lakehouse Federation for cross-cube, VBA workbook inventory + migration playbook | 10 wks | Existing Smart View client connects unchanged. Non-technical admin can add a dimension via the visual editor. Agent answers "why did margin drop" |
| **P5 — Long-tail parity** | Report designer, remaining MDX functions, rarely-used calc script verbs, pixel-perfect Excel formatting preservation | ongoing | Each closed gap retires one legacy Essbase dependency |

Total to real parity: **~12 months** (not 10 — Excel Smart View parity and forms designer each earn their quarters). **P0+P1 still ship in 13 weeks** as "modern cube analytics on Databricks" with ad-hoc gestures Essbase users recognize.

Contrast: the previous draft of this blueprint had a 24-month plan because it tried to build a calc engine, an XMLA service, a scenario runtime, and a security engine. Dropping those in favor of existing Databricks abstractions still cuts ~50% of the work, even after we give Excel/Forms/migration-tooling the scope they deserve.

## 7. Critical Artifacts When Implementation Begins

- `lakecube/spec/` — YAML schema (OSI superset) + JSON Schema validator
- `lakecube/compiler/` — `spec → {UC Metric View DDL, Lakeflow YAML, ABAC policies, Delta ops}`
- `lakecube/fn/` — cube-aware SQL/Python helpers (`parent`, `descendants`, `ytd`, `allocate`)
- `lakecube/cli/` — Click app; subcommands for compile/deploy/scenario/diff
- `lakecube/app/` — Databricks App (Workbench) with pivot + POV + scenarios
- `lakecube/excel/` — Databricks Excel Add-in plugin (POV + write-back)
- `lakecube/xmla/` — optional legacy bridge (Phase 4)
- `lakecube/examples/sample_basic/` — Essbase's canonical example re-expressed

Existing utilities to reuse (not reinvent):
- `databricks.sdk` for everything catalog/pipeline/app
- `dbt-databricks` macros for SQL codegen patterns
- `olap4j` (Java) or `mondrian` (parser only) if we build the XMLA bridge
- OSI YAML schema from [semanticinterchange.org](https://semanticinterchange.org/) as the base format

## 8. Known Gaps & Open Questions

1. **UC Metric View expressiveness**: member formulas, attribute dims, and solve_order are not fully supported today. Short-term: compiler emits pattern-matched SQL views; long-term: contribute upstream.
2. **Hierarchy performance at scale**: 10M+ members needs benchmarking. STRUCT-nested and closure-table paths both emit SQL; pick per cube via benchmark.
3. **Legacy calc script migration**: some customer scripts are gnarly. Provide a best-effort transpiler + a "wrap in Python UDF" escape hatch; don't promise 100%.
4. **Smart View fidelity**: Excel plugin does POV + refresh + submit. Pixel-perfect formatting, VBA compat, macro libraries — explicitly out of scope. Legacy users connect via the XMLA bridge during migration, not forever.
5. **Commercial packaging**: OSS reference implementation vs. Databricks product vs. partner build vs. field asset — this blueprint is neutral. Recommend: **OSS compiler + CLI + examples**, commercial Workbench App if scale demands it.

## 9. Verification — End-to-End Demo

When P0+P1 (10 weeks) complete, this works:

1. `git clone lakecube && cd examples/sample_basic && lakecube deploy`
2. AI/BI dashboard auto-wires to the compiled metric view; drill Market → Region → City works
3. Genie against the cube: *"why did Q1 cola sales drop in the East?"* → tuple-level driver answer via Explain-Changes
4. `lakecube diff --against essbase://sample.basic` — data-parity report (via MaxL export + diff)
5. `lakecube scenario new budget-v2 --fork main` → Delta branch appears; edits land in Lakebase; `lakecube scenario merge budget-v2` promotes atomically

P2+: add procedural calc tests (`lakecube calc run allocations.py` matches Essbase within tolerance). P3: full planning cycle demo. P4: legacy Smart View connects to XMLA bridge unchanged.

## 10. Recommendation

Commit a **13-week P0+P1 spike** against Sample.Basic. Success criteria: an Essbase analyst opens the Workbench (and, stretch goal, the Excel plugin), drills, zooms, keeps-only, pivots, and reproduces five representative reports without asking "how do I…?" once — against a real compiled cube on Databricks. If that lands with the familiar gestures working, Phase 2/3/4 is incremental work on a proven foundation, and migration commitment from a reference customer becomes possible.

The key mindset shift this blueprint encodes: **Lakecube should feel like a dbt-shaped project that happens to produce cubes, running on the Lakehouse you already own** — but one whose **front door preserves every gesture an Essbase user has spent 20 years learning**. The runtime is entirely new; the daily experience should not be. It is not a new OLAP engine. Essbase's lasting contribution was the *contract* between finance users and their data model — and the *workflow* they practice daily — both of which survive. Everything else was a product of its era.

---

## 11. Essbase User Migration Parity

The critical question this section answers: *when an Essbase user logs into Lakecube on day one, what do they lose, what must they adapt to, and what do they gain?*

### 11.1 Daily-workflow coverage by persona

Coverage status: 🟢 = native equivalent with familiar gestures; 🟡 = works, but minor adaptation (new UI, same concept); 🔴 = genuine loss (rare, and called out).

#### The Ad-hoc Analyst (Smart View Excel)
| Essbase action | Lakecube equivalent | Status |
|---|---|---|
| Connect to cube | Excel plugin → connect to catalog.cube | 🟢 |
| Zoom-in/out | Right-click → Zoom In/Out (same menu, same shortcut) | 🟢 |
| Keep-only / Remove-only | Right-click → Keep Only / Remove Only | 🟢 |
| Pivot dimension | Drag or right-click Pivot | 🟢 |
| Free-form member entry | Type name → plugin resolves (partial match + aliases) | 🟢 |
| Member selector dialog | Hierarchy tree with search, attributes, UDAs | 🟢 |
| POV bar | Persistent POV toolbar | 🟢 |
| Change alias table | Ribbon dropdown | 🟢 |
| Drill-through | Right-click → Drill Through → new sheet with source rows | 🟢 |
| Cell comments / LROs | Right-click → Comment / Attach; stored in Lakebase | 🟢 |
| Grid formulas (`=Sales*1.05`) | Same syntax, evaluated locally by plugin | 🟢 |
| Refresh preserves formatting | Yes (this is the feature competitors miss) | 🟢 |
| VBA macros | Python/JS Excel API; VBA books run via XMLA bridge during migration | 🟡 |
| Smart Slice / Smart Query | Workbench Query Designer; Excel variant follows | 🟡 |

#### The Planner / Budget Owner
| Essbase action | Lakecube equivalent | Status |
|---|---|---|
| Open a data form | Workbench → Forms → open; or Excel with form link | 🟢 |
| Type budget numbers | Same grid editing, autosave to Lakebase | 🟢 |
| Run a business rule | Right-click in grid → Run Rule → parameter prompt | 🟢 |
| Save / submit | Submit button → validates via rules → writes to scenario branch | 🟢 |
| Scenario sandbox | Scenario picker creates a named Delta branch | 🟢 |
| Approval workflow | Govern mode inbox with side-by-side diff | 🟢 |
| Task lists | Lakeflow Jobs + Workbench task panel | 🟡 |
| Copy-paste from one POV to another | Workbench + Excel: right-click → Copy POV | 🟢 |

#### The Cube Designer / Admin
| Essbase action | Lakecube equivalent | Status |
|---|---|---|
| Edit outline | `cube.yaml` (git) OR Workbench Design mode (visual) | 🟢 / 🟡 (admins who hate git use the visual editor; git is still the source of truth behind the scenes) |
| Set consolidation operator (+/−/~/^) | Member property panel | 🟢 |
| Write member formula | Formula editor with autocomplete, live validation | 🟢 |
| Write calc script | Python + `lakecube.fn` OR import legacy `.csc` | 🟢 |
| Test calc before commit | Design mode → "Preview Calc" → runs against ephemeral Delta branch, shows diff | 🟢 |
| Restructure database | Commit YAML → `lakecube diff` → idempotent apply (no downtime) | 🟢 |
| Create/manage security filters | YAML `security:` block → compiles to UC ABAC; or Govern-mode filter manager | 🟢 |
| Substitution variables | `params.yaml`; legacy `&Var` syntax accepted in imported scripts | 🟢 |
| Manage aliases | `aliases:` section in YAML, surfaced in Design mode | 🟢 |
| Backup / restore | Delta time travel + UC clone | 🟢 (strictly better) |

#### The MaxL / Automation Developer
| Essbase action | Lakecube equivalent | Status |
|---|---|---|
| Run MaxL script | `lakecube maxl run script.mxl` (interpreter) OR `lakecube maxl convert` → native CLI | 🟢 |
| Create/alter app/db | `lakecube deploy` (declarative) | 🟢 |
| Load data | `lakecube data load` OR Lakeflow pipeline | 🟢 |
| Execute calc | `lakecube calc run` | 🟢 |
| Manage filters | `lakecube security apply` | 🟢 |
| Schedule jobs | Lakeflow Jobs (cron + triggers) | 🟢 |
| Rest API / EPM Automate | `databricks.sdk` + `lakecube` Python SDK | 🟡 (new surface, same capability) |

#### The Integrator / ETL Engineer
| Essbase action | Lakecube equivalent | Status |
|---|---|---|
| Rules file for flat-file load | `lakecube import rules` → Lakeflow pipeline; or author Lakeflow directly | 🟢 |
| Transparent partition | Lakehouse Federation (query remote cube/table without copy) | 🟢 |
| Replicated partition | Delta Sharing or scheduled Lakeflow copy | 🟢 |
| Linked partition (drill) | `drill_through:` config in YAML | 🟢 |

### 11.2 The "retain the verbs" principle

Where Essbase users know a term, **we keep the term** in the UI even if the underlying tech is entirely different. Vocabulary is half the mental model.

| Essbase word | Lakecube UI still uses | Notes |
|---|---|---|
| Retrieve | "Retrieve" (button + keyboard shortcut) | Even though it's a SQL query under the hood |
| Zoom In / Zoom Out | "Zoom In" / "Zoom Out" | Same menu path, same gestures |
| POV | "POV" | Not "filters", not "slicers" |
| Member | "Member" | Not "value", not "level attribute" |
| Outline | "Outline" (as a section of the cube editor) | Even though the backing file is YAML |
| Scenario | "Scenario" | Even though backing is a Delta branch |
| Business Rule | "Business Rule" | Even though backing is a Python function |
| Substitution Variable | "Substitution Variable" (alias for parameter) | Muscle memory |
| Drill Through | "Drill Through" | Standard cross-OLAP term anyway |
| Calc Script | Retained as import artifact; new files are "Calc" | Transitional |

New concepts that genuinely have no Essbase analog (scenario branches as git-like, Genie NL, agents) get new vocabulary — we don't pretend they're something they're not.

### 11.3 What the user *does* have to adapt to

Be honest about the non-zero adaptations. These are the ones we can't and shouldn't hide:

1. **"Outline is YAML" mental model** for admins who want to edit source directly. Visual Design mode covers the allergic; everyone else benefits from version control. Net positive, small learning curve.
2. **Calc scripts run as pipelines, not in-line**. Fast dev loop via "Preview Calc" mitigates, but the execution model is a chain of Lakeflow jobs, not a single `.csc` run. Observability is better (lineage, logs, retries); semantics equivalent.
3. **MDX is not the query language**. SQL, metric-view queries, and Genie NL are. Legacy MDX runs via the bridge during migration. This is probably the biggest conceptual shift.
4. **Security filters are ABAC tags + row filters under the hood**, not outline members. Authoring is in familiar terms; admins may occasionally need to inspect UC policies directly.
5. **No BSO/ASO choice**. This is a feature (the platform decides), but old hands will ask "which storage mode?" for a while.

### 11.4 What the user *gains*

The point isn't to break even — it's to come out ahead:

- **Genie on the cube** — "why did margin drop in Q2 vs forecast" answered in English
- **Agent Bricks cube assistant** — automates the "analyst walks the cube" workflow
- **Git history of the outline** — who changed what, when, why; diffs; rollback is `git revert`
- **Scenarios as branches** — fork 50 what-ifs cheaply; merge the winner; audit trail free
- **No downtime restructures** — add a dim member without kicking users off
- **Unified platform** — same cube data feeds ML, streaming, data science, BI, without exports
- **Streaming cubes** — real-time rollup via Lakeflow, not nightly batch
- **Cost elasticity** — serverless compute, pay for what you query
- **Open formats** — Delta/Iceberg, not a proprietary `.pag` file
- **Standards-based metrics (OSI)** — same cube surfaces in Tableau, Power BI, Hex, Sigma, without custom connectors

### 11.5 Migration path for a real customer

Not a big-bang cutover. A 6-step rollout so users never feel stranded:

1. **Dual-run**. Import existing outline + calc scripts + rules + MaxL into Lakecube. Load same data into both. Run `lakecube parity test` on nightly basis — green = ready.
2. **Read-only cohort**. Give the Workbench (Analyze mode) and Excel plugin to 10% of analysts for ad-hoc + reporting; Essbase remains write-back-of-record. Feedback loop on UX gestures.
3. **Bridge connect**. Stand up XMLA bridge so VBA-heavy workbooks and legacy BI tools hit Lakecube unchanged. Inventory which workbooks need plugin-native port vs. bridge-forever.
4. **Form cohort**. Migrate one budget form / planning flow to Workbench Forms + Lakebase write-back. Run a parallel plan cycle in both systems. Compare.
5. **Cutover by cube**. When parity tests pass + form cohort succeeds + ad-hoc users are comfortable, cut one cube over. Essbase for that cube becomes read-only then decommissioned. Repeat per cube.
6. **Sunset**. When the last cube migrates, Essbase licenses drop, the docker-essbase container goes dark. Customer is now fully on the Lakehouse with their OLAP workflows intact.

At no point does a user stop being able to do their job because the tool changed. That's the bar.

### 11.6 Gaps we're explicitly accepting (for now)

Honesty about 🔴 items — small, not core, but named:

- **Pixel-perfect Excel formatting on every refresh**: 80/20 supported. Some edge cases (conditional formatting tied to cell queries, merged cells spanning POV changes) may lose fidelity. Workaround: XMLA bridge.
- **Obscure MDX functions**: ~20% tail not supported by the bridge. `lakecube mdx lint` flags these; owners rewrite as metric views or grid formulas.
- **VBA-heavy automation**: runs via bridge indefinitely or gets ported to Python. We don't rebuild a VBA host.
- **Essbase Studio / Essbase Server admin console**: replaced by Workbench Govern + `lakecube` CLI + Databricks workspace UI. Different UI, same capability.
- **Oracle EPM suite deep integrations** (Hyperion Planning, HFM, FCCS specifics): if the customer runs full EPM Cloud, we're an Essbase replacement, not an EPM Cloud replacement. Partner or deeper integration project.
