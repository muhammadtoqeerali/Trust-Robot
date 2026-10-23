# R126-B: identity-aware candidate feasibility

Uses the actual archived R122/R117/R116 synthetic terminal objects,
with R123's manufactured saturation fixture.

An explicit deepcopy memo retains the original inert object()-type
owner and lease tokens while separately cloning selected mutable registry,
pool, session, denial, policy and terminal receipt structures.

Two normal operations are evaluated separately: terminal cancellation and
ordered terminal retirement. Eight candidate-stage injected faults and
two postpublication acknowledgement ambiguities are tested.

Candidate failures remain unpublished; successfully validated candidates
may replace one local adapter pointer. This does NOT alter the original
R122 source or make direct users of the original TerminalPath transactional.

CRITICAL LIMITATIONS:

- Other external references to the old facade remain usable.
- Checked alias relationships are not an exhaustive heap-isolation proof.
- User code can access private Python objects and bypass this adapter.
- Single-threaded observation only; no concurrent publication guarantee.
- No process crash, power loss, durability, authentication, liveness,
  physical stop, or real-time deadline proof.
- No estimator factors executed during terminal transitions.
- No M2DGR recording, original GT or sealed test access.
- No real factor admission or independently referenced ATE/RPE.
- The exact 11 R43 scientific gates remain CLOSED.
- This experiment is a feasibility step, not a complete R117/R122 repair.
