"""Pydantic implementation of the requirements/test-case formalism.

This module is the *surface* layer (an embedded Python DSL) and the *canonical*
layer (a JSON-serialisable typed AST) at once: every formalism construct is a
Pydantic node whose ``node`` field tags it for a discriminated union, so a tree
of node objects round-trips to/from JSON and a JSON Schema can be generated from
the class definitions.

The structure mirrors ``resources/formalism/tex-new/formalism.tex`` section by
section: primitives & values, entities, expressions, predicates, trace
predicates (temporal constructs), operations (stimuli) and finally the
requirement / test-case / module containers.

Operator sugar
--------------
For readability close to the maths, expression nodes overload Python operators:

* arithmetic ``+ - * /`` build ``Add/Sub/Mul/Div`` (Def: arithmetic operators);
* ordered comparisons ``< <= > >=`` build ``Cmp`` (Def: comparison predicate).

Equality is **not** overloaded -- Pydantic uses ``__eq__``/``__ne__`` for model
equality -- so use the :func:`Eq` / :func:`Ne` helpers for ``=`` / ``!=``.
Predicates do **not** overload boolean operators: combine them explicitly with
``AllOf`` / ``AnyOf`` / ``Not`` (and ``TAnd`` / ``TOr`` / ``TNot`` for trace
predicates), keeping the surface close to the formalism vocabulary. Only
numeric-valued expression nodes carry the operator sugar; value leaves such as
``EntityRef`` do not.
"""

from __future__ import annotations

import inspect
from enum import Enum
# ``Union`` is aliased so the formalism's set-operation node can keep the name
# ``Union`` without shadowing ``typing.Union`` used in the type annotations below.
from typing import Annotated, Callable, Literal
from typing import Union as TypingUnion

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations (primitives)
# ---------------------------------------------------------------------------


class EntityType(str, Enum):
    """Entity type set ``T_E`` (Def: entity type set)."""

    SIGNAL = "Signal"
    STORAGE = "Storage"
    EVENT = "Event"
    EVENT_TRIGGER = "EventTrigger"
    CHANNEL = "Channel"
    STATE = "State"
    VALUE = "Value"
    ABSTRACT = "Abstract"
    SET = "Set"


class EventTypeLabel(str, Enum):
    """Event type label set ``EventTypeLabel`` (Def: event type label set)."""

    GENERIC = "generic"
    CALCULATED = "calculated"
    WRITTEN = "written"
    READ = "read"
    ENTERED = "entered"
    TRANSMITTED = "transmitted"
    RECEIVED = "received"
    INSERTED = "inserted"
    REMOVED = "removed"
    CLEARED = "cleared"


class CmpOp(str, Enum):
    """Comparison operators (Def: comparison predicate)."""

    EQ = "="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


class Flavour(str, Enum):
    """Time-set flavour fixing ``T`` for a requirement (Def: requirement)."""

    DISCRETE = "Discrete"
    CONTINUOUS = "Continuous"


# ---------------------------------------------------------------------------
# Base node and operator mix-ins
# ---------------------------------------------------------------------------


class Node(BaseModel):
    """Common base: forbids unknown fields and adds a JSON convenience."""

    model_config = ConfigDict(extra="forbid")

    def to_json(self) -> dict:
        """Canonical JSON-compatible ``dict`` for this node and its subtree."""
        return self.model_dump(mode="json")


