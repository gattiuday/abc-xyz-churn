"""ABC and XYZ classification, and the two arbitrary choices inside it.

ABC sorts items by value and cuts the cumulative curve at two thresholds. XYZ
sorts by coefficient of variation and cuts at two more. An item's class is where
it falls relative to those four numbers and relative to every other item in the
assortment. The numbers themselves are below, declared as the conventions they
are, and every document that quotes them is checked against them.

Two things follow and neither is usually said out loud. The thresholds are
conventions with no derivation, so an item near one is assigned by a choice
rather than by a measurement. And an ABC class is a rank, so an item's class can
change because another item moved: nothing about the item itself need differ.

A policy keyed to class inherits both. This module computes the classes; the
rest of the package measures what the policy inherits.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from axc.errors import UnusableAssortment

__all__ = ["ABC_CUTS", "XYZ_CUTS", "Classification", "classify", "coefficient_of_variation"]

#: Cumulative value shares at which A becomes B and B becomes C. The convention,
#: and the thing an item near a boundary is assigned by.
ABC_CUTS = (0.80, 0.95)

#: Coefficient of variation at which X becomes Y and Y becomes Z. Also a
#: convention, and a less defensible one: 0.5 and 1.0 are round numbers.
XYZ_CUTS = (0.5, 1.0)


def coefficient_of_variation(demand: np.ndarray) -> float:
    """Standard deviation over mean, which is what XYZ ranks on.

    Undefined at a mean of zero rather than infinite. An item that sold nothing
    has no variability to speak of and no class, and reporting it as the most
    variable item in the assortment is how a dead item ends up in Z and in
    whatever policy Z carries.
    """
    if len(demand) == 0:
        raise UnusableAssortment("a coefficient of variation over no periods is undefined")
    mean = float(demand.mean())
    if mean <= 0:
        raise UnusableAssortment(
            "this item sold nothing in the period, so its coefficient of variation is "
            "undefined rather than infinite"
        )
    return float(demand.std(ddof=1) / mean) if len(demand) > 1 else 0.0


@dataclass(frozen=True)
class Classification:
    """One assortment's classes, with the quantities they were derived from."""

    items: tuple[str, ...]
    value: np.ndarray
    variability: np.ndarray
    abc: np.ndarray
    xyz: np.ndarray

    @property
    def classes(self) -> np.ndarray:
        """The nine way class, as a string per item."""
        return np.array([f"{a}{x}" for a, x in zip(self.abc, self.xyz, strict=True)])

    def of(self, item: str) -> str:
        index = self.items.index(item)
        return f"{self.abc[index]}{self.xyz[index]}"


def classify(
    items: list[str],
    value: np.ndarray,
    demand: np.ndarray,
    abc_cuts: tuple[float, float] = ABC_CUTS,
    xyz_cuts: tuple[float, float] = XYZ_CUTS,
) -> Classification:
    """Assign an ABC and an XYZ class to every item.

    `demand` is periods by items, so the variability is computed per column.
    `value` is the period's value per item, which is what the ABC curve is cut
    on.
    """
    if demand.ndim != 2:
        raise UnusableAssortment(f"demand must be periods by items, got shape {demand.shape}")
    if len(items) != demand.shape[1] or len(value) != len(items):
        raise UnusableAssortment(
            f"{len(items)} items, {len(value)} values and {demand.shape[1]} demand columns "
            "do not describe the same assortment"
        )
    if not 0 < abc_cuts[0] < abc_cuts[1] < 1:
        raise UnusableAssortment(f"ABC cuts of {abc_cuts} are not two shares in order")
    if not 0 < xyz_cuts[0] < xyz_cuts[1]:
        raise UnusableAssortment(f"XYZ cuts of {xyz_cuts} are not two positive numbers in order")

    total = float(value.sum())
    if total <= 0:
        raise UnusableAssortment(
            "the assortment has no value in this period, so an ABC curve is undefined"
        )

    order = np.argsort(-value)
    cumulative = np.cumsum(value[order]) / total
    abc = np.empty(len(items), dtype=object)
    for rank, index in enumerate(order):
        share = cumulative[rank]
        abc[index] = "A" if share <= abc_cuts[0] else ("B" if share <= abc_cuts[1] else "C")

    variability = np.array([coefficient_of_variation(demand[:, i]) for i in range(len(items))])
    xyz = np.where(
        variability <= xyz_cuts[0], "X", np.where(variability <= xyz_cuts[1], "Y", "Z")
    ).astype(object)

    return Classification(
        items=tuple(items), value=value, variability=variability, abc=abc, xyz=xyz
    )
