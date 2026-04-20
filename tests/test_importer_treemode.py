"""Tests for tree-mode Essbase outline imports.

Tree mode (`export outline ... tree to xml_file`) strips member attributes:
no consoltype, datastorage, aliases, UDAs, or formulas. Attribute dimensions
appear as plain <Dimension> at the app level and are linked via
<AttributeDimension nameRef> references inside the base dimension.

These tests exercise that code path against a handwritten fixture modeled
on Oracle's real tree-mode output.
"""

from __future__ import annotations

from pathlib import Path

from lakecube.compiler.compile import compile_cube
from lakecube.importers.outline import import_outline
from lakecube.spec import Cube

FIXTURE = Path(__file__).parent / "fixtures" / "Sample.Basic.treemode.xml"


def test_fixture_parses() -> None:
    result = import_outline(FIXTURE)
    assert isinstance(result.cube, Cube)


def test_all_dimensions_imported() -> None:
    result = import_outline(FIXTURE)
    names = {d.name for d in result.cube.dimensions}
    assert names == {
        "year", "measures", "product", "market", "scenario",
        "caffeinated", "ounces", "population",
    }


def test_measures_dim_still_detected_by_name() -> None:
    """Essbase tree-mode omits type='accounts', but name='Measures' is enough."""
    result = import_outline(FIXTURE)
    meas = next(d for d in result.cube.dimensions if d.name == "measures")
    assert meas.is_measures


def test_attribute_dims_typed_via_nameRef_back_references() -> None:
    """Tree mode omits type='attribute'; we infer from <AttributeDimension nameRef>."""
    result = import_outline(FIXTURE)
    for dim_name in ("caffeinated", "ounces", "population"):
        dim = next(d for d in result.cube.dimensions if d.name == dim_name)
        assert dim.type == "attribute", f"{dim_name!r} should be attribute"


def test_base_dimensions_remain_standard_despite_attribute_links() -> None:
    result = import_outline(FIXTURE)
    product = next(d for d in result.cube.dimensions if d.name == "product")
    market = next(d for d in result.cube.dimensions if d.name == "market")
    assert product.type == "standard"
    assert market.type == "standard"


def test_sparse_members_get_default_consolidation() -> None:
    """No consoltype attribute in the XML — importer defaults to '+'."""
    result = import_outline(FIXTURE)
    year = next(d for d in result.cube.dimensions if d.name == "year")
    qtr1 = year.hierarchies[0].members[0]
    assert qtr1.name == "Qtr1"
    assert qtr1.consolidation == "+"
    assert qtr1.storage is None  # no datastorage attribute in tree-mode


def test_shared_members_preserved_under_multiple_parents() -> None:
    """'100-20' appears under '100' AND under 'Diet' — both paths kept."""
    result = import_outline(FIXTURE)
    product = next(d for d in result.cube.dimensions if d.name == "product")
    top = product.hierarchies[0].members
    names_100 = {c.name for c in next(t for t in top if t.name == "100").children}
    names_diet = {c.name for c in next(t for t in top if t.name == "Diet").children}
    assert "100-20" in names_100
    assert "100-20" in names_diet


def test_no_aliases_no_udas_no_formulas() -> None:
    """Tree-mode export strips these — empty collections on every member."""
    result = import_outline(FIXTURE)

    def walk(m, check):
        check(m)
        for c in m.children:
            walk(c, check)

    for dim in result.cube.dimensions:
        for h in dim.hierarchies:
            for top in h.members:
                walk(top, lambda m: (
                    m.alias is None
                    and not m.udas
                    and not m.attributes
                    and m.formula is None
                ))


def test_cube_compiles_with_shared_members() -> None:
    """Compile + closure emitter must dedupe rows for shared members."""
    result = import_outline(FIXTURE)
    plan = compile_cube(result.cube)
    closure = next(a for a in plan.artifacts if a.kind == "sql" and "closure" in a.path)

    rows_block = closure.content.split("VALUES\n", 1)[1].rstrip(";\n")
    rows = [r.strip().rstrip(",") for r in rows_block.splitlines()]
    assert len(rows) == len(set(rows))

    # '100-20' should be a descendant of BOTH '100' and 'Diet' at depth 1.
    assert "('product', '100', '100-20', 1)" in closure.content
    assert "('product', 'Diet', '100-20', 1)" in closure.content


def test_measures_still_lifted_without_explicit_storage() -> None:
    """Accounts-dim leaves with no datastorage should still lift as sum measures.

    Tree mode drops datastorage — we treat 'unknown storage' as 'not label-only',
    so the leaf becomes a measure.
    """
    result = import_outline(FIXTURE)
    names = {m.name for m in result.cube.measures}
    assert "Sales" in names
    assert "COGS" in names
    assert "Marketing" in names
    sales = next(m for m in result.cube.measures if m.name == "Sales")
    assert sales.aggregation == "sum"


def test_trailing_cube_and_smartlists_ignored() -> None:
    """<cube> and <smartLists> are siblings of <Dimension> inside <application>.

    Our importer uses findall('Dimension') on the root, which skips them.
    """
    result = import_outline(FIXTURE)
    assert len(result.cube.dimensions) == 8
