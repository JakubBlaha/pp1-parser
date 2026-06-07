"""Req 08 -- State transition on received mastership data.

Requirement: The software shall operate as Backup when it receives a new data
instance of ``MastershipInfo`` with parameter Mastership_b equal to BACKUP.

Note: BACKUP is an enum constant; enum types are not yet part of V_base. It is
modelled here as a ``Value`` entity (entities are values in V_nonset), so the
guard becomes an equality against that entity reference.
"""

from verifier import *

MastershipInfo = Entity(id="MastershipInfo", type=EntityType.CHANNEL)
ev_received_mastership = Entity(
    id="ev_received_mastership", type=EntityType.EVENT,
    modifiers={"target": "MastershipInfo", "type": "received"},
)
Backup = Entity(id="Backup", type=EntityType.STATE)
ev_entered_backup = Entity(
    id="ev_entered_backup", type=EntityType.EVENT,
    modifiers={"target": "Backup", "type": "entered"},
)
BACKUP = Entity(id="BACKUP", type=EntityType.VALUE)

requirement = Requirement(
    id="Req08",
    flavour=Flavour.DISCRETE,
    entities=[MastershipInfo, ev_received_mastership, Backup, ev_entered_backup, BACKUP],
    constraint=Causes(
        cond=AllOf(items=[
            Happening(entity=ev_received_mastership, time=Now),
            Eq(Val(entity=MastershipInfo, time=Now), BACKUP),
        ]),
        effect=Happening(entity=ev_entered_backup, time=Now),
    ),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
