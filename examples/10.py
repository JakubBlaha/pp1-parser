"""Req 10 -- Repeated failure triggers emergency mode.

Requirement: The software shall enter emergency mode if any of the following
failures individually occurs twice in less than 10 seconds:
(a) sensor failure, (b) energy failure, (c) communication failure.

Note: each failure type is tracked independently. ``MkIntervalOO(Now-10, Now)``
is open on both ends: the left endpoint excludes a gap of exactly 10 s ("less
than"), the right excludes Now itself so only the previous occurrence is counted
alongside the current Happening.
"""

from verifier import *

sensor_failure = Entity(id="sensor_failure", type=EntityType.EVENT_TRIGGER)
ev_sensor_fail = Entity(
    id="ev_sensor_fail", type=EntityType.EVENT,
    modifiers={"target": "sensor_failure", "type": "generic"},
)
energy_failure = Entity(id="energy_failure", type=EntityType.EVENT_TRIGGER)
ev_energy_fail = Entity(
    id="ev_energy_fail", type=EntityType.EVENT,
    modifiers={"target": "energy_failure", "type": "generic"},
)
comm_failure = Entity(id="comm_failure", type=EntityType.EVENT_TRIGGER)
ev_comm_fail = Entity(
    id="ev_comm_fail", type=EntityType.EVENT,
    modifiers={"target": "comm_failure", "type": "generic"},
)
emergency_mode = Entity(id="emergency_mode", type=EntityType.STATE)


def recurred(ev):
    """Failure ``ev`` happens now and has happened at least once in (Now-10, Now)."""
    return AllOf(items=[
        Happening(entity=ev, time=Now),
        EvtOccCount(event=ev, interval=MkIntervalOO(start=Now - 10, end=Now)) >= 1,
    ])


requirement = Requirement(
    id="Req10",
    flavour=Flavour.CONTINUOUS,  # time unit: seconds
    entities=[
        sensor_failure, ev_sensor_fail, energy_failure, ev_energy_fail,
        comm_failure, ev_comm_fail, emergency_mode,
    ],
    constraint=Causes(
        cond=AnyOf(items=[
            recurred(ev_sensor_fail),
            recurred(ev_energy_fail),
            recurred(ev_comm_fail),
        ]),
        effect=Eq(Val(entity=emergency_mode, time=Now), True),
    ),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
