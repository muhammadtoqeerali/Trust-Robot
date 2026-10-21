# M2DGR `room_02` source provenance / timing request — draft, not sent

**Status:** Source request only. No email or GitHub issue was posted. No external ground-truth file was acquired, parsed, or qualified.

## First actionable public lead (still unverified as local data)

- Author repository README pinned at commit `5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5` (Git blob SHA1 `c394994a8431426c0bd4b3dcf618faf7b97d119f`): https://github.com/SJTU-ViSYS/M2DGR/blob/5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5/README.md
- Published `room_02` GT link appearing in that README: https://sjtueducn-my.sharepoint.com/:t:/g/personal/594666_sjtu_edu_cn/ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL
- Author dataset website: https://sjtu-visys.github.io/M2DGR/
- Expected existing raw `room_02` reference SHA256 from frozen R43: `79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d`.
- **Do not presume** the linked download matches that SHA. In R55, validate the response content type, exact bytes, SHA256, document format and correspondence to this room recording before any use.

## Author-facing message (review and send manually if source provenance remains unresolved)

**Subject: M2DGR room_02 — GT reference export, clock mapping and calibration provenance**

Hello M2DGR team,

We are conducting reproducible TRAIN-only research using the published `room_02` recording (2021-07-30) and would appreciate primary-source clarification before using sensor calibrations or computing ATE/RPE.

1. Could you confirm that the `room_02` GT link in your pinned README is the correct original mocap export, and provide its canonical filename, original SHA256, format, row field meanings, quaternion ordering, coordinate handedness, units and timestamp source?
2. Which physical tracked marker cluster or rigid body does the Vicon mocap pose represent? What are the tracked-body origin and the direction/units of the rigid transform from mocap body to Velodyne LiDAR and relevant robot `base_link` frame?
3. Our existing source audit flags 90 invalid reference rotation rows; can you clarify the export convention, missing/invalid markers and a documented policy for these samples?
4. For `/camera/color/image_raw/compressed`, `/camera/imu`, `/handsfree/imu`, and `/velodyne_points`, which physical event does `header.stamp` represent, on which hardware or host timebase, and were any time offsets/drift corrections or scan-time transformations applied in the `room_02` recording pipeline?
5. Does `calibration_results.txt` and the `my_params_camera.yaml` / `my_params_lidar.yaml` published at this commit apply to the same `room_02` hardware devices and recording date? Could you provide serials, firmware, calibration version and physically validated camera/IMU/LiDAR extrinsic directions and measurement uncertainty?
6. The camera application points at `/handsfree/imu` but its four IMU noise parameters numerically match 10 times the published Xsens values; please clarify intended physical IMU and parameter units. Is the published camera-to-IMU translation the intended `room_02` transform?
7. Can you provide independent validation receipts for any timebase mappings, reference transform and calibration values, particularly the interpretation of the motion-capture reference export clock?

We can supply a description of our source audit if useful. We will cite your official source and preserve your original files byte-for-byte.

Thank you.

## Required provenance for any returned evidence

Keep response and downloaded files **outside Git** until authenticated. Save source URL, originating person/organization, retrieval timestamp, exact bytes SHA256, byte size, media type, hardware/trajectory applicability, author version and independent check. Reject HTML login pages and redirects as GT content. Do not interpret this request or a matching hash as sufficient physical qualification.

All five R53 physical source receipts remain explicitly null; all eleven R43 qualification receipts remain empty. Four physical clock domains unverified, 90 invalid reference rotations unresolved, and the frozen 22/7/7 split (including sealed confirmation_test) remains unchanged.

## Next: R55

Attempt controlled acquisition of only the published `room_02` GT candidate, never the raw rosbag or confirmation_test; compare against the expected reference SHA256. If inaccessible, record a transport failure and use this request packet, without fabricating a reference.
