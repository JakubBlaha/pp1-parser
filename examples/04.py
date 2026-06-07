"""Req 04 -- Exception vector table configuration.

Requirement: The software must configure IVORx registers with the addresses of
Exception Vectors composing the Exception Vector Table:
    IVOR0 -> Critical input,  IVOR1 -> Machine check.
"""

from verifier import *

IVOR0 = Entity(id="IVOR0", type=EntityType.STORAGE, modifiers={"register": True})
IVOR1 = Entity(id="IVOR1", type=EntityType.STORAGE, modifiers={"register": True})
CriticalInput = Entity(id="CriticalInput", type=EntityType.STORAGE)
MachineCheck = Entity(id="MachineCheck", type=EntityType.STORAGE)

requirement = Requirement(
    id="Req04",
    flavour=Flavour.DISCRETE,
    entities=[IVOR0, IVOR1, CriticalInput, MachineCheck],
    constraint=Eventually(inner=AllOf(items=[
        Eq(Val(entity=IVOR0, time=Now), Addr(entity=CriticalInput)),
        Eq(Val(entity=IVOR1, time=Now), Addr(entity=MachineCheck)),
    ])),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
