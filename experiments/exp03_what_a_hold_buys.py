"""What does the cheapest stabiliser cost, and what does it buy?

If most reclassification is noise, the obvious remedy is to require a new class
to persist before acting on it. That is one line in a planning system and it is
not free: a real transition is acted on late, and an item that genuinely moved
spends a period or two under the wrong policy.

Both sides are measured here. The cost is the delay on real transitions and the
real moves never acted on at all. The benefit is the churn removed. A hold of
one period is the unstabilised case and is included so the table has its own
baseline.
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

from axc.classify import classify
from axc.generator import DEFAULT_SEED, generate_assortment
from axc.policy import changes_between, stabilise

#: Periods a new class must persist before it is acted on. One is no hold.
HOLDS = (1, 2, 3)


def main() -> None:
    series, rows = [], []
    for hold in HOLDS:
        churn, hand, delay, missed, real = [], [], [], [], []
        for replication in range(REPLICATIONS):
            assortment = generate_assortment(
                items=ITEMS,
                periods=PERIODS,
                weeks_per_period=WEEKS_PER_PERIOD,
                transition_rate=HEADLINE_RATE,
                seed=DEFAULT_SEED + 6_131 * replication,
            )
            raw = [
                classify(
                    list(assortment.items), assortment.value[period], assortment.demand[period]
                ).classes
                for period in range(assortment.periods)
            ]
            held = stabilise(raw, hold)

            changes = hand_moves = 0
            for period in range(len(held) - 1):
                counts = changes_between(held[period], held[period + 1])
                changes += counts["class"]
                hand_moves += counts["hand_review"]
            churn.append(changes)
            hand.append(hand_moves)

            # For each item that genuinely moved tier, how long until the held
            # classification reflected whatever the unheld one said at the time
            # of the move, and whether it ever did.
            waits, never = [], 0
            moves = 0
            for period in range(1, assortment.periods):
                for index in np.flatnonzero(assortment.tier_changed[period]):
                    moves += 1
                    target = raw[period][index]
                    if target == held[period - 1][index]:
                        waits.append(0)
                        continue
                    wait = None
                    for ahead in range(period, assortment.periods):
                        if held[ahead][index] == target:
                            wait = ahead - period
                            break
                    if wait is None:
                        never += 1
                    else:
                        waits.append(wait)
            delay.append(float(np.mean(waits)) if waits else 0.0)
            missed.append(never)
            real.append(moves)

        entry = {
            "hold_periods": hold,
            "class_changes": float(np.mean(churn)),
            "hand_review_moves": float(np.mean(hand)),
            "mean_delay_on_a_real_move_periods": float(np.mean(delay)),
            "real_moves_never_reflected": float(np.mean(missed)),
            "real_moves": float(np.mean(real)),
        }
        series.append(entry)
        rows.append(
            (
                f"{hold}",
                f"{entry['class_changes']:.0f}",
                f"{entry['hand_review_moves']:.0f}",
                f"{entry['mean_delay_on_a_real_move_periods']:.2f}",
                f"{entry['real_moves_never_reflected']:.0f}",
            )
        )

    baseline, best = series[0], series[1]
    emit(
        "exp03_what_a_hold_buys",
        {
            "question": "what does holding a class for a period cost, and what does it remove",
            "replications": REPLICATIONS,
            "items": ITEMS,
            "periods": PERIODS,
            "transition_rate": HEADLINE_RATE,
            "holds": list(HOLDS),
            "series": series,
            "churn_removed_share": 1 - best["class_changes"] / baseline["class_changes"],
            "delay_cost_periods": best["mean_delay_on_a_real_move_periods"]
            - baseline["mean_delay_on_a_real_move_periods"],
            "note": (
                "a two period hold removes most of the churn and costs a fraction of a "
                "period of delay on the moves that are real. That is a good trade and it is "
                "not a free one, which is the reason to measure both columns. What it does "
                "not do is make the classification right: the items whose class is noise are "
                "still assigned a class, and the hold only stops that assignment changing "
                "every quarter"
            ),
        },
        rows,
        ("hold", "class changes", "hand review moves", "delay on a real move", "never reflected"),
    )


if __name__ == "__main__":
    main()