class ExprMixin:
    """Operator sugar for expression nodes (arithmetic + ordered comparison)."""

    def __add__(self, other) -> "Add":
        return Add(left=self, right=lift(other))

    def __radd__(self, other) -> "Add":
        return Add(left=lift(other), right=self)

    def __sub__(self, other) -> "Sub":
        return Sub(left=self, right=lift(other))

    def __rsub__(self, other) -> "Sub":
        return Sub(left=lift(other), right=self)

    def __mul__(self, other) -> "Mul":
        return Mul(left=self, right=lift(other))

    def __rmul__(self, other) -> "Mul":
        return Mul(left=lift(other), right=self)

    def __truediv__(self, other) -> "Div":
        return Div(left=self, right=lift(other))

    def __rtruediv__(self, other) -> "Div":
        return Div(left=lift(other), right=self)

    def __neg__(self) -> "Sub":
        return Sub(left=RealConst(value=0.0), right=self)

    def __lt__(self, other) -> "Cmp":
        return Cmp(op=CmpOp.LT, lhs=self, rhs=lift(other))

    def __le__(self, other) -> "Cmp":
        return Cmp(op=CmpOp.LE, lhs=self, rhs=lift(other))

    def __gt__(self, other) -> "Cmp":
        return Cmp(op=CmpOp.GT, lhs=self, rhs=lift(other))

    def __ge__(self, other) -> "Cmp":
        return Cmp(op=CmpOp.GE, lhs=self, rhs=lift(other))


# ---------------------------------------------------------------------------
# Entities (Def: entity)
# ---------------------------------------------------------------------------


class Entity(Node):
    """An entity ``e = (id_e, t_e, mu_e)``.

    ``modifiers`` is the modifier assignment function ``mu_e``; keys are
    expected to lie within those permitted for the type (Def: entity type
    modifiers function), but the catalogue is open to extension so arbitrary
    keys are accepted here and checked elsewhere.
    """

    id: str
    type: EntityType
    modifiers: dict[str, TypingUnion[bool, float, int, str]] = Field(default_factory=dict)


def _to_entity_id(v):
    """Accept an :class:`Entity`, a bound :class:`VarRef`, or a raw id string."""
    if isinstance(v, Entity):
        return v.id
    return v


# An entity-position argument: a concrete entity id or a bound variable.
EntityArg = Annotated[TypingUnion["VarRef", str], BeforeValidator(_to_entity_id)]


# ---------------------------------------------------------------------------
# Values / constants (Def: base values, values; constant expression)
# ---------------------------------------------------------------------------


class BoolConst(Node):
    node: Literal["bool"] = "bool"
    value: bool


class RealConst(ExprMixin, Node):
    node: Literal["real"] = "real"
    value: float


class TimeConst(ExprMixin, Node):
    """A time point in ``T``; ``"inf"`` denotes the greatest element."""

    node: Literal["time"] = "time"
    value: TypingUnion[float, Literal["inf"]]


class IntervalConst(Node):
    """An interval ``(t, d, l, r)`` (Def: interval)."""

    node: Literal["interval"] = "interval"
    start: float
    duration: float
    left_open: bool = False
    right_open: bool = False


class EventTypeLabelConst(Node):
    """An event-type label used as a value."""

    node: Literal["label"] = "label"
    value: EventTypeLabel


class EntityRef(Node):
    """A reference to a declared entity, usable as a value/expression leaf."""

    node: Literal["entity_ref"] = "entity_ref"
    entity: str


class VarRef(Node):
    """A bound variable introduced by ``Filter`` / ``ForAll`` / ``Exists``."""

    node: Literal["var"] = "var"
    name: str


class SetConst(Node):
    """A finite, flat set value (Def: values)."""

    node: Literal["set"] = "set"
    elements: list["ValueNode"] = Field(default_factory=list)


def lift(v):
    """Coerce a Python literal / entity into an expression node.

    Already-built nodes pass through unchanged; this is what lets the operator
    sugar and the convenience constructors accept ``3``, ``True`` or an
    :class:`Entity` interchangeably with node objects.
    """
    if isinstance(v, Entity):
        return EntityRef(entity=v.id)
    if isinstance(v, Node):
        return v
    if isinstance(v, bool):
        return BoolConst(value=v)
    if isinstance(v, (int, float)):
        return RealConst(value=float(v))
    if isinstance(v, EventTypeLabel):
        return EventTypeLabelConst(value=v)
    if isinstance(v, (set, frozenset, list, tuple)):
        return SetConst(elements=[lift(x) for x in v])
    # Anything else (e.g. a dict coming back from JSON parsing) is passed
    # through unchanged so the discriminated union validates it normally.
    return v


