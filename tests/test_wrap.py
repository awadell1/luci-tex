from pathlib import Path
from unittest.mock import Mock

import pyperclip
import pytest
from typer.testing import CliRunner

from luci.cli import cli


@pytest.mark.parametrize(
    "clip, save", [(False, False), (True, False), (False, True), (True, True)]
)
def test_wrap_destinations(
    cli_runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    clip: bool,
    save: bool,
) -> None:
    source = tmp_path / "abstract.tex"
    source.write_bytes("  A\t\\textbf{café}\r\n\r\n  costs  5\\%.\n".encode())
    expected = r"A \textbf{café} costs 5\%."
    dest = tmp_path / "abstract.txt"
    copy = Mock()
    monkeypatch.setattr(pyperclip, "copy", copy)

    args = ["wrap", str(source)]
    if clip:
        args.append("--clip")
    if save:
        args.extend(["--output", str(dest)])
    result = cli_runner.invoke(cli, args)

    assert result.exit_code == 0, result.output
    assert result.stdout == ("" if clip or save else expected + "\n")
    if clip:
        copy.assert_called_once_with(expected)
    else:
        copy.assert_not_called()
    if save:
        assert dest.read_text(encoding="utf-8") == expected + "\n"


def test_wrap_blank(cli_runner: CliRunner, tmp_path: Path) -> None:
    source = tmp_path / "blank.tex"
    source.write_text(" \n\t", encoding="utf-8")
    result = cli_runner.invoke(cli, ["wrap", str(source)])
    assert result.exit_code == 0
    assert result.stdout == "\n"


def test_wrap_missing_input(cli_runner: CliRunner, tmp_path: Path) -> None:
    dest = tmp_path / "out.txt"
    result = cli_runner.invoke(
        cli, ["wrap", str(tmp_path / "missing.tex"), "--output", str(dest)]
    )
    assert result.exit_code != 0
    assert not dest.exists()
