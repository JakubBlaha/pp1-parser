"""Req 01 -- Arithmetic recurrence with condition.

Requirement: The signal ``EngagementNoSat_u`` shall equal
1.2 x EngagementNoSat_u(k-1) when ``Switch_b`` is true, and ``Lon_u`` otherwise.
The initial value is 0.
"""

from verifier import *

EngagementNoSat_u = Entity(id="EngagementNoSat_u", type=EntityType.SIGNAL)
Switch_b = Entity(id="Switch_b", type=EntityType.SIGNAL)
Lon_u = Entity(id="Lon_u", type=EntityType.SIGNAL)

requirement = Requirement(
    id="Req01",
    flavour=Flavour.DISCRETE,
    entities=[EngagementNoSat_u, Switch_b, Lon_u],
    constraint=TAnd(items=[
        Initial(inner=Eq(Val(entity=EngagementNoSat_u, time=0), 0)),
        Always(inner=AllOf(items=[
            Implies(
                antecedent=Eq(Val(entity=Switch_b, time=Now), True),
                consequent=Eq(
                    Val(entity=EngagementNoSat_u, time=Now),
                    1.2 * Val(entity=EngagementNoSat_u, time=Prev(time=Now)),
                ),
            ),
            Implies(
                antecedent=Ne(Val(entity=Switch_b, time=Now), True),
                consequent=Eq(
                    Val(entity=EngagementNoSat_u, time=Now),
                    Val(entity=Lon_u, time=Now),
                ),
            ),
        ])),
    ]),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
