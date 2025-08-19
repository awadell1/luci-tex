import json
from pathlib import Path

import pytest
from luci import bibtools as bib
from luci.cli import cli

from tests.utils import write


def test_merge_bibs_cli_monkeypatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cli_runner
):
    # Prepare two simple bib files
    b1 = tmp_path / "a.bib"
    b2 = tmp_path / "b.bib"
    write(b1, "@article{k1, title={One}}\n")
    write(b2, "@article{k2, title={Two}}\n")

    # Monkeypatch the dedupe step so we don't require bibtex-tidy on CI
    def fake_run_dedupe(p: Path):
        merged = b1.read_text() + b2.read_text()
        return merged, {"k2": "k1"}

    monkeypatch.setattr(bib, "run_bibtex_tidy_dedupe", fake_run_dedupe)

    out = tmp_path / "merged.bib"
    map_json = tmp_path / "map.json"

    res = cli_runner.invoke(
        cli,
        [
            "merge-bibs",
            str(b1),
            str(b2),
            "--output",
            str(out),
            "--mapping",
            str(map_json),
        ],
    )
    assert res.exit_code == 0, res.stdout
    assert out.exists() and map_json.exists()
    # Mapping should reflect our fake dedupe
    assert json.loads(map_json.read_text()) == {"k2": "k1"}
