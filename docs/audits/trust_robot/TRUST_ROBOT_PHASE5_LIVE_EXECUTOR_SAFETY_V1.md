# TRUST-ROBOT Phase-5 Live Executor Safety Contract V1

## Scope

This layer addresses the local engineering hazards exposed by the offline
execution-readiness audit.

It is not a live executor.

It performs no network request, sensor probe or packet capture.

## Output publication policy

A future execution session must use an explicitly supplied absolute output
root.

A fresh session directory is required and collisions are rejected.

Raw artifacts may not be written directly to their final names.

Each artifact is first written to a same-directory `.partial` file.

Before publication:

- the file is fsynced;
- SHA-256 is computed.

Publication uses same-directory atomic replacement.

After publication:

- the directory is fsynced;
- SHA-256 is recomputed;
- the pre/post hashes must match.

Existing final artifacts may not be overwritten.

These are local evidence-integrity rules, not health semantics.

## HTTP bounding policy

A future invocation must explicitly supply:

- connection timeout;
- total request timeout.

The protocol selects no numeric timeout values.

These are engineering process bounds.

They are not:

- LiDAR measurement-time tolerances;
- sensor synchronization tolerances;
- reference-association tolerances.

No retry policy, request order or polling period is selected.

## Packet-capture completion policy

A deterministic classic-PCAP structural validator is now available.

For a PCAP to become eligible for raw-evidence publication, the candidate
policy requires:

- recognized classic-PCAP magic;
- complete global header;
- complete packet-record boundaries;
- at least one complete packet.

This establishes only structurally preserved packet evidence.

It does not establish sensor health.

The future finalization receipt must separately preserve:

- process return code;
- whether the capture deadline expired;
- whether SIGINT was requested;
- whether kill-after-grace was triggered.

Return code `124` alone determines neither success nor failure.

Actual tcpdump capture permission remains unverified.

Actual tcpdump SIGINT finalization remains unverified.

## Current authorization state

Filesystem safety primitives are implemented and tested only with synthetic
local files.

Network execution is not implemented.

Subprocess execution is not implemented.

Live sensor probing is not implemented.

Packet capture is not implemented.

No real output root is selected.

No capture interface is selected.

No sensor address is selected.

Raw capture artifacts: **0**.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

Live executor implementation ready: **false**.

Live execution authorized: **false**.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
