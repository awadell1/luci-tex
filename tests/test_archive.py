import zipfile
from pathlib import Path

import pytest
from luci.cli import cli


def test_archive_builds_zip_without_validation(
    latex_project, tmp_path: Path, cli_runner, monkeypatch: pytest.MonkeyPatch
):
    # Run from the LaTeX project directory so relative asset paths resolve
    monkeypatch.chdir(tmp_path)
    outzip = tmp_path / "main.zip"
    res = cli_runner.invoke(
        cli,
        [
            "archive",
            str(latex_project.main),
            "--output",
            str(outzip),
            "--no-validate",
        ],
    )
    assert res.exit_code == 0, res.stdout
    assert outzip.exists()

    with zipfile.ZipFile(outzip) as zf:
        names = set(zf.namelist())
        # main.tex content is flattened to a temp file named main.tex in archive
        assert "main.tex" in names
        # Included assets should be added by filename
        assert "plot.pdf" in names
        assert "foo.cls" in names


def test_documentclass_prefers_cls_when_multiple_candidates(
    tmp_path: Path, cli_runner, monkeypatch: pytest.MonkeyPatch
):
    # NOTE: Additional nested dependency tests (e.g., class -> sty -> ldf) are
    # covered indirectly via end-to-end validation on the example project.

    # Create both foo.cls and foo.bst with same basename
    (tmp_path / "foo.cls").write_text("\\ProvidesClass{foo}", encoding="utf-8")
    (tmp_path / "foo.bst").write_text("ENTRY{ }{}{}\n", encoding="utf-8")

    # Main file references documentclass without extension
    main = tmp_path / "main.tex"
    main.write_text(
        r"""
        \documentclass{foo}
        \begin{document}Hi\end{document}
        """,
        encoding="utf-8",
    )

    # Run from project root
    monkeypatch.chdir(tmp_path)
    outzip = tmp_path / "main.zip"
    res = cli_runner.invoke(
        cli,
        ["archive", str(main), "--output", str(outzip), "--no-validate"],
    )
    assert res.exit_code == 0, res.stdout
    assert outzip.exists()

    # Ensure the class file is included (not a bare 'foo')
    with zipfile.ZipFile(outzip) as zf:
        names = set(zf.namelist())
        assert "foo.cls" in names
