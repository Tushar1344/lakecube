"""`lakecube` CLI entry point.

Subcommands map to verbs an Essbase admin recognizes (compile/deploy/scenario/
calc) plus migration tooling (import outline/calc/rules/maxl).
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from lakecube import __version__
from lakecube.compiler.compile import compile_cube, load_spec, write_plan

console = Console()


@click.group()
@click.version_option(__version__, prog_name="lakecube")
def cli() -> None:
    """Lakecube — a thin cube contract over Databricks."""


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False),
    default="build",
    help="Directory to write emitted artifacts into.",
)
@click.option("--show", is_flag=True, help="Print each artifact's content after writing.")
def compile(spec_path: str, out_dir: str, show: bool) -> None:
    """Validate a spec and emit deployable artifacts into `out/`."""
    cube = load_spec(spec_path)
    plan = compile_cube(cube)
    written = write_plan(plan, Path(out_dir) / cube.name)

    console.print(f"[green]OK[/green] {cube.name} v{cube.version} — {len(written)} artifacts")
    table = Table(show_header=True, header_style="bold")
    table.add_column("kind")
    table.add_column("path")
    table.add_column("bytes", justify="right")
    for art, path in zip(plan.artifacts, written, strict=True):
        table.add_row(art.kind, str(path), str(len(art.content)))
    console.print(table)

    if show:
        for art in plan.artifacts:
            console.rule(f"[cyan]{art.path}[/cyan]")
            console.print(art.content)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
@click.option("--catalog", required=True, help="Target UC catalog.")
@click.option("--schema", default="lakecube", help="Target UC schema.")
def deploy(spec_path: str, catalog: str, schema: str) -> None:
    """Compile and apply the emission plan to Databricks. TODO(P0): SDK apply."""
    _ = load_spec(spec_path)
    console.print(f"[yellow]deploy not implemented yet[/yellow] — target {catalog}.{schema}")


@cli.command(name="diff")
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False), default="cube.yaml")
def diff_cmd(spec_path: str) -> None:
    """Show what a deploy would change. TODO(P0)."""
    _ = load_spec(spec_path)
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
