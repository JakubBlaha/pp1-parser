"""Type-compatibility tests decoded from the formalism.

These assert the verifier REJECTS ill-typed inputs. They are written against
``resources/formalism/tex-new/formalism.tex`` -- the spec -- and NOT against the
current implementation, so that they reveal where the verifier is wrong.

Two kinds of tests live here:

* Rules the verifier already enforces -- the layer discipline
  (Expr / Pred / TracePred), via Pydantic's discriminated unions -- are plain
  passing tests.

* Rules the verifier does NOT yet enforce are marked ``xfail(strict=True)`` with
  a reason citing the formalism. They currently fail (the verifier wrongly
  accepts the input); once enforcement is added they will XPASS and the strict
  marker turns that into a failure, prompting removal of the marker.
"""

import pytest
from pydantic import ValidationError

from verifier import *  # noqa: F401,F403

SIGNAL = Entity(id="sig", type=EntityType.SIGNAL)
STORE = Entity(id="store", type=EntityType.STORAGE)
EVENT = Entity(id="ev", type=EntityType.EVENT, modifiers={"target": "sig", "type": "written"})


# ---------------------------------------------------------------------------
# Layer discipline (Expr / Pred / TracePred) -- the verifier enforces these.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        # Temporal constructs take a point-in-time Pred (def:temporal_constructs).
        pytest.param(lambda: Always(inner=Always(inner=TrueP())), id="temporal_given_tracepred"),
        pytest.param(lambda: Always(inner=Val(entity=SIGNAL, time=Now)), id="temporal_given_expr"),
        pytest.param(lambda: Causes(cond=RealConst(value=1), effect=TrueP()), id="causes_cond_given_expr"),
        # Pred combinators take Preds (def:pred_not / def:pred_allandany / def:pred_implies).
        pytest.param(lambda: AllOf(items=[Eventually(inner=TrueP())]), id="allof_given_tracepred"),
        pytest.param(lambda: Not(inner=Now), id="not_given_expr"),
        pytest.param(lambda: Implies(antecedent=Eventually(inner=TrueP()), consequent=TrueP()), id="implies_given_tracepred"),
        # Trace combinators take TracePreds (temporal-constructs composition).
        pytest.param(lambda: TAnd(items=[Happening(entity=EVENT, time=Now)]), id="trace_and_given_pred"),
        pytest.param(lambda: TNot(inner=Happening(entity=EVENT, time=Now)), id="trace_not_given_pred"),
        # Cmp / set-fn operands are expressions, not predicates (def:pred_cmp / def:size).
        pytest.param(lambda: Cmp(op=CmpOp.EQ, lhs=Happening(entity=EVENT, time=Now), rhs=RealConst(value=1)), id="cmp_given_pred"),
        pytest.param(lambda: Size(set=Happening(entity=EVENT, time=Now)), id="size_given_pred"),
        # Filter's body is a Pred (def:filter).
        pytest.param(lambda: Filter(set=mkset(SIGNAL), var="x", body=Val(entity=SIGNAL, time=Now)), id="filter_body_given_expr"),
        # A requirement's constraint is a TracePred (def:requirement).
        pytest.param(
            lambda: Requirement(id="R", flavour=Flavour.DISCRETE, entities=[EVENT],
                                constraint=Happening(entity=EVENT, time=Now)),
            id="requirement_constraint_given_pred",
        ),
    ],
)
def test_layer_violation_is_rejected(build):
    with pytest.raises(ValidationError):
        build()


# ---------------------------------------------------------------------------
# Operator sugar blocks a few incompatible uses at construction (TypeError).
# This is the Python-level guard from stripping ExprMixin off non-numeric nodes
# and not giving predicates boolean operators.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: EntityRef(entity="a") + 3, id="arith_on_entity_ref"),
        pytest.param(lambda: mkset(SIGNAL) < 5, id="order_on_set"),
        pytest.param(lambda: LastOcc(event=EVENT, time=Now) + 1, id="arith_on_interval"),
        pytest.param(lambda: Union(left=mkset(SIGNAL), right=mkset(STORE)) > 2, id="order_on_set_op"),
        pytest.param(lambda: IsReg(entity=STORE) + 1, id="arith_on_bool_accessor"),
        pytest.param(lambda: Happening(entity=EVENT, time=Now) & Happening(entity=EVENT, time=Now), id="and_on_predicates"),
    ],
)
def test_operator_sugar_blocks_incompatible_use(build):
    with pytest.raises(TypeError):
        build()


# ---------------------------------------------------------------------------
# Well-typed inputs the verifier must keep accepting (guards against over-rejection).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: Add(left=Val(entity=SIGNAL, time=Now), right=RealConst(value=3)), id="arith_on_val"),
        pytest.param(lambda: Cmp(op=CmpOp.EQ, lhs=mkset(SIGNAL), rhs=mkset(SIGNAL)), id="equality_on_sets"),
        pytest.param(lambda: Happening(entity=EVENT, time=Now), id="happening_on_event"),
        pytest.param(lambda: Always(inner=Eq(Val(entity=SIGNAL, time=Now), RealConst(value=1))), id="always_of_pred"),
    ],
)
def test_well_typed_is_accepted(build):
    build()  # must not raise


