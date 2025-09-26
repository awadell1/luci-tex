import logging
import re
import sys
import zipfile
from collections.abc import Callable, Iterable
from enum import Enum
from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile, TemporaryDirectory

from .bibparse import parse_bibliographies
from .check import scan_logs

DEFAULT_COMMANDS = [
    "documentclass",
    "includegraphics",
    "addbibresource",
    "bibliography",
    "RequirePackage",
    "usepackage",
    "InputIfFileExists",
    "templatetype",
]


def strip_paths_from_command(
    latex_text: str, command: str
) -> tuple[str, dict[str, Path]]:
    r"""
    Replaces \command{path/to/file} with \command{file} using pathlib,
    and returns a list of (original path, updated line) replacements.

    Args:
        latex_text: The LaTeX document as a string.
        command: The command name without backslash, e.g., 'includegraphics'.

    Returns:
        A tuple:
            - Updated LaTeX text with paths stripped
            - List of (original path, updated line) for each replacement
    """
    pattern = re.compile(r"(\\" + command + r".*)\{([^}]+)}")
    replacements: dict[str, Path] = {}

    def replacer(match):
        prefix = match.group(1)
        arg = match.group(2).strip()
        # If the argument contains a macro, try to include matching local files
        # but don't modify the LaTeX content.
        if "\\" in arg:
            macro_path = Path(arg)
            parent = macro_path.parent
            name_part = macro_path.name
            static_prefix = name_part.split("\\", 1)[0]
            static_suffix = Path(name_part).suffix
            if static_prefix:
                for c in parent.glob(static_prefix + "*" + static_suffix):
                    replacements[c.name] = c
            return match.group(0)

        full_path = Path(arg)
        filename = full_path.name
        updated = prefix + "{" + filename + "}"
        if not full_path.exists() and full_path.suffix == "":
            canidates = list(full_path.parent.glob(filename + ".*"))
            if len(canidates) == 1:
                full_path = canidates[0]
            elif len(canidates) == 0:
                logging.debug("No matches for %s", full_path)
                return match.group(0)
            else:
                # Prefer an extension based on the command
                pref_exts: dict[str, list[str]] = {
                    "documentclass": [".cls"],
                    "addbibresource": [".bib"],
                    "bibliography": [".bib"],
                    "RequirePackage": [".sty"],
                    "usepackage": [".sty"],
                    "templatetype": [".sty"],
                    "InputIfFileExists": [".ldf", ".tex", ".sty"],
                    "includegraphics": [
                        ".pdf",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".eps",
                    ],
                }
                exts = pref_exts.get(command, [])
                chosen = None
                for ext in exts:
                    for c in canidates:
                        if c.suffix.lower() == ext:
                            chosen = c
                            break
                    if chosen is not None:
                        break
                if chosen is not None:
                    full_path = chosen
                else:
                    # Fall back to first candidate deterministically
                    full_path = sorted(canidates)[0]

        replacements[full_path.name] = full_path
        return updated

    updated_text = pattern.sub(replacer, latex_text)
    return updated_text, replacements


def flatten_latex(
    file_path: Path,
    commands_to_flatten=DEFAULT_COMMANDS,
    root: Path | None = None,
    scratch=None,
):
    r"""
    Recursively flattens a LaTeX file by replacing \input and \include with actual content.
    Returns the flattened LaTeX as a string.
    """
    scratch = scratch or TemporaryDirectory()
    scratch_dir = getattr(scratch, "name", scratch)
    tex_path = Path(file_path).resolve()
    root = root or tex_path.parent

    if not tex_path.exists():
        raise FileNotFoundError(f"File not found: {tex_path}")

    with open(tex_path, encoding="utf-8") as f:
        lines = f.readlines()

    flattened_lines = []
    dependencies: dict[str, Path] = {}
    input_pattern = re.compile(r"^(.*?)\\(input|include)\{([^}]+)\}(.*)$")
    comment_line = re.compile(r"^\s*%")

    for line in lines:
        # Skip comments entirely when searching for commands
        if comment_line.match(line):
            continue

        # Flatten commands
        for cmd in commands_to_flatten:
            line, deps = strip_paths_from_command(line, cmd)
            dependencies.update(deps)

        match = input_pattern.match(line)
        if match:
            pre, cmd, filename, post = match.groups()
            inc_path = root.joinpath(filename).with_suffix(".tex")
            included_text, deps = flatten_latex(
                inc_path,
                root=root,
                commands_to_flatten=commands_to_flatten,
                scratch=scratch,
            )
            dependencies.update(deps)
            # Preserve any prefix and postfix text on the line (e.g. macro wrappers)
            # by reconstructing the full line with the flattened include inserted.
            flattened_lines.append(pre + included_text + post + "\n")
        else:
            flattened_lines.append(line)

    # Flatten class and style files to discover nested dependencies
    nested_deps = {}
    for name, file in list(dependencies.items()):
        if file.suffix in {".cls", ".sty"}:
            text, deps = flatten_latex(file, scratch=scratch)
            fid = NamedTemporaryFile(dir=scratch_dir, delete=False)
            fid.write(text.encode("utf-8"))
            dependencies[name] = Path(fid.name)
            nested_deps.update(deps)
    dependencies.update(nested_deps)

    return "".join(flattened_lines), dependencies


