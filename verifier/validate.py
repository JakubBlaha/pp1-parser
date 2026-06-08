"""Semantic validation pass over a :class:`Module`.

Pydantic enforces the *structural* layer discipline (Expr / Pred / TracePred).
This pass adds the *semantic* rules from the formalism that need context -- the
entity table and the requirement flavour -- which a single node cannot check on
its own:

* arithmetic operands must be numeric (def:arithmetic);
* ordered comparison ``< <= > >=`` needs an ordered (numeric) domain (def:pred_cmp);
* set functions take set operands (def:size, def:set_ops, def:filter, ...);
* event predicates/accessors take ``Event`` entities; modifier accessors take
  ``Storage``; operations target the type from the operations table;
* ``Prev`` / ``Next`` / ``RelTime`` are discrete-time only (def:prev/next/reltime);
* every referenced entity is declared in the module's entity set (def:requirement,
  ``entities`` subset of ``E``).

A sort is inferred for every expression; the polymorphic nodes whose sort cannot
be known statically (``Val``, ``ValBefore``, ``MaxVal``, ``MinVal``, a bound
``VarRef``) are treated as ``UNKNOWN`` and accepted everywhere, so the pass never
rejects a *possibly* well-typed term.
"""

from dataclasses import dataclass
from enum import Enum

from .lib import *  # noqa: F401,F403
from .lib import _Now as _NowNode


class Sort(str, Enum):
    BOOL = "bool"
    NUMERIC = "numeric"      # reals, naturals, time points, durations -- ordered & arithmetic
    INTERVAL = "interval"
    SET = "set"
    ENTITY = "entity"
    LABEL = "label"
    UNKNOWN = "unknown"      # statically unknown -> accepted everywhere


_NUMERICISH = {Sort.NUMERIC, Sort.UNKNOWN}
_SETTISH = {Sort.SET, Sort.UNKNOWN}
_INTERVALISH = {Sort.INTERVAL, Sort.UNKNOWN}


