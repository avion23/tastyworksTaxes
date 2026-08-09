import subprocess
import sys


def test_importing_cli_module_preserves_application_logging_configuration():
    scenario = """
import logging

root = logging.getLogger()
before_level = root.level
before_handlers = tuple(root.handlers)

import tastyworksTaxes.main  # noqa: F401

assert root.level == before_level
assert tuple(root.handlers) == before_handlers
"""
    result = subprocess.run(
        [sys.executable, "-c", scenario],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
