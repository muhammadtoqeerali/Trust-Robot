# M2DGR room_02: original ground-truth download access and reference-frame/timebase clarification

Hello M2DGR maintainers,

We are working on a reproducible, TRAIN-only scientific audit of the
original M2DGR `room_02` sequence (2021-07-30). We have its published
rosbag, but **we have not obtained the official reference GT file**.

The GT link appears in your immutable README at commit
`5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5` (Git blob `c394994a8431426c0bd4b3dcf618faf7b97d119f`):

https://sjtueducn-my.sharepoint.com/:t:/g/personal/594666_sjtu_edu_cn/ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL

Two noninteractive HTTPS attempts returned HTTP 302 redirect responses
without GT bytes. Could you confirm whether this download currently works
through a normal authorized browser session, or provide an alternative
official access mechanism for this exact original `room_02` GT export?

We will not circumvent authentication or redistribute the source.

For scientifically correct reference use, could you also clarify:

1. The canonical filename, source SHA-256, version, column schema,
   pose convention, quaternion order, units and timestamp epoch.
2. The tracked Vicon rigid body and its physically measured transform
   to `base_link` / Velodyne LiDAR, including direction and uncertainty.
3. The cause and recommended handling of 90 reference rotation records
   flagged invalid in our earlier frozen diagnostics.
4. The reference export clock and its mapping to `/velodyne_points`,
   `/handsfree/imu`, `/camera/imu` and
   `/camera/color/image_raw/compressed` sensor-header timestamps.
   Are measured clock offset/drift corrections available?
5. Which published physical camera/IMU/LiDAR calibrations apply
   specifically to `room_02`, including hardware identity and version?

Our previously recorded raw reference SHA-256 is
`79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d`, but we have not authenticated
that historical value against newly downloaded official GT bytes.
It is not a substitute for a checksum confirmed by the authors.

Thank you for maintaining M2DGR and for any guidance.
