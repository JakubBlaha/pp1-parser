"""Tests for the verifier CLI input modes (file argument and stdin)."""

import io
import json
import textwrap

import pytest

from verifier import cli

# A minimal, valid definition: one signal, one requirement, wrapped in a module.
SAMPLE = textwrap.dedent(
    """
    from verifier import *

    sig = Entity(id="sig", type=EntityType.SIGNAL)
    requirement = Requirement(
        id="R1", flavour=Flavour.DISCRETE, entities=[sig],
        constraint=Always(inner=Eq(Val(entity=sig, time=Now), True)),
    )
    module = Module(entities=[sig], requirements=[requirement])
    """
)

# Constructs a Requirement with an invalid flavour -> ValidationError on build.
SAMPLE_INVALID = textwrap.dedent(
    """
    from verifier import *

    module = Module(requirements=[
        Requirement(id="R", flavour="BAD", entities=[],
                    constraint=Always(inner=TrueP())),
    ])
    """
)

# Valid requirement but no top-level `module` to emit.
SAMPLE_NO_MODULE = textwrap.dedent(
    """
    from verifier import *

    sig = Entity(id="sig", type=EntityType.SIGNAL)
    requirement = Requirement(
        id="R", flavour=Flavour.DISCRETE, entities=[sig],
        constraint=Always(inner=TrueP()),
    )
    """
)


def _feed_stdin(monkeypatch, source: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(source))


def test_from_file(tmp_path, capsys):
    path = tmp_path / "req.py"
    path.write_text(SAMPLE)

    rc = cli.main([str(path)])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["requirements"][0]["id"] == "R1"
    assert data["entities"][0]["id"] == "sig"


def test_from_stdin_no_arg(capsys, monkeypatch):
    _feed_stdin(monkeypatch, SAMPLE)

    rc = cli.main([])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["requirements"][0]["id"] == "R1"


def test_from_stdin_dash(capsys, monkeypatch):
    _feed_stdin(monkeypatch, SAMPLE)

    rc = cli.main(["-"])

    assert rc == 0
    assert json.loads(capsys.readouterr().out)["requirements"][0]["id"] == "R1"


def test_file_and_stdin_produce_identical_json(tmp_path, capsys, monkeypatch):
    path = tmp_path / "req.py"
    path.write_text(SAMPLE)

    cli.main([str(path)])
    file_out = capsys.readouterr().out

    _feed_stdin(monkeypatch, SAMPLE)
    cli.main([])
    stdin_out = capsys.readouterr().out

    assert file_out == stdin_out


def test_missing_file_returns_2(capsys):
    rc = cli.main(["does_not_exist.py"])

    assert rc == 2
    assert "no such file" in capsys.readouterr().err


def test_invalid_definition_returns_1(capsys, monkeypatch):
    _feed_stdin(monkeypatch, SAMPLE_INVALID)

    rc = cli.main([])

    assert rc == 1
    err = capsys.readouterr().err
    assert "invalid" in err
    assert "flavour" in err


def test_no_module_returns_1(capsys, monkeypatch):
    _feed_stdin(monkeypatch, SAMPLE_NO_MODULE)

    rc = cli.main([])

    assert rc == 1
    assert "no top-level `module`" in capsys.readouterr().err


def test_output_file(tmp_path, capsys):
    src = tmp_path / "req.py"
    src.write_text(SAMPLE)
    out = tmp_path / "out.json"

    rc = cli.main([str(src), "-o", str(out)])

    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == ""               # nothing written to stdout
    assert "wrote" in captured.err
    data = json.loads(out.read_text())      # the file holds valid JSON
    assert data["requirements"][0]["id"] == "R1"
