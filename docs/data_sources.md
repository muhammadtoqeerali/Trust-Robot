# Data source registry

## Local upstream source

UNIVRFall, KFall, historical segments, and the original Protechto
preprocessing assets are available from the local upstream project:

`Protechto-master`

This upstream directory is treated as read-only by IMU_Reliability.

The absolute workstation-specific path is stored only in
`configs/datasets/local_paths.yaml`, which is excluded from Git.

Derived manifests, split definitions, integrity injections, processed
artifacts, and experiment outputs must be created under IMU_Reliability
rather than written back into the upstream project.
