"""Of the items that change class each quarter, how many actually changed?

The question a reclassification answers implicitly. An item's class is a rank
against the rest of the assortment, cut at thresholds nobody derived, computed
from an estimate of its variability. All three of those move between periods
without the item moving.

The generator gives every item a tier it keeps, so a class change with no tier
change is noise by construction. A share of items do change tier, because an
assortment where nothing changes makes every reclassification noise and the
finding trivial.
"""

from __future__ import annotations

import numpy as np
from _harness import (
    HEADLINE_RATE,
    ITEMS,
    PERIODS,
    REPLICATIONS,
    TRANSITION_RATES,
    WEEKS_PER_PERIOD,
    emit,
)

from axc.classify import classify
from axc.generator import DEFAULT_SEED, generate_assortment
from axc.policy import changes_between


def measure(rate: float) -> dict:
    churn, real, justified, hand = [], [], [], []
    for replication in range(REPLICATIONS):
        assortment = generate_assortment(
            items=ITEMS,
            periods=PERIODS,
            weeks_per_period=WEEKS_PER_PERIOD,
            transition_rate=rate,
            seed=DEFAULT_SEED + 6_131 * replication,
        )
        classes = [
            classify(
                list(assortment.items), assortment.value[period], assortment.demand[period]
            ).classes
            for period in range(assortment.periods)
        ]
        changed = moved = hand_moves = backed = 0
        for period in range(len(classes) - 1):
            counts = changes_between(classes[period], classes[period + 1])
            changed += counts["class"]
            hand_moves += counts["hand_review"]
            truth = assortment.tier_changed[period + 1]
            moved += int(truth.sum())
            # A class change on an item that genuinely moved tier in the same
            # period. Not every real transition produces a class change and not
            # every class change on a moved item is caused by the move, so this
            # is an upper bound on how much of the churn is justified.
            backed += int(((classes[period] != classes[period + 1]) & truth).sum())
        churn.append(changed)
        real.append(moved)
        justified.append(backed)
        hand.append(hand_moves)

    changes = float(np.mean(churn))
    return {
        "transition_rate": rate,
        "class_changes": changes,
        "class_changes_per_item_per_period": changes / (ITEMS * (PERIODS - 1)),
        "real_tier_changes": float(np.mean(real)),
        "changes_with_a_real_move_behind_them": float(np.mean(justified)),
        "justified_share": float(np.mean(justified)) / changes if changes else 0.0,
        "hand_review_moves": float(np.mean(hand)),
    }


def main() -> None:
    series = [measure(rate) for rate in TRANSITION_RATES]
    headline = next(row for row in series if row["transition_rate"] == HEADLINE_RATE)
    emit(
        "exp01_how_much_churn_is_real",
        {
            "question": "of the items that change class each quarter, how many actually changed",
            "replications": REPLICATIONS,
            "items": ITEMS,
            "periods": PERIODS,
            "headline_transition_rate": HEADLINE_RATE,
            "series": series,
            "headline": headline,
            "note": (
                "a class is a rank against the rest of the assortment, cut at thresholds "
                "nobody derived, computed from an estimate of variability. All three move "
                "between periods without the item moving, and the result is that most of "
                "what a quarterly reclassification produces is not a change in the item. "
                "The row at a transition rate of zero is the control: every class change "
                "there is noise by construction and there are nearly as many of them"
            ),
        },
        [
            (
                f"{row['transition_rate'] * 100:.1f}",
                f"{row['class_changes']:.0f}",
                f"{row['real_tier_changes']:.0f}",
                f"{row['justified_share']:.1%}",
                f"{row['hand_review_moves']:.0f}",
            )
            for row in series
        ],
        ("real moves pts", "class changes", "real tier changes", "justified", "hand review moves"),
    )


if __name__ == "__main__":
    main()
