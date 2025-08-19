import zipfile
from pathlib import Path

from luci.cli import cli
import pytest


def test_archive_builds_zip_without_validation(latex_project, tmp_path: Path, cli_runner, monkeypatch: pytest.MonkeyPatch):
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
