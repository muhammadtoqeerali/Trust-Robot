# R123 — Synthetic terminal failure-boundary audit

## Scope

R123 injects eight deterministic faults into the
unchanged R122 terminal-only lifecycle interface.

All original R122 and earlier implementation sources
remain SHA-256 pinned and unchanged.

## Injected boundaries

Cancellation:
- Before underlying registry mutation.
- After registry mutation but before receipt append.
- Before terminal receipt append.
- After terminal receipt append.

Retirement:
- Before underlying registry mutation.
- After registry mutation but before receipt append.
- Before terminal receipt append.
- After terminal receipt append.

## Observed distinction

Failures before any mutation permit a fresh retry
after the injected fault is removed.

Failures after a mutation create an uncertain
publication boundary.

Some cases mutate the registry without producing
the corresponding terminal receipt.

Other cases append the receipt but raise before
the caller receives the result.

R123 uses a diagnostic wrapper that quarantines
these ambiguous outcomes and rejects automatic
retry through that wrapper.

The wrapper does not cryptographically or physically
isolate access to the original Python objects.

## Scientific conclusions

R122 has demonstrated a terminal-only software
path under defined synthetic conditions.

R123 does NOT establish transactional atomicity
across registry mutation and receipt publication.

R123 does NOT establish crash-safe retry,
durable receipts, arbitrary exception recovery,
concurrent safety, wall-clock deadlines, process
termination or physical emergency-stop behavior.

These failure conditions are explicitly recorded
as unresolved engineering boundaries.

## Restrictions

The original S6 and R104-R122 sources remain
unchanged. The R95 15D prior is not imported into
the S6 30D synthetic same-graph prior backend.

No recorded sensor-factor execution, original
ROSbags, raw ground truth, health training,
independent ATE/RPE, physical extrinsics or
physical clock qualification are introduced.

The sealed confirmation_test remains untouched.

All 11 scientific gates remain CLOSED.
