import re
import zipfile
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory, NamedTemporaryFile


def parse_dependencies(makefile_content: str):
    dependencies = []
    current_deps = []

    pattern = re.compile(r"^[^:]+: (.+)$")
    continuation_pattern = re.compile(r"\\$")

    for line in makefile_content.splitlines():
        line = line.strip()
        if continuation_pattern.search(line):
            current_deps.append(line[:-1].strip())
        else:
            current_deps.append(line)
            joined_deps = " ".join(current_deps)
            match = pattern.match(joined_deps)
            if match:
                deps = match.group(1).split()
                dependencies.extend(deps)
            current_deps = []

    return dependencies


def get_dependencies(filename: str):
    with NamedTemporaryFile() as makefile:
        run(
            f"tectonic --makefile-rules {makefile.name} {filename}",
            shell=True,
            capture_output=True,
            check=True,
        )
        return parse_dependencies(Path(makefile.name).read_text())


def flatten_deps(filename: str, deps: list[str]):
    with open(filename + ".tmp", "w") as dst:
        with open(filename, "r") as src:
            for line in src:
                dst.write(replace_deps(line, deps))

    Path(filename).unlink()
    Path(filename + ".tmp").rename(filename)


def replace_deps(line: str, deps: list[str]):
    for dep in deps:
        dep = Path(dep)
        line = re.sub("{" + str(dep) + "}", "{" + dep.name + "}", line)
        dep = dep.with_suffix("")
        line = re.sub("{" + str(dep) + "}", "{" + dep.name + "}", line)

    return line


def latexpand(main: str):
    expand = str(Path(main).with_suffix(".expand.tex"))
    run(["latexpand", "--output", expand, main])
    return expand


def create_archive(archive: str, files: list[str], flat: bool = False):
    with zipfile.ZipFile(archive, "w") as zipf:
        for file in files:
            try:
                zipf.write(file, Path(file).name if flat else file)
            except FileNotFoundError:
                print(f"Warning: {file} not found and will not be added to the zip.")


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


def archive(main: str, output: str | None = None, expand: bool = True):
    output = output or str(Path(main).with_suffix(".zip"))
    if expand:
        main = latexpand(main)

    deps = get_dependencies(main)
    if expand:
        flatten_deps(main, deps)

    create_archive(output, deps, flat=expand)
    validate_archive(output, main)
