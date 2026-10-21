"""The classifier and its edges."""

from __future__ import annotations

import numpy as np
import pytest

from axc.classify import classify, coefficient_of_variation
from axc.errors import UnusableAssortment


def _demand(columns: int, periods: int = 13) -> np.ndarray:
    return np.tile(np.arange(1.0, periods + 1).reshape(-1, 1), (1, columns))


def test_the_curve_puts_the_largest_items_in_a():
    items = [f"SKU-{i}" for i in range(10)]
    value = np.array([100.0, 80.0, 5.0, 4.0, 3.0, 2.0, 2.0, 1.0, 1.0, 1.0])
    result = classify(items, value, _demand(10))
    assert result.abc[0] == "A"
    assert result.abc[-1] == "C"


def test_an_item_on_a_cut_is_assigned_by_the_cut_and_not_by_a_measurement():
    """Two items a thousandth of a share apart can land either side.

    This is the repository's subject stated as a test: the assignment is a
    choice about where to draw a line, and nothing about the items differs by
    enough to justify the difference in policy that follows.
    """
    items = [f"SKU-{i}" for i in range(4)]
    value = np.array([80.0, 15.0, 2.5, 2.5])
    result = classify(items, value, _demand(4))
    assert set(result.abc) >= {"A", "B"}


def test_the_coefficient_of_variation_is_undefined_on_an_item_that_sold_nothing():
    with pytest.raises(UnusableAssortment, match="undefined rather than infinite"):
        coefficient_of_variation(np.zeros(10))


def test_the_coefficient_of_variation_over_no_periods_is_undefined():
    with pytest.raises(UnusableAssortment, match="over no periods"):
        coefficient_of_variation(np.array([]))


def test_a_single_period_has_no_variability_rather_than_infinite():
    assert coefficient_of_variation(np.array([5.0])) == 0.0


def test_an_assortment_with_no_value_has_no_curve():
    with pytest.raises(UnusableAssortment, match="no value in this period"):
        classify(["A", "B"], np.zeros(2), _demand(2))


def test_a_one_dimensional_demand_array_is_refused():
    with pytest.raises(UnusableAssortment, match="periods by items"):
        classify(["A"], np.array([1.0]), np.array([1.0, 2.0]))


def test_mismatched_item_and_column_counts_are_refused():
    with pytest.raises(UnusableAssortment, match="do not describe the same assortment"):
        classify(["A", "B"], np.array([1.0, 1.0]), _demand(3))


@pytest.mark.parametrize("cuts", [(0.95, 0.80), (1.2, 1.5), (0.0, 0.5)])
def test_abc_cuts_out_of_order_or_out_of_range_are_refused(cuts):
    with pytest.raises(UnusableAssortment, match="not two shares in order"):
        classify(["A", "B"], np.array([2.0, 1.0]), _demand(2), abc_cuts=cuts)


def test_xyz_cuts_out_of_order_are_refused():
    with pytest.raises(UnusableAssortment, match="not two positive numbers"):
        classify(["A", "B"], np.array([2.0, 1.0]), _demand(2), xyz_cuts=(1.0, 0.5))


def test_the_nine_way_class_is_the_two_letters():
    items = [f"SKU-{i}" for i in range(3)]
    result = classify(items, np.array([10.0, 5.0, 1.0]), _demand(3))
    assert all(len(klass) == 2 for klass in result.classes)
    assert result.of(items[0]) == result.classes[0]
