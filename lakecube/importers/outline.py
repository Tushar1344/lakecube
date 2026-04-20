"""Essbase outline XML → Lakecube Cube importer.

Handles the format produced by Essbase's MaxL `export outline ... to xml_file`
command across 11.1.2.x, 19.3, and 21c. Schema reference:

  https://docs.oracle.com/en/database/other-databases/essbase/21/esssr/export-outline.html

Supported mappings (Essbase → Lakecube):

  <application name="X">                     → Cube.name (slugified)
  <AliasTableList>                           → collected; first table annotated
                                               on Dimension.aliases
  <Dimension name="..." type="...">          → Cube.dimensions[]
    type="accounts"                          → Cube.dimension.type = "measures"
    type="time" + isTimeGeneration           → Cube.dimension.type = "time"
    type="attribute"                         → Cube.dimension.type = "attribute"
  <Member name="..." consoltype="+"          → Member nested tree with
         datastorage="..." solveOrder="...">    consolidation, storage, solve_order
    <Formula><![CDATA[...]]></Formula>       → Member.formula
    <Alias table="X" value="Y"/>             → Member.alias (Default table only
                                               here; others retained on the
                                               dimension)
    <UDA value="..."/>                       → Member.udas[]
    <Attribute dimension="X" value="Y"/>     → Member.attributes[X] = Y

The accounts/measures dimension's leaf members are ALSO lifted into
Cube.measures — dense-stored leaves become aggregation="sum" measures,
members with <Formula> become aggregation="formula" measures with the
Essbase formula preserved verbatim (marked TODO for calc transpiler).

Out of scope (per Oracle docs, these live outside the outline export):
  - Security filters        — separate MaxL command
  - Substitution variables  — application-level config
  - Partitions              — version-dependent, often separate export
  - Data / cell values      — data export, not outline

No external deps — uses stdlib xml.etree.ElementTree.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from lakecube.spec import Cube, Dimension, Fact, Hierarchy, Measure, Member

# Essbase datastorage values → Lakecube Member.storage
_STORAGE_MAP = {
    "storeData": "stored",
    "dynamic": "dynamic",
    "dynamicCalc": "dynamic",
    "dynamicStore": "dynamic-stored",
    "dynamicCalcAndStore": "dynamic-stored",
    "labelOnly": "label-only",
    "neverShare": "never-share",
    "shared": "shared",
    # Abbreviations sometimes seen in older exports:
    "X": "dynamic",
    "V": "dynamic-stored",
    "O": "label-only",
}

# Essbase dimension type → Lakecube Dimension.type
_DIM_TYPE_MAP = {
    "standard": "standard",
    "accounts": "measures",
    "time": "time",
    "attribute": "attribute",
    "country": "standard",
    "currency": "standard",
}


@dataclass
class ImportWarning:
    """Something the importer couldn't fully translate — user sees these after run."""

    category: str   # "formula" | "attribute" | "security" | "unknown_type" | ...
    detail: str


@dataclass
class ImportResult:
    cube: Cube
    warnings: list[ImportWarning]


