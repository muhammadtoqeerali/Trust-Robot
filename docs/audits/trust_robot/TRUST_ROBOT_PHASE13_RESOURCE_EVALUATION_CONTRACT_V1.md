# TRUST-ROBOT Phase-13 Resource-Evaluation Contract V1

Status: resource-evaluation software architecture implemented locally;
concrete measurement policy and empirical resource evidence remain deferred.

## Authoritative scope

Phase 13 is resource evaluation.

TRUST-ROBOT must eventually measure two views:

- complete-system cost;
- incremental trust-layer overhead.

Required future evidence families are:

- mean latency;
- P95 latency;
- deadline misses;
- throughput;
- processor utilization where measurable;
- peak memory;
- storage;
- average power;
- peak power;
- energy per update or trajectory.

These names are evidence requirements, not measurements already obtained.

## Required measurement metadata

Future measurements must record:

- hardware versions;
- software versions;
- power/clock mode;
- sensor rates;
- estimator window size;
- warm-up policy;
- measurement method.

The concrete values remain unfrozen.

## Measurement policy

No exact latency definition, measurement clock, deadline, throughput
definition, processor-utilization method, memory method, storage scope, power
method, energy method, warm-up policy, repetition policy, aggregation policy,
CPU/GPU-specific metric, or real-time acceptance threshold is selected.

## Historical resource protocol

The repository contains historical
`RUNTIME_RESOURCE_OVERHEAD_PROTOCOL_V1`.

It is not the TRUST-ROBOT Phase-13 protocol.

The following historical choices are not adopted:

- old 5% / 10% latency targets;
- 500 warm-up iterations;
- historical repetition/block counts;
- `time.perf_counter_ns`;
- median-primary incremental latency;
- historical RSS method;
- tracemalloc policy;
- historical x86-64 results;
- historical IMU/HAR resource semantics.

Historical instrumentation may only inform later engineering implementation
after explicit Phase-13 binding.

## Platform claim boundary

Reference-host evidence is not onboard-robot evidence.

Reference-host or native-C evidence is not STM32 evidence.

Target-specific resource claims require target-specific measurements.

No STM32 latency, energy, flash, RAM, or cycle claim is authorized.

## RQ4

Phase 13 covers the resource component of RQ4.

The guarded closed-loop safety component remains Phase 14.

No onboard resource constraint, fallback threshold, or resource answer is
currently available.

## Execution

No resource measurement is executed.

No resource claim is authorized.

Validation remains unopened.

Confirmation remains closed.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `999034456e4ab8eb62e36f08e769e670a8777d52f60876856f1bdc8caa71040b`
- module: `409b84eccba8d89009c5311ba4727ec3479a7bc55fc2881dd28b72b5adfb9620`
- tests: `76371bbb25b84053be2263a659067b0d3a24017fc9345fc8f71bf6f6239739ae`
- Phase-12 freeze: `bf95425b257d486510c16cdea1d2907d64480bc00a6fe07b088316c4333bbf05`
- frontier report: `4120763b090e7b2e3a1d0bdf92aa55323abb675e261d07ebde94f27f6268077b`
- frontier JSON: `71a8ea7d900a72780a06c9d1d174c2a43df79dd462d6064279c56b97cc075bdb`
- basis report: `222661b5977a371d11d332f9e53d2ea147d87791d8f8db4d8f47f29b4a92e5c1`
- basis JSON: `7eca5a47174e29f77b739bcc6a8552b29940ac98e56eedca11e713cb87062147`
