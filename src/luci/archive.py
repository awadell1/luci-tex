import re
import zipfile
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory, NamedTemporaryFile


DEFAULT_COMMANDS = [
    "documentclass",
    "includegraphics",
    "addbibresource",
    "bibliography",
]


def strip_paths_from_command(
    latex_text: str, command: str
) -> tuple[str, dict[str, Path]]:
    """
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
        full_path = Path(match.group(2).strip())
        filename = full_path.name
        updated = prefix + "{" + filename + "}"
        if not full_path.exists() and full_path.suffix == "":
            canidates = list(full_path.parent.glob(filename + ".*"))
            if len(canidates) == 1:
                full_path = canidates[0]
            elif len(canidates) == 0:
                print("No matches for ", full_path)
                return match.group(0)

        replacements[full_path.name] = full_path
        return updated

    updated_text = pattern.sub(replacer, latex_text)
    return updated_text, replacements


def flatten_latex(
    file_path: Path,
    commands_to_flatten=DEFAULT_COMMANDS,
    scratch=TemporaryDirectory(),
):
    """
    Recursively flattens a LaTeX file by replacing \input and \include with actual content.
    Returns the flattened LaTeX as a string.
    """
    tex_path = Path(file_path).resolve()

    if not tex_path.exists():
        raise FileNotFoundError(f"File not found: {tex_path}")

    with open(tex_path, encoding="utf-8") as f:
        lines = f.readlines()

    flattened_lines = []
    dependencies: dict[str, Path] = {}
    input_pattern = re.compile(r"^(.*?)\\(input|include)\{([^}]+)\}(.*)$")

    for line in lines:
        # Skip comments entirely when searching for commands
        stripped_line = line.split("%")[0]

        # Flatten commands
        for cmd in commands_to_flatten:
            line, deps = strip_paths_from_command(line, cmd)
            dependencies.update(deps)

        match = input_pattern.match(stripped_line)
        if match:
            pre, cmd, filename, post = match.groups()
            inc_path = tex_path.parent.joinpath(filename).with_suffix(".tex")
            included_text, deps = flatten_latex(inc_path)
            dependencies.update(deps)
            flattened_lines.append(included_text)

            # Add any trailing content after the command on the same line
            if post.strip():
                flattened_lines.append(post + "\n")
        else:
            flattened_lines.append(line)

    # Flatten Class files as well
    cls_deps = {}
    for name, file in dependencies.items():
        if file.suffix == ".cls":
            text, deps = flatten_latex(file)
            fid = NamedTemporaryFile(dir=scratch, delete=False)
            fid.write(text.encode("utf-8"))
            dependencies[name] = Path(fid.name)
            cls_deps.update(deps)
    dependencies.update(cls_deps)

    return "".join(flattened_lines), dependencies


def create_archive(archive: str, files: dict[str, Path]):
    with zipfile.ZipFile(archive, "w") as zipf:
        for dst, src in files.items():
            try:
                zipf.write(src, dst)
            except FileNotFoundError as e:
                print(f"Warning: {src} not found and will not be added to the zip: {e}")


def validate_archive(archive: str, mainfile: str):
    with TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(archive, "r") as zipf:
            zipf.extractall(temp_dir)

        run(
            f"tectonic {mainfile}",
            cwd=temp_dir,
            capture_output=True,
            shell=True,
            check=True,
        )


def archive(main: str, output: str | None = None):
    output = output or str(Path(main).with_suffix(".zip"))
    with TemporaryDirectory() as scratch:
        main_text, deps = flatten_latex(main, scratch=scratch)
        with NamedTemporaryFile(dir=scratch) as fid:
            fid.write(main_text.encode("utf-8"))
            fid.flush()
            deps[Path(main).name] = Path(fid.name)
            create_archive(output, deps)

    validate_archive(output, Path(main).name)
