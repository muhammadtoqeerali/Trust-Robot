"""Issue a local L34 post-capture challenge.

This is a userspace engineering challenge, not hardware attestation.
"""

import argparse
import hashlib
import json
import secrets
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--contract", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()

contract_file = Path(a.contract)
output = Path(a.output)

assert contract_file.is_file()
assert not contract_file.is_symlink()

contract_sha = hashlib.sha256(
    contract_file.read_bytes()
).hexdigest()

assert contract_sha == (
    "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
)

contract = json.loads(contract_file.read_text())

assert contract["schema"] == (
    "TRUST_ROBOT_L33_PROSPECTIVE_ACQUISITION_CONTRACT_V1"
)
assert contract["pose_factors_authorized"] == 0

challenge = {
    "schema": "TRUST_ROBOT_L34_LOCAL_CHALLENGE_V1",
    "purpose": "POST_CAPTURE_OFFLINE_DRYRUN",
    "nonce_hex": secrets.token_hex(32),
    "issued_monotonic_ns_unqualified": time.monotonic_ns(),
    "issued_wall_ns_unqualified": time.time_ns(),
    "l33_contract_sha256": contract_sha,
    "physical_sensor_attestation": False,
}

with output.open("x", encoding="utf-8") as f:
    json.dump(challenge, f, indent=2, sort_keys=True)
    f.write("\n")

print("L34_CHALLENGE_ISSUED=PASS")
