# R105 same-graph synthetic S6 local prior recentering

R105 consumes R104's validated single-fixture synthetic graph.
The original S6 solver produces a 30D prior on two retained nodes after
eliminating each of the oldest three 15D nonlinear states.

R105 intercepts each produced prior and performs an **exact local
coordinate rebase**: if the old prior is r(x) = S(x - x0) + b,
then for new reference x1 = x0 + d the unchanged residual is
r(x) = S(x - x1) + (b + S d).

The recentered 30D prior is RETURNED to the running S6 nonlinear
optimizer, and the next actual window consumes it. The same synthetic
fixture is solved without instrumentation as an independent control.
Ownership, chronology, camera/LiDAR IDs, IMU samples and solver-state
comparisons are checked. The original S6 source is not edited.

This is a coordinate reparameterization in S6's local rotation-vector
chart, **not** geometric SE(3) relinearization or a change in information.
It does not merge R95's unrelated single-state 15D Gaussian prior with
S6's 30D two-state prior. It is not sensor fusion accuracy evidence.

All 11 scientific gates stay CLOSED. There is no recorded-sensor access,
physical time synchronization or extrinsic proof, real sensor factors,
health model training, ATE/RPE or held-out confirmation test access.
