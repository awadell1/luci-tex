import zipfile
from pathlib import Path

import pytest
from luci.cli import cli


def test_replace_citeauthor_commands(
    tmp_path: Path, cli_runner, monkeypatch: pytest.MonkeyPatch
):
    # Prepare a minimal project with a bib file and citeauthor usages
    monkeypatch.chdir(tmp_path)

    bib = tmp_path / "refs.bib"
    bib.write_text(
        r"""
@article{foo,
  author = {Doe, John},
  title = {X},
  year = {2020}
}

@inproceedings{bar,
  author = {Smith, Alice and Doe, John and Roe, Jane},
  title = {Y},
  year = {2021}
}

@book{two,
  author = {Alpha, Ann and Beta, Bob},
  title = {Z},
  year = {2022}
}
        """,
        encoding="utf-8",
    )

    main = tmp_path / "main.tex"
    main.write_text(
        r"""
        \documentclass{article}
        % Define citeauthorcite macro that should be removed by archive pass
        \newcommand{\citeauthorcite}[1]{\citeauthor{#1}\cite{#1}}
        \addbibresource{refs.bib}
        \begin{document}
        A \citeauthor{foo} view. Also, \citeauthorcite{bar}.
        And a pair: \citeauthor{two}.
        \end{document}
        """,
        encoding="utf-8",
    )

    outzip = tmp_path / "main.zip"
    res = cli_runner.invoke(
        cli, ["archive", str(main), "--output", str(outzip), "--no-validate"]
    )
    assert res.exit_code == 0, res.stdout
    assert outzip.exists()

    with zipfile.ZipFile(outzip) as zf:
        data = zf.read("main.tex").decode("utf-8")

    # Single author -> last name only
    assert "Doe view" in data
    # Three authors -> First last name + et al. and cite preserved
    assert "Smith et al.\\cite{bar}" in data
    # Two authors -> joined with ' and '
    assert "pair: Alpha and Beta" in data
    # Ensure macros are gone
    assert "\\citeauthor{" not in data
    assert "\\citeauthorcite{" not in data
    # Macro definition should be stripped out
    assert "\\newcommand{\\citeauthorcite}[1]{\\citeauthor{#1}\\cite{#1}}" not in data
