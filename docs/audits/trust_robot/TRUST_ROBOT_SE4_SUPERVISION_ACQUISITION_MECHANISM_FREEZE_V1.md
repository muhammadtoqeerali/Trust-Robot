# TRUST-ROBOT SE4 Supervision Acquisition Mechanism Freeze V1

Status: **prospective acquisition mechanism resolved; live execution remains blocked.**

## Scope

This freeze resolves the software mechanism for future prospective LiDAR
supervision-evidence acquisition.

It does not contact a sensor and it does not create physical evidence.

## Selected mechanisms

The following future raw-acquisition mechanisms are prospectively selected:

- one-shot HTTP GET `/cgi/info.json` for physical-device identity;
- one-shot HTTP GET `/cgi/status.json` for raw sensor status;
- one-shot HTTP GET `/cgi/diag.json` for raw diagnostic evidence;
- bounded UDP packet preservation in classic PCAP form for measurement data;
- bounded UDP packet preservation in classic PCAP form for position/telemetry
  data.

The primary physical-device identity field remains manufacturer serial.

HTTP response bodies and headers are preserved raw.

UDP evidence is preserved as raw classic PCAP.

## Runtime values intentionally not selected

No real sensor IPv4 address is selected.

No capture interface is selected.

No data or telemetry UDP port is selected.

No capture duration is selected.

No real output root is selected.

No HTTP timeout values are selected.

No capture shutdown grace value is selected.

No status polling period is selected.

No retry policy is selected.

No capture order is selected.

No physical timing tolerance, fixed offset, interpolation or interval-binding
mechanism is selected.

These values depend on a future real TRAIN acquisition environment and may not
be fabricated from software evidence.

## Safety and provenance

Any future execution must preserve:

- acquisition-session identity;
- TRAIN split role;
- manufacturer serial identity;
- raw identity/status/diagnostic responses;
- raw artifact SHA-256;
- capture metadata SHA-256;
- host capture timestamps as transport provenance only;
- prospective no-intervention declaration;
- fresh non-overwriting session directories;
- atomic publication and pre/post-publication digest equality;
- PCAP structural validation;
- process termination/finalization receipts.

## Current empirical state

Network I/O executed: **false**.

Subprocess execution performed: **false**.

Live sensor probe executed: **false**.

Raw capture artifacts: **0**.

Device identity receipts: **0**.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

Physical interval binding established: **false**.

## Scientific boundary

HTTP status is not automatically a health label.

HTTP diagnostic evidence is not automatically a health label.

Raw packet capture is not automatically proof of baseline nominality.

Raw packet capture is not automatically accepted health supervision.

Host capture time is not physical measurement time.

No reference trajectory was read.

No ATE/RPE was computed.

No final localization score was computed.

No validation or confirmation data was opened.

## Transition

The acquisition mechanism is resolved.

Live execution remains unauthorized.

Source acceptance remains unauthorized.

Health-label generation remains unauthorized.

SE4 remains incomplete.

SE4 model training remains unauthorized.

SE5 remains blocked.

Validation remains closed.

Confirmation remains closed.

SE9 remains closed.

The next required event is resolution of explicit real TRAIN acquisition
runtime values plus a separately authorized live execution path. Any resulting
raw evidence must still satisfy interval-binding, baseline-nominality and
supervision-source acceptance rules before health labels can exist.

## Frozen artifacts

Resolution module SHA-256:

`4c63e450facef3353d0ae1b3cd16eefd66bc14c9e6ddc04ef9dcd4df68ec6869`

Resolution config SHA-256:

`6150971b4a16e5ba2ad51c754174a7fd37df287763559f1fc4f60b481758e464`

Resolution config content SHA-256:

`01b5d5a593c1927e861fb69d6ec61ec223d335b14d99f986cfeef89f58bdc7b9`

Implementation test SHA-256:

`84a2dd880aa2e83a74acf903705cda2241eb17b3701fd88c241f1f376c8e33dd`

Freeze manifest SHA-256:

`18df2dd2a88d60939f31b844f584a21d090f3a15026369e511c2cb4d39dd20f4`

Freeze manifest content SHA-256:

`5e78f33ee30ed2be3af23401d3ac25059a8bb372ab71558ac0502f83742eb6e7`

Freeze test SHA-256:

`e4eec16c925386e1a1d0b72be58ab869c64de2b397642c0986f977bbbcfc83d1`

Parent checkpoint:

`9ff7782f08212c4e5192d6189a8ecabc9d9490e5`

Parent tree:

`4d8ce9fddb17ed35fcd84c0de1479ae33537807a`
