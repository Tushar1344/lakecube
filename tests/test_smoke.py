"""Smoke tests — ensure the package imports, the CLI loads, and Sample.Basic parses."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import lakecube
from lakecube.cli.main import cli
from lakecube.compiler.compile import compile_cube, load_spec

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


def test_sample_basic_compiles_to_plan() -> None:
    cube = load_spec(SAMPLE_BASIC)
    plan = compile_cube(cube)
    assert plan.metric_views
    assert plan.lakeflow_pipelines
    assert plan.abac_policies
    assert plan.delta_branches
    assert plan.lakebase_schemas


def test_cli_compile_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["compile", str(SAMPLE_BASIC)])
    assert result.exit_code == 0
    assert "sample_basic" in result.output
