"""Req 13 -- Bounded count of large register values.

Requirement: The number of values larger than 10 in the four registers
A, B, C, D in different cores, when they are written in parallel at the same
timestep, is never greater than 2.

Note: "all four written at the same timestep" is quantified over the four
write-event entities; the consequent filters over the register entities
themselves. The written values are read with ``ValAfter``: at a write time
``Val`` still gives the value before the write. "In different cores" has no
counterpart in the formalism and does not change the condition.
"""

from verifier import *

A = Entity(id="A", type=EntityType.STORAGE, modifiers={"register": True})
B = Entity(id="B", type=EntityType.STORAGE, modifiers={"register": True})
C = Entity(id="C", type=EntityType.STORAGE, modifiers={"register": True})
D = Entity(id="D", type=EntityType.STORAGE, modifiers={"register": True})
ev_written_A = Entity(id="ev_written_A", type=EntityType.EVENT,
                      modifiers={"target": "A", "type": "written"})
ev_written_B = Entity(id="ev_written_B", type=EntityType.EVENT,
                      modifiers={"target": "B", "type": "written"})
ev_written_C = Entity(id="ev_written_C", type=EntityType.EVENT,
                      modifiers={"target": "C", "type": "written"})
ev_written_D = Entity(id="ev_written_D", type=EntityType.EVENT,
                      modifiers={"target": "D", "type": "written"})

regs = mkset(A, B, C, D)
write_events = mkset(ev_written_A, ev_written_B, ev_written_C, ev_written_D)

entities = [A, B, C, D, ev_written_A, ev_written_B, ev_written_C, ev_written_D]

requirement = Requirement(
    id="Req13",
    flavour=Flavour.DISCRETE,
    entities=entities,
    constraint=Always(inner=Implies(
        antecedent=ForAll.of(write_events, lambda ev: Happening(entity=ev, time=Now)),
        consequent=Cmp(
            op=CmpOp.LE,
            lhs=Size(set=Filter.of(regs, lambda e: ValAfter(entity=e, time=Now) > 10)),
            rhs=2,
        ),
    )),
)


module = Module(entities=entities, requirements=[requirement])


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