# ---------------------------------------------------------------------------
# Semantic type rules, enforced by the verifier's validation pass.
# Each wraps the ill-typed snippet in a minimal module and asserts the pass
# rejects it (InvalidModule). These need context (entity table / flavour) that
# a single node cannot check at construction.
# ---------------------------------------------------------------------------


def _check_pred(pred, entities=(), flavour=Flavour.DISCRETE):
    validate(Module(
        entities=list(entities),
        requirements=[Requirement(id="R", flavour=flavour, entities=list(entities),
                                  constraint=Always(inner=pred))],
    ))


def _check_expr(expr, entities=(), flavour=Flavour.DISCRETE):
    _check_pred(Eq(expr, RealConst(value=0)), entities, flavour)


def _check_stimulus(stim, entities=()):
    validate(Module(entities=list(entities), test_cases=[TestCase(id="T", stimuli=[stim])]))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_expr(Add(left=EntityRef(entity="sig"), right=RealConst(value=3)), [SIGNAL]), id="add_entity_and_real"),
        pytest.param(lambda: _check_expr(Mul(left=mkset(SIGNAL), right=RealConst(value=2)), [SIGNAL]), id="mul_set_and_real"),
    ],
)
def test_arithmetic_requires_numeric_operands(build):
    with pytest.raises(InvalidModule):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_pred(Cmp(op=CmpOp.LT, lhs=mkset(SIGNAL), rhs=mkset(STORE)), [SIGNAL, STORE]), id="lt_on_sets"),
        pytest.param(lambda: _check_pred(Cmp(op=CmpOp.GT, lhs=EntityRef(entity="sig"), rhs=EntityRef(entity="store")), [SIGNAL, STORE]), id="gt_on_entities"),
    ],
)
def test_ordered_comparison_requires_ordered_domain(build):
    with pytest.raises(InvalidModule):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_expr(Size(set=RealConst(value=3))), id="size_of_real"),
        pytest.param(lambda: _check_expr(Union(left=RealConst(value=1), right=RealConst(value=2))), id="union_of_reals"),
        pytest.param(lambda: _check_pred(Contains(value=RealConst(value=1), set=RealConst(value=2))), id="contains_in_real"),
    ],
)
def test_set_functions_require_set_operands(build):
    with pytest.raises(InvalidModule):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_pred(Happening(entity=SIGNAL, time=Now), [SIGNAL]), id="happening_on_signal"),
        pytest.param(lambda: _check_expr(EvtOccCount(event=SIGNAL, interval=SinceZero(time=Now)), [SIGNAL]), id="evtocccount_on_signal"),
    ],
)
def test_event_predicates_require_event_entities(build):
    with pytest.raises(InvalidModule):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_expr(Addr(entity=SIGNAL), [SIGNAL]), id="addr_on_signal"),
        pytest.param(lambda: _check_expr(EvtType(entity=STORE), [STORE]), id="evttype_on_storage"),
    ],
)
def test_modifier_accessor_requires_matching_entity_type(build):
    with pytest.raises(InvalidModule):
        build()


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_stimulus(Write(time=0, target=SIGNAL, expr=RealConst(value=1)), [SIGNAL]), id="write_to_signal"),
        pytest.param(lambda: _check_stimulus(Fire(time=0, target=SIGNAL), [SIGNAL]), id="fire_non_trigger"),
    ],
)
def test_operation_requires_matching_target_type(build):
    with pytest.raises(InvalidModule):
        build()


def test_discrete_only_function_in_continuous_flavour_is_rejected():
    with pytest.raises(InvalidModule):
        _check_pred(
            Eq(Val(entity=SIGNAL, time=Prev(time=Now)), RealConst(value=0)),
            [SIGNAL], flavour=Flavour.CONTINUOUS,
        )


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda: _check_pred(Happening(entity="ghost", time=Now)), id="entity_position"),
        pytest.param(lambda: _check_expr(EntityRef(entity="ghost")), id="entity_ref_node"),
        pytest.param(lambda: _check_stimulus(Fire(time=0, target="ghost")), id="stimulus_target"),
    ],
)
def test_undeclared_entity_reference_is_rejected(build):
    with pytest.raises(InvalidModule):
        build()


def test_well_typed_passes_validation():
    # Sanity: well-typed constraints survive the validation pass.
    _check_pred(Happening(entity=EVENT, time=Now), [EVENT])
    _check_expr(Add(left=Val(entity=SIGNAL, time=Now), right=RealConst(value=3)), [SIGNAL])
    _check_pred(Cmp(op=CmpOp.EQ, lhs=mkset(SIGNAL), rhs=mkset(SIGNAL)), [SIGNAL])
