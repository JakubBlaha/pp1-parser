"""Req 03 -- Ordered read then store to CPU register.

Requirement: The software must perform the following actions in order:
1) Read the calibration constant value at address 0xAA000018;
2) Store the calibration constant value in the DTSCON register.
"""

from verifier import *

calibration_const = Entity(
    id="calibration_const", type=EntityType.STORAGE,
    modifiers={"address": 0xAA000018},
)
DTSCON = Entity(id="DTSCON", type=EntityType.STORAGE, modifiers={"register": True})
ev_read_cc = Entity(
    id="ev_read_cc", type=EntityType.EVENT,
    modifiers={"target": "calibration_const", "type": "read"},
)
ev_written_dtscon = Entity(
    id="ev_written_dtscon", type=EntityType.EVENT,
    modifiers={"target": "DTSCON", "type": "written"},
)

requirement = Requirement(
    id="Req03",
    flavour=Flavour.DISCRETE,
    entities=[calibration_const, DTSCON, ev_read_cc, ev_written_dtscon],
    constraint=Sequence(steps=[
        Happening(entity=ev_read_cc, time=Now),
        AllOf(items=[
            Happening(entity=ev_written_dtscon, time=Now),
            Eq(
                Val(entity=DTSCON, time=Now),
                Val(
                    entity=calibration_const,
                    time=Start(interval=LastOcc(event=ev_read_cc, time=Now, n=1)),
                ),
            ),
        ]),
    ]),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
