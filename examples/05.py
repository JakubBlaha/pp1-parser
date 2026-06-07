"""Req 05 -- Exception handling procedure.

Requirement: The software, when handling an exception, must execute in order:
(1) copy register SRR0 to R5; (2) invoke the image exception handler;
(3) if the handler returns, hold software execution.
"""

from verifier import *

SRR0 = Entity(id="SRR0", type=EntityType.STORAGE, modifiers={"register": True})
R5 = Entity(id="R5", type=EntityType.STORAGE, modifiers={"register": True})
ev_written_r5 = Entity(
    id="ev_written_r5", type=EntityType.EVENT,
    modifiers={"target": "R5", "type": "written"},
)
exception = Entity(id="exception", type=EntityType.EVENT_TRIGGER)
ev_exception = Entity(
    id="ev_exception", type=EntityType.EVENT,
    modifiers={"target": "exception", "type": "generic"},
)
invoke_ieh = Entity(id="invoke_ieh", type=EntityType.EVENT_TRIGGER)
ev_invoke_ieh = Entity(
    id="ev_invoke_ieh", type=EntityType.EVENT,
    modifiers={"target": "invoke_ieh", "type": "generic"},
)
return_ieh = Entity(id="return_ieh", type=EntityType.EVENT_TRIGGER)
ev_return_ieh = Entity(
    id="ev_return_ieh", type=EntityType.EVENT,
    modifiers={"target": "return_ieh", "type": "generic"},
)
hold_exec = Entity(id="hold_exec", type=EntityType.EVENT_TRIGGER)
ev_hold_exec = Entity(
    id="ev_hold_exec", type=EntityType.EVENT,
    modifiers={"target": "hold_exec", "type": "generic"},
)

requirement = Requirement(
    id="Req05",
    flavour=Flavour.DISCRETE,
    entities=[
        SRR0, R5, ev_written_r5, exception, ev_exception,
        invoke_ieh, ev_invoke_ieh, return_ieh, ev_return_ieh, hold_exec, ev_hold_exec,
    ],
    constraint=TAnd(items=[
        Sequence(steps=[
            Happening(entity=ev_exception, time=Now),
            AllOf(items=[
                Happening(entity=ev_written_r5, time=Now),
                Eq(Val(entity=R5, time=Now), Val(entity=SRR0, time=Now)),
            ]),
            Happening(entity=ev_invoke_ieh, time=Now),
        ]),
        Causes(
            cond=Happening(entity=ev_return_ieh, time=Now),
            effect=Happening(entity=ev_hold_exec, time=Now),
        ),
    ]),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
