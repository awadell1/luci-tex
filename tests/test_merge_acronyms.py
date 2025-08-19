from pathlib import Path

from luci.cli import cli

from tests.utils import write


def test_merge_acronyms_cli(tmp_path: Path, cli_runner):
    f1 = tmp_path / "a.tex"
    f2 = tmp_path / "b.tex"
    write(
        f1,
        r"""
        % comment
        \acro{NLP}{Natural Language Processing}
        \acrodef{ML}[ML]{Machine Learning}
        """,
    )
    write(
        f2,
        r"""
        \acro{NLP}{Natural Language Processing}
        \acro{AI}{Artificial Intelligence}
        """,
    )

    out = tmp_path / "acros.tex"
    res = cli_runner.invoke(
        cli,
        [
            "merge-acronyms",
            str(f1),
            str(f2),
            "--output",
            str(out),
        ],
    )
    assert res.exit_code == 0, res.stdout
    text = out.read_text()
    # NLP had no explicit short form, so output omits [short]
    assert "\\acro{NLP}{Natural Language Processing}" in text
    assert "\\acro{AI}{Artificial Intelligence}" in text
