# TRUST-ROBOT Phase-9 Suppression / Recovery / Status Contract V1

Status: software architecture implemented locally; runtime suppression,
recovery, and estimator-status decisions remain disabled.

## Authoritative hysteresis

Hard modality suppression may not be a single-frame arbitrary decision.

The project requires a hysteretic structure containing:

- an unusable-probability entry threshold;
- a consecutive-window entry requirement;
- a lower recovery threshold;
- a consecutive-window recovery requirement.

This checkpoint freezes that structure only.

No threshold value and no consecutive-window count is selected.

## Remaining factor support

Before hard suppression, remaining factor support must be assessed.

The current project does not yet define a valid numerical or structural
sufficiency criterion.

No minimum modality count or observability test is invented.

No unsupported observability guarantee is claimed.

## Estimator status

When remaining factor support is insufficient, the authoritative project text
requires reporting either:

- degraded estimator state; or
- unavailable estimator state;

instead of forcing a nominal estimate.

The rule for choosing degraded versus unavailable remains unselected.

Runtime estimator-status execution therefore remains disabled.

## Health versus suppression

Phase-5 health state is not itself a suppression command.

Measurement availability is not a health label.

Hard suppression requires the explicit Phase-9 policy and cannot be inferred
directly from a health-state name.

## Fallback boundary

The broader project mentions fallback/safety operating points, but fallback is
not defined by the authoritative Phase-9 suppression/recovery section.

No fallback policy or threshold is therefore invented by this checkpoint.

## Upstream gate

Numerical Phase-8 factor conditioning remains unavailable.

Suppression, recovery and estimator-status execution therefore remain fail
closed.

## Data boundary

No validation data are opened.

Confirmation remains closed and may not select thresholds, window counts or
support rules.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `41be6fd118e99c2e990462c54aad44edba67d80b109ee4c756f6bd750546f1a1`
- module: `38122e409875700f04a26b41420ed45485393ca1f9a35b89e3bc41a496fa0471`
- tests: `21422eee6b518b30dd073f1911a4ecf9443e8e606b9ac88043fdfeeec5ae9edb`
- Phase-8 freeze: `9b4934404b97f1726b0acbd1e8b6eaa77bc2c3cb6ab6be38b4eb87a0800c337c`
- Phase-5 health semantics: `dc77b600b7306eb146f4ab901e7beca26f1075a6befee5d977a0f0e43070dc22`
- frontier report: `b2b7eedc7ccbd50af8ef2d05e66ccbccf0ee9c2f6ef5e9015f68537723c0ac24`
- frontier JSON: `3d3612e34bac2ef08469f0a4942ad9b49cb78b064fa6c1711766729ef9fb2be7`