# An expression-position argument that lifts Python literals automatically.
ExprArg = Annotated["ExprNode", BeforeValidator(lift)]
ValueArg = Annotated["ValueNode", BeforeValidator(lift)]


# ---------------------------------------------------------------------------
# Expressions (Section: expressions and predicates -> expressions)
# ---------------------------------------------------------------------------


# -- Arithmetic operators (Def: arithmetic operators) --


class Add(ExprMixin, Node):
    node: Literal["add"] = "add"
    left: "ExprArg"
    right: "ExprArg"


class Sub(ExprMixin, Node):
    node: Literal["sub"] = "sub"
    left: "ExprArg"
    right: "ExprArg"


class Mul(ExprMixin, Node):
    node: Literal["mul"] = "mul"
    left: "ExprArg"
    right: "ExprArg"


class Div(ExprMixin, Node):
    node: Literal["div"] = "div"
    left: "ExprArg"
    right: "ExprArg"


# -- Time functions (Def: now / prev / next / reltime / diff) --


class _Now(ExprMixin, Node):
    """The ambient time point ``t`` (Def: current time)."""

    node: Literal["now"] = "now"


#: Singleton ambient-time expression. Write bare ``Now`` (not ``Now()``).
Now = _Now()


class Prev(ExprMixin, Node):
    """Preceding time step; discrete time only (Def: prev)."""

    node: Literal["prev"] = "prev"
    time: "ExprArg"


class Next(ExprMixin, Node):
    """Following time step; discrete time only (Def: next)."""

    node: Literal["next"] = "next"
    time: "ExprArg"


class RelTime(ExprMixin, Node):
    """Shift a time point by ``offset`` steps; discrete only (Def: reltime)."""

    node: Literal["reltime"] = "reltime"
    time: "ExprArg"
    offset: int


class Diff(ExprMixin, Node):
    """Duration between two time points (Def: diff)."""

    node: Literal["diff"] = "diff"
    a: "ExprArg"
    b: "ExprArg"


# -- Interval constructors and accessors --


class MkIntervalCC(Node):
    node: Literal["mk_interval_cc"] = "mk_interval_cc"
    start: "ExprArg"
    end: "ExprArg"


class MkIntervalOC(Node):
    node: Literal["mk_interval_oc"] = "mk_interval_oc"
    start: "ExprArg"
    end: "ExprArg"


class MkIntervalCO(Node):
    node: Literal["mk_interval_co"] = "mk_interval_co"
    start: "ExprArg"
    end: "ExprArg"


class MkIntervalOO(Node):
    node: Literal["mk_interval_oo"] = "mk_interval_oo"
    start: "ExprArg"
    end: "ExprArg"


class SinceZero(Node):
    """Interval from time zero to ``time`` (Def: since-zero interval)."""

    node: Literal["since_zero"] = "since_zero"
    time: "ExprArg"


class Start(ExprMixin, Node):
    node: Literal["start"] = "start"
    interval: "ExprArg"


class End(ExprMixin, Node):
    node: Literal["end"] = "end"
    interval: "ExprArg"


class IntervalDuration(ExprMixin, Node):
    """Duration of an interval (Def: interval duration)."""

    node: Literal["interval_duration"] = "interval_duration"
    interval: "ExprArg"


class IsLeftOpen(Node):
    node: Literal["is_left_open"] = "is_left_open"
    interval: "ExprArg"


class IsRightOpen(Node):
    node: Literal["is_right_open"] = "is_right_open"
    interval: "ExprArg"


# -- Entity attribute accessors (Def: modifier accessors) --


class Addr(ExprMixin, Node):
    """``address`` modifier of a ``Storage`` entity (Def: modifier accessors)."""

    node: Literal["addr"] = "addr"
    entity: EntityArg


