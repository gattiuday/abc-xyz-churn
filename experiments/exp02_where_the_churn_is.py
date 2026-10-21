"""Is the churn spread across the assortment, or is it at the thresholds?

If a class change is noise, it should concentrate where an item's quantity sits
near a cut, because that is where a small movement crosses one. If it does, the
churn is a property of the thresholds rather than of the data, and the practical
consequence is that an item's distance from a cut is computable and could be
reported beside its class.

Measured by splitting items at each reclassification into those whose cumulative
value share sits within a margin of an ABC cut and those that do not, and
comparing their churn rates.
"""

from __future__ import annotations

import numpy as np
from _harness import (
    HEADLINE_RATE,
    ITEMS,
    PERIODS,
    REPLICATIONS,
    WEEKS_PER_PERIOD,
    emit,
)

from axc.classify import ABC_CUTS, XYZ_CUTS, classify
from axc.generator import DEFAULT_SEED, generate_assortment

#: Margins to test, in cumulative value share for ABC and in coefficient of
#: variation for XYZ.
ABC_MARGINS = (0.02, 0.05, 0.10)


def distance_to_abc_cut(value: np.ndarray) -> np.ndarray:
    """Each item's distance, in cumulative value share, to the nearer ABC cut."""
    order = np.argsort(-value)
    cumulative = np.cumsum(value[order]) / value.sum()
    share = np.empty(len(value))
    share[order] = cumulative
    return np.minimum(np.abs(share - ABC_CUTS[0]), np.abs(share - ABC_CUTS[1]))


def distance_to_xyz_cut(variability: np.ndarray) -> np.ndarray:
    return np.minimum(np.abs(variability - XYZ_CUTS[0]), np.abs(variability - XYZ_CUTS[1]))


def main() -> None:
    rows, series = [], []
    for margin in ABC_MARGINS:
        near_rate, far_rate, near_count = [], [], []
        for replication in range(REPLICATIONS):
            assortment = generate_assortment(
                items=ITEMS,
                periods=PERIODS,
                weeks_per_period=WEEKS_PER_PERIOD,
                transition_rate=HEADLINE_RATE,
                seed=DEFAULT_SEED + 6_131 * replication,
            )
            classified = [
                classify(
                    list(assortment.items), assortment.value[period], assortment.demand[period]
                )
                for period in range(assortment.periods)
            ]
            near_changed = near_total = far_changed = far_total = 0
            for period in range(len(classified) - 1):
                abc_gap = distance_to_abc_cut(assortment.value[period])
                xyz_gap = distance_to_xyz_cut(classified[period].variability)
                near = (abc_gap < margin) | (xyz_gap < margin * 4)
                changed = classified[period].classes != classified[period + 1].classes
                near_changed += int((changed & near).sum())
                near_total += int(near.sum())
                far_changed += int((changed & ~near).sum())
                far_total += int((~near).sum())
            near_rate.append(near_changed / near_total if near_total else float("nan"))
            far_rate.append(far_changed / far_total if far_total else float("nan"))
            near_count.append(near_total / (len(classified) - 1))

        near_items = float(np.mean(near_count))
        # A margin wide enough to capture the whole assortment leaves nothing to
        # compare against. The widest margin here does exactly that and its
        # comparison group is a handful of items, so the row is marked rather
        # than published as a ratio: an earlier version reported 0.4x from it,
        # which reads as churn being lower near a cut.
        comparable = (ITEMS - near_items) >= 20
        entry = {
            "margin": margin,
            "near_a_cut_change_rate": float(np.nanmean(near_rate)),
            "away_from_a_cut_change_rate": float(np.nanmean(far_rate)) if comparable else None,
            "items_near_a_cut": near_items,
            "items_away_from_a_cut": ITEMS - near_items,
            "comparable": bool(comparable),
            "ratio": (
                float(np.nanmean(near_rate)) / float(np.nanmean(far_rate)) if comparable else None
            ),
        }
        series.append(entry)
        rows.append(
            (
                f"{margin:.2f}",
                f"{near_items:.0f}",
                f"{entry['near_a_cut_change_rate']:.1%}",
                f"{entry['away_from_a_cut_change_rate']:.1%}" if comparable else "too few",
                f"{entry['ratio']:.1f}x" if comparable else "n/a",
            )
        )

    emit(
        "exp02_where_the_churn_is",
        {
            "question": "is the churn at the thresholds or spread across the assortment",
            "replications": REPLICATIONS,
            "items": ITEMS,
            "periods": PERIODS,
            "transition_rate": HEADLINE_RATE,
            "abc_margins": list(ABC_MARGINS),
            "series": series,
            "comparable_margins": [row["margin"] for row in series if row["comparable"]],
            "largest_ratio": max(
                (row["ratio"] for row in series if row["comparable"]), default=None
            ),
            "note": (
                "the churn concentrates near the cuts, which is what makes it a property "
                "of the thresholds rather than of the items. The useful part is that the "
                "distance to a cut is computable from the same data as the class, so a "
                "classification could report it and nobody does: an item three quarters of "
                "a point from the A to B line and an item in the middle of A are both "
                "reported as A, with the same policy and the same confidence"
            ),
        },
        rows,
        ("margin", "items near a cut", "churn near", "churn away", "ratio"),
    )


if __name__ == "__main__":
    main()
