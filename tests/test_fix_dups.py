import json
from pathlib import Path

from luci.cli import cli
from tests.utils import write


def test_fix_dups_updates_citations(tmp_path: Path, cli_runner):
    # Create mapping and a tex file with cites
    mapping = tmp_path / "dups.json"
    mapping.write_text(json.dumps({"k2": "k1", "k3": None}), encoding="utf-8")
    tex = tmp_path / "main.tex"
    write(
        tex,
        r"""
        Some text \cite{alpha, k2} more text.
        Another \citet{beta,k3} line.
        """,
    )

    res = cli_runner.invoke(cli, ["fix-dups", str(mapping), str(tex)])
    assert res.exit_code == 0, res.stdout

    updated = tex.read_text()
    # k2 is remapped to k1, k3=None is dropped (no spaces preserved)
    assert "\\cite{alpha,k1}" in updated
    assert "k3" not in updated
