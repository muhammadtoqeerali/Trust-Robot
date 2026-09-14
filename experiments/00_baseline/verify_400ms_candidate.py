from pathlib import Path
import hashlib
import torch

from imu_reliability.baseline.date2025_cnn400 import (
    Date2025CNN400,
)


CKPT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

EXPECTED_SHA = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


print("CHECKPOINT =", CKPT)

actual_sha = sha256(CKPT)

print("SHA256     =", actual_sha)
print("SHA_MATCH  =", actual_sha == EXPECTED_SHA)

if actual_sha != EXPECTED_SHA:
    raise RuntimeError(
        "Checkpoint hash differs from frozen forensic hash."
    )

ckpt = torch.load(
    CKPT,
    map_location="cpu",
    weights_only=False,
)

historical_state = ckpt["state_dict"]

model_state = {
    key.removeprefix("model."): value
    for key, value in historical_state.items()
    if key.startswith("model.")
}

print()
print("HISTORICAL MODEL STATE KEYS =", len(model_state))

model = Date2025CNN400()

load_result = model.load_state_dict(
    model_state,
    strict=True,
)

print("STRICT_LOAD =", load_result)

model.eval()

parameter_count = sum(
    p.numel()
    for p in model.parameters()
    if p.requires_grad
)

print("TRAINABLE_PARAMETERS =", parameter_count)

if parameter_count != 63173:
    raise RuntimeError(
        f"Unexpected parameter count: {parameter_count}"
    )

torch.manual_seed(20250818)

x = torch.randn(
    16,
    40,
    9,
    dtype=torch.float32,
)

with torch.inference_mode():
    logits_reference = model(x)

    logits_feature_path, features = (
        model.forward_with_features(x)
    )

max_abs_diff = (
    logits_reference - logits_feature_path
).abs().max().item()

pred_reference = logits_reference.argmax(dim=1)
pred_feature = logits_feature_path.argmax(dim=1)

print()
print(
    "REFERENCE_LOGITS_SHAPE =",
    tuple(logits_reference.shape),
)

print(
    "FEATURE_LOGITS_SHAPE   =",
    tuple(logits_feature_path.shape),
)

print(
    "FEATURE_SHAPE          =",
    tuple(features.shape),
)

print(
    "MAX_LOGIT_ABS_DIFF     =",
    max_abs_diff,
)

print(
    "PREDICTIONS_IDENTICAL  =",
    torch.equal(
        pred_reference,
        pred_feature,
    ),
)

if max_abs_diff != 0.0:
    raise RuntimeError(
        "Feature-returning path changed task logits."
    )

if not torch.equal(
    pred_reference,
    pred_feature,
):
    raise RuntimeError(
        "Feature-returning path changed predictions."
    )

print()
print("FC1_WEIGHT =", tuple(model.fc[1].weight.shape))

if tuple(model.fc[1].weight.shape) != (256, 224):
    raise RuntimeError(
        "Recovered FC geometry does not match checkpoint."
    )

# Negative control: 30 samples must not silently pass.
try:
    bad = torch.randn(
        1,
        30,
        9,
        dtype=torch.float32,
    )

    with torch.inference_mode():
        model(bad)

except ValueError as exc:
    print("30_SAMPLE_REJECTION = PASS")
    print("MESSAGE =", exc)
else:
    raise RuntimeError(
        "30-sample input was incorrectly accepted."
    )

print()
print("BASELINE_RECONSTRUCTION_VERIFICATION = PASS")
