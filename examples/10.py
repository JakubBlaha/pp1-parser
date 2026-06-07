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


entities = [
    sensor_failure, ev_sensor_fail, energy_failure, ev_energy_fail,
    comm_failure, ev_comm_fail, emergency_mode,
]


def recurred(ev):
    """Failure ``ev`` happens now and has happened at least once in (Now-10, Now)."""
    return AllOf(items=[
        Happening(entity=ev, time=Now),
        EvtOccCount(event=ev, interval=MkIntervalOO(start=Now - 10, end=Now)) >= 1,
    ])


requirement = Requirement(
    id="Req10",
    flavour=Flavour.CONTINUOUS,  # time unit: seconds
    entities=entities,
    constraint=Causes(
        cond=AnyOf(items=[
            recurred(ev_sensor_fail),
            recurred(ev_energy_fail),
            recurred(ev_comm_fail),
        ]),
        effect=Eq(Val(entity=emergency_mode, time=Now), True),
    ),
)


# --- Test cases (from resources/formalism/req/10.md) ---
#
# A failure is fired on its EventTrigger; "entering emergency mode" is verified
# as an assertion on the ``emergency_mode`` state. Negative cases assert that the
# mode is *not* entered at the observation time.


def entered(t):
    """Assertion predicate: emergency mode is entered at time ``t``."""
    return Eq(Val(entity=emergency_mode, time=t), True)


def not_entered(t):
    """Assertion predicate: emergency mode is not entered at time ``t``."""
    return Ne(Val(entity=emergency_mode, time=t), True)


test_cases = [
    # TC1: no failure -> not entering.
    TestCase(
        id="TC1",
        stimuli=[],
        assertions=[Assertion(time=10, predicates=[not_entered(10)])],
    ),
    # TC2: sensor failure twice within 9 s -> entering.
    TestCase(
        id="TC2",
        stimuli=[Fire(time=0, target=sensor_failure),
                 Fire(time=9, target=sensor_failure)],
        assertions=[Assertion(time=9, predicates=[entered(9)])],
    ),
    # TC3: sensor failure twice 11 s apart -> not entering.
    TestCase(
        id="TC3",
        stimuli=[Fire(time=0, target=sensor_failure),
                 Fire(time=11, target=sensor_failure)],
        assertions=[Assertion(time=11, predicates=[not_entered(11)])],
    ),
    # TC4: energy failure twice within 9 s -> entering.
    TestCase(
        id="TC4",
        stimuli=[Fire(time=0, target=energy_failure),
                 Fire(time=9, target=energy_failure)],
        assertions=[Assertion(time=9, predicates=[entered(9)])],
    ),
    # TC5: energy failure twice 11 s apart -> not entering.
    TestCase(
        id="TC5",
        stimuli=[Fire(time=0, target=energy_failure),
                 Fire(time=11, target=energy_failure)],
        assertions=[Assertion(time=11, predicates=[not_entered(11)])],
    ),
    # TC6: comm failure twice 11 s apart -> not entering.
    TestCase(
        id="TC6",
        stimuli=[Fire(time=0, target=comm_failure),
                 Fire(time=11, target=comm_failure)],
        assertions=[Assertion(time=11, predicates=[not_entered(11)])],
    ),
    # TC7: energy then comm within 9 s -> not entering (distinct types don't
    # combine; robustness case).
    TestCase(
        id="TC7",
        stimuli=[Fire(time=0, target=energy_failure),
                 Fire(time=9, target=comm_failure)],
        assertions=[Assertion(time=9, predicates=[not_entered(9)])],
    ),
    # TC_MISSING: comm failure twice within 9 s -> entering. The md flags this as
    # the coverage gap (no positive comm-failure case among TC1-TC7).
    TestCase(
        id="TC_MISSING",
        stimuli=[Fire(time=0, target=comm_failure),
                 Fire(time=9, target=comm_failure)],
        assertions=[Assertion(time=9, predicates=[entered(9)])],
    ),
]


module = Module(entities=entities, requirements=[requirement], test_cases=test_cases)


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