class IsReg(Node):
    """``register`` flag of a ``Storage`` entity (Def: modifier accessors)."""

    node: Literal["is_reg"] = "is_reg"
    entity: EntityArg


class IsNonVol(Node):
    """``non_volatile`` flag of a ``Storage`` entity (Def: modifier accessors)."""

    node: Literal["is_non_vol"] = "is_non_vol"
    entity: EntityArg


class EvtTarget(Node):
    """``target`` modifier of an ``Event`` entity (Def: modifier accessors)."""

    node: Literal["evt_target"] = "evt_target"
    entity: EntityArg


class EvtType(Node):
    """``type`` modifier of an ``Event`` entity (Def: modifier accessors)."""

    node: Literal["evt_type"] = "evt_type"
    entity: EntityArg


# -- Trace functions --


class Val(ExprMixin, Node):
    """Value of entity ``e`` at time ``t`` (Def: expr val)."""

    node: Literal["val"] = "val"
    entity: EntityArg
    time: "ExprArg"


class ValBefore(ExprMixin, Node):
    """Left limit of the value of ``e`` at ``t`` (Def: value before time)."""

    node: Literal["val_before"] = "val_before"
    entity: EntityArg
    time: "ExprArg"


class EvtOccCount(ExprMixin, Node):
    """Number of occurrences of an event in an interval (Def: evt occ count)."""

    node: Literal["evt_occ_count"] = "evt_occ_count"
    event: EntityArg
    interval: "ExprArg"


class LastOcc(Node):
    """Interval over the ``n`` most recent occurrences up to ``time``."""

    node: Literal["last_occ"] = "last_occ"
    event: EntityArg
    time: "ExprArg"
    n: int = 1


class FirstOcc(Node):
    """Interval over the ``n`` earliest occurrences at/after ``time``."""

    node: Literal["first_occ"] = "first_occ"
    event: EntityArg
    time: "ExprArg"
    n: int = 1


class MaxVal(ExprMixin, Node):
    """Maximum value of ``e`` over an interval (Def: maximum value)."""

    node: Literal["max_val"] = "max_val"
    entity: EntityArg
    interval: "ExprArg"


class MinVal(ExprMixin, Node):
    """Minimum value of ``e`` over an interval (Def: minimum value)."""

    node: Literal["min_val"] = "min_val"
    entity: EntityArg
    interval: "ExprArg"


# -- Set functions (Def: set size / filter / ops / element add-discard) --


class Size(ExprMixin, Node):
    node: Literal["size"] = "size"
    set: "ExprArg"


class Filter(Node):
    """Subset of ``set`` whose elements (bound to ``var``) satisfy ``body``."""

    node: Literal["filter"] = "filter"
    set: "ExprArg"
    var: str
    body: "PredNode"

    @classmethod
    def of(cls, the_set, fn: Callable[["VarRef"], "PredNode"], var: str = "x") -> "Filter":
        """Build a ``Filter`` from a Python callable receiving the bound var."""
        return cls(set=lift(the_set), var=var, body=fn(VarRef(name=var)))


class Union(Node):
    """Union of two set values (Def: set union, intersection, and difference)."""

    node: Literal["union"] = "union"
    left: "ExprArg"
    right: "ExprArg"


class Intersection(Node):
    """Intersection of two set values (Def: set union, intersection, and difference)."""

    node: Literal["intersection"] = "intersection"
    left: "ExprArg"
    right: "ExprArg"


class Difference(Node):
    """Relative complement ``left`` minus ``right`` (Def: set union, intersection, and difference)."""

    node: Literal["difference"] = "difference"
    left: "ExprArg"
    right: "ExprArg"


# ---------------------------------------------------------------------------
# Predicates (Section: predicates) -- point-in-time, evaluate to bool
# ---------------------------------------------------------------------------


class TrueP(Node):
    """Always-true predicate ``T`` (Def: boolean constants)."""

    node: Literal["true"] = "true"


class FalseP(Node):
    """Always-false predicate ``_|_`` (Def: boolean constants)."""

    node: Literal["false"] = "false"


