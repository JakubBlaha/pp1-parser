"""Every example builds a valid ``Module`` that round-trips through canonical JSON.

Guards the examples against future DSL changes: each ``examples/NN.py`` is loaded,
its ``module`` is round-tripped through JSON, and run through the CLI.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from verifier import Module, cli

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXAMPLE_FILES = sorted(EXAMPLES_DIR.glob("[0-9]*.py"))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"example_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_examples_discovered():
    assert EXAMPLE_FILES, f"no example files found in {EXAMPLES_DIR}"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_example_module_round_trips(path):
    mod = _load(path)
    assert hasattr(mod, "module"), f"{path.name} defines no `module`"
    module = mod.module
    assert isinstance(module, Module)
    assert Module.model_validate(module.to_json()) == module


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.stem)
def test_example_via_cli(path, capsys):
    rc = cli.main([str(path)])

    assert rc == 0
    json.loads(capsys.readouterr().out)     # CLI emitted parseable JSON
