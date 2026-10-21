"""Fixtures shared across the suite."""

from __future__ import annotations

import pytest

from axc.classify import classify
from axc.generator import generate_assortment


@pytest.fixture(scope="session")
def assortment():
    return generate_assortment(items=300, periods=8)


@pytest.fixture(scope="session")
def still_assortment():
    """An assortment where no item ever changes tier, so all churn is noise."""
    return generate_assortment(items=300, periods=8, transition_rate=0.0)


@pytest.fixture(scope="session")
def classes(assortment):
    return [
        classify(
            list(assortment.items), assortment.value[period], assortment.demand[period]
        ).classes
        for period in range(assortment.periods)
    ]
