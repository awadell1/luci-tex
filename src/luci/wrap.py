from pathlib import Path
from typing import Annotated

import pyperclip
import typer


def wrap(
    filename: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    clip: Annotated[
        bool, typer.Option("--clip", help="Copy the line to the clipboard.")
    ] = False,
    output: Annotated[
        Path | None, typer.Option(help="Write the line to this UTF-8 file.")
    ] = None,
) -> None:
    """Collapse whitespace in a TeX source file to produce a single line of text.

    By default, print the line to stdout. Use both options to copy and save it.
    """
    try:
        line = " ".join(filename.read_text(encoding="utf-8").split())
        if output is not None:
            output.write_text(line + "\n", encoding="utf-8")
        if clip:
            pyperclip.copy(line)
        if output is None and not clip:
            typer.echo(line)
    except (OSError, UnicodeError, pyperclip.PyperclipException) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