class Cmp(Node):
    """Comparison predicate ``a op b`` (Def: comparison predicate)."""

    node: Literal["cmp"] = "cmp"
    op: CmpOp
    lhs: "ExprArg"
    rhs: "ExprArg"


class Contains(Node):
    """Set membership ``v in s`` (Def: set membership)."""

    node: Literal["contains"] = "contains"
    value: "ExprArg"
    set: "ExprArg"


class IsEmpty(Node):
    """Set emptiness (Def: set emptiness)."""

    node: Literal["is_empty"] = "is_empty"
    set: "ExprArg"


class Subset(Node):
    """Subset relation, ``left`` included in ``right`` (Def: subset and superset)."""

    node: Literal["subset"] = "subset"
    left: "ExprArg"
    right: "ExprArg"


class Superset(Node):
    """Superset relation, ``left`` contains ``right`` (Def: subset and superset)."""

    node: Literal["superset"] = "superset"
    left: "ExprArg"
    right: "ExprArg"


class Disjoint(Node):
    """Set disjointness, empty intersection (Def: set disjointness)."""

    node: Literal["disjoint"] = "disjoint"
    left: "ExprArg"
    right: "ExprArg"


class InInterval(Node):
    """Time point falls within an interval (Def: time point interval membership)."""

    node: Literal["in_interval"] = "in_interval"
    time: "ExprArg"
    interval: "ExprArg"


class Not(Node):
    """Negation (Def: negation)."""

    node: Literal["not"] = "not"
    inner: "PredNode"


class AllOf(Node):
    """Conjunction of predicates (Def: conjunction and disjunction)."""

    node: Literal["all_of"] = "all_of"
    items: list["PredNode"]


class AnyOf(Node):
    """Disjunction of predicates (Def: conjunction and disjunction)."""

    node: Literal["any_of"] = "any_of"
    items: list["PredNode"]


class Implies(Node):
    """Implication ``A => B`` (Def: implication)."""

    node: Literal["implies"] = "implies"
    antecedent: "PredNode"
    consequent: "PredNode"


class ForAll(Node):
    """Universal quantifier over a finite set (Def: quantifiers)."""

    node: Literal["for_all"] = "for_all"
    domain: "ExprArg"
    var: str
    body: "PredNode"

    @classmethod
    def of(cls, domain, fn: Callable[["VarRef"], "PredNode"], var: str = "x") -> "ForAll":
        return cls(domain=lift(domain), var=var, body=fn(VarRef(name=var)))


class Exists(Node):
    """Existential quantifier over a finite set (Def: quantifiers)."""

    node: Literal["exists"] = "exists"
    domain: "ExprArg"
    var: str
    body: "PredNode"

    @classmethod
    def of(cls, domain, fn: Callable[["VarRef"], "PredNode"], var: str = "x") -> "Exists":
        return cls(domain=lift(domain), var=var, body=fn(VarRef(name=var)))


class Happening(Node):
    """Event occurs at ``time`` (Def: event happening)."""

    node: Literal["happening"] = "happening"
    entity: EntityArg
    time: "ExprArg"


class HasHappened(Node):
    """Event has occurred at or before ``time`` (Def: event has happened)."""

    node: Literal["has_happened"] = "has_happened"
    entity: EntityArg
    time: "ExprArg"


class IntervalIncludes(Node):
    node: Literal["interval_includes"] = "interval_includes"
    outer: "ExprArg"
    inner: "ExprArg"


class IntervalExcludes(Node):
    node: Literal["interval_excludes"] = "interval_excludes"
    first: "ExprArg"
    second: "ExprArg"


class StartOfFirstIntervalIn(Node):
    node: Literal["start_in"] = "start_in"
    first: "ExprArg"
    second: "ExprArg"


class EndOfFirstIntervalIn(Node):
    node: Literal["end_in"] = "end_in"
    first: "ExprArg"
    second: "ExprArg"


