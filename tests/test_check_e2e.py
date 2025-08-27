import json
import shutil
import subprocess
from pathlib import Path

import pytest
from luci.cli import cli

from .utils import write


def _tectonic_available() -> bool:
    return shutil.which("tectonic") is not None


@pytest.mark.skipif(not _tectonic_available(), reason="tectonic not installed")
def test_e2e_undefined_citation_detected(tmp_path: Path, cli_runner):
    # Minimal doc that compiles but has an undefined citation
    write(
        tmp_path / "main.tex",
        r"""
        \documentclass{article}
        \begin{document}
        See \cite{missingkey}.
        \end{document}
        """,
    )

    # Build with tectonic to produce a real .log
    res = subprocess.run(
        ["tectonic", "--keep-logs", "main.tex"], cwd=tmp_path, capture_output=True
    )
    if not (tmp_path / "main.log").exists():
        pytest.skip(
            f"tectonic failed to produce a log: {res.stderr.decode().strip()[:120]}"
        )

    out = cli_runner.invoke(cli, ["check", str(tmp_path / "main.log"), "--json"])
    assert out.exit_code == 0, out.stdout
    payload = json.loads(out.stdout)
    assert any(i["kind"] == "Undefined citation" for i in payload["issues"])
    # Strict treats warnings as errors
    out_strict = cli_runner.invoke(
        cli, ["check", str(tmp_path / "main.log"), "--json", "--strict"]
    )
    assert out_strict.exit_code == 1, out_strict.stdout


@pytest.mark.skipif(not _tectonic_available(), reason="tectonic not installed")
def test_e2e_undefined_reference_detected(tmp_path: Path, cli_runner):
    write(
        tmp_path / "main.tex",
        r"""
        \documentclass{article}
        \begin{document}
        See Section~\ref{does-not-exist}.
        \end{document}
        """,
    )
    res = subprocess.run(
        ["tectonic", "--keep-logs", "main.tex"], cwd=tmp_path, capture_output=True
    )
    if not (tmp_path / "main.log").exists():
        pytest.skip(
            f"tectonic failed to produce a log: {res.stderr.decode().strip()[:120]}"
        )

    out = cli_runner.invoke(cli, ["check", str(tmp_path / "main.log"), "--json"])
    assert out.exit_code == 0, out.stdout
    payload = json.loads(out.stdout)
    assert any(i["kind"] == "Undefined reference" for i in payload["issues"])


@pytest.mark.skipif(not _tectonic_available(), reason="tectonic not installed")
def test_e2e_missing_file_detected(tmp_path: Path, cli_runner):
    write(
        tmp_path / "main.tex",
        r"""
        \documentclass{article}
        \begin{document}
        \input{nope/missing}
        \end{document}
        """,
    )
    res = subprocess.run(
        ["tectonic", "--keep-logs", "main.tex"], cwd=tmp_path, capture_output=True
    )
    # Build is expected to fail; but if tectonic itself fails on this env, skip
    if not (tmp_path / "main.log").exists():
        pytest.skip(
            f"tectonic failed to produce a log: {res.stderr.decode().strip()[:120]}"
        )

    out = cli_runner.invoke(cli, ["check", str(tmp_path / "main.log"), "--json"])
    payload = json.loads(out.stdout)
    kinds = {i["kind"] for i in payload["issues"]}
    assert "Missing file" in kinds


def test_unit_biblatex_split_warning_detected(tmp_path: Path, cli_runner):
    # Replicate biblatex split-line form seen in some logs
    log = tmp_path / "example.log"
    write(
        log,
        "\n".join(
            [
                "(./main.tex)",
                "(biblatex)                mosesReversemodeAutomaticDifferentiation2021",
                "although it is yet undefined on input line 42.",
            ]
        ),
    )
    res = cli_runner.invoke(cli, ["check", str(log), "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert any(
        i["kind"] == "Undefined citation"
        and i["message"] == "mosesReversemodeAutomaticDifferentiation2021"
        for i in payload["issues"]
    )
