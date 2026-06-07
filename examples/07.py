"""Req 07 -- Mode enable transmission after initialisation.

Requirement: After its initialisation, the software shall transmit the signal
Mode Enable with value true through DDS topic ``MODESET_TOPIC``.
"""

from verifier import *

MODESET_TOPIC = Entity(id="MODESET_TOPIC", type=EntityType.CHANNEL)
ev_transmitted_modeset = Entity(
    id="ev_transmitted_modeset", type=EntityType.EVENT,
    modifiers={"target": "MODESET_TOPIC", "type": "transmitted"},
)
initialization_end = Entity(id="initialization_end", type=EntityType.EVENT_TRIGGER)
ev_init_end = Entity(
    id="ev_init_end", type=EntityType.EVENT,
    modifiers={"target": "initialization_end", "type": "generic"},
)

requirement = Requirement(
    id="Req07",
    flavour=Flavour.DISCRETE,
    entities=[MODESET_TOPIC, ev_transmitted_modeset, initialization_end, ev_init_end],
    constraint=Causes(
        cond=Happening(entity=ev_init_end, time=Now),
        effect=AllOf(items=[
            Happening(entity=ev_transmitted_modeset, time=Now),
            Eq(Val(entity=MODESET_TOPIC, time=Now), True),
        ]),
    ),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
