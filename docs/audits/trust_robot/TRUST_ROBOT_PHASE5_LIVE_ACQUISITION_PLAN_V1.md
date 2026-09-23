# TRUST-ROBOT Phase-5 Non-Executing Live Acquisition Plan V1

## Purpose

This layer provides a parameterized command-plan generator for a future
VLP-32C acquisition.

It is deliberately non-executing.

The implementation contains no subprocess execution, network I/O, socket
operation or sensor probe.

## Explicit runtime parameters

The plan requires the future operator to supply explicitly:

- acquisition-session identity;
- TRAIN or VALIDATION split;
- sensor IPv4 address;
- capture interface;
- data UDP port;
- telemetry UDP port;
- capture duration;
- output directory.

No sensor address, port, interface or duration default is adopted.

In particular, the manufacturer's example/default address is not silently
selected.

## Candidate command primitives

The generated argv plan contains read-only manufacturer HTTP requests for:

- `/cgi/info.json`;
- `/cgi/status.json`;
- `/cgi/diag.json`.

It also contains candidate bounded packet-capture argv for:

- measurement UDP packets;
- position/telemetry UDP packets.

The plan uses argv arrays rather than shell command strings.

`curl`, `tcpdump` and `timeout` are candidate engineering primitives only.

No command is executed by this layer.

## Raw preservation intent

The HTTP plans preserve response bodies and response headers separately.

The UDP plans write raw packet captures.

A future executor must still create the frozen raw-artifact receipts and
capture host-side provenance around actual execution.

This plan does not itself create those receipts.

## Scientific boundary

A generated plan does not establish:

- sensor reachability;
- physical-device identity observation;
- interval binding;
- baseline nominality;
- accepted health supervision;
- any healthy/degraded/unusable label.

No capture ordering is selected.

No repeated HTTP polling period is selected.

No timing tolerance, fixed offset or interpolation is selected.

Host timestamps remain transport provenance only.

## Current state

Live plan instances in the scientific evidence registry: **0**.

Raw capture artifacts: **0**.

Device-identity receipts: **0**.

No-intervention declarations: **0**.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

Live execution remains unauthorized.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
