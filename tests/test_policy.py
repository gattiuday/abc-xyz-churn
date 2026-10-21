"""The policy attached to a class, and the stabiliser."""

from __future__ import annotations

import numpy as np
import pytest

from axc.errors import UnusableAssortment
from axc.policy import POLICY, changes_between, policy_for, stabilise


def test_every_class_in_the_scheme_has_a_policy():
    for first in "ABC":
        for second in "XYZ":
            assert policy_for(f"{first}{second}") in POLICY.values()


def test_an_unknown_class_has_no_policy():
    with pytest.raises(UnusableAssortment, match="no policy for class"):
        policy_for("DQ")


def test_an_unchanged_assortment_creates_no_work():
    before = np.array(["AX", "BY", "CZ"], dtype=object)
    assert changes_between(before, before.copy())["class"] == 0


def test_a_change_within_one_policy_dimension_is_counted_once():
    before = np.array(["AX"], dtype=object)
    after = np.array(["AY"], dtype=object)
    counts = changes_between(before, after)
    assert counts["class"] == 1
    assert counts["safety_factor"] == 1
    assert counts["hand_review"] == 0


def test_moving_an_item_out_of_hand_review_is_counted():
    counts = changes_between(np.array(["AX"], dtype=object), np.array(["BX"], dtype=object))
    assert counts["hand_review"] == 1


def test_mismatched_assortments_are_refused():
    with pytest.raises(UnusableAssortment, match="same assortment"):
        changes_between(np.array(["AX"], dtype=object), np.array(["AX", "BY"], dtype=object))


def test_a_one_period_excursion_is_never_acted_on_under_a_two_period_hold():
    sequence = [
        np.array(["AX"], dtype=object),
        np.array(["BX"], dtype=object),
        np.array(["AX"], dtype=object),
    ]
    held = stabilise(sequence, 2)
    assert [str(step[0]) for step in held] == ["AX", "AX", "AX"]


def test_a_persistent_change_is_acted_on_once_it_persists():
    sequence = [
        np.array(["AX"], dtype=object),
        np.array(["BX"], dtype=object),
        np.array(["BX"], dtype=object),
    ]
    held = stabilise(sequence, 2)
    assert [str(step[0]) for step in held] == ["AX", "AX", "BX"]


def test_a_hold_of_zero_is_refused():
    with pytest.raises(UnusableAssortment, match="is not a hold"):
        stabilise([np.array(["AX"], dtype=object)], 0)


def test_an_empty_sequence_cannot_be_stabilised():
    with pytest.raises(UnusableAssortment, match="empty sequence"):
        stabilise([], 2)


def test_switching_proposals_resets_the_streak():
    """An item oscillating between two new classes never settles on either."""
    sequence = [
        np.array(["AX"], dtype=object),
        np.array(["BX"], dtype=object),
        np.array(["CX"], dtype=object),
        np.array(["BX"], dtype=object),
    ]
    held = stabilise(sequence, 2)
    assert all(str(step[0]) == "AX" for step in held)
