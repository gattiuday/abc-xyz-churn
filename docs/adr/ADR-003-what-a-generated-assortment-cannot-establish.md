# ADR-003: What a generated assortment cannot establish

Status: accepted

## Context

The tiers are planted. A real assortment has value and demand and nothing that says which
items genuinely moved. This is the inventory of which claims survive leaving the fixture.

## Claims the fixture establishes

- **A class is a rank, so an item's class can change without the item changing.**
  Definitional, and the control case where no item ever changes tier still produces hundreds
  of class changes.
- **An item near a threshold is assigned by the threshold.** Definitional. Two items a
  thousandth of a value share apart land either side of a cut and carry different policies.
- **A hold removes churn and delays real moves.** Both follow from what a hold is, and both
  are measured rather than one of them.

## Claims the fixture establishes only conditionally

- **The share of churn with a real move behind it.** Around a tenth here, and it is a
  function of the planted transition rate, the number of items, the length of a period and
  how close the tiers are to the cuts. The direction, that most churn is not a real move,
  holds wherever the measurement noise is comparable to the gap between tiers.
- **The concentration of churn near the cuts.** Roughly twice the rate at the margins
  measured, and the margins themselves are choices.
- **What a two period hold costs.** Here it never reflects about a quarter of the real moves.
  That depends on how long a real transition persists, which this generator makes permanent
  and a real one does not.

## Claims this repository does not make

- **That ABC/XYZ should not be used.** It is a way of deciding where to spend attention and
  it works for that. The claim is narrower: the boundary between two classes carries less
  information than the policy difference across it implies, and nothing in the usual output
  tells a reader which items are near one.
- **That these thresholds are wrong.** Eighty and ninety five per cent are conventions with
  no derivation, and so is any replacement. The problem is not the number, it is that an item
  near it is reported with the same confidence as one in the middle of its class.
- **That a hold is the right remedy.** It is the cheapest one and its costs are measured.
  Reporting the distance to a cut alongside the class would be better and is not implemented,
  because it is a reporting change rather than a measurable one and this repository measures.
- **Anything about assortments where the value distribution is flat.** The ABC curve here has
  the usual shape. A flat assortment has no meaningful A class and the churn would be total.

## Consequences

A team wanting to know whether this applies to them can run `axc churn` on two consecutive
classifications of their own and read the class change count and the hand review moves.
Neither needs the planted tiers. What they cannot get without the tiers is the share that was
real, and the honest reading of that is that nobody knows it for any real assortment,
including the ones currently being reclassified every quarter.