# ---------------------------------------------------------------------------
# Trace predicates (Section: temporal constructs) -- evaluate over a trace
# ---------------------------------------------------------------------------


class Always(Node):
    node: Literal["always"] = "always"
    inner: "PredNode"


class Eventually(Node):
    node: Literal["eventually"] = "eventually"
    inner: "PredNode"


class Initial(Node):
    """Holds at time 0 (Def: temporal constructs)."""

    node: Literal["initial"] = "initial"
    inner: "PredNode"


class Causes(Node):
    """Whenever ``cond`` holds, ``effect`` eventually follows."""

    node: Literal["causes"] = "causes"
    cond: "PredNode"
    effect: "PredNode"


class CausesWithin(Node):
    """``Causes`` with a duration bound ``[t, t + bound]``."""

    node: Literal["causes_within"] = "causes_within"
    cond: "PredNode"
    effect: "PredNode"
    bound: float


class Sequence(Node):
    """Existential ordered occurrence of the given predicates."""

    node: Literal["sequence"] = "sequence"
    steps: list["PredNode"]


class Precedes(Node):
    node: Literal["precedes"] = "precedes"
    first: "PredNode"
    second: "PredNode"


class Excludes(Node):
    node: Literal["excludes"] = "excludes"
    first: "PredNode"
    second: "PredNode"


class Immediately(Node):
    """If ``first`` holds at ``t`` then ``second`` holds at ``Next(t)``."""

    node: Literal["immediately"] = "immediately"
    first: "PredNode"
    second: "PredNode"


class TAnd(Node):
    """Conjunction of trace predicates."""

    node: Literal["trace_and"] = "trace_and"
    items: list["TracePredNode"]


class TOr(Node):
    """Disjunction of trace predicates."""

    node: Literal["trace_or"] = "trace_or"
    items: list["TracePredNode"]


class TNot(Node):
    node: Literal["trace_not"] = "trace_not"
    inner: "TracePredNode"


class TImplies(Node):
    node: Literal["trace_implies"] = "trace_implies"
    antecedent: "TracePredNode"
    consequent: "TracePredNode"


class TIff(Node):
    node: Literal["trace_iff"] = "trace_iff"
    left: "TracePredNode"
    right: "TracePredNode"


# ---------------------------------------------------------------------------
# Operations / stimuli (Section: operations; Def: stimulus)
# ---------------------------------------------------------------------------


class Calculate(Node):
    node: Literal["calculate"] = "calculate"
    time: float
    target: EntityArg
    expr: "ExprArg"


class Write(Node):
    node: Literal["write"] = "write"
    time: float
    target: EntityArg
    expr: "ExprArg"


class Read(Node):
    node: Literal["read"] = "read"
    time: float
    src: EntityArg
    dst: EntityArg


class Fire(Node):
    node: Literal["fire"] = "fire"
    time: float
    target: EntityArg


class SetState(Node):
    node: Literal["set_state"] = "set_state"
    time: float
    target: EntityArg
    state: "ValueArg"


class Transmit(Node):
    node: Literal["transmit"] = "transmit"
    time: float
    target: EntityArg
    expr: "ExprArg"


class Receive(Node):
    node: Literal["receive"] = "receive"
    time: float
    src: EntityArg
    dst: EntityArg


class Insert(Node):
    node: Literal["insert"] = "insert"
    time: float
    target: EntityArg
    value: "ValueArg"


class Remove(Node):
    node: Literal["remove"] = "remove"
    time: float
    target: EntityArg
    value: "ValueArg"


class Clear(Node):
    node: Literal["clear"] = "clear"
    time: float
    target: EntityArg


# ---------------------------------------------------------------------------
# Discriminated unions
# ---------------------------------------------------------------------------

ValueNode = Annotated[
    TypingUnion[BoolConst, RealConst, TimeConst, IntervalConst, EventTypeLabelConst, EntityRef, SetConst],
    Field(discriminator="node"),
]

