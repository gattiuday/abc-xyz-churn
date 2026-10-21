# ADR-001: Give every item a tier it keeps

Status: accepted

## Context

A reclassification produces a list of items that changed class. Nothing in that list says
whether the item changed. An ABC class is a rank against the rest of the assortment cut at a
convention, and an XYZ class is an estimate of variability cut at another, so an item's class
can move because another item moved, because the estimate wobbled, or because the item sat
near a line. None of those is the item changing.

Measuring how much of a reclassification is real therefore requires knowing which items
really moved, which means planting it.

## Decision

Every item is given a value tier and a variability tier that it keeps across periods. Its
demand each period is drawn from those parameters, so two consecutive periods differ by
sampling and nothing else. A class change with no tier change is noise by construction.

A share of items do change tier at each boundary, to an adjacent tier rather than across the
assortment, because products mature and promotions end and an assortment where nothing
changes would make every reclassification noise and the finding trivial. A transition to a
distant tier would also be trivially separable from the noise, which would make the
measurement flattering.

`classify.py` and `policy.py` never see the tiers. A test reads their source and fails if
either mentions `value_tier`, `variability_tier`, `tier_changed` or `VALUE_TIERS`.

The tiers are separated by more than a factor of three at each step, and a test says so,
because a generator whose tiers overlapped would churn because the tiers are
indistinguishable. That would be a different claim and a weaker one.

## Consequences

The headline figure is a ratio against something a real assortment does not have, so it
cannot be computed on one. What a real assortment supports is `axc churn`, which reports the
number of class changes and the number of items moved in or out of hand review without
needing the tiers, and `axc boundaries`, which reports an item's distance to a cut. Both of
those are computable and neither is reported by any classification scheme the author has
seen.

The simplification worth naming is that an item's variability tier never changes here, only
its value tier. A real item becomes erratic as it ages out, and modelling that would raise
the real transition count and lower the noise share. It would not change the control case,
where nothing moves at all and the churn is still in the hundreds.
