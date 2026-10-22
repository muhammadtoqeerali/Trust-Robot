# R108 — Bounded synthetic delivery and fault injection

## Engineering objective

Test an in-process bounded reorder buffer feeding
R107's previously validated sequential synthetic estimator.

The source graph remains the R104 manufactured
camera-LiDAR-IMU graph.

The original S6 nonlinear source is unchanged.

## Delivery model

Four manufactured two-sample inertial bundles
are delivered for estimator nodes 1, 2, 3 and 4.

The buffer admits only:
- Exact references from the selected R104 graph.
- Correct session and fixture identity.
- Correct synthetic node time and IMU sample IDs.
- Correct pose-factor membership and source frame.
- At most two nodes ahead of the expected node.
- At most two buffered future nodes.

Valid buffered nodes are processed in increasing
estimator-node order.

## Fault tests

The regression suite checks duplicate, delayed,
missing, future, altered, wrongly sourced and
cross-graph packet deliveries.

Rejections occur before queue mutation or
estimator invocation.

A failed finalization does not falsely mark
an incomplete run as successful.

This software does NOT guarantee rollback after
an internal numerical solver failure.

## Performance and source limitations

The inputs are fully manufactured before being
replayed by the delivery buffer.

The graph uses a synthetic node clock. It is not
a physically verified hardware capture clock.

No ROS/network transport, packet authentication,
real-time execution deadlines, latency distribution,
or real sensor failure recovery is measured.

The deterministic session identifier is a local
correlation label, not a cryptographic signature.

Object-identity checking is specific to the local
in-process graph and is not a network serialization
or authenticated distributed admission mechanism.

No R95 Gaussian backend priors are imported into S6.

No recorded camera, LiDAR or IMU factors, health
training, independent GT scoring, ATE/RPE, original
ROSBags, or sealed confirmation-test access.

All 11 scientific gates remain CLOSED.
