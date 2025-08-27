import typer

from .acromerge import merge_acronyms
from .archive import archive
from .bibtools import merge_and_dedupe, update_citation
from .check import check

cli = typer.Typer(
    help=(
        "Utilities for LaTeX projects: check logs, merge bibs, archive sources, "
        "and consolidate acronyms."
    )
)

cli.command("merge-bibs")(merge_and_dedupe)
cli.command("fix-dups")(update_citation)
cli.command()(archive)
cli.command()(merge_acronyms)
cli.command()(check)
