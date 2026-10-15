#!/usr/bin/env python3
"""Check frozen local L1–L3 package and fail-closed logic. No writes."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parent

def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def main():
    assert len(sys.argv) == 2, 'usage: verify_checkpoint.py V16_READINESS_REPORT'
    manifest = read(PKG/'checkpoint_manifest_v1.json')
    assert manifest['schema'] == 'TRUST_ROBOT_V16_L123_DIAGNOSTIC_ADMISSION_CHECKPOINT_V1'
    assert manifest['parent_commit'] == '555edb8c0c0490c3791c0bdc3bc8a771ab11309c'
    for relative, expected in manifest['files_sha256'].items():
        assert sha(PKG/relative) == expected, relative
    for line in (PKG/'SHA256SUMS.txt').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        assert sha(PKG/relative) == digest, relative
    for name in ('phase_l1_registration.py','phase_l2_ambiguity.py','phase_l3_factor_gate.py'):
        ast.parse((PKG/'code'/name).read_text())
    upstream = Path(sys.argv[1]); assert sha(upstream)==manifest['upstream_v16_sha256']
    v16 = read(upstream)
    l1 = read(PKG/'evidence/registration_transfer_report_v1.json')
    l2 = read(PKG/'evidence/l2_registration_ambiguity_report_v1.json')
    l3 = read(PKG/'evidence/l3_factor_admission_report_v1.json')
    assert v16['offline_sensor_file_validation_pass'] is True
    assert l1['implementation_sha256'] == sha(PKG/'code/phase_l1_registration.py')
    assert l2['implementation_sha256'] == sha(PKG/'code/phase_l2_ambiguity.py')
    assert l3['implementation_sha256'] == sha(PKG/'code/phase_l3_factor_gate.py')
    assert l1['source_evidence_sha256'] == sha(upstream)
    assert l2['source_l1_report_sha256'] == sha(PKG/'evidence/registration_transfer_report_v1.json')
    assert l3['l1_sha256'] == sha(PKG/'evidence/registration_transfer_report_v1.json')
    assert l3['l2_sha256'] == sha(PKG/'evidence/l2_registration_ambiguity_report_v1.json')
    assert l1['pair_attempts']==10 and l1['frozen_diagnostics_available']==8 and l1['sparse_pairs_rejected']==2
    assert l2['engineering_audit_complete'] is True and l2['pose_factors_accepted']==0
    assert l3['engineering_gate_pass'] is True and l3['factors_admitted']==0
    assert l3['negative_tampering_tests_passed']==8
    assert all(x['estimator_pose_increment'] is None for x in l3['factor_decisions'])
    assert all(x['admission']=='DENIED' for x in l3['factor_decisions'])
    spec=importlib.util.spec_from_file_location('l3_frozen',PKG/'code/phase_l3_factor_gate.py')
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reproduced=module.decisions(l1,l2,v16)
    assert module.canon(reproduced)==module.canon(l3['factor_decisions'])
    assert module.selftests(l1,l2,v16)==8
    print('VERSIONED_SOURCE_AND_EVIDENCE=HASH_VERIFIED',flush=True)
    print('NEGATIVE_TAMPERING_TESTS=8_PASS',flush=True)
    print('QUALIFIED_POSE_FACTORS=0',flush=True)
    print('LOCAL_PACKAGE_VALIDATION=PASS',flush=True)

if __name__ == '__main__':
    main()
