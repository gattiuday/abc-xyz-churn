"""The checks that make the figures mean anything, written before the prose."""

from __future__ import annotations

import numpy as np
import pytest

from axc.classify import ABC_CUTS, classify
from axc.generator import VALUE_TIERS, generate_assortment
from axc.policy import changes_between, policy_for, stabilise


def test_an_item_that_never_changes_tier_still_changes_class(still_assortment):
    """The control, and the repository's whole finding in one assertion.

    No item in this assortment ever changes tier, so every class change is
    produced by sampling, by the rank of other items, or by an item sitting near
    a threshold. There are hundreds of them.
    """
    assert still_assortment.real_transitions == 0
    classified = [
        classify(
            list(still_assortment.items),
            still_assortment.value[period],
            still_assortment.demand[period],
        ).classes
        for period in range(still_assortment.periods)
    ]
    changes = sum(
        changes_between(classified[period], classified[period + 1])["class"]
        for period in range(len(classified) - 1)
    )
    assert changes > 300, f"only {changes} class changes with nothing changing"


def test_most_class_changes_have_no_real_move_behind_them(assortment, classes):
    """The headline, pinned at the assortment level."""
    changed = justified = 0
    for period in range(len(classes) - 1):
        moved = assortment.tier_changed[period + 1]
        differs = classes[period] != classes[period + 1]
        changed += int(differs.sum())
        justified += int((differs & moved).sum())
    assert changed > 0
    assert justified / changed < 0.25, (
        f"{justified / changed:.1%} of class changes had a real move behind them, which "
        "would refute this repository's central claim"
    )


def test_every_class_has_a_policy_and_the_policies_differ(classes):
    """A classification whose classes shared a policy would cost nothing to churn."""
    seen = {str(klass) for period in classes for klass in period}
    assert seen
    policies = {klass: policy_for(klass) for klass in seen}
    assert (
        len({(p.review_weeks, p.safety_factor, p.reviewed_by_hand) for p in policies.values()}) > 1
    )


def test_a_class_change_is_counted_once_per_dimension_it_moves(classes):
    """The policy dimensions are different kinds of work and are counted apart."""
    counts = changes_between(classes[0], classes[1])
    assert counts["class"] >= counts["review_weeks"]
    assert counts["class"] >= counts["safety_factor"]
    assert counts["class"] >= counts["hand_review"]


def test_holding_a_class_removes_churn_and_delays_real_moves(assortment, classes):
    """Both sides of the trade, because the benefit alone would be an advert."""
    held = stabilise(classes, 2)
    raw_changes = sum(
        changes_between(classes[p], classes[p + 1])["class"] for p in range(len(classes) - 1)
    )
    held_changes = sum(changes_between(held[p], held[p + 1])["class"] for p in range(len(held) - 1))
    assert held_changes < raw_changes / 2

    # And it costs: some real moves are never reflected at all.
    never = 0
    for period in range(1, assortment.periods):
        for index in np.flatnonzero(assortment.tier_changed[period]):
            target = classes[period][index]
            if not any(held[ahead][index] == target for ahead in range(period, assortment.periods)):
                never += 1
    assert never > 0, "the hold cost nothing, which would mean it removed nothing real"


def test_a_hold_of_one_period_changes_nothing(classes):
    """The baseline, so the table has its own control."""
    held = stabilise(classes, 1)
    for original, kept in zip(classes, held, strict=True):
        assert list(original) == list(kept)


def test_the_classifier_never_sees_a_tier(assortment):
    """Enforced by reading the source, because the grading depends on it."""
    import inspect

    from axc import classify as classify_module
    from axc import policy as policy_module

    for module in (classify_module, policy_module):
        code = inspect.getsource(module)
        for token in ("value_tier", "variability_tier", "tier_changed", "VALUE_TIERS"):
            assert token not in code, f"{module.__name__} mentions {token}"


def test_the_abc_curve_cuts_where_the_convention_says(assortment):
    """A for the first eighty per cent of value, and the cut is the convention."""
    classified = classify(list(assortment.items), assortment.value[0], assortment.demand[0])
    a_value = assortment.value[0][classified.abc == "A"].sum()
    assert a_value / assortment.value[0].sum() <= ABC_CUTS[0] + 0.05


def test_the_tiers_are_far_enough_apart_to_be_recoverable():
    """Said out loud, because if they were not the finding would be about that.

    A generator whose tiers overlapped would churn because the tiers are
    indistinguishable, which is a different claim. These are separated by a
    factor of nearly five at each step.
    """
    values = sorted(VALUE_TIERS.values())
    assert values[1] / values[0] > 3.0
    assert values[2] / values[1] > 3.0


def test_an_assortment_too_small_for_interior_thresholds_is_refused():
    from axc.errors import UnusableAssortment

    with pytest.raises(UnusableAssortment, match="too few for an ABC curve"):
        generate_assortment(items=5)


def test_an_assortment_whose_shapes_disagree_is_refused():
    from axc.errors import UnusableAssortment
    from axc.generator import Assortment

    with pytest.raises(UnusableAssortment, match="demand has"):
        Assortment(
            items=("A", "B"),
            demand=np.zeros((2, 3, 1)),
            value=np.zeros((2, 1)),
            value_tier=np.empty((2, 1), dtype=object),
            variability_tier=np.empty((2, 1), dtype=object),
            tier_changed=np.zeros((2, 1), dtype=bool),
        )


def test_a_value_array_of_the_wrong_shape_is_refused():
    from axc.errors import UnusableAssortment
    from axc.generator import Assortment

    with pytest.raises(UnusableAssortment, match="value must be periods by items"):
        Assortment(
            items=("A",),
            demand=np.zeros((2, 3, 1)),
            value=np.zeros((5, 1)),
            value_tier=np.empty((2, 1), dtype=object),
            variability_tier=np.empty((2, 1), dtype=object),
            tier_changed=np.zeros((2, 1), dtype=bool),
        )


def test_a_single_period_cannot_be_reclassified():
    from axc.errors import UnusableAssortment

    with pytest.raises(UnusableAssortment, match="at least two periods"):
        generate_assortment(items=20, periods=1)


def test_a_transition_rate_that_is_not_a_share_is_refused():
    from axc.errors import UnusableAssortment

    with pytest.raises(UnusableAssortment, match="is not a share"):
        generate_assortment(items=20, transition_rate=0.9)
