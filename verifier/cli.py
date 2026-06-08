"""Command-line interface for the verifier.

Reads DSL source that builds a top-level ``module`` (a ``Module``) -- from a
file argument, or from stdin when the argument is omitted or given as ``-`` --
validates it, and prints the canonical JSON. Validation happens when the source
constructs its Pydantic nodes; a malformed definition raises and is reported
with a non-zero exit code.

Note: the input file is executed as Python, so only run files you trust.
"""

import argparse
import json
import sys
import types
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .validate import InvalidModule, validate


def _exec_source(source: str, origin: str):
    """Execute DSL source in an isolated module namespace and return it."""
    mod = types.ModuleType("_verifier_input")
    mod.__file__ = origin
    exec(compile(source, origin, "exec"), mod.__dict__)
    return mod


def _extract(mod) -> BaseModel | None:
    """Return the top-level ``module`` to emit, or ``None`` if absent.

    A ``Module`` is required because it carries the full entity definitions
    (type and modifiers); a bare ``Requirement`` would serialise entities as
    id-only references.
    """
    obj = getattr(mod, "module", None)
    return obj if isinstance(obj, BaseModel) else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="verifier",
        description="Parse and validate a requirements/test-case definition file "
        "and emit its canonical JSON.",
    )
    parser.add_argument(
        "input", type=Path, nargs="?", default=None,
        help="Python file defining a top-level `module`. Reads from stdin if "
        "omitted or given as '-'.",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write JSON here instead of stdout.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2).")
    args = parser.parse_args(argv)

    # Resolve the source: a file, or stdin when omitted / given as '-'.
    if args.input is None or str(args.input) == "-":
        source, origin = sys.stdin.read(), "<stdin>"
    elif args.input.is_file():
        source, origin = args.input.read_text(), str(args.input)
    else:
        print(f"error: no such file: {args.input}", file=sys.stderr)
        return 2

    # Execute + construct the definitions; this is where validation happens.
    try:
        mod = _exec_source(source, origin)
    except ValidationError as e:
        print(f"invalid: {origin} failed validation:\n{e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 -- surface any load/build failure to the user
        print(f"error: failed to load {origin}: {e}", file=sys.stderr)
        return 1

    obj = _extract(mod)
    if obj is None:
        print(
            f"error: {origin} defines no top-level `module` "
            f"(wrap your requirement(s) in a Module)",
            file=sys.stderr,
        )
        return 1

    # Semantic validation against the formalism's type rules.
    try:
        validate(obj)
    except InvalidModule as e:
        print(f"invalid: {origin}:\n{e}", file=sys.stderr)
        return 1

    # Defensive re-validation: round-trip the canonical form back through the model.
    try:
        data = obj.to_json()
        type(obj).model_validate(data)
    except ValidationError as e:
        print(f"invalid: {origin} is not a valid definition:\n{e}", file=sys.stderr)
        return 1

    text = json.dumps(data, indent=args.indent)
    if args.output is not None:
        args.output.write_text(text + "\n")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
