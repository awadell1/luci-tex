import json
from pathlib import Path

from luci.cli import cli
from tests.utils import write


def test_check_parses_log_and_json_output(tmp_path: Path, cli_runner):
    # Create a synthetic log with an undefined citation and an overfull box
    log = tmp_path / "example.log"
    write(
        log,
        "\n".join(
            [
                "(./main.tex)",
                "LaTeX Warning: Citation `foo' on page 3 undefined on input line 12.",
                "Overfull \\hbox (15.0pt too wide) in paragraph at lines 100--101".replace("\\\\", "\\"),
                "[ 3 ]",
            ]
        ),
    )

    res = cli_runner.invoke(cli, ["check", str(log), "--json"])
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    kinds = {i["kind"] for i in payload["issues"]}
    assert "Undefined citation" in kinds
    assert any("Overfull hbox" == i["kind"] for i in payload["issues"])
