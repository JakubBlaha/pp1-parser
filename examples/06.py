"""Req 06 -- Scheduling deadline.

Requirement: The software must start executing the sequence of tasks allocated
to the execution schedule in less than 2 seconds after processor power-up.

Note: CausesWithin uses a closed interval [t, t+2], slightly over-approximating
the strict ``< 2 s`` bound.
"""

from verifier import *

processor_power_up = Entity(id="processor_power_up", type=EntityType.EVENT_TRIGGER)
ev_power_up = Entity(
    id="ev_power_up", type=EntityType.EVENT,
    modifiers={"target": "processor_power_up", "type": "generic"},
)
invoke_task_seq = Entity(id="invoke_task_seq", type=EntityType.EVENT_TRIGGER)
ev_invoke_task_seq = Entity(
    id="ev_invoke_task_seq", type=EntityType.EVENT,
    modifiers={"target": "invoke_task_seq", "type": "generic"},
)

entities = [processor_power_up, ev_power_up, invoke_task_seq, ev_invoke_task_seq]

requirement = Requirement(
    id="Req06",
    flavour=Flavour.CONTINUOUS,  # time unit: seconds
    entities=entities,
    constraint=CausesWithin(
        cond=Happening(entity=ev_power_up, time=Now),
        effect=Happening(entity=ev_invoke_task_seq, time=Now),
        bound=2,
    ),
)


module = Module(entities=entities, requirements=[requirement])


if __name__ == "__main__":
    import json
    print(json.dumps(module.to_json(), indent=2))