ExprNode = Annotated[
    TypingUnion[
        BoolConst, RealConst, TimeConst, IntervalConst, EventTypeLabelConst, EntityRef, VarRef, SetConst,
        Add, Sub, Mul, Div,
        _Now, Prev, Next, RelTime, Diff,
        MkIntervalCC, MkIntervalOC, MkIntervalCO, MkIntervalOO, SinceZero,
        Start, End, IntervalDuration, IsLeftOpen, IsRightOpen,
        Addr, IsReg, IsNonVol, EvtTarget, EvtType,
        Val, ValBefore, EvtOccCount, LastOcc, FirstOcc, MaxVal, MinVal,
        Size, Filter, Union, Intersection, Difference,
    ],
    Field(discriminator="node"),
]

PredNode = Annotated[
    TypingUnion[
        TrueP, FalseP, Cmp, Contains, IsEmpty, Subset, Superset, Disjoint, InInterval,
        Not, AllOf, AnyOf, Implies, ForAll, Exists,
        Happening, HasHappened,
        IntervalIncludes, IntervalExcludes, StartOfFirstIntervalIn, EndOfFirstIntervalIn,
    ],
    Field(discriminator="node"),
]

TracePredNode = Annotated[
    TypingUnion[
        Always, Eventually, Initial, Causes, CausesWithin,
        Sequence, Precedes, Excludes, Immediately,
        TAnd, TOr, TNot, TImplies, TIff,
    ],
    Field(discriminator="node"),
]

StimulusNode = Annotated[
    TypingUnion[Calculate, Write, Read, Fire, SetState, Transmit, Receive, Insert, Remove, Clear],
    Field(discriminator="node"),
]


# ---------------------------------------------------------------------------
# Requirements & test cases (Section: requirements & test cases)
# ---------------------------------------------------------------------------


def _to_entity_id_list(v):
    if isinstance(v, (list, tuple, set)):
        return [_to_entity_id(x) for x in v]
    return v


class Requirement(Node):
    """A requirement ``R = (flavour, entities, constraint)`` (Def: requirement)."""

    id: str
    flavour: Flavour
    entities: Annotated[list[str], BeforeValidator(_to_entity_id_list)] = Field(default_factory=list)
    constraint: "TracePredNode"


class Assertion(Node):
    """Predicates a test verifies at a single time point."""

    time: float
    predicates: list["PredNode"]


def _lift_setup(v):
    if isinstance(v, dict):
        return {
            (_to_entity_id(k) if isinstance(k, Entity) else k): lift(val)
            for k, val in v.items()
        }
    return v


class TestCase(Node):
    """A test case ``(setup, stimuli, assertions)`` (Def: test case)."""

    id: str
    setup: Annotated[dict[str, "ValueNode"], BeforeValidator(_lift_setup)] = Field(default_factory=dict)
    stimuli: list["StimulusNode"] = Field(default_factory=list)
    assertions: list[Assertion] = Field(default_factory=list)


class Module(Node):
    """A shared-entity context binding requirements and test cases together.

    Both requirements and test cases operate over the same entity set ``E``;
    declaring entities once here is what makes coverage checking meaningful.
    """

    entities: list[Entity] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def Eq(a, b) -> Cmp:
    """Equality comparison ``a = b`` (``__eq__`` is reserved by Pydantic)."""
    return Cmp(op=CmpOp.EQ, lhs=lift(a), rhs=lift(b))


def Ne(a, b) -> Cmp:
    """Inequality comparison ``a != b``."""
    return Cmp(op=CmpOp.NE, lhs=lift(a), rhs=lift(b))


def mkset(*items) -> SetConst:
    """Build a :class:`SetConst` from entities / literals."""
    return SetConst(elements=[lift(x) for x in items])


# ---------------------------------------------------------------------------
# Resolve forward references for every node model
# ---------------------------------------------------------------------------

for _obj in list(globals().values()):
    if inspect.isclass(_obj) and issubclass(_obj, BaseModel) and _obj is not BaseModel:
        _obj.model_rebuild()
