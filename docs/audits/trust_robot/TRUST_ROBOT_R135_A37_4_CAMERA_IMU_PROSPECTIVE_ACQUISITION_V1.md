# TRUST-ROBOT R135-A37-4 — Prospective camera / IMU independent health-evidence acquisition design V1

Status: **draft source-specific acquisition design**, not a frozen source-acceptance protocol, physical measurement, real health label, or authorized intervention.

## Reason for this phase

A37-1 documented zero accepted real health-supervision sources and zero real healthy/degraded/unusable labels. A37-2 and A37-3 published a prospective evidence intake interface: four generic roles for camera and IMU, seven roles for the existing Velodyne VLP-32C-specific LiDAR protocol. A camera or IMU source still needs instrument-specific prospective acquisition methods. This design makes the next real acquisition more concrete **without pretending that an empty evidence packet supplies labels**.

## Camera: independent evidence candidate

- Identify the actual camera, measurement role, selected TRAIN source, and acquisition interval.
- Prospectively record camera device state, exposure/gain data and acquisition provenance **where supported**; independently record scene/test-target conditions and a functional measurement relation appropriate to visual motion.
- Verify device-to-image interval binding from independent physical-event/clock provenance. Do not use bag recorder timestamps or matching string clock names as proof of synchronization.
- Predeclare operational and state criteria independently of image brightness, blur scores, tracking residuals, localization error or held-out confirmation.
- Only after safety review may an authorized operator plan controlled imaging changes; the code does **not** execute them.

## IMU: independent evidence candidate

- Identify the actual IMU, its sensing role, axes, units, range/configuration and TRAIN interval.
- Prospectively record manufacturer-supported device-status and saturation/self-test evidence and, if feasible, an independent physical motion/reference instrument or verified stationary apparatus.
- Independently verify physical interval association, including event-time and any inter-device clock relationship.
- Predeclare impairment criteria for biased, noisy, stuck or saturated readings based on independent measurement-role evidence, not measured norm alone or a classifier's own inference.
- No motor excitation, robot motion, physical interference or on-robot command is authorized here.

## Separation and requirements

The A37-2 generic roles remain identical: prospective source declaration, independent measurement-role evidence, independent interval provenance, and independent state-criteria evidence. Filled SHA-256 fields would only satisfy a *shape* check. Artifact existence, origin, independence, measurement relation and real health labels still require separate review and acceptance under SE2. The VLP-32C status protocol is **not** transferable to Nova's LiDAR.

No thresholds are selected. Sensor-device operational status alone need not prove suitability for the full localization measurement role. Faults, environmental degradation, attacks and disagreement are not automatically source-attributed. Confirmation and validation partitions remain untouched.

## Outputs and next physical action

The module creates two deterministic empty acquisition packets with instrument-specific instructions and missing evidence roles. The operator/research team must select actual hardware instruments and acceptable independent measurement references **before any acquisition**. Follow-on work should first inventory the available independent camera and IMU status/physical-reference sources on the chosen robot, then approve a passive, time-bounded TRAIN acquisition protocol, and only later consider controlled interventions. Safety and physical timing review are prerequisites to accepting source evidence.

Real health-label count: **0**. Health-model training: **BLOCKED**. Physical factor admission: **DENIED**. Suppression, return-home, stop or robot action: **NOT AUTHORIZED**.
