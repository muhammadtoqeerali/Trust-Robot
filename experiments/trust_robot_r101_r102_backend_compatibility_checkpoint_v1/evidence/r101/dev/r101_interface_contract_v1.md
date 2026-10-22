# R101 synthetic prior-representation adapter

This phase converts R95 information-form Gaussian
priors to the S6 SquareRootInformationPrior type.

The conversion preserves the local quadratic:

q(d) = 0.5 d.T H d - g.T d + c

by constructing S and b satisfying:

S.T S = H
S.T b = -g

and an additive energy constant:

k = c - 0.5 b.T b

The adapter tests four deterministic perturbations
per converted prior.

Important restrictions:

- The source is an R90-validated synthetic R95 record.
- The source and target coordinate namespace must both
  equal R95_LOCAL_GAUSSIAN_TANGENT_V1.
- The local sandbox node ID is 100 + segment ID.
- Live S6 nodes and the S6 nonlinear frame are denied.
- Records may not be reused across timestamp-gap segments.
- The conversion does not certify matching gauge,
  reference frames, chronology or factor history.
- The R90 record fingerprint is not a digital signature.
- The actual R95 Gaussian backend is NOT yet
  integrated into the S6 nonlinear estimator.
- No raw sensor input, ground-truth evaluation,
  health training, ATE/RPE or confirmation-test access.

All 11 scientific gates remain CLOSED.

The next phase must establish explicit chronological,
frame, gauge and factor-ownership compatibility before
testing integration with an S6 nonlinear optimization
window. It must remain synthetic-only.
