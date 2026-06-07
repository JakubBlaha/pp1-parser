"""Req 09 -- Timed signal toggle with multi-condition guard.

Requirement: The software must toggle ``valid_range`` within 500 ns of a write
to ``d`` if ALL of:
  - last Maximum Peak minus Minimum Peak of d is higher than 655;
  - it is the second write to d after the Minimum Peak detection;
  - signed value of d is higher than the signed value of last d.

Note: ``valid_range`` is boolean; the toggle ``new = not old`` is encoded as the
boolean-equivalent ``new != old`` (avoids a value-level negation expression).
"""

from verifier import *

d = Entity(id="d", type=EntityType.SIGNAL)
valid_range = Entity(id="valid_range", type=EntityType.SIGNAL)
ev_written_d = Entity(
    id="ev_written_d", type=EntityType.EVENT,
    modifiers={"target": "d", "type": "written"},
)
ev_written_vr = Entity(
    id="ev_written_vr", type=EntityType.EVENT,
    modifiers={"target": "valid_range", "type": "written"},
)
min_peak_det = Entity(id="min_peak_det", type=EntityType.EVENT_TRIGGER)
ev_min_peak_det = Entity(
    id="ev_min_peak_det", type=EntityType.EVENT,
    modifiers={"target": "min_peak_det", "type": "generic"},
)
max_peak_det = Entity(id="max_peak_det", type=EntityType.EVENT_TRIGGER)
ev_max_peak_det = Entity(
    id="ev_max_peak_det", type=EntityType.EVENT,
    modifiers={"target": "max_peak_det", "type": "generic"},
)

# Abbreviations: times of the most recent min-peak / max-peak detection and the
# second-to-last write to d, all up to Now.
t_mpd = Start(interval=LastOcc(event=ev_min_peak_det, time=Now, n=1))
t_Mpd = Start(interval=LastOcc(event=ev_max_peak_det, time=Now, n=1))
t_prevd = Start(interval=LastOcc(event=ev_written_d, time=Now, n=2))

requirement = Requirement(
    id="Req09",
    flavour=Flavour.CONTINUOUS,  # time unit: nanoseconds
    entities=[
        d, valid_range, ev_written_d, ev_written_vr,
        min_peak_det, ev_min_peak_det, max_peak_det, ev_max_peak_det,
    ],
    constraint=CausesWithin(
        cond=AllOf(items=[
            Happening(entity=ev_written_d, time=Now),
            (Val(entity=d, time=t_Mpd) - Val(entity=d, time=t_mpd)) > 655,
            Eq(
                EvtOccCount(event=ev_written_d, interval=MkIntervalOC(start=t_mpd, end=Now)),
                2,
            ),
            Val(entity=d, time=Now) > Val(entity=d, time=t_prevd),
        ]),
        effect=AllOf(items=[
            Happening(entity=ev_written_vr, time=Now),
            Ne(
                Val(entity=valid_range, time=Now),
                ValBefore(entity=valid_range, time=Now),
            ),
        ]),
        bound=500,
    ),
)


if __name__ == "__main__":
    import json
    print(json.dumps(requirement.to_json(), indent=2))