def replace_citeauthor_commands(
    latex_text: str,
    bib_files: Iterable[Path],
    max_names: int = 2,
) -> str:
    """Replace \\citeauthor and \\citeauthorcite commands with author text.

    - ``\\citeauthor{foo}`` -> "<authors for foo>"
    - ``\\citeauthorcite{foo}`` -> "<authors for foo>\\cite{foo}"

    When an entry has more than ``max_names`` authors, only the first last name
    is kept followed by " et al.". Otherwise, up to ``max_names`` last names
    are joined with " and ".

    Args:
        latex_text: The flattened LaTeX text.
        bib_files: Paths to .bib files referenced by the project.
        max_names: Maximum number of last names to display before using et al.

    Returns:
        Updated LaTeX text with citeauthor macros replaced.
    """
    # Remove an inline macro definition for \citeauthorcite if present
    # Exact macro semantics: \newcommand{\citeauthorcite}[1]{\citeauthor{#1}\cite{#1}}
    macro_pat = re.compile(
        r"\\newcommand\{\\citeauthorcite\}\[1\]\{\s*\\citeauthor\{#1\}\s*\\cite\{#1\}\s*\}",
    )
    text = macro_pat.sub("", latex_text)

    # Build a key -> list[last names] map from provided bib files
    authors = parse_bibliographies(bib_files)
    # Convert to key -> display-string per max_names policy
    author_map: dict[str, str] = {}
    for key, last_names in authors.items():
        if len(last_names) > max_names:
            display = f"{last_names[0]} et al."
        else:
            display = " and ".join(last_names[:max_names])
        author_map[key] = display

    if not author_map:
        return text

    def render_authors(keys_str: str) -> str:
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        rendered: list[str] = []
        for k in keys:
            rendered.append(author_map[k])
        return ", ".join(rendered)

    def repl_citeauthor(m: re.Match) -> str:
        return render_authors(m.group(1))

    def repl_citeauthorcite(m: re.Match) -> str:
        keys_str = m.group(1)
        return f"{render_authors(keys_str)}\\cite{{{keys_str}}}"

    text = re.sub(r"\\citeauthor\{([^}]+)\}", repl_citeauthor, text)
    text = re.sub(r"\\citeauthorcite\{([^}]+)\}", repl_citeauthorcite, text)
    return text


def create_archive(archive: str, files: dict[str, Path]):
    with zipfile.ZipFile(archive, "w") as zipf:
        for dst, src in files.items():
            try:
                zipf.write(src, dst)
            except FileNotFoundError as e:
                logging.warning(
                    "%s not found and will not be added to the zip: %s", src, e
                )


def validate_archive(archive: Path, mainfile: str):
    with TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(archive, "r") as zipf:
            zipf.extractall(temp_dir)

        result = run(
            f"tectonic --keep-logs {mainfile}",
            cwd=temp_dir,
            capture_output=True,
            shell=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            logging.error("Archive valiation failed")
            print(result.stdout, file=sys.stdout)
            print(result.stderr, file=sys.stderr)
            for log_file in Path(temp_dir).glob("*.log"):
                print(f"{log_file.name}:", file=sys.stderr)
                print(log_file.read_text(), file=sys.stderr)
            raise RuntimeError("Archive valiation failed")

        scan_logs(
            [Path(temp_dir).joinpath(mainfile).with_suffix(".log")],
            overflow_threshold_pt=10,
        )


def add_bbl_file(archive: Path, main: str, deps: dict[str, Path]):
    with TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(archive, "a") as zipf:
            zipf.extractall(temp_dir)

            run(
                f"tectonic --keep-intermediates {main}",
                cwd=temp_dir,
                capture_output=True,
                shell=True,
                check=True,
            )

            # Add bbl files to archive
            for file in Path(temp_dir).glob("*.bbl"):
                zipf.write(file, file.name)


class BibStyle(Enum):
    biblatex = "biblatex"
    bibtex = "bibtex"


def archive(
    main: Path,
    output: Path | None = None,
    validate: bool = True,
    bbl: bool = False,
    bibstyle: BibStyle = BibStyle.bibtex,
):
    output = output or Path(main).with_suffix(".zip")
    with TemporaryDirectory() as scratch:
        main_text, deps = flatten_latex(main, scratch=scratch)
        # Post-process flattened text with additional passes (extensible)
        bibs = [p for n, p in deps.items() if Path(n).suffix == ".bib"]
        passes: list[Callable[[str], str]] = []
        # Replace citeauthor-like commands using available bib files
        if bibs and bibstyle == BibStyle.bibtex:
            passes.append(lambda t: replace_citeauthor_commands(t, bibs))
        for fn in passes:
            main_text = fn(main_text)
        with NamedTemporaryFile(dir=scratch) as fid:
            fid.write(main_text.encode("utf-8"))
            fid.flush()
            deps[main.name] = Path(fid.name)
            create_archive(output, deps)

    if bbl:
        add_bbl_file(output, main.name, deps)

    if validate:
        validate_archive(output, main.name)
