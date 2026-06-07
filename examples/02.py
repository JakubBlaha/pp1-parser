"""Req 02 -- Store to non-volatile memory.

Requirement: The software shall store the maximum execution time measurement
data in non-volatile memory at address ``MEASUREMT_BLOCK``.
"""

from verifier import *

max_exec_time_data = Entity(id="max_exec_time_data", type=EntityType.ABSTRACT)
MEASUREMT_BLOCK = Entity(
    id="MEASUREMT_BLOCK", type=EntityType.STORAGE,
    modifiers={"non_volatile": True},
)
reset = Entity(id="reset", type=EntityType.EVENT_TRIGGER)
ev_reset = Entity(
    id="ev_reset", type=EntityType.EVENT,
    modifiers={"target": "reset", "type": "generic"},
)

entities = [max_exec_time_data, MEASUREMT_BLOCK, reset, ev_reset]

requirement = Requirement(
    id="Req02",
    flavour=Flavour.DISCRETE,
    entities=entities,
    constraint=TAnd(items=[
        Eventually(inner=Eq(
            Val(entity=MEASUREMT_BLOCK, time=Now),
            Val(entity=max_exec_time_data, time=Now),
        )),
        Always(inner=Implies(
            antecedent=Happening(entity=ev_reset, time=Now),
            consequent=Eq(
                Val(entity=MEASUREMT_BLOCK, time=Next(time=Now)),
                ValBefore(entity=MEASUREMT_BLOCK, time=Now),
            ),
        )),
    ]),
)


module = Module(entities=entities, requirements=[requirement])


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
