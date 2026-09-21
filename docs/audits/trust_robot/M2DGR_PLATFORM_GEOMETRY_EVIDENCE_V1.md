# M2DGR Platform Geometry Evidence V1

## Status

`blocked_pending_physical_evidence`

Permanent evidence:

`manifests/m2dgr_platform_geometry_evidence_v1.json`

Content SHA256:

`6886f60101055363d8aac710d66ebb3b6013226e743071dcc4d1051b5a2ff8e2`

File SHA256:

`e1ba372d38faf32107b2c23ed836ab8a78b783269bab7f89e20f542c57159882`

This additive checkpoint records only explicit author drawing annotations and
qualitative platform-layout relationships.

It does not create or verify a reference-to-LiDAR transform and does not
authorize trajectory scoring.

## Author drawing provenance

The hash-bound platform drawing is:

`newcar4.png`

SHA256:

`07336e365b8b0e0067e2b29862bddf4f0227b5befc530541a29206a6cc939d01`

Git blob:

`b14648570f8993e037f4e5dc8fab1e8c335fb061`

Pinned source commit:

`e33e5ca6d1f914885c409be8b30c89a62500ca2e`

Author date:

`2021-12-19T10:25:35Z`

The hash-bound historical M2DGR sensor page is:

`sensor_calibration.md`

SHA256:

`394792f5ebf338527bc8a9fdd88930bbcd32ba9197a545b0bad49337ac7d5f6e`

Git blob:

`920d953b15e22525d62e205fde3266c615dba453`

Pinned source commit:

`011685e529a8ef1ffabb031922853fde3599521c`

Author date:

`2023-04-12T13:58:41Z`

The historical page states that the physical robot drawings use centimeters
and that the sensor-axis colors are:

- red: X;
- green: Y;
- blue: Z.

The page identifies the platform GNSS-IMU as Xsens MTi-680G and the LiDAR as
Velodyne VLP-32C.

These author sources are not treated as runtime MTi configuration, GT export
logs, timestamp-calibration logs, or independent physical calibration.

## Explicit drawing legend

Relevant numbered components are:

- `3`: LIDAR;
- `4`: GNSS-IMU;
- `5`: IMU;
- `6`: Antenna.

GNSS-IMU `#4` and Antenna `#6` are explicitly separate labeled components.

The drawing does not identify Antenna `#6` specifically as the MTi-680G GNSS
antenna and does not identify an antenna phase center.

## Explicit side-view annotation

Panel (a) explicitly shows a `15 cm` vertical dimension associated with LiDAR
`#3` above the middle-deck plane.

This checkpoint accepts that value only as an explicit author drawing
annotation.

It does not declare the `15 cm` annotation equal to the published
Xsens-to-LiDAR candidate vertical component of `-16.824 cm`.

No transform component is created or replaced from this annotation.

## Explicit middle-deck top-view annotations

Panel (c) explicitly depicts:

- middle-deck width: `58 cm`;
- middle-deck depth: `44 cm`;
- LiDAR center dimension from the left deck boundary: `29 cm`;
- GNSS-IMU `#4` and LiDAR `#3` on the same drawn dashed planar centerline.

The centerline relationship is retained as qualitative layout evidence only.

It is not promoted to an exact zero translation component.

The depicted sensor-axis arrows are qualitative orientation/layout evidence
only and are not promoted to a calibrated rotation matrix.

## Explicit upper-platform annotations

Panel (b) explicitly depicts:

- upper-platform width: `70 cm`;
- upper-platform depth: `50 cm`;
- Antenna `#6` dimension from the left boundary: `42 cm`;
- Antenna `#6` centerline dimension from the top boundary: `25 cm`.

No cross-panel coordinate registration is supplied.

No dimensions are subtracted across panels to manufacture an
Xsens-to-antenna, Xsens-to-LiDAR, or GNSS-to-LiDAR lever arm.

## Published candidate-transform context

The already frozen author calibration source contains:

Xsens IMU to LiDAR candidate translation:

`[15.905, 0.067, -16.824] cm`

GNSS to LiDAR candidate translation:

`[-9.825, 0.582, 72.673] cm`

Candidate Xsens/GNSS origin separation:

`93.12363359534464 cm`

Those values remain published candidate context only.

The platform drawing does not numerically verify:

- the Xsens-to-LiDAR candidate translation;
- the Xsens-to-LiDAR candidate rotation;
- the GNSS candidate transform;
- the runtime MTi-680G GNSS lever arm;
- the released-GT physical Xsens origin.

## Leica and mocap limitations

The drawing does not explicitly label:

- a Leica prism reference point;
- a mocap tracked-body origin.

This checkpoint therefore does not close either reference-origin problem.

## Visual-review methodology

The visual interpretation is limited to explicit:

- legend labels;
- printed dimensions;
- dimension arrows;
- platform boundaries;
- drawn dashed centerlines;
- sensor-axis arrows.

The review does not use:

- OCR as metric evidence;
- pixel-coordinate measurement;
- pixel-to-centimeter conversion;
- image registration;
- cross-panel fitting;
- calibration fitting;
- assumed enclosure centers;
- assumed antenna phase centers.

## Scientific conclusion

Positive evidence:

- hash-bound historical author platform drawing: TRUE;
- author-supported centimeter units: TRUE;
- author-supported axis-color semantics: TRUE;
- GNSS-IMU and antenna are distinct labeled components: TRUE;
- explicit LiDAR `15 cm` annotation present: TRUE;
- explicit `58 cm` deck width and `29 cm` LiDAR-center dimension present: TRUE;
- GNSS-IMU and LiDAR share a drawn planar centerline: TRUE;
- qualitative platform-layout support: TRUE.

Not established:

- independent physical calibration verification: FALSE;
- exact Xsens measurement origin: FALSE;
- Xsens-to-LiDAR candidate translation verified: FALSE;
- Xsens-to-LiDAR candidate rotation verified: FALSE;
- runtime MTi GNSS lever arm verified: FALSE;
- Antenna `#6` identified as MTi-680G GNSS antenna: FALSE;
- antenna phase center verified: FALSE;
- GNSS candidate-transform applicability verified: FALSE;
- Leica prism reference point verified: FALSE;
- Leica candidate-transform applicability verified: FALSE;
- mocap body origin verified: FALSE;
- GT timestamp physical-event semantics verified: FALSE;
- GT timestamp export/timebase semantics verified: FALSE;
- reference temporal association verified: FALSE;
- fixed reference offset supported: FALSE;
- interpolation authorized: FALSE;
- nearest-neighbor association authorized: FALSE;
- association tolerance supported: FALSE;
- evaluation interval authorized: FALSE;
- alignment selected: FALSE;
- estimator scoring authorized: FALSE;
- dataset calibration verified: FALSE;
- synchronization verified: FALSE;
- evaluation ready: FALSE.

No ATE/RPE scoring is authorized.

## Frozen-evidence handling

This checkpoint is additive.

Evaluation Protocol V2 and all predecessor reference/timing/calibration/split
evidence remain byte-identical.
