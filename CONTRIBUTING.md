# Contributing to Lakecube

Lakecube is pre-alpha. The scaffold is in place; the substance is ahead. Early-stage contributions especially welcome in these areas:

## Where help is most useful

1. **Essbase migration parity** — pressure-test the [parity matrix](docs/ARCHITECTURE.md#11-essbase-user-migration-parity). If you use Essbase daily and something on your workflow isn't covered, open an issue.
2. **`cube.yaml` spec** — the authoring format is the most important decision. Critique the schema; propose simplifications.
3. **Sample.Basic example** — the canonical Essbase cube re-expressed as Lakecube YAML. Refinements welcome.
4. **Importers** — if you have real Essbase `.otl` / `.csc` / `.rul` / `.mxl` files (anonymized), we need them to test the importers against reality.

## Dev setup

```bash
git clone https://github.com/Tushar1344/lakecube
cd lakecube
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Style

- `ruff` for lint + format
- `mypy` for types (gradually)
- Prefer small, focused PRs
- Tests required for new behavior (smoke tests accepted for scaffolding)

## Design principles (repeat often)

1. **Nothing Databricks already provides gets rebuilt.** If you're about to write a query engine, a catalog, a materialization runtime, a BI tool, a semantic layer — stop. Lakecube emits configuration for those; it doesn't replace them.
2. **Timeless Essbase ideas survive; 1990s implementation details don't.** BSO/ASO labels, MaxL-as-language, outline binaries — gone. Cubes, hierarchies, POV, scenarios, driver calc, Smart-View gestures — preserved.
3. **Every daily Essbase workflow has a Lakecube equivalent before we ship.** See the parity matrix. If a workflow isn't covered, either a new issue lands or we explicitly accept the gap with a workaround documented.

## Code of Conduct

Be kind. Be rigorous. Assume the other person has read the spec.
