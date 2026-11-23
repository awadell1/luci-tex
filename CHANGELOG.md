# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- wrap: Write a TeX file as a single line to stdout, the clipboard, or a file.
- diff: New `luci diff` subcommand to generate LaTeX diffs between a git ref
  and either the working tree or another ref. Produces `<stem>_old.tex`,
  `<stem>_new.tex`, and `<stem>_diff.tex` in `<stem>-diff/` by default, with
  optional custom output directory and compilation.

### Changed
- cli: Improve help text formatting and descriptions for all commands.

### Fixed
- archive: Resolve `.cls` vs `.bst` ambiguity and include nested local dependencies.
- archive: Correctly handle `\input` commands wrapped inline by another commands
- check: Flag undefined acronyms from the `acronym` package
- check: Detect biblatex-style split-line undefined citation warnings.

### Tests
- archive: Add coverage for `\documentclass` resolution.
- check: Added tests for undefined citations, references or missing files.
- diff: Add tests covering OLD vs working tree, two-ref mode, and custom
  output directory; latexdiff is monkeypatched to avoid external dependency.

## [0.1.0] - 2025-08-18

### Added
- Initial release of `luci` CLI.

[Unreleased]: https://github.com/awadell1/luci-tex/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/awadell1/luci-tex/releases/tag/v0.1.0