class InvalidModule(Exception):
    """Raised by :func:`validate` when a module breaks the formalism's type rules."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("invalid module:\n  - " + "\n  - ".join(self.errors))


@dataclass
class _Ctx:
    types: dict          # entity id -> EntityType
    flavour: object      # Flavour or None (test cases have no single flavour)


# ---------------------------------------------------------------------------
# Operand requirement helpers
# ---------------------------------------------------------------------------


def _require(allowed, node, ctx, errs, what):
    s = expr_sort(node, ctx, errs)
    if s not in allowed:
        names = " or ".join(x.value for x in allowed if x is not Sort.UNKNOWN)
        errs.append(f"{what} must be {names}, got {s.value}")
    return s


def _require_entity(entity, allowed, ctx, errs, what):
    if isinstance(entity, VarRef):
        return  # bound variable -- type unknown, accept
    etype = ctx.types.get(entity)
    if etype is None:
        errs.append(f"{what} references undeclared entity '{entity}'")
        return
    if allowed is not None and etype not in allowed:
        names = " or ".join(a.value for a in allowed)
        errs.append(f"{what} expects a {names} entity, but '{entity}' is {etype.value}")


# ---------------------------------------------------------------------------
# Sort inference for expressions
# ---------------------------------------------------------------------------


def expr_sort(n, ctx, errs) -> Sort:
    match n:
        case BoolConst():
            return Sort.BOOL
        case RealConst() | TimeConst():
            return Sort.NUMERIC
        case IntervalConst():
            return Sort.INTERVAL
        case EventTypeLabelConst():
            return Sort.LABEL
        case EntityRef():
            if n.entity not in ctx.types:
                errs.append(f"references undeclared entity '{n.entity}'")
            return Sort.ENTITY
        case VarRef():
            return Sort.UNKNOWN
        case SetConst():
            for el in n.elements:
                if expr_sort(el, ctx, errs) is Sort.SET:
                    errs.append("set literal elements must be non-set values")
            return Sort.SET
        case Add() | Sub() | Mul() | Div():
            _require(_NUMERICISH, n.left, ctx, errs, "arithmetic operand")
            _require(_NUMERICISH, n.right, ctx, errs, "arithmetic operand")
            return Sort.NUMERIC
        case _NowNode():
            return Sort.NUMERIC
        case Prev() | Next() | RelTime():
            if ctx.flavour is Flavour.CONTINUOUS:
                errs.append(f"{type(n).__name__} is defined for discrete time only")
            _require(_NUMERICISH, n.time, ctx, errs, f"{type(n).__name__} argument")
            return Sort.NUMERIC
        case Diff():
            _require(_NUMERICISH, n.a, ctx, errs, "Diff argument")
            _require(_NUMERICISH, n.b, ctx, errs, "Diff argument")
            return Sort.NUMERIC
        case MkIntervalCC() | MkIntervalOC() | MkIntervalCO() | MkIntervalOO():
            _require(_NUMERICISH, n.start, ctx, errs, "interval endpoint")
            _require(_NUMERICISH, n.end, ctx, errs, "interval endpoint")
            return Sort.INTERVAL
        case SinceZero():
            _require(_NUMERICISH, n.time, ctx, errs, "SinceZero argument")
            return Sort.INTERVAL
        case Start() | End() | IntervalDuration():
            _require(_INTERVALISH, n.interval, ctx, errs, f"{type(n).__name__} argument")
            return Sort.NUMERIC
        case IsLeftOpen() | IsRightOpen():
            _require(_INTERVALISH, n.interval, ctx, errs, f"{type(n).__name__} argument")
            return Sort.BOOL
        case Addr():
            _require_entity(n.entity, {EntityType.STORAGE}, ctx, errs, "Addr")
            return Sort.NUMERIC
        case IsReg() | IsNonVol():
            _require_entity(n.entity, {EntityType.STORAGE}, ctx, errs, type(n).__name__)
            return Sort.BOOL
        case EvtTarget():
            _require_entity(n.entity, {EntityType.EVENT}, ctx, errs, "EvtTarget")
            return Sort.ENTITY
        case EvtType():
            _require_entity(n.entity, {EntityType.EVENT}, ctx, errs, "EvtType")
            return Sort.LABEL
        case Val() | ValBefore():
            _require_entity(n.entity, None, ctx, errs, type(n).__name__)
            _require(_NUMERICISH, n.time, ctx, errs, f"{type(n).__name__} time")
            return Sort.UNKNOWN
        case EvtOccCount():
            _require_entity(n.event, {EntityType.EVENT}, ctx, errs, "EvtOccCount")
            _require(_INTERVALISH, n.interval, ctx, errs, "EvtOccCount interval")
            return Sort.NUMERIC
        case LastOcc() | FirstOcc():
            _require_entity(n.event, {EntityType.EVENT}, ctx, errs, type(n).__name__)
            _require(_NUMERICISH, n.time, ctx, errs, f"{type(n).__name__} time")
            return Sort.INTERVAL
        case MaxVal() | MinVal():
            _require_entity(n.entity, None, ctx, errs, type(n).__name__)
            _require(_INTERVALISH, n.interval, ctx, errs, f"{type(n).__name__} interval")
            return Sort.UNKNOWN
        case Size():
            _require(_SETTISH, n.set, ctx, errs, "Size argument")
            return Sort.NUMERIC
        case Filter():
            _require(_SETTISH, n.set, ctx, errs, "Filter set")
            check_pred(n.body, ctx, errs)
            return Sort.SET
        case Union() | Intersection() | Difference():
            _require(_SETTISH, n.left, ctx, errs, f"{type(n).__name__} operand")
            _require(_SETTISH, n.right, ctx, errs, f"{type(n).__name__} operand")
            return Sort.SET
        case _:
            return Sort.UNKNOWN


# ---------------------------------------------------------------------------
# Point-in-time predicates
# ---------------------------------------------------------------------------


def check_pred(n, ctx, errs) -> None:
    match n:
        case TrueP() | FalseP():
            pass
        case Cmp():
            ls = expr_sort(n.lhs, ctx, errs)
            rs = expr_sort(n.rhs, ctx, errs)
            if n.op in (CmpOp.LT, CmpOp.LE, CmpOp.GT, CmpOp.GE):
                if ls not in _NUMERICISH:
                    errs.append(f"ordered comparison needs an ordered left operand, got {ls.value}")
                if rs not in _NUMERICISH:
                    errs.append(f"ordered comparison needs an ordered right operand, got {rs.value}")
        case Contains():
            if expr_sort(n.value, ctx, errs) is Sort.SET:
                errs.append("Contains value must be a non-set")
            _require(_SETTISH, n.set, ctx, errs, "Contains set")
        case IsEmpty():
            _require(_SETTISH, n.set, ctx, errs, "IsEmpty argument")
        case Subset() | Superset() | Disjoint():
            _require(_SETTISH, n.left, ctx, errs, f"{type(n).__name__} operand")
            _require(_SETTISH, n.right, ctx, errs, f"{type(n).__name__} operand")
        case InInterval():
            _require(_NUMERICISH, n.time, ctx, errs, "InInterval time")
            _require(_INTERVALISH, n.interval, ctx, errs, "InInterval interval")
        case Not():
            check_pred(n.inner, ctx, errs)
        case AllOf() | AnyOf():
            for p in n.items:
                check_pred(p, ctx, errs)
        case Implies():
            check_pred(n.antecedent, ctx, errs)
            check_pred(n.consequent, ctx, errs)
        case ForAll() | Exists():
            _require(_SETTISH, n.domain, ctx, errs, f"{type(n).__name__} domain")
            check_pred(n.body, ctx, errs)
        case Happening() | HasHappened():
            _require_entity(n.entity, {EntityType.EVENT}, ctx, errs, type(n).__name__)
            _require(_NUMERICISH, n.time, ctx, errs, f"{type(n).__name__} time")
        case IntervalIncludes():
            _require(_INTERVALISH, n.outer, ctx, errs, "IntervalIncludes operand")
            _require(_INTERVALISH, n.inner, ctx, errs, "IntervalIncludes operand")
        case IntervalExcludes() | StartOfFirstIntervalIn() | EndOfFirstIntervalIn():
            _require(_INTERVALISH, n.first, ctx, errs, f"{type(n).__name__} operand")
            _require(_INTERVALISH, n.second, ctx, errs, f"{type(n).__name__} operand")
        case _:
            pass


# ---------------------------------------------------------------------------
# Trace predicates (temporal constructs)
# ---------------------------------------------------------------------------


def check_trace(n, ctx, errs) -> None:
    match n:
        case Always() | Eventually() | Initial():
            check_pred(n.inner, ctx, errs)
        case Causes() | CausesWithin():
            check_pred(n.cond, ctx, errs)
            check_pred(n.effect, ctx, errs)
        case Sequence():
            for p in n.steps:
                check_pred(p, ctx, errs)
        case Precedes() | Excludes() | Immediately():
            check_pred(n.first, ctx, errs)
            check_pred(n.second, ctx, errs)
        case TAnd() | TOr():
            for t in n.items:
                check_trace(t, ctx, errs)
        case TNot():
            check_trace(n.inner, ctx, errs)
        case TImplies():
            check_trace(n.antecedent, ctx, errs)
            check_trace(n.consequent, ctx, errs)
        case TIff():
            check_trace(n.left, ctx, errs)
            check_trace(n.right, ctx, errs)
        case _:
            pass


# ---------------------------------------------------------------------------
# Stimuli (operation target types, from the operations table)
# ---------------------------------------------------------------------------


def check_stimulus(s, ctx, errs) -> None:
    match s:
        case Calculate():
            _require_entity(s.target, {EntityType.SIGNAL}, ctx, errs, "calculate target")
            expr_sort(s.expr, ctx, errs)
        case Write():
            _require_entity(s.target, {EntityType.STORAGE}, ctx, errs, "write target")
            expr_sort(s.expr, ctx, errs)
        case Read():
            _require_entity(s.src, {EntityType.STORAGE}, ctx, errs, "read source")
            _require_entity(s.dst, {EntityType.SIGNAL}, ctx, errs, "read destination")
        case Fire():
            _require_entity(s.target, {EntityType.EVENT_TRIGGER}, ctx, errs, "fire target")
        case SetState():
            _require_entity(s.target, {EntityType.STATE}, ctx, errs, "set_state target")
            expr_sort(s.state, ctx, errs)
        case Transmit():
            _require_entity(s.target, {EntityType.CHANNEL}, ctx, errs, "transmit target")
            expr_sort(s.expr, ctx, errs)
        case Receive():
            _require_entity(s.src, {EntityType.CHANNEL}, ctx, errs, "receive source")
            _require_entity(s.dst, {EntityType.SIGNAL}, ctx, errs, "receive destination")
        case Insert() | Remove():
            _require_entity(s.target, {EntityType.SET}, ctx, errs, f"{type(s).__name__} target")
            if expr_sort(s.value, ctx, errs) is Sort.SET:
                errs.append(f"{type(s).__name__} value must be a non-set")
        case Clear():
            _require_entity(s.target, {EntityType.SET}, ctx, errs, "clear target")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def validate(module) -> None:
    """Check ``module`` against the formalism's type rules; raise on any violation."""
    types = {e.id: e.type for e in module.entities}
    errs: list[str] = []

    for req in module.requirements:
        ctx = _Ctx(types=types, flavour=req.flavour)
        check_trace(req.constraint, ctx, errs)

    for tc in module.test_cases:
        ctx = _Ctx(types=types, flavour=None)  # a test case has no single flavour
        for stim in tc.stimuli:
            check_stimulus(stim, ctx, errs)
        for assertion in tc.assertions:
            for pred in assertion.predicates:
                check_pred(pred, ctx, errs)

    if errs:
        raise InvalidModule(errs)
