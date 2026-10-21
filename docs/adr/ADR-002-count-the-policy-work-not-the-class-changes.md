# ADR-002: Count the policy work, not the class changes

Status: accepted

## Context

A class change is only interesting because something is keyed to the class. If every class
carried the same policy, churn would cost nothing and this repository would have no subject.

So the unit of measurement should be the work a change creates rather than the change
itself. Counting class changes alone also overstates and understates in different places: an
item moving from AX to AY changes its safety factor and nothing else, while an item moving
from AX to BX changes whether a human looks at it, and those are not the same event.

## Decision

Attach an ordinary policy to each of the nine classes and count changes per policy dimension:
the review cadence, the safety factor, and whether the item is reviewed by hand. The policy
values are conventions and are declared as such; what matters is that they differ by class.

The dimension worth reporting separately is hand review, because it is the one whose cost is
a person's time rather than stock on a shelf, and because it is binary: an item is either on
a planner's list or it is not, and moving it on and off is work regardless of which direction.

## Consequences

The headline carries two numbers rather than one: the class changes and the items moved in or
out of hand review. On the committed fixture the second is a fifth of the first, which is the
share worth arguing about with a planning manager.

What this does not do is cost the churn in money. A safety factor change is stock, a review
cadence change is a planner's calendar, and converting either into a figure would require
holding costs and wage rates this repository has no business inventing. The counts are
reported and the conversion is left to someone with the numbers.
