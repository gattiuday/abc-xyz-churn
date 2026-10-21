"""An assortment whose items have a true type, so reclassification can be graded.

Each item is given a value tier and a variability tier that it keeps. Every
period its demand is drawn from those parameters, so two consecutive periods
differ by sampling and nothing else, and any class change between them is noise
by construction.

A small share of items do genuinely change tier, because an assortment where
nothing ever changes would make every reclassification noise and the finding
trivial. The share is recorded, so the share of observed churn that is real is a
measurement rather than an assumption.

Nothing in `classify.py` or `policy.py` sees the tiers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from axc.errors import UnusableAssortment

__all__ = ["DEFAULT_SEED", "Assortment", "generate_assortment"]

DEFAULT_SEED = 20261021

#: Value tiers, as a multiplier on the assortment's base value. Chosen so the
#: resulting ABC curve puts roughly the conventional shares in each class, which
#: is what makes the thresholds meaningful rather than arbitrary here.
VALUE_TIERS = {"high": 24.0, "mid": 5.0, "low": 1.0}

#: Variability tiers, as a coefficient of variation the item's demand is drawn to
#: have. Placed either side of the conventional XYZ cuts and one squarely on a
#: cut, because an item sitting on a threshold is the case the repository is
#: about.
VARIABILITY_TIERS = {"steady": 0.30, "boundary": 0.50, "erratic": 0.85}


@dataclass(frozen=True)
class Assortment:
    """One assortment over several periods, with the true tiers recorded."""

    items: tuple[str, ...]
    demand: np.ndarray
    value: np.ndarray
    value_tier: np.ndarray
    variability_tier: np.ndarray
    tier_changed: np.ndarray

    def __post_init__(self) -> None:
        periods, items = self.demand.shape[0], self.demand.shape[2]
        if items != len(self.items):
            raise UnusableAssortment(f"{len(self.items)} items but demand has {items} columns")
        if self.value.shape != (periods, items):
            raise UnusableAssortment(
                f"value must be periods by items, got {self.value.shape} for {periods} "
                f"periods and {items} items"
            )

    @property
    def periods(self) -> int:
        return self.demand.shape[0]

    @property
    def weeks_per_period(self) -> int:
        return self.demand.shape[1]

    @property
    def real_transitions(self) -> int:
        """Items that genuinely changed tier at some point, which is the signal."""
        return int(self.tier_changed.any(axis=0).sum())


def generate_assortment(
    items: int = 300,
    periods: int = 8,
    weeks_per_period: int = 13,
    transition_rate: float = 0.05,
    seed: int = DEFAULT_SEED,
) -> Assortment:
    """An assortment reclassified every quarter for two years.

    `transition_rate` is the share of items that genuinely change tier at each
    boundary. A real assortment has some: products mature, promotions end,
    competitors arrive. The point of recording it is that the share of observed
    churn which is real can then be measured.
    """
    if items < 10:
        raise UnusableAssortment(
            f"{items} items is too few for an ABC curve to have interior thresholds"
        )
    if periods < 2:
        raise UnusableAssortment("reclassification needs at least two periods to compare")
    if not 0.0 <= transition_rate < 0.5:
        raise UnusableAssortment(f"a transition rate of {transition_rate} is not a share")

    rng = np.random.default_rng(seed)
    value_names = list(VALUE_TIERS)
    variability_names = list(VARIABILITY_TIERS)

    # The tiers an assortment starts with. Weighted so most items are low value,
    # which is what an ABC curve looks like on any real assortment.
    value_tier = rng.choice(value_names, size=items, p=[0.12, 0.28, 0.60])
    variability_tier = rng.choice(variability_names, size=items, p=[0.35, 0.3, 0.35])

    demand = np.zeros((periods, weeks_per_period, items))
    value = np.zeros((periods, items))
    tiers_value = np.empty((periods, items), dtype=object)
    tiers_variability = np.empty((periods, items), dtype=object)
    changed = np.zeros((periods, items), dtype=bool)

    unit_value = rng.uniform(0.6, 1.6, items)
    for period in range(periods):
        if period > 0:
            moving = rng.random(items) < transition_rate
            for index in np.flatnonzero(moving):
                # A tier change is to an adjacent tier, because a product does
                # not go from the top of the assortment to the bottom in a
                # quarter, and a generator that let it would make the real
                # transitions trivially easy to tell from the noise.
                position = value_names.index(value_tier[index])
                step = rng.choice([-1, 1])
                value_tier[index] = value_names[int(np.clip(position + step, 0, 2))]
            changed[period] = moving
        tiers_value[period] = value_tier
        tiers_variability[period] = variability_tier

        base = np.array([VALUE_TIERS[tier] for tier in value_tier])
        spread = np.array([VARIABILITY_TIERS[tier] for tier in variability_tier])
        # Lognormal with the requested coefficient of variation, so an item's
        # measured variability is an estimate of its tier and not the tier.
        sigma = np.sqrt(np.log1p(spread**2))
        mu = np.log(base * 40.0) - sigma**2 / 2
        draws = rng.lognormal(mu, sigma, (weeks_per_period, items))
        demand[period] = draws
        value[period] = draws.sum(axis=0) * unit_value

    return Assortment(
        items=tuple(f"SKU-{index:04d}" for index in range(items)),
        demand=demand,
        value=value,
        value_tier=tiers_value,
        variability_tier=tiers_variability,
        tier_changed=changed,
    )
