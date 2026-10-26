# R130 — Hilti-Oxford calibration provenance review

Scope: original research documentation; the underlying calibration handoff and source data are not approved for public redistribution.

## Provenance

The Hilti-Research 2022 challenge dataset publisher mirror was used
to identify six calibration YAML files from pinned repository revision
`e62017f907007fdc5ab8c721842e4ae7359d7f49`.

Publisher dataset: https://huggingface.co/datasets/Hilti-Research/hilti-slam-challenge-2022

Dataset license: CC BY-NC-SA 3.0:
https://creativecommons.org/licenses/by-nc-sa/3.0/

Academic citation: Zhang et al., *Hilti-Oxford Dataset:
A Millimeter-Accurate Benchmark for Simultaneous Localization and
Mapping*, IEEE Robotics and Automation Letters 8(1), 408-415
(2023), DOI:10.1109/LRA.2022.3226077.

No Hilti endorsement is implied.

## Engineering evidence

R130-B1 preserved six original publisher YAMLs on UNIVER, off Git,
under a source manifest with SHA256
`ffd88df49b95f4f0caf44a472236761085d74802e680b759c2546a54ad4daed3`.

R130-B2's first lexical parser was incomplete. Subsequent safe YAML
parsing reconstructed five camera models and six rigid transformations.
R130-B2-R2 checked camera topics, transformation structure, stereo
composition, frame hierarchy and eleven synthetic negative controls.

R130-B3 archived a source-pinned validator and detailed deterministic
report exclusively off Git on UNIVER. R130-B4 independently recomputed
the geometry using NumPy and reported ten tamper-control rejections.
The separately executed B4 program was not cryptographically archived;
its results are operator-witness evidence, not a sealed independent replay.

R130-B5 created a reduced five-file handoff. R130-B6A independently
audited it; R130-B6B transferred it through Windows; R130-B6C-R1
completed the KIOS off-Git intake after correcting a five-file
portable-verifier versus six-file intake-directory layout mismatch.

Minimal handoff archive SHA256:
`e87e64c075629d54166f4a610b9fd44c9fa52361901a78b7b192411c05b87899`.

KIOS intake receipt SHA256:
`9f310e9fc4dd0594b5cf5de20fd335d9f5b364e892747325d1e074b1aa4d1d92`.

## Scope and exclusions

Publisher calibration parameters and detailed validation results
are retained off Git. This documentation contains neither source
YAMLs nor calibration parameter arrays, raw bag bytes, per-message
sensor samples, calibration PDFs or reference ground-truth payloads.

Structural consistency does not establish physical extrinsic accuracy,
capture-time semantics, hardware clock synchronization, or an
independently proven alias between the recorded `imu_sensor_frame`
and the publisher calibration node `imu`.

Declared camera-IMU time corrections have not been applied.
No real estimator factors, calibrated sensor-health labels,
health-head training, ATE/RPE scoring or robot safety actions
are authorized.

M2DGR remains frozen at 22 TRAIN, 7 validation_calibration,
7 sealed confirmation_test. All eleven scientific gates remain CLOSED.

The underlying B5 handoff explicitly disallows public Git publication.
This documentation does not overturn that restriction or grant permission
to redistribute original publisher files or adapted calibration data.
No repository-wide license is inferred from the absence of a LICENSE file.

See the R130 scientific audit for further limitations.
