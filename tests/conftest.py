"""Expose fixtures defined in tests/utils.py for pytest discovery.

We forward names instead of importing with an unused import to avoid
auto-fixers stripping the import.
"""

from . import utils as _utils

cli_runner = _utils.cli_runner
latex_project = _utils.latex_project
