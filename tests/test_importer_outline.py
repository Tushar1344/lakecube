"""Tests for the Essbase outline XML importer."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from lakecube.cli.main import cli
from lakecube.importers.outline import import_outline
from lakecube.spec import Cube

FIXTURE = Path(__file__).parent / "fixtures" / "Sample.Basic.xml"


def test_fixture_exists() -> None:
    assert FIXTURE.exists(), f"missing test fixture: {FIXTURE}"


def test_import_returns_cube_and_warnings() -> None:
    result = import_outline(FIXTURE)
    assert isinstance(result.cube, Cube)
    assert isinstance(result.warnings, list)


def test_cube_name_slugified_from_app() -> None:
    result = import_outline(FIXTURE)
    assert result.cube.name == "sample"


def test_explicit_cube_name_override() -> None:
    result = import_outline(FIXTURE, cube_name="SAMPLE BASIC")
    assert result.cube.name == "sample_basic"


def test_all_dimensions_imported() -> None:
    result = import_outline(FIXTURE)
    names = {d.name for d in result.cube.dimensions}
    assert names == {"year", "measures", "product", "market", "scenario", "caffeinated"}


def test_accounts_dim_typed_as_measures() -> None:
    result = import_outline(FIXTURE)
    meas_dim = next(d for d in result.cube.dimensions if d.name == "measures")
    assert meas_dim.is_measures


def test_time_dim_typed_as_time() -> None:
    result = import_outline(FIXTURE)
    year = next(d for d in result.cube.dimensions if d.name == "year")
    assert year.type == "time"
    assert year.time_grain == "month"


def test_attribute_dim_typed_as_attribute() -> None:
    result = import_outline(FIXTURE)
    attr = next(d for d in result.cube.dimensions if d.name == "caffeinated")
    assert attr.type == "attribute"


def test_member_hierarchy_preserved() -> None:
    result = import_outline(FIXTURE)
    year = next(d for d in result.cube.dimensions if d.name == "year")
    top = year.hierarchies[0].members
    assert len(top) == 1 and top[0].name == "Year"
    quarters = top[0].children
    assert [q.name for q in quarters] == ["Qtr1", "Qtr2", "Qtr3", "Qtr4"]
    assert [m.name for m in quarters[0].children] == ["Jan", "Feb", "Mar"]


def test_consolidation_operators_preserved() -> None:
    result = import_outline(FIXTURE)
    meas = next(d for d in result.cube.dimensions if d.name == "measures")
    profit = meas.hierarchies[0].members[0]
    assert profit.name == "Profit"
    assert profit.consolidation == "+"
    total_expenses = next(c for c in profit.children if c.name == "Total Expenses")
    assert total_expenses.consolidation == "-"


def test_storage_types_mapped() -> None:
    result = import_outline(FIXTURE)
    meas = next(d for d in result.cube.dimensions if d.name == "measures")
    profit = meas.hierarchies[0].members[0]
    assert profit.storage == "dynamic"
    margin = profit.children[0]
    sales = margin.children[0]
    assert sales.storage == "stored"


def test_formulas_extracted() -> None:
    result = import_outline(FIXTURE)
    meas = next(d for d in result.cube.dimensions if d.name == "measures")
    profit = meas.hierarchies[0].members[0]
    assert profit.formula and "Margin" in profit.formula
    assert any(w.category == "formula" for w in result.warnings)


def test_aliases_extracted_for_default_table() -> None:
    result = import_outline(FIXTURE)
    product = next(d for d in result.cube.dimensions if d.name == "product")
    top = product.hierarchies[0].members[0]
    colas = next(c for c in top.children if c.name == "100")
    assert colas.alias == "Colas"


def test_udas_captured() -> None:
    result = import_outline(FIXTURE)
    meas = next(d for d in result.cube.dimensions if d.name == "measures")
    profit = meas.hierarchies[0].members[0]
    margin = profit.children[0]
    sales = margin.children[0]
    assert "Revenue" in sales.udas


def test_attribute_association_captured() -> None:
    result = import_outline(FIXTURE)
    product = next(d for d in result.cube.dimensions if d.name == "product")
    top = product.hierarchies[0].members[0]
    colas = next(c for c in top.children if c.name == "100")
    assert colas.attributes.get("Caffeinated") == "Caffeinated_True"


def test_measures_lifted_from_accounts_dim() -> None:
    result = import_outline(FIXTURE)
    names = {m.name for m in result.cube.measures}
    # Stored leaves and formula members both show up as measures.
    assert "Sales" in names
    assert "COGS" in names
    assert "Margin" in names   # formula
    assert "Profit" in names   # formula
    assert "Marketing" in names


def test_formula_measures_keep_formula() -> None:
    result = import_outline(FIXTURE)
    margin = next(m for m in result.cube.measures if m.name == "Margin")
    assert margin.aggregation == "formula"
    assert margin.formula and "Sales" in margin.formula


def test_stored_leaf_becomes_sum_measure() -> None:
    result = import_outline(FIXTURE)
    sales = next(m for m in result.cube.measures if m.name == "Sales")
    assert sales.aggregation == "sum"
    assert sales.source == "sales_amt"


def test_fact_placeholder_generated() -> None:
    result = import_outline(FIXTURE)
    assert result.cube.fact.table.endswith("_facts")
    for dim in result.cube.dimensions:
        if not dim.is_measures:
            assert dim.name in result.cube.fact.dimension_keys


def test_cube_compiles_after_import() -> None:
    """Imported cube must pass through the compiler without errors."""
    from lakecube.compiler.compile import compile_cube

    result = import_outline(FIXTURE)
    plan = compile_cube(result.cube)
    assert plan.artifacts
    kinds = {a.kind for a in plan.artifacts}
    assert "metric_view" in kinds
    assert "lakeflow" in kinds


def test_rejects_non_essbase_root() -> None:
    xml = "<?xml version='1.0'?><root/>"
    path = Path("tests/fixtures/_bad.xml")
    path.write_text(xml)
    try:
        with pytest.raises(ValueError, match="unexpected root element"):
            import_outline(path)
    finally:
        path.unlink()


def test_cli_import_outline_writes_yaml(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "cube.yaml"
    result = runner.invoke(
        cli, ["import", "outline", str(FIXTURE), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    loaded = yaml.safe_load(out.read_text())
    assert loaded["name"] == "sample"
    # Round-trip: the written YAML should itself be a valid Cube.
    Cube.model_validate(loaded)
