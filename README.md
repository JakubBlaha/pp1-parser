# verifier

A logic-agnostic formalism for expressing software **requirements** and **test
cases** as a typed, JSON-serialisable AST. The Python package
[`verifier/`](verifier/) is both an embedded DSL (you build requirements with
ordinary Python) and the canonical form (every node round-trips to/from JSON and
a JSON Schema can be generated from it).

The formalism itself lives in the [`pp1`](resources/formalism) git submodule
under [`resources/formalism/tex-new/`](resources/formalism/tex-new):

- `formalism.tex` — the formal definitions.
- `examples.tex` — worked example requirements.

## Layout

| Path | What it is |
|------|------------|
| [`verifier/lib.py`](verifier/lib.py) | The DSL: entities, expressions, predicates, temporal constructs, operations, requirements/test cases. |
| [`examples/`](examples) | One module per `examples.tex` requirement (`00.py` .. `13.py`), each building a `Requirement`. |
| [`resources/formalism/`](resources/formalism) | The formalism `pp1` submodule (LaTeX source). |

## Installation

Requires Python 3.10+.

```bash
# 1. Clone with the formalism submodule
git clone <repo-url> pp1-parser
cd pp1-parser
git submodule update --init --recursive

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Editable-install the verifier package (pulls in pydantic)
pip install -e .
```

The editable install is what lets any script do `from verifier import *`
regardless of the working directory — no `sys.path` or `importlib` juggling.

## Usage

Build a requirement with the DSL:

```python
from verifier import *

init_end = Entity(id="initialization_end", type=EntityType.EVENT_TRIGGER)
ev_init_end = Entity(
    id="ev_init_end", type=EntityType.EVENT,
    modifiers={"target": "initialization_end", "type": "generic"},
)
modeset = Entity(id="MODESET_TOPIC", type=EntityType.CHANNEL)
ev_tx = Entity(
    id="ev_transmitted_modeset", type=EntityType.EVENT,
    modifiers={"target": "MODESET_TOPIC", "type": "transmitted"},
)

req = Requirement(
    id="Req07", flavour=Flavour.DISCRETE,
    entities=[init_end, ev_init_end, modeset, ev_tx],
    constraint=Causes(
        cond=Happening(entity=ev_init_end, time=Now),
        effect=AllOf(items=[
            Happening(entity=ev_tx, time=Now),
            Eq(Val(entity=modeset, time=Now), True),
        ]),
    ),
)

print(req.to_json())                 # canonical JSON
Requirement.model_validate(req.to_json())   # parse it back
Requirement.model_json_schema()      # JSON Schema for the format
```

## Running the examples

```bash
# Print one example's canonical JSON
python examples/07.py
```
