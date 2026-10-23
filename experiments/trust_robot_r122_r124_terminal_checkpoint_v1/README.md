# TRUST-ROBOT R125 — R122/R123/R124 synthetic terminal checkpoint

This archive preserves three sequential, off-Git experiments:

- R122: bounded local terminal cancellation and retirement when ordinary denial capacity is saturated. Original 72-test milestone.
- R123: fault injection into R122 terminal mutation and receipt boundaries, exposing four missing-receipt and two ambiguous-acknowledgement cases. Original 78-test milestone, including its earlier corrected observation witness.
- R124: isolated, single-session modeled shadow publication. 51 tests; 22 injection witnesses, consisting of 18 prepublication rollback/no-visible-mutation cases and four postpublication acknowledgement-ambiguity cases.

The R124 independent validator initially failed a case-sensitive scientific-contract marker check. Its original text, corrected validator, and repair-lineage report are all included.

Evidence resides under evidence/r122, evidence/r123 and evidence/r124. Each phase has dev and result directories. R125 also contains fresh regression logs, a SHA256 manifest, this README, a scientific-scope record, and a standalone checkpoint verifier.

All results are synthetic software evidence. R124 is NOT a transactional implementation of R117/R122. The 11 physical admissibility gates are CLOSED.

No original M2DGR bags, source records, ground-truth trajectories, private calibration evidence, or sealed confirmation-test data are included. Receipt hashes detect modeled accidental changes; they are not cryptographic authentication or durability evidence.
