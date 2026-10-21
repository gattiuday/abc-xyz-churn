"""Command line entry point: generate, churn, hold, boundaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from axc.classify import ABC_CUTS, classify
from axc.errors import ClassificationError, UnusableAssortment
from axc.generator import Assortment, generate_assortment
from axc.policy import changes_between, policy_for, stabilise

__all__ = ["main", "read_assortment", "write_assortment"]

COLUMNS = ("item", "period", "week", "demand", "value", "value_tier", "variability_tier", "moved")


def write_assortment(assortment: Assortment, path: Path) -> None:
    records = []
    for period in range(assortment.periods):
        for week in range(assortment.weeks_per_period):
            for index, item in enumerate(assortment.items):
                records.append(
                    {
                        "item": item,
                        "period": period,
                        "week": week,
                        "demand": assortment.demand[period, week, index],
                        "value": assortment.value[period, index] if week == 0 else 0.0,
                        "value_tier": assortment.value_tier[period, index],
                        "variability_tier": assortment.variability_tier[period, index],
                        "moved": bool(assortment.tier_changed[period, index]),
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(path, index=False, float_format="%.4f")


def read_assortment(path: Path) -> Assortment:
    frame = pd.read_csv(path)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise UnusableAssortment(
            f"{path} is missing column(s) {', '.join(missing)}; this is not an assortment "
            "this tool can read"
        )
    if frame.empty:
        raise ClassificationError(
            f"{path} contains no rows, so there is nothing to classify; this is undefined "
            "rather than a stable assortment"
        )
    items = sorted(frame["item"].unique())
    periods = sorted(frame["period"].unique())
    weeks = sorted(frame["week"].unique())
    demand = np.zeros((len(periods), len(weeks), len(items)))
    value = np.zeros((len(periods), len(items)))
    tiers_value = np.empty((len(periods), len(items)), dtype=object)
    tiers_var = np.empty((len(periods), len(items)), dtype=object)
    moved = np.zeros((len(periods), len(items)), dtype=bool)
    index_of = {item: position for position, item in enumerate(items)}
    for row in frame.itertuples():
        column = index_of[row.item]
        demand[row.period, row.week, column] = row.demand
        if row.week == 0:
            value[row.period, column] = row.value
            tiers_value[row.period, column] = row.value_tier
            tiers_var[row.period, column] = row.variability_tier
            moved[row.period, column] = bool(row.moved)
    return Assortment(
        items=tuple(items),
        demand=demand,
        value=value,
        value_tier=tiers_value,
        variability_tier=tiers_var,
        tier_changed=moved,
    )


def _classes(assortment: Assortment) -> list[np.ndarray]:
    return [
        classify(
            list(assortment.items), assortment.value[period], assortment.demand[period]
        ).classes
        for period in range(assortment.periods)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="axc", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("generate", help="write an assortment with the true tiers")
    make.add_argument("--out", type=Path, required=True)
    make.add_argument("--items", type=int, default=300)
    make.add_argument("--transition-rate", type=float, default=0.05)

    churn = sub.add_parser("churn", help="how much reclassification has a real move behind it")
    churn.add_argument("--assortment", type=Path, required=True)

    hold = sub.add_parser("hold", help="what holding a class for a period costs and removes")
    hold.add_argument("--assortment", type=Path, required=True)

    near = sub.add_parser("boundaries", help="items sitting closest to an ABC cut")
    near.add_argument("--assortment", type=Path, required=True)
    near.add_argument("--top", type=int, default=10)

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            assortment = generate_assortment(items=args.items, transition_rate=args.transition_rate)
            write_assortment(assortment, args.out)
            print(f"wrote {len(assortment.items)} items over {assortment.periods} periods")
            return 0

        assortment = read_assortment(args.assortment)
        classes = _classes(assortment)

        if args.command == "churn":
            changed = justified = hand = 0
            for period in range(len(classes) - 1):
                counts = changes_between(classes[period], classes[period + 1])
                changed += counts["class"]
                hand += counts["hand_review"]
                differs = classes[period] != classes[period + 1]
                justified += int((differs & assortment.tier_changed[period + 1]).sum())
            share = justified / changed if changed else 0.0
            print(f"class changes: {changed}")
            print(f"with a real move behind them: {justified} ({share:.1%})")
            print(f"items moved in or out of hand review: {hand}")
            print()
            print("the second line is not computable without the true tiers, which a real")
            print("assortment does not have; the first and third are")
            return 1 if share < 0.5 else 0

        if args.command == "hold":
            print(f"{'hold':>5s} {'class changes':>14s} {'hand review moves':>18s}")
            print("-" * 40)
            for periods in (1, 2, 3):
                held = stabilise(classes, periods)
                changes = sum(
                    changes_between(held[p], held[p + 1])["class"] for p in range(len(held) - 1)
                )
                hand = sum(
                    changes_between(held[p], held[p + 1])["hand_review"]
                    for p in range(len(held) - 1)
                )
                print(f"{periods:5d} {changes:14d} {hand:18d}")
            print()
            print("a hold removes churn and delays the moves that are real; both are costs")
            return 0

        first = classify(list(assortment.items), assortment.value[0], assortment.demand[0])
        order = np.argsort(-assortment.value[0])
        cumulative = np.cumsum(assortment.value[0][order]) / assortment.value[0].sum()
        share = np.empty(len(assortment.items))
        share[order] = cumulative
        gap = np.minimum(np.abs(share - ABC_CUTS[0]), np.abs(share - ABC_CUTS[1]))
        print(f"{'item':12s} {'class':>6s} {'share':>8s} {'to a cut':>9s} {'hand review':>12s}")
        print("-" * 52)
        for index in np.argsort(gap)[: args.top]:
            klass = first.of(assortment.items[index])
            print(
                f"{assortment.items[index]:12s} {klass:>6s} {share[index]:8.3f} "
                f"{gap[index]:9.3f} {policy_for(klass).reviewed_by_hand!s:>12s}"
            )
        print()
        print("every item above is reported with the same confidence as one in the middle")
        print("of its class, and the distance is computable from the same data")
        return 0
    except UnusableAssortment as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except ClassificationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised by the console script
    raise SystemExit(main())
