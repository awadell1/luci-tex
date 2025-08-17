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
* `merge-bibs`: Merge and deduplicate bib files.
* `fix-dups`: Fix duplicate citations.
* `archive`: Archive the project.
* `merge-acronyms`: Merge acronyms.

## Contributing

To contribute to `luci`, clone the repository and install the development dependencies:

```shell
git clone https://github.com/awadell1/luci-tex.git
cd luci-tex
uv pip install -e .[dev,docs]
```

Then, you can run the tests with:

```shell
pytest
```

And build the documentation with:

```shell
cd docs && uv run make html
```
