# R126-D2: Full cooperative authority fault matrix

This bounded synthetic software experiment runs against the actual
archived R122/R117/R116 object classes via the R126-D1 authority.

The original R126-D1 implementation is not modified.

Cancellation and retirement are each fault-injected at 11 stages:
candidate creation (pre/post), registry mutation (pre/post),
terminal receipt append (pre/post), candidate verification (pre/post),
publication (pre/post), and acknowledgement pre-return.

Expected experimental outcome:
- 22 total fault witnesses;
- 18 prepublication failures with unchanged published observations;
- four postpublication acknowledgement ambiguities;
- controlled retry after unpublished failure;
- duplicate denial after publication;
- independent terminal, denial and retirement receipt reconstruction.

The D1 supported API does not return raw mutable backend objects.
Nevertheless, Python name-mangled private state remains accessible.
The adversarial suite demonstrates direct backend invocation and
pointer rebinding when code circumvents the supported API.

This is NOT a security sandbox, revocation proof, exhaustive alias
analysis, concurrent transaction, durable journal, physical emergency
stop, or full replacement of the actual R117/R122 API.

No real recorded sensor factors, M2DGR original data, source GT,
sealed confirmation_test, qualified ATE/RPE or calibrated health
model are accessed. All eleven scientific gates remain CLOSED.
