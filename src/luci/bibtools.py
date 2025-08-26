import json
import re
import subprocess
import tempfile
from pathlib import Path

import typer

DUPLICATE_RE = re.compile(
    r"DUPLICATE_ENTRY: Duplicate removed\. Entry (\S+) .* entry (\S+)\."
)

# Emoji regex covering general emoji ranges
EMOJI_RE = re.compile(
    "[\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map symbols
    "\U0001f1e0-\U0001f1ff"  # flags (iOS)
    "\U00002702-\U000027b0"
    "\U000024c2-\U0001f251"
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    return EMOJI_RE.sub("", text)


def merge_bibtex_files(bibfiles: list[Path], merged_path: Path):
    """Merge multiple BibTeX files into a single file (earlier takes precedence)."""
    merged_content = ""
    for bibfile in bibfiles:
        typer.echo(f"Merging {bibfile}")
        merged_content += bibfile.read_text(encoding="utf-8") + "\n"

    # Strip emojis from merged content
    cleaned_content = strip_emojis(merged_content)

    merged_path.write_text(cleaned_content, encoding="utf-8")
    typer.echo(f"Merged and cleaned {len(bibfiles)} files into {merged_path}")


def run_bibtex_tidy_dedupe(input_bib: Path) -> tuple[str, dict[str, str]]:
    """Run bibtex-tidy to deduplicate, returning (deduplicated text, old→new mapping)."""
    cmd = [
        "bibtex-tidy",
        "--duplicates=doi,citation,key",
        "--merge=first",
        "--omit=abstract,note",
        "--remove-empty-fields",
        "--remove-dupe-fields",
        "--escape",
        "--sort-fields",
        "--strip-comments",
        "--modify",
        "--v2",
        str(input_bib),
    ]
    typer.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        typer.echo("bibtex-tidy failed:")
        typer.echo(result.stdout)
        typer.echo(result.stderr)
        raise RuntimeError("bibtex-tidy failed")

    # Parse duplicate mappings from stderr
    key_updates = {}
    for line in result.stdout.splitlines():
        if m := DUPLICATE_RE.search(line):
            old_key, new_key = m.groups()
            key_updates[old_key] = new_key

    return input_bib.read_text(), key_updates


def merge_and_dedupe(
    bibfiles: list[Path],
    output: Path = Path("merged.bib"),
    mapping: Path = Path("duplicate_keys.json"),
):
    """Merge multiple BibTeX files, deduplicate, and write output and removed key map.
    Earlier files take precedence.

    This function takes a list of BibTeX files, merges them into a single file,
    and then uses `bibtex-tidy` to deduplicate the entries. The deduplicated
    BibTeX file is written to the specified output path. A JSON file containing
    a mapping of the removed duplicate keys to the keys that were kept is also
    generated.

    Args:
        bibfiles: A list of paths to the BibTeX files to merge.
        output: The path to write the merged and deduplicated BibTeX file to.
        mapping: The path to write the JSON file with the duplicate key mappings to.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bib") as tmp:
        merged_path = Path(tmp.name)
        tmp.close()

    try:
        merge_bibtex_files(bibfiles, merged_path)

        dedup_text, key_updates = run_bibtex_tidy_dedupe(merged_path)

        output.write_text(dedup_text, encoding="utf-8")
        mapping.write_text(json.dumps(key_updates, indent=2))
        typer.echo(f"Wrote deduplicated bib to {output}")
        typer.echo(f"Wrote deduplication key map to {mapping}")

    finally:
        merged_path.unlink()  # Clean up temporary file


def update_citation(duplicate_keys: Path, files: list[Path]):
    """
    Update citations in LaTeX files based on duplicate key mappings from a JSON file.
    """
    key_updates = json.loads(duplicate_keys.read_text())
    cite_pattern = re.compile(r"(\\cite\w*\{([^}]+)\})")

    def replace_cite_keys(match):
        cite_command = match.group(1)
        keys_str = match.group(2)
        keys = [k.strip() for k in keys_str.split(",")]
        updated_keys = [
            key_updates.get(k, k) for k in keys if key_updates.get(k, k) is not None
        ]
        return f"{cite_command.split('{')[0]}{{{','.join(updated_keys)}}}"

    for file in files:
        with open(file, "r") as f:
            updated = []
            for line in f:
                updated.append(cite_pattern.sub(replace_cite_keys, line))

        with open(file, "w") as f:
            f.writelines(updated)
