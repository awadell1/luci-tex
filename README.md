# Luci - Helper tools for wrangling LaTeX Projects

## Documentation

The full documentation for `luci` is available at [https://awadell1.github.io/luci-tex](https://awadell1.github.io/luci-tex).

## Installation

Install `luci` with [uv](https://docs.astral.sh/uv/getting-started/installation/):


```shell
uv tool install git+https://github.com/awadell1/luci-tex
```

## Usage

```shell
luci --help
```

`luci` provides the following commands:

* `check`: Check latex build for errors.
* `merge-bibs`: Merge and de-duplicate bib files.
* `fix-dups`: Fix duplicate citations.
* `archive`: Archive the project.
* `merge-acronyms`: Merge acronyms.
* `wrap`: Collapse whitespace in a UTF-8 TeX file to a single line, preserving LaTeX commands.

`luci wrap abstract.tex` prints the line to stdout. Add `--clip` to copy it to
the clipboard, `--output abstract.txt` to save it, or both to copy and save it.

## Contributing

To contribute to `luci`, clone the repository and install the development dependencies:

```shell
git clone https://github.com/awadell1/luci-tex.git
cd luci-tex
uv pip install -e .[dev,docs]
```

Then, you can run the tests with:

```shell
uv run pytest
```

And build the documentation with:

```shell
uv run --group docs sphinx-autobuild docs build/html
```
