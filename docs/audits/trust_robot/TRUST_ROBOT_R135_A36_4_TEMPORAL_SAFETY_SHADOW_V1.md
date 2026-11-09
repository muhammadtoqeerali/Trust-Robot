# TRUST-ROBOT R135-A36-4 — Synthetic Temporal Trust / Safety Shadow V1

Status: software-only candidate. Physical and scientific execution gates **CLOSED**.

## Objective

Bridge the existing Phase-9 suppression/recovery contract and Phase-14 safety-supervisor contract using a bounded, deterministic, **synthetic-only** multi-window experiment. This does **not** implement a real health classifier, estimator factor reweighting, operational fallback, or robot motion.

## Input contract

Each indexed frame contains explicit independent *test fixture* assertions about camera, IMU and LiDAR declared health (healthy/degraded/unusable/unknown), delivery (present/missing), remaining factor support, tracker/solver validity, consistency, route evidence, and a return request. No frame can be marked physical. An absent recording must never be relabelled unhealthy. Inconsistency cannot identify a guilty modality without independent evidence.

## Experimental-only state machine

The module uses **two consecutive fixture-unusable windows** before any synthetic suppression, and **three consecutive fixture-healthy-or-degraded delivered windows** before recovery. These numbers are **not** selected, calibrated, frozen, or authorized for operational use. Even a synthetic suppression requires an explicit sufficient-support fixture and a delivered alternative. Unverified support blocks the shadow transition.

## Non-executing supervisor

Only synthetic candidate responses are emitted: nominal continuation, degraded continuation, return-home candidate, or safe-hold review. Missing/unknown health, unsupported remaining factors, solver/tracking uncertainty, ambiguous disagreement, or an unverified return route force review. A synthetic return-home candidate does not authorize autonomous navigation. A physical safe-stop procedure requires independent design, controller integration and validation.

## Scientific boundaries

Real health labels: 0. Calibrated health inference: unavailable. Physical factor admission: DENIED. Real suppression, recovery, route execution, stop action, sensor/ROS/network access: none. M2DGR 11 gates remain closed and held-out confirmation cannot be used for threshold selection.

## Future work

Develop independent health-supervision sources and real TRAIN features; train and calibrate the three-state health model on authorized splits; bind genuine factor support and innovation consistency; freeze suppression/recovery and safety thresholds on valid validation evidence; conduct offline end-to-end causal fault tests; only then progress to guarded physical control.
