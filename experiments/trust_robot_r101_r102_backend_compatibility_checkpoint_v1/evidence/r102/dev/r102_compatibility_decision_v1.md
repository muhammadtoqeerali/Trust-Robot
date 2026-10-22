# R102 — Gaussian/nonlinear backend compatibility decision

R101 proved information-to-square-root mathematical
representation equivalence on quarantined synthetic nodes.

R102 checks actual R95 and S6 objects.

Shared mathematical components:

- Both have 15D position, rotation-vector, velocity,
  gyro-bias and accelerometer-bias state conventions.
- Both reuse the same analytic covariance-whitened
  inertial residual implementation.

Integration blockers observed:

1. Distinct local coordinate/frame namespaces.
2. No qualified mapping between synthetic timestamp epochs.
3. R95's first inertial window covers 100 ms while
   S6's node-to-node preintegration covers 200 ms.
4. Manufactured initial state anchors differ.
5. R95 exports a 15D prior while the actual S6
   first marginalization retains a 30D prior.
6. Quarantined R101 node IDs do not match S6 live nodes.
7. R95 stabilization and S6 anchoring serve
   different roles and cannot be equated.
8. Cross-backend factor identity and consumption
   histories have not been mapped and verified.

Decision: DO NOT directly bind R95 priors into S6.

Next engineering milestone:

Build a single-source synthetic experiment with shared
time indexing, explicit state/gauge coordinates, and
factor ownership. Verify the transfer mathematically
before proposing any nonlinear optimizer integration.

This audit is software-only. No real measured source,
physical clock/extrinsics, health-model training,
ground-truth scoring or confirmation-test access.

All 11 scientific gates remain closed.
