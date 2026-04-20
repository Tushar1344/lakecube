"""Migration tooling — ingest existing Essbase artifacts.

- outline.py  — parse Essbase .otl XML export → cube.yaml
- calc.py     — transpile .csc calc scripts → Lakeflow / `lakecube.fn` Python
- rules.py    — convert .rul data-load rules → Lakeflow Declarative Pipelines
- maxl.py     — interpret or translate .mxl automation scripts

Design goal: idempotent and re-runnable. As the importers mature, users
re-import legacy artifacts and benefit from improved coverage without
manual intervention.
"""
