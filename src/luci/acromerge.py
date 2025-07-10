import re
import logging
from pathlib import Path

ACRODEF_PATTERN = re.compile(r"\\acro(?:def)?\{(.+?)\}\{(.+?)\}")


def parse_acrodefs_from_file(path: Path) -> dict[str, str]:
    """
    Parse \\acrodef entries from a LaTeX file using regex.

    Args:
        path: Path to the LaTeX file.

    Returns:
        Dictionary mapping short form to long form.
    """
    acros = {}
    with path.open() as f:
        for line in f:
            match = ACRODEF_PATTERN.search(line)
            if match:
                short, long = match.groups()
                if short in acros:
                    if acros[short] != long:
                        logging.warning(
                            "Conflict in %s for %s: %s vs %s",
                            path,
                            short,
                            acros[short],
                            long,
                        )
                else:
                    acros[short] = long
    return acros


def merge_acrodef_files(file_paths: list[Path]) -> dict[str, str]:
    """
    Merge multiple LaTeX acrodef files into a deduplicated dictionary.

    Args:
        file_paths: List of file paths as strings.

    Returns:
        Dictionary of short -> long definitions.
    """
    merged = {}
    for file_path in file_paths:
        file_acros = parse_acrodefs_from_file(file_path)
        for short, long in file_acros.items():
            if short in merged:
                if merged[short] != long:
                    logging.warning(
                        "Conflict for %s: %s vs %s", short, merged[short], long
                    )
            else:
                merged[short] = long
    return merged


def format_acrodefs(acro_map: dict[str, str], command: str) -> str:
    """
    Format acrodefs into a single string for output.

    Args:
        acro_map: Dictionary of short -> long definitions.

    Returns:
        Formatted string of \\acro{} entries.
    """
    lines = [
        f"\\{command}{{{short}}}{{{long}}}" for short, long in sorted(acro_map.items())
    ]
    return "\n".join(lines)


def merge_acronyms(
    files: list[Path], output: Path | None = None, command: str = "acro"
):
    """Extract and merge acronyms from multiple LaTeX files into a single file"""
    merged_acros = merge_acrodef_files(files)
    merged = format_acrodefs(merged_acros, command)
    if output:
        output.write_text(merged)
    else:
        print(merged)
