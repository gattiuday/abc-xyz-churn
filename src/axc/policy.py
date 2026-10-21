"""What a class is used for, and what changing it costs.

A classification is not an end in itself. It drives a policy: how often an item
is reviewed, what service level it is held to, how much safety stock it carries,
whether a planner looks at it by hand. So a class change is a work order.

This module attaches an ordinary policy to each class and counts the changes.
The policy values are conventions and are declared as such; what matters is that
they differ by class, which is the whole reason a classification exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from axc.errors import UnusableAssortment

__all__ = ["POLICY", "Policy", "changes_between", "policy_for", "stabilise"]


@dataclass(frozen=True)
class Policy:
    """What an item of a given class is managed to."""

    review_weeks: int
    service_level: float
    safety_factor: float
    reviewed_by_hand: bool


#: Class to policy. A to C by value, X to Z by variability, which is the usual
#: shape: the valuable and steady items are reviewed often and held tightly, and
#: the cheap erratic ones are left to a rule.
POLICY = {
    "AX": Policy(1, 0.98, 1.4, True),
    "AY": Policy(1, 0.97, 1.9, True),
    "AZ": Policy(2, 0.95, 2.6, True),
    "BX": Policy(2, 0.96, 1.3, False),
    "BY": Policy(2, 0.95, 1.7, False),
    "BZ": Policy(4, 0.93, 2.3, False),
    "CX": Policy(4, 0.94, 1.1, False),
    "CY": Policy(4, 0.92, 1.5, False),
    "CZ": Policy(13, 0.90, 2.0, False),
}


def policy_for(klass: str) -> Policy:
    if klass not in POLICY:
        raise UnusableAssortment(
            f"no policy for class '{klass}'; expected one of {', '.join(sorted(POLICY))}"
        )
    return POLICY[klass]


def changes_between(before: np.ndarray, after: np.ndarray) -> dict[str, int]:
    """How much policy work a reclassification creates.

    Counted per dimension rather than as one number, because they are different
    kinds of work. A review cadence change is a planner's calendar; a safety
    factor change is stock on the floor; moving an item in or out of hand review
    is a person's workload.
    """
    if before.shape != after.shape:
        raise UnusableAssortment(
            f"before and after must describe the same assortment, got {before.shape} "
            f"and {after.shape}"
        )
    counts = {"class": 0, "review_weeks": 0, "safety_factor": 0, "hand_review": 0}
    for old, new in zip(before, after, strict=True):
        if old == new:
            continue
        counts["class"] += 1
        first, second = policy_for(str(old)), policy_for(str(new))
        counts["review_weeks"] += int(first.review_weeks != second.review_weeks)
        counts["safety_factor"] += int(first.safety_factor != second.safety_factor)
        counts["hand_review"] += int(first.reviewed_by_hand != second.reviewed_by_hand)
    return counts


def stabilise(sequence: list[np.ndarray], periods: int = 2) -> list[np.ndarray]:
    """Hold an item's class until a new one has persisted for `periods` periods.

    The cheapest stabiliser there is and the one most planning systems could
    implement in an afternoon. It trades promptness for stability: a real
    transition is acted on late by up to `periods` minus one periods, and a
    one period excursion is never acted on at all.

    What it costs and what it buys are measured in `experiments/exp03` rather
    than argued here. Returning the held sequence rather than mutating lets the
    two be compared on the same classifications.
    """
    if periods < 1:
        raise UnusableAssortment(f"a hold of {periods} periods is not a hold")
    if not sequence:
        raise UnusableAssortment("an empty sequence of classifications cannot be stabilised")

    held = [sequence[0].copy()]
    pending = [None] * len(sequence[0])
    streak = [0] * len(sequence[0])
    for current in sequence[1:]:
        out = held[-1].copy()
        for index, proposed in enumerate(current):
            if proposed == out[index]:
                pending[index], streak[index] = None, 0
                continue
            if pending[index] == proposed:
                streak[index] += 1
            else:
                pending[index], streak[index] = proposed, 1
            if streak[index] >= periods:
                out[index] = proposed
                pending[index], streak[index] = None, 0
        held.append(out)
    return held
