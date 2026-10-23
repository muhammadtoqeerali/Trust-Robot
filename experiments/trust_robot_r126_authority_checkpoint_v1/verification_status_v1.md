# R127-B verification and sealing record

Date: 2026-10-23.

The initial README preserves the earlier R127-A candidate state.
This companion record describes the subsequent R127-B verification.

The three archived R126 suites were re-executed from their
checkpoint evidence copies:

- R126-B1: 18 tests.
- R126-C: 15 tests.
- R126-D2: 45 tests, including the 11 D1 tests.

Combined distinct tests: 78.

The original failing B1 test log is represented by one explicitly
redacted archival copy. Its original SHA256 remains recorded in the
source-lineage and repair-lineage evidence. The original unmodified
log remains outside Git.

The standalone verifier checks the R126 evidence and manifest.
Its success must be demonstrated by actually executing
`python3 -B verify_checkpoint.py verify <checkpoint_path>`.

A successful standalone verification demonstrates the specified
synthetic, single-threaded experimental invariants only.

The public API is cooperative and is not a Python security
boundary. Direct private-object access and pointer rebinding
were independently demonstrated.

There is no verified actual R117/R122 drop-in atomicity,
thread safety, durable recovery, authenticated receipts,
physical emergency stop, or sensor-based localization scoring.

All 11 scientific admissibility gates remain CLOSED.


## R127-B1 targeted verifier correction — 2026-10-23

R127-B completed fresh 18 + 15 + 45 regression tests and
sealed its initial manifest, but standalone verification
stopped at SCIENTIFIC_SCOPE_DOCUMENT.

The verifier incorrectly required the literal numeric
substring 11 within scientific_scope_v1.md, whereas the
unchanged document explicitly says that all eleven
physical/scientific admissibility gates are CLOSED.

Only the verifier's scientific-scope text predicate is
corrected. The manifest still independently requires
scientific_gates_closed = 11.

Original verifier SHA256: 18df763516b7c1a65e32d4b1b06b5346d76cc1959e16818b134a807d759dafd6
Original status SHA256: 8ce964d91a8aa5aec57d727d5c2b1daa30eaa7ed84a2c1aa7ebc6a15d8a5455a
Original scope SHA256: 9c68fb5eb46a9ed4a22b6dba261805471a19229f0921f134f120adf3d0808137
Original manifest SHA256: bc80a8aee13aa161c2e60767d9fd6375200b67e8fe29e68525227f5fb3678cfd

The three original files are retained in separately named
off-Git R127-B1 backup artifacts on the KIOS workstation.

All original R127-A evidence files, scientific-scope
document and source-lineage files remain unchanged.

This repair does not alter scientific conclusions,
physical admissibility gates or the archived R126 engines.
