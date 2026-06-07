"""Custom Counter.

Requirement: After the system enters emergency mode, at each discrete time step
the counter ``counter_1`` is incremented by 3.
"""

from verifier import *

enter_emergency = Entity(id="enter_emergency", type=EntityType.EVENT_TRIGGER)
ev_enter_emergency = Entity(
    id="ev_enter_emergency", type=EntityType.EVENT,
    modifiers={"target": "enter_emergency", "type": "generic"},
)
counter_1 = Entity(id="counter_1", type=EntityType.SIGNAL)

entities = [enter_emergency, ev_enter_emergency, counter_1]

requirement = Requirement(
    id="CustomCounter",
    flavour=Flavour.DISCRETE,
    entities=entities,
    constraint=Always(inner=Implies(
        antecedent=HasHappened(entity=ev_enter_emergency, time=Now),
        consequent=Eq(
            Val(entity=counter_1, time=Now),
            Val(entity=counter_1, time=Prev(time=Now)) + 3,
        ),
    )),
)


module = Module(entities=entities, requirements=[requirement])


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
