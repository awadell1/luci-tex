# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- archive: Resolve `.cls` vs `.bst` ambiguity and include nested local dependencies.
- archive: Correctly handle `\input` commands wrapped inline by another commands
- check: Flag undefined acronyms from the `acronym` package

### Tests
- archive: Add coverage for `\documentclass` resolution.

## [0.1.0] - 2025-08-18

### Added
- Initial release of `luci` CLI.

[Unreleased]: https://github.com/awadell1/luci-tex/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/awadell1/luci-tex/releases/tag/v0.1.0
