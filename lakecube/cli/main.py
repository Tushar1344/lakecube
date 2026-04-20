"""`lakecube` CLI entry point.

Subcommands map to the verbs an Essbase admin recognizes (compile/deploy/
scenario/calc) plus the migration tooling (import outline/calc/rules/maxl).

All scaffolding — real behavior lands phase by phase.
"""

from __future__ import annotations

import click
from rich.console import Console

from lakecube import __version__
from lakecube.compiler import compile_cube
from lakecube.compiler.compile import load_spec

console = Console()


@click.group()
@click.version_option(__version__, prog_name="lakecube")
def cli() -> None:
    """Lakecube — a thin cube contract over Databricks."""


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
def compile(spec_path: str) -> None:
    """Validate a spec and preview what would be deployed."""
    cube = load_spec(spec_path)
    plan = compile_cube(cube)
    console.print(f"[green]OK[/green] {cube.name} v{cube.version}")
    for label, items in [
        ("metric_views", plan.metric_views),
        ("lakeflow_pipelines", plan.lakeflow_pipelines),
        ("abac_policies", plan.abac_policies),
        ("delta_branches", plan.delta_branches),
        ("lakebase_schemas", plan.lakebase_schemas),
    ]:
        if items:
            console.print(f"  [cyan]{label}[/cyan]: {', '.join(items)}")


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
@click.option("--catalog", required=True, help="Target UC catalog.")
@click.option("--schema", default="lakecube", help="Target UC schema.")
def deploy(spec_path: str, catalog: str, schema: str) -> None:
    """Compile and apply the emission plan to Databricks.

    TODO(P0): dispatch via databricks-sdk.
    """
    console.print(f"[yellow]deploy not implemented yet[/yellow] — target {catalog}.{schema}")


@cli.command(name="diff")
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
def diff_cmd(spec_path: str) -> None:
    """Show what a deploy would change. TODO(P0)."""
    console.print("[yellow]diff not implemented yet[/yellow]")


@cli.group()
def scenario() -> None:
    """Scenario management (Delta branches)."""


@scenario.command("new")
@click.argument("name")
@click.option("--fork", default="main")
def scenario_new(name: str, fork: str) -> None:
    """Fork a new scenario branch. TODO(P3)."""
    console.print(f"[yellow]scenario new[/yellow] — would fork {name} from {fork}")


@scenario.command("merge")
@click.argument("name")
def scenario_merge(name: str) -> None:
    """Merge an approved scenario to main. TODO(P3)."""
    console.print(f"[yellow]scenario merge[/yellow] — would merge {name}")


@cli.group(name="import")
def import_cmd() -> None:
    """Migration tooling for legacy Essbase artifacts."""


@import_cmd.command("outline")
@click.argument("path", type=click.Path(exists=True))
def import_outline(path: str) -> None:
    """Import an Essbase .otl export into cube.yaml. TODO(P0)."""
    console.print(f"[yellow]import outline[/yellow] — would parse {path}")


@import_cmd.command("calc")
@click.argument("path", type=click.Path(exists=True))
def import_calc(path: str) -> None:
    """Transpile an Essbase .csc calc script. TODO(P2)."""
    console.print(f"[yellow]import calc[/yellow] — would transpile {path}")


@import_cmd.command("rules")
@click.argument("path", type=click.Path(exists=True))
def import_rules(path: str) -> None:
    """Convert an Essbase .rul data-load rules file. TODO(P3)."""
    console.print(f"[yellow]import rules[/yellow] — would convert {path}")


@cli.group()
def maxl() -> None:
    """MaxL compatibility layer."""


@maxl.command("run")
@click.argument("path", type=click.Path(exists=True))
def maxl_run(path: str) -> None:
    """Interpret a .mxl script against Lakecube. TODO(P2)."""
    console.print(f"[yellow]maxl run[/yellow] — would execute {path}")


@maxl.command("convert")
@click.argument("path", type=click.Path(exists=True))
def maxl_convert(path: str) -> None:
    """Translate a .mxl script to native `lakecube` CLI calls. TODO(P2)."""
    console.print(f"[yellow]maxl convert[/yellow] — would translate {path}")


if __name__ == "__main__":
    cli()
