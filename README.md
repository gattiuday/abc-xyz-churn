# abc-xyz-churn

**An ABC class is a rank against the rest of the assortment, cut at a threshold nobody derived. So an item's class changes when another item moves, when the variability estimate wobbles, or when it sits near a line. Reclassify this assortment every quarter and 805 items change class; 108 actually changed tier, and only 8.9% of the class changes have a real move behind them.**

[![CI](https://github.com/GITHUB_USERNAME/abc-xyz-churn/actions/workflows/ci.yml/badge.svg)](https://github.com/GITHUB_USERNAME/abc-xyz-churn/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Tests](https://img.shields.io/badge/tests-86-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## The thing a classification cannot tell you

A class is three things an item does not control. It is a rank, so it moves when other items
move. It is a cut at 80% and 95% of cumulative value, which are conventions with no
derivation, so an item near one is assigned by a choice. And the XYZ half is an estimate of
variability from a finite sample cut at 0.5 and 1.0 in that estimate. An item near any of
those four numbers is assigned by the number.

A reclassification produces a list of items that changed class. Nothing in that list says
whether the item changed, and nothing in the usual output says which items were near a line.

Run the classification on an assortment where **no item ever changes tier** and it still
produces 770 class changes over seven quarters on 300 items. That is the control, and every
one of those changes is noise by construction.

## The uncomfortable numbers

Measured across twelve independent assortments of 300 items over eight quarters, with one item
in twenty genuinely changing tier at each boundary:

- **805 class changes, and only 108 items changed tier.** 8.9% of the class changes have a
  real move behind them, and that is an upper bound: it counts any class change on an item
  that moved in the same quarter, whether or not the move caused it.
- **147 items are moved in or out of hand review** over two years. That is the dimension
  whose cost is a planner's time rather than stock on a shelf, and it is binary: an item is
  either on someone's list or it is not.
- **Churn concentrates at the thresholds.** Within two points of cumulative value share of a
  cut, 52.1% of items change class in a quarter, against 27.6% of those further away, 1.9
  times the rate.
- **A two quarter hold removes 78% of the churn**, and it is not free. Class changes fall to
  177 and 42 hand review moves, at a cost of 0.58 of a period of delay on the moves that are
  real, and it never reflects 28 of them at all.

86 tests, 100.00% line coverage, and every figure above is re-measured by CI and checked
against this document in both directions on every push.

## Claim 1: most reclassification is not a reclassification of anything

<!-- generated: churn-table.md -->
| Items really moving, per quarter | Class changes | Real tier changes | With a real move behind them | Hand review moves |
| --- | --- | --- | --- | --- |
| 0.0% | 770 | 0 | 0.0% | 108 |
| 2.5% | 776 | 53 | 4.5% | 122 |
| 5.0% | 805 | 108 | 8.9% | 147 |
| 10.0% | 841 | 212 | 17.0% | 182 |
<!-- end generated: churn-table.md -->

The first row is the one to read first. Nothing moves, and the scheme still finds hundreds of
items to move. Adding real transitions adds class changes roughly one for one, which is the
scheme working, and it does not reduce the noise floor underneath.

The justified column is an upper bound rather than an estimate. It counts a class change on
an item that genuinely moved tier in the same quarter as justified, without asking whether
the move caused the change, because establishing that would need a counterfactual the fixture
does not carry. The true share is lower.

## Claim 2: the churn is at the lines

<!-- generated: boundary-table.md -->
| Margin | Items near a cut | Churn near a cut | Churn away from one | Ratio |
| --- | --- | --- | --- | --- |
| 0.02 | 132 | 52.1% | 27.6% | 1.9x |
| 0.05 | 266 | 40.9% | 18.4% | 2.2x |
| 0.10 | 300 | 38.2% | too few to compare | n/a |
<!-- end generated: boundary-table.md -->

An item two points of value share from the A to B line and an item in the middle of A are
both reported as A, with the same policy and the same confidence. One of them will probably
be a B next quarter.

The practical point is that **the distance to a cut is computable from the same data as the
class**. Run `axc boundaries` on the committed fixture and the closest items sit a thousandth
of a share apart on opposite sides of a line, carrying different review cadences. No
classification scheme the author has seen reports that column, and nothing stops one.

The widest margin in the table has no comparison group, because it captures the entire
assortment. It is marked rather than dropped; an earlier version of this experiment published
a ratio from it that read as churn being lower near a cut.

## Claim 3: a hold removes most of it, and costs something real

<!-- generated: hold-table.md -->
| Hold, quarters | Class changes | Hand review moves | Mean delay on a real move, quarters | Real moves never reflected |
| --- | --- | --- | --- | --- |
| 1 | 805 | 147 | 0.00 | 0 |
| 2 | 177 | 42 | 0.58 | 28 |
| 3 | 78 | 22 | 0.80 | 44 |
<!-- end generated: hold-table.md -->

Requiring a new class to persist for a quarter before acting on it is one line in a planning
system. It removes most of the churn, which is the easy half of the sentence.

The last two columns are the other half. A real transition is acted on late, and about a
quarter of the real moves are never acted on at all, because the item's class oscillates and
never settles for long enough. **That is a worse failure than churn for the items it happens
to**, and it is the reason this table has five columns rather than two.

What a hold does not do is make the classification right. The items whose class is noise are
still assigned a class and still carry its policy; the hold only stops the assignment
changing every quarter.

## What is in the fixture

300 items over eight quarters of thirteen weeks. Every item has a value tier and a variability tier it
keeps, so its demand each quarter is drawn from the same parameters and two consecutive
quarters differ by sampling alone. One item in twenty changes value tier at each boundary, to
an adjacent tier, because products mature and promotions end.

The tiers are separated by more than a factor of three at each step, and a test asserts it,
because a generator whose tiers overlapped would churn because the tiers are
indistinguishable. That would be a different and weaker claim.
[ADR-001](docs/adr/ADR-001-give-every-item-a-tier-it-keeps.md) is the full account.

## What this cannot measure

- **Whether ABC/XYZ is worth doing.** It is a way of deciding where to spend attention and it
  works for that. The claim here is narrower: the boundary between two classes carries less
  information than the policy difference across it implies.
- **The cost in money.** A safety factor change is stock and a review cadence change is a
  planner's calendar. Converting either needs holding costs and wage rates this repository
  has no business inventing, so the counts are reported and the conversion is left to someone
  with the numbers.
- **An item whose variability changes.** Only the value tier moves here. A real item becomes
  erratic as it ages out, which would raise the real transition count and lower the noise
  share, and would not change the control case.
- **A flat assortment.** The value curve here has the usual shape. One without a meaningful A
  class would churn totally.

## Layout

```
src/axc/
  classify.py    ABC and XYZ, and the two arbitrary choices inside
  generator.py   items with a tier they keep, so churn can be graded
  policy.py      what a class is used for, and the hold that stabilises it
  cli.py         generate, churn, hold, boundaries
experiments/     three experiments writing JSON to docs/experiments/
docs/adr/        three decision records
tools/           the metrics collector and the number checker
```

## Running it

```bash
make install
make verify        # lint, test, receipts, then the suite again
axc churn --assortment data/fixtures/assortment.csv
axc boundaries --assortment data/fixtures/assortment.csv
```

`axc churn` exits 1 when most reclassification is unexplained, so a scheduled job fails
rather than filing a reclassification, and 2 when the assortment is malformed. The
distinction is declared where the exception is raised: `UnusableAssortment` subclasses both
`ClassificationError` and `ValueError`, and the handler's `except` order resolves it.

## Receipts

Every figure in this README is read from a run. `tools/collect_metrics.py` reads the test
run, the coverage report and the three experiment outputs into `docs/metrics.json`;
`tools/check_numbers.py` checks the documents against it in both directions. A figure quoted
outside the sentence that claims it fails the build, and so does any number no anchor phrase
puts where it sits. The three tables above are generated into this file and compared by
equality.

A figure written in words is invisible to a digit scanner, and `#` comments and `tests/` are
outside the checked set.

## Decision records

- [ADR-001: Give every item a tier it keeps](docs/adr/ADR-001-give-every-item-a-tier-it-keeps.md)
- [ADR-002: Count the policy work, not the class changes](docs/adr/ADR-002-count-the-policy-work-not-the-class-changes.md)
- [ADR-003: What a generated assortment cannot establish](docs/adr/ADR-003-what-a-generated-assortment-cannot-establish.md)
