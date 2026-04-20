"""Smoke tests — ensure scaffold, CLI, and emitters all produce reasonable output."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import lakecube
from lakecube.cli.main import cli
from lakecube.compiler.compile import compile_cube, load_spec, write_plan
from lakecube.emitters import (
    emit_lakebase,
    emit_lakeflow,
    emit_metric_view,
    emit_scenarios,
    emit_security,
)

SAMPLE_BASIC = Path(__file__).parent.parent / "examples" / "sample_basic" / "cube.yaml"


def test_version() -> None:
    assert lakecube.__version__


def test_cli_loads() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "lakecube" in result.output.lower()


def test_sample_basic_parses() -> None:
    cube = load_spec(SAMPLE_BASIC)
    assert cube.name == "sample_basic"
    assert any(d.name == "measures" for d in cube.dimensions)
    assert any(d.name == "market" for d in cube.dimensions)
    assert cube.scenarios
    assert cube.security


def test_metric_view_emits_valid_yaml_body() -> None:
    cube = load_spec(SAMPLE_BASIC)
    art = emit_metric_view(cube)
    assert art.kind == "metric_view"
    assert "CREATE OR REPLACE VIEW" in art.content
    assert "version: '1.1'" in art.content or "version: \"1.1\"" in art.content
    assert cube.fact.table in art.content
    # Measures-dimension is excluded from dims; separate measures section emitted.
    assert "- name: market" in art.content
    assert "- name: Sales" in art.content


def test_lakeflow_covers_every_non_measures_dim() -> None:
    cube = load_spec(SAMPLE_BASIC)
    arts = emit_lakeflow(cube)
    assert arts and arts[0].kind == "lakeflow"
    body = arts[0].content
    for dim in cube.dimensions:
        if dim.is_measures:
            assert f"dim_{dim.name}" not in body
        else:
            assert f"dim_{dim.name}" in body
    assert "fact_mv" in body


def test_security_emits_row_filter_per_rule() -> None:
    cube = load_spec(SAMPLE_BASIC)
    arts = emit_security(cube)
    assert len(arts) == 1
    body = arts[0].content
    for flt in cube.security:
        assert flt.name in body
    assert "SET ROW FILTER" in body


def test_scenarios_emits_delta_branches() -> None:
    cube = load_spec(SAMPLE_BASIC)
    arts = emit_scenarios(cube)
    assert len(arts) == 1
    body = arts[0].content
    for sc in cube.scenarios:
        assert "CREATE BRANCH" in body
        assert sc.name.replace("-", "_") in body


def test_lakebase_schema_covers_every_non_measures_dim() -> None:
    cube = load_spec(SAMPLE_BASIC)
    arts = emit_lakebase(cube)
    assert len(arts) == 1
    body = arts[0].content
    assert "CREATE SCHEMA" in body
    for dim in cube.dimensions:
        if not dim.is_measures:
            assert f"{dim.name}_key" in body


def test_cli_compile_writes_artifacts_to_build_dir(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "build"
    result = runner.invoke(
        cli, ["compile", str(SAMPLE_BASIC), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert "sample_basic" in result.output
    assert (out / "sample_basic" / "metric_views" / "sample_basic.sql").exists()
    assert (out / "sample_basic" / "lakeflow" / "sample_basic.yaml").exists()
    assert (out / "sample_basic" / "security" / "sample_basic_row_filters.sql").exists()
    assert (out / "sample_basic" / "scenarios" / "sample_basic_branches.sql").exists()
    assert (out / "sample_basic" / "lakebase" / "sample_basic_writeback.sql").exists()


def test_write_plan_returns_all_paths(tmp_path: Path) -> None:
    cube = load_spec(SAMPLE_BASIC)
    plan = compile_cube(cube)
    written = write_plan(plan, tmp_path)
    assert len(written) == len(plan.artifacts)
    for p in written:
        assert p.exists()
        assert p.read_text()
