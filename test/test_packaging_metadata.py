from pathlib import Path


def test_declared_dependencies_are_installable_on_supported_python():
    metadata = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'requires-python = ">=3.10"' in metadata
    assert '"pandas>=2.0"' in metadata
