# TRUST-ROBOT Phase-5 Acquisition-Session Provenance V1

## Manufacturer-grounded physical-device identity

The VLP-32C manual explicitly documents `/cgi/info.json` as returning:

- sensor model;
- serial number;
- firmware versions.

The manufacturer example parses the serial number from `data['serial']`.

The manual separately states that each sensor has a unique factory-assigned
Serial Number that cannot be changed.

Therefore this prospective format selects the serial number returned through
the manufacturer information interface as the primary physical-device
identity field.

No live value has been captured.

## MAC-address boundary

The manual also documents a user-configurable MAC-address override.

Therefore the active MAC address is not selected as the primary
physical-device identity.

A network address is also not physical-device identity.

No network address is selected by this layer.

## Firmware boundary

Firmware versions are preserved as acquisition/runtime configuration context.

Firmware versions are not physical-device identity by themselves and are not
health truth.

## Optional snapshot corroboration

The manufacturer snapshot carries a serial value in `info.serial`.

Snapshot corroboration remains optional and is not selected for live capture
by this layer.

## Prospective no-intervention declaration

A separate declaration format is defined for the future baseline acquisition.

It requires:

- acquisition-session identity;
- TRAIN or VALIDATION split role;
- baseline condition `full`;
- an explicit statement that no deliberate availability intervention was
  applied;
- prospective declaration before the controlled-intervention phase;
- a SHA-256 identity for the declaration artifact.

This is procedural provenance.

It is not physical sensor-health truth and cannot establish baseline nominality
by itself.

## Current state

No live sensor has been contacted.

No identity response has been captured.

No serial value has been observed.

No network address is selected.

Device-identity receipts: **0**.

No-intervention declarations: **0**.

Session-provenance bundles: **0**.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

No interval-binding mechanism, timing tolerance, fixed offset or interpolation
is selected.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
