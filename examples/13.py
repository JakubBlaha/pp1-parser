"""Req 13 -- Bounded count of large register values.

Requirement: The number of values larger than 10 in the four registers
A, B, C, D, when they are read at the same timestep, is never greater than 2.

Note: the formalism's antecedent ``ForAll(regs, lambda e. Happening(e, read, Now))``
uses a ``read`` shorthand. ``Happening`` takes an Event entity, so the
"all four read simultaneously" antecedent is quantified over the four read-event
entities; the consequent filters over the register entities themselves.
"""

from verifier import *

A = Entity(id="A", type=EntityType.STORAGE, modifiers={"register": True})
B = Entity(id="B", type=EntityType.STORAGE, modifiers={"register": True})
C = Entity(id="C", type=EntityType.STORAGE, modifiers={"register": True})
D = Entity(id="D", type=EntityType.STORAGE, modifiers={"register": True})
ev_read_A = Entity(id="ev_read_A", type=EntityType.EVENT,
                   modifiers={"target": "A", "type": "read"})
ev_read_B = Entity(id="ev_read_B", type=EntityType.EVENT,
                   modifiers={"target": "B", "type": "read"})
ev_read_C = Entity(id="ev_read_C", type=EntityType.EVENT,
                   modifiers={"target": "C", "type": "read"})
ev_read_D = Entity(id="ev_read_D", type=EntityType.EVENT,
                   modifiers={"target": "D", "type": "read"})

regs = mkset(A, B, C, D)
read_events = mkset(ev_read_A, ev_read_B, ev_read_C, ev_read_D)

entities = [A, B, C, D, ev_read_A, ev_read_B, ev_read_C, ev_read_D]

requirement = Requirement(
    id="Req13",
    flavour=Flavour.DISCRETE,
    entities=entities,
    constraint=Always(inner=Implies(
        antecedent=ForAll.of(read_events, lambda ev: Happening(entity=ev, time=Now)),
        consequent=Cmp(
            op=CmpOp.LE,
            lhs=Size(set=Filter.of(regs, lambda e: Val(entity=e, time=Now) > 10)),
            rhs=2,
        ),
    )),
)


module = Module(entities=entities, requirements=[requirement])


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
