"""Run every example module and dump its canonical JSON to ``examples/out/``.

Usage:  python examples/run_all.py
"""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load(path):
    """Import an example file by path and return its module object."""
    spec = importlib.util.spec_from_file_location(f"example_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    OUT.mkdir(exist_ok=True)
    # Numeric-named example files (00.py .. 13.py); skips __init__.py / this script.
    for path in sorted(HERE.glob("[0-9]*.py")):
        mod = load(path)
        obj = getattr(mod, "module", None) or mod.requirement
        out_path = OUT / f"{path.stem}.json"
        out_path.write_text(json.dumps(obj.to_json(), indent=2) + "\n")
        print(f"{path.name} -> {out_path.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
