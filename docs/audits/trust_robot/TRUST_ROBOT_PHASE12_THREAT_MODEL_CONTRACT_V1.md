# TRUST-ROBOT Phase-12 Threat-Model Contract V1

Status: explicit attack-evaluation software architecture implemented locally;
no attack protocol has been instantiated and attack execution remains disabled.

## Scope

Phase 12 is:

**Explicit attack evaluation — threat-model-bounded RQ3 evidence.**

## Evidence-category separation

Fault evaluation remains separate from attack evaluation.

Environmental/non-attack degradation remains separate from attack evaluation.

Synthetic corruption identity and controlled-fault truth are not attack truth.

## Planned attack taxonomy

The proposal currently names six potential planned attack identities:

- false-data injection / spoofing;
- bounded adversarial image or point-cloud perturbation;
- replay;
- timestamp manipulation;
- coordinated two-modality corruption;
- adaptive white-box digital evasion.

These names are taxonomy entries only.

None is currently an instantiated executable attack protocol.

## Required threat-model fields

Every eventual attack protocol must specify:

- attacker knowledge;
- writable modality/modalities;
- writable fields;
- attack duration;
- magnitude/rate/norm budget;
- objective;
- protected-source assumptions;
- identifiability assumptions.

Current instantiated protocol count: zero.

## RQ3

RQ3 concerns handling of:

- single-sensor attacks;
- coordinated attacks;
- adaptive attacks;

under explicitly stated identifiability assumptions.

Concrete operational definitions remain unselected.

Numeric Phase-7 auxiliary consistency evidence remains unavailable.

RQ3 is not executable and no RQ3 answer is claimed.

## Source attribution

Successful source attribution may not be claimed when available uncompromised
information is insufficient.

Current sufficiency is unverified and source-attribution claims are disabled.

## Phase-3 / Phase-10 reuse

Frozen native Phase-3 mechanism identities remain:

- EVENT_GAP;
- EVENT_REPEAT;
- TIMESTAMP_STEP_SHIFT.

They are not authorized as Phase-12 attack executions.

Phase-3 future candidate identities include replay,
threat-model-bounded spoofing, LiDAR geometric perturbation, and calibration
perturbation. They remain unimplemented candidates.

The Phase-3 selection policy is not itself a Phase-12 threat model.

Phase-10 controlled-fault evidence does not become Phase-12 attack evidence.

## Operating points

No attack duration, budget, magnitude, rate, norm, schedule, seed schedule, or
threshold is selected.

Attack budgets and thresholds must be fixed before held-out testing.

Held-out testing cannot select them.

## Execution / evaluation

No synthetic attack is executed.

No physical attack is executed.

No attack evaluation is authorized.

Validation remains unopened.

Confirmation remains closed.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `b81f4fa6ddeac61775fdc017dc70effa875ceeffe4c017c7b57489f0aa431e73`
- module: `03b7ebcc468b8b798f9240e8105ceec88b3c2b919a5bc78dad6d6554617d5983`
- tests: `e663bd9fb3cedd0a80615bc3844c4a91af8ebc4b41f6e0475d18bf2c32ad5bdc`
- Phase-11 freeze: `842860e2fb17079853f6a07877b4b717deb16c5425bdcf3aefaa9314294bbc61`
- frontier report: `5fca5b0e4d9822381190a98faa14abeffa9247a2e400c3225fc7bc844a3eb959`
- frontier JSON: `9944764551a402cad59b3c7bb1c26b29d08ab9bde3250b6ea45eb7b484033da9`
- basis report: `4eb113eab4a8c4290922ec903afaad6b046c8853d2a903c218ee222c467cbd78`
- basis JSON: `409a9c94dbfcb6d998e7d9f974426c7b7b58bc25e7908c66ec8e1a134873b00c`
- Phase-3 freeze: `330c5041cb27b9460cb2502aa3ea32b5b4e565facfa2fe5b1bc30554257189f0`
