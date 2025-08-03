import re
import logging
from pathlib import Path

# Matches \acro{<id>}[<short>]{<long>} and \acrodef{<id>}[<short>]{<long>}
ACRODEF_PATTERN = re.compile(r"\\acro(?:def)?\{(.+?)\}(?:\[(.+?)\])?\{(.+?)\}")


def parse_acrodefs_from_file(path: Path) -> dict[str, tuple[str, str]]:
    """
    Parse \\acro and \\acrodef entries from a LaTeX file, supporting the optional
    short-name form: \\acro{id}[short]{long}.

    Args:
        path: Path to the LaTeX file.

    Returns:
        Dictionary mapping id to (short, long) where short is optional.
    """
    acros: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            for match in ACRODEF_PATTERN.finditer(line):
                id_, opt_short, long = match.groups()
                short = opt_short if opt_short is not None else id_
                if id_ in acros:
                    if acros[id_][1] != long:
                        logging.warning(
                            "Conflict in %s for %s: %s vs %s",
                            path,
                            short,
                            acros[id_],
                            long,
                        )
                else:
                    acros[id_] = (opt_short, long)
    return acros


def merge_acrodef_files(file_paths: list[Path]) -> dict[str, tuple[str, str]]:
    """
    Merge multiple LaTeX acro/acrodef files into a deduplicated dictionary.

    Args:
        file_paths: List of Path objects to LaTeX files.

    Returns:
        Dictionary of short -> long definitions.
    """
    merged: dict[str, tuple[str, str]] = {}
    for file_path in file_paths:
        file_acros = parse_acrodefs_from_file(file_path)
        for id, (short, long) in file_acros.items():
            if id in merged:
                if merged[id][1] != long:
                    logging.warning(
                        "Conflict for %s: %s vs %s", short, merged[id], long
                    )
            else:
                merged[id] = (short, long)
    return merged


def format_acrodefs(acro_map: dict[str, str], command: str) -> str:
    """
    Format acrodefs into a single string for output.

    Args:
        acro_map: Dictionary of short -> long definitions.
        command: The base command to emit, e.g. "acro" or "acrodef".

    Returns:
        Formatted string of \\<command>{...} entries.
    """
    lines = []
    for id, (short, long) in sorted(acro_map.items()):
        if short is None:
            lines.append(f"\\{command}{{{id}}}{{{long}}}")
        else:
            lines.append(f"\\{command}{{{id}}}[{short}]{{{long}}}")
    return "\n".join(lines)


def merge_acronyms(
    files: list[Path], output: Path | None = None, command: str = "acro"
):
    """Extract and merge acronyms from multiple LaTeX files into a single file."""
    merged_acros = merge_acrodef_files(files)
    merged = format_acrodefs(merged_acros, command)
    if output:
        output.write_text(merged, encoding="utf-8")
    else:
        print(merged)
