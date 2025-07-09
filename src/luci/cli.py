import typer

from .archive import archive
from .bibtools import merge_and_dedupe, update_citation

cli = typer.Typer()

cli.command("merge-bibs")(merge_and_dedupe)
cli.command("fix-dups")(update_citation)
cli.command()(archive)
