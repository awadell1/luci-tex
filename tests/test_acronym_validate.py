import json
import shutil
from pathlib import Path
from subprocess import run

import pytest
from luci.cli import cli


def _requires_tectonic():
    if shutil.which("tectonic") is None:
        pytest.skip("tectonic is required for this test")


def test_check_detects_undefined_acronym(tmp_path: Path, cli_runner):
    _requires_tectonic()

    # Minimal LaTeX document that uses an undefined acronym (EC)
    main = tmp_path / "main.tex"
    main.write_text(
        r"""
        \documentclass{article}
        \usepackage{acronym}
        \begin{document}
        Using \ac{EC} in text without definition.
        \end{document}
        """,
        encoding="utf-8",
    )

    # Build with tectonic to produce a real .log file
    try:
        res = run(
            ["tectonic", "--keep-logs", str(main.name)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("tectonic is required for this test")

    assert res.returncode == 0, res.stderr
    log_path = tmp_path / "main.log"
    assert log_path.exists(), "Expected build to emit main.log"

    # Run luci check on the produced log and assert the acronym issue is detected
    out = cli_runner.invoke(cli, ["check", str(log_path), "--json"])
    assert out.exit_code == 0, out.stdout
    payload = json.loads(out.stdout)
    kinds = {i["kind"] for i in payload["issues"]}
    assert "Undefined acronym" in kinds
    assert any(i["message"] == "EC" for i in payload["issues"])
