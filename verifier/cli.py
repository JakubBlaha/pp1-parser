"""Command-line interface for the verifier.

Loads an input ``.py`` file that builds a top-level ``module`` (a ``Module``)
with the DSL, validates it, and prints the canonical JSON. Validation happens
when the file constructs its Pydantic nodes; a malformed definition raises and
is reported with a non-zero exit code.

Note: the input file is executed as Python, so only run files you trust.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from pydantic import BaseModel, ValidationError


def _load(path: Path):
    """Execute the input file in an isolated module namespace."""
    spec = importlib.util.spec_from_file_location(f"_verifier_input_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
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
        "input", type=Path,
        help="Path to a Python file defining a `module` or `requirement`.",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write JSON here instead of stdout.",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2).")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: no such file: {args.input}", file=sys.stderr)
        return 2

    # Load + construct the definitions; this is where validation happens.
    try:
        mod = _load(args.input)
    except ValidationError as e:
        print(f"invalid: {args.input} failed validation:\n{e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 -- surface any load/build failure to the user
        print(f"error: failed to load {args.input}: {e}", file=sys.stderr)
        return 1

    obj = _extract(mod)
    if obj is None:
        print(
            f"error: {args.input} defines no top-level `module` "
            f"(wrap your requirement(s) in a Module)",
            file=sys.stderr,
        )
        return 1

    # Defensive re-validation: round-trip the canonical form back through the model.
    try:
        data = obj.to_json()
        type(obj).model_validate(data)
    except ValidationError as e:
        print(f"invalid: {args.input} is not a valid definition:\n{e}", file=sys.stderr)
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
