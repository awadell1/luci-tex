from pathlib import Path
from typing import NamedTuple

import pytest
from typer.testing import CliRunner


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


class LatexProject(NamedTuple):
    main: Path
    inc: Path
    img: Path
    cls: Path


@pytest.fixture()
def latex_project(tmp_path: Path) -> LatexProject:
    main = tmp_path / "main.tex"
    inc = tmp_path / "chap" / "part.tex"
    img = tmp_path / "figs" / "plot.pdf"
    cls = tmp_path / "vendor" / "foo.cls"

    write(inc, "Included.")
    write(img, "PDF")
    write(cls, "\\ProvidesClass{foo}")
    write(
        main,
        r"""
        \documentclass{vendor/foo}
        \begin{document}
        Hello \input{chap/part}
        \includegraphics{figs/plot}
        \end{document}
        """,
    )

    return LatexProject(main=main, inc=inc, img=img, cls=cls)
