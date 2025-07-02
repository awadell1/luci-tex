import typer

from .archive import archive
from .bibtools import add_doi, parse_tidy_dups, update_citation

cli = typer.Typer()

cli.command("add-doi")(add_doi)
cli.command("parse-dups")(parse_tidy_dups)
cli.command("fix-dups")(update_citation)
cli.command()(archive)
