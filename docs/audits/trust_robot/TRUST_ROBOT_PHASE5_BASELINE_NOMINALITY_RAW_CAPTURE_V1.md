# TRUST-ROBOT Phase-5 Baseline-Nominality Raw Capture Format V1

## Purpose

The prospective baseline-nominality protocol requires raw operational evidence
bound to an exact future acquisition interval.

The offline feasibility audit established that raw evidence acquisition is
technically plausible, but live hardware and interval binding remain
unverified.

This layer therefore freezes only the raw evidence artifact format.

It does not execute a capture.

## Multi-artifact evidence model

The format can preserve four raw evidence kinds:

- measurement;
- sensor status;
- sensor diagnostic;
- position packet.

This is intentionally multi-artifact because the manufacturer evidence is
asymmetric.

The manual explicitly documents `cgi/status.json` for motor and laser state.

The manual documents Thermal Status separately in the position packet at
offset `0xCB`, with:

- `0` = `Ok`;
- `1` = `Thermal shutdown`.

The feasibility audit did not establish an explicit Thermal Status field in
the documented HTTP status or diagnostic sections.

Therefore this layer does not assume that one HTTP response supplies all three
baseline-operational facts.

## Raw artifact receipt

Every artifact receipt records:

- artifact identity;
- acquisition-session identity;
- TRAIN or VALIDATION split role;
- evidence kind;
- source identifier;
- VLP-32C hardware identity;
- SHA-256 of raw bytes;
- raw byte count;
- SHA-256 of capture metadata;
- host clock identity;
- host capture start/end observations.

Raw bytes and capture metadata must both be preserved.

## Host-time boundary

Host capture timestamps are transport/provenance observations only.

This layer explicitly does not claim that host time is:

- physical LiDAR measurement time;
- HTTP sensor-state time;
- position-packet measurement time.

It performs no temporal association.

It selects no:

- timing tolerance;
- fixed offset;
- interpolation.

## No live acquisition selection

This layer selects no:

- live sensor address;
- HTTP polling period;
- measurement capture mechanism;
- position-packet capture mechanism;
- packet-capture command;
- ROS capture implementation.

No sensor is contacted.

## No supervision implication

A valid raw artifact receipt establishes only preservation/provenance shape.

It does not establish:

- baseline nominality;
- interval binding;
- accepted supervision;
- healthy/degraded/unusable labels.

Current state:

- raw capture artifacts: 0;
- candidate nominality receipts: 0;
- accepted baseline-nominality sources: 0;
- accepted health-supervision sources: 0;
- real health labels: 0.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