def _slugify(name: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return out or "cube"


def _parse_member(
    mbr_el: ET.Element,
    warnings: list[ImportWarning],
    default_alias_table: str | None,
) -> Member:
    name = mbr_el.get("name") or mbr_el.get("mbrName") or ""
    consolidation = mbr_el.get("consoltype", "+")
    storage_raw = mbr_el.get("datastorage") or ""
    storage = _STORAGE_MAP.get(storage_raw)

    # Formula: either attribute or <Formula> child (CDATA).
    formula = None
    formula_el = mbr_el.find("Formula")
    if formula_el is not None and formula_el.text:
        formula = formula_el.text.strip()
        if formula:
            warnings.append(
                ImportWarning(
                    "formula",
                    f"Member {name!r}: Essbase formula preserved verbatim; "
                    "run calc transpiler (P2) or rewrite to SQL.",
                )
            )

    # Default alias — only take the one for the outline's active alias table
    # (or the first available); others can be reconstructed from the dimension.
    alias = None
    for alias_el in mbr_el.findall("Alias"):
        table = alias_el.get("table")
        value = alias_el.get("value")
        if value and (table == default_alias_table or alias is None):
            alias = value
            if table == default_alias_table:
                break

    # UDAs
    udas = [
        u.get("value") for u in mbr_el.findall("UDA") if u.get("value") is not None
    ]

    # Attribute-dim associations
    attributes: dict[str, str] = {}
    for attr_el in mbr_el.findall("Attribute"):
        dim = attr_el.get("dimension")
        val = attr_el.get("value")
        if dim and val:
            attributes[dim] = val

    # Recurse for children
    children = [
        _parse_member(child, warnings, default_alias_table)
        for child in mbr_el.findall("Member")
    ]

    return Member(
        name=name,
        alias=alias,
        consolidation=consolidation,
        storage=storage,
        formula=formula,
        udas=udas,  # type: ignore[arg-type]
        attributes=attributes,
        children=children,
    )


def _parse_dimension(
    dim_el: ET.Element,
    warnings: list[ImportWarning],
    default_alias_table: str | None,
) -> Dimension:
    name = dim_el.get("name") or "unnamed"
    essbase_type = (dim_el.get("type") or "standard").lower()
    lc_type = _DIM_TYPE_MAP.get(essbase_type, "standard")
    if essbase_type not in _DIM_TYPE_MAP:
        warnings.append(
            ImportWarning(
                "unknown_type",
                f"Dimension {name!r} has Essbase type={essbase_type!r}; "
                "mapped to 'standard'.",
            )
        )

    # Time grain heuristic: if time dimension, infer from member names
    time_grain = None
    if lc_type == "time":
        time_grain = "month"  # Sample.Basic and most Essbase time dims are monthly

    # Each immediate <Member> under <Dimension> is a top-level root of the tree.
    top_members = [
        _parse_member(m, warnings, default_alias_table)
        for m in dim_el.findall("Member")
    ]

    hierarchy = Hierarchy(name="default", default=True, members=top_members)

    return Dimension(
        name=_slugify(name),
        type=lc_type,
        hierarchies=[hierarchy],
        time_grain=time_grain,
    )


def _flatten_leaves(member: Member) -> list[Member]:
    """Return leaves (+ formula-bearing nodes) under a member subtree."""
    if not member.children:
        return [member]
    out: list[Member] = []
    for c in member.children:
        out.extend(_flatten_leaves(c))
    # Include formula-bearing intermediate nodes too — they're real measures.
    if member.formula:
        out.append(member)
    return out


def _derive_measures(measures_dim: Dimension, warnings: list[ImportWarning]) -> list[Measure]:
    """Lift accounts-dim leaves + formula members into Cube.measures."""
    measures: list[Measure] = []
    seen: set[str] = set()
    for h in measures_dim.hierarchies:
        for root in h.members:
            for leaf in _flatten_leaves(root):
                if leaf.name in seen or leaf.storage == "label-only":
                    continue
                seen.add(leaf.name)
                if leaf.formula:
                    measures.append(
                        Measure(
                            name=leaf.name,
                            aggregation="formula",
                            formula=leaf.formula,
                            solve_order=0,
                        )
                    )
                else:
                    measures.append(
                        Measure(
                            name=leaf.name,
                            aggregation="sum",
                            source=f"{_slugify(leaf.name)}_amt",
                        )
                    )
    if not measures:
        warnings.append(
            ImportWarning(
                "measures",
                "No measures derived from accounts dimension — check storage types.",
            )
        )
    return measures


def _active_alias_table(root: ET.Element) -> str | None:
    for tbl in root.findall(".//AliasTable"):
        if tbl.get("isActive", "").lower() == "true":
            return tbl.get("name")
    first = root.find(".//AliasTable")
    return first.get("name") if first is not None else None


def import_outline(
    otl_path: str | Path,
    cube_name: str | None = None,
) -> ImportResult:
    """Parse an Essbase outline XML and return a Lakecube Cube + warnings."""
    tree = ET.parse(otl_path)
    root = tree.getroot()
    if root.tag.lower() not in {"application", "outline"}:
        raise ValueError(
            f"unexpected root element <{root.tag}> — "
            "expected <application> from Essbase export"
        )
    app_name = root.get("name") or "imported_cube"
    name = cube_name or _slugify(app_name)

    warnings: list[ImportWarning] = []
    default_alias = _active_alias_table(root)

    dimensions = [
        _parse_dimension(d, warnings, default_alias)
        for d in root.findall("Dimension")
    ]

    # Measures: derived from the first measures-typed dimension, if any.
    measures_dim = next((d for d in dimensions if d.is_measures), None)
    measures = _derive_measures(measures_dim, warnings) if measures_dim else []

    fact_keys = {d.name: f"{d.name}_key" for d in dimensions if not d.is_measures}
    fact = Fact(
        table=f"main.lakecube_imports.{name}_facts",
        dimension_keys=fact_keys,
    )

    cube = Cube(
        name=name,
        description=f"Imported from Essbase outline application={app_name!r}",
        fact=fact,
        dimensions=dimensions,
        measures=measures,
    )

    if root.find(".//SecurityFilter") is not None:
        warnings.append(
            ImportWarning(
                "security",
                "Security filters are not included in Essbase outline exports; "
                "run the separate security export and author cube.security manually.",
            )
        )

    return ImportResult(cube=cube, warnings=warnings)
