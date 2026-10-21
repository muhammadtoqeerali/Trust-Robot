"""Standalone R75 SHA-pinned, fail-closed Git archive verifier."""
import hashlib
import json
import pathlib
import stat
import sys

BASE = '6873da42fda57f23a46c0ecb2c788489802faa8c'

SOURCE_PINS = {
    'evidence/dev/r74_independent.py': 'f0fc607373661d2f257f2ecec609650e43dcfdc76d780751076c50ce690bc5b3',
    'evidence/dev/r74_review.py': '17a1588d8284a4f5a3c2f563f9c315845d6e7e1a9964ef65c9ecd3ce1811c9d0',
    'evidence/dev/test_r74.py': '010b3d8149a9c8ce171c3722893337b9951df5a17b49ec02983eded3e734b516',
    'evidence/result/r74_independent_validation_v1.json': 'b1c24d687050ce8ce3bbc86c8627daff021e8c99b61abc5c7b5f47fb8d2a666c',
    'evidence/result/r74_scientific_admissibility_v1.json': '22b02194a8899a263484a90e30afd3f95a3fb45d2ccdd7dec8bb8908d59fc98b',
    'evidence/result/r74_scientific_summary_v1.md': 'a7f27a895ec649785d286f5897861403f41556833f070dc6971f11c9c61dc73d',
}

TRANSFERRED_PINS = {
    'r70': 'ae0ff5e201f449d34d749b0b6f22254e4455fb0b5422862cc127103e84eba5a0',
    'r71a': 'c0b5264a70ca708d7b532b77388dfe6ce90d71ebba4b47011e48f522d25661e5',
    'r72': 'efcbcbc85dc02732e1fd130c840b921d0abdab72dfda494dd3490b8609fb3d74',
    'r73': 'a90b3bbd9de75e2c6a50a6121eec1779b40a8e48362e38308480d736f6a877c0',
}

GT_SHA = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
QUALITY_SHA = '8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49'

def need(x, why):
    if not x:
        raise ValueError('R75_VERIFY_DENIED:' + why)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(root):
    need(root.is_dir() and not root.is_symlink(), 'ROOT')

    expected = set(SOURCE_PINS) | {
        'README.md',
        'checkpoint_manifest_v1.json',
        'verify_checkpoint.py'
    }

    actual = {
        str(p.relative_to(root))
        for p in root.rglob('*')
        if p.is_file() or p.is_symlink()
    }

    need(expected == actual and len(actual) == 9, 'FILE_ALLOWLIST')

    for rel in expected:
        p = root / rel
        s = p.lstat()
        need(
            stat.S_ISREG(s.st_mode)
            and s.st_nlink == 1
            and 0 < s.st_size <= 1024*1024,
            'REGULAR_FILE:' + rel
        )

    for rel, hash_expected in SOURCE_PINS.items():
        need(sha(root / rel) == hash_expected, 'SHA256:' + rel)

    m = json.loads(
        (root / 'checkpoint_manifest_v1.json').read_text('utf-8')
    )

    need(
        m.get('schema') ==
        'TRUST_ROBOT_R70_R74_SANITIZED_CHECKPOINT_V1',
        'SCHEMA'
    )
    need(
        m.get('parent_commit') == BASE
        and m.get('branch') == 'kios-isaacsim-v15-integration',
        'GIT_PARENT'
    )
    need(
        m.get('source_pins') == SOURCE_PINS
        and m.get('source_count') == 6,
        'SOURCE_MANIFEST'
    )
    need(
        m.get('verona_private_report_pins') == TRANSFERRED_PINS,
        'PRIVATE_REPORT_LINEAGE'
    )
    need(
        m.get('gt_sha256') == GT_SHA
        and m.get('quality_sha256') == QUALITY_SHA,
        'REFERENCE_PINS'
    )
    need(m.get('scientific_gates_closed') == 11, 'GATES')

    for key in (
        'raw_gt_archived',
        'rosbags_archived',
        'private_verona_reports_archived',
        'confirmation_test_accessed',
        'physical_frame_qualified',
        'physical_clock_qualified',
        'pose_scoring_authorized',
        'health_training_authorized',
    ):
        need(m.get(key) is False, 'MANIFEST_DENIAL:' + key)

    r = json.loads(
        (root / 'evidence/result/r74_scientific_admissibility_v1.json').read_text('utf-8')
    )
    i = json.loads(
        (root / 'evidence/result/r74_independent_validation_v1.json').read_text('utf-8')
    )

    need(
        r.get('schema') ==
        'TRUST_ROBOT_R74_SANITIZED_EVIDENCE_DECISION_V1',
        'R74_SCHEMA'
    )
    need(
        r.get('source_report_sha256') == TRANSFERRED_PINS,
        'R74_REPORT_LINEAGE'
    )
    need(
        r.get('historical_gt_sha256') == GT_SHA
        and r.get('historical_quality_sha256') == QUALITY_SHA,
        'GT_QUALITY'
    )
    need(
        r.get('historical_gt_records') == 3831
        and r.get('structurally_invalid_rotations') == 90
        and r.get('invalid_rotation_sample_runs') == 61,
        'QUALITY_COUNTS'
    )
    need(
        r.get('scientific_gates_closed') == 11
        and all(v is False for v in r.get('physical_qualification', {}).values())
        and len(r.get('physical_qualification', {})) == 10,
        'R74_DENIAL'
    )

    for key in (
        'raw_gt_read_in_r74',
        'raw_rosbag_read_in_r74',
        'confirmation_test_accessed',
        'ate_rpe_authorized',
        'health_training_authorized',
        'real_pose_factors_authorized',
    ):
        need(r.get(key) is False, 'R74_SAFETY:' + key)

    need(
        i.get('status') == 'PASS'
        and i.get('primary_report_sha256') ==
        sha(root / 'evidence/result/r74_scientific_admissibility_v1.json'),
        'INDEPENDENT_RECEIPT'
    )
    need(
        i.get('scientific_gates_closed') == 11
        and i.get('physical_frame_or_clock_qualified') is False
        and i.get('raw_gt_or_rosbag_opened') is False,
        'INDEPENDENT_DENIAL'
    )

    for rel in (
        'evidence/result/r74_scientific_admissibility_v1.json',
        'evidence/result/r74_independent_validation_v1.json',
        'evidence/result/r74_scientific_summary_v1.md',
        'README.md',
        'checkpoint_manifest_v1.json',
    ):
        contents = (root / rel).read_text('utf-8')
        for forbidden in (
            '/home/kios/',
            '/mnt/hdd16T/',
            'C:\\Users\\',
            '"matching_excerpt_samples"',
            '"path":',
        ):
            need(
                forbidden not in contents,
                'PRIVATE_PATH_OR_EXCERPT:' + rel
            )

    print('R75_STANDALONE_CHECKPOINT_VERIFIER=PASS')
    print('R75_SOURCE_ARTIFACT_PINS=6_EXACT')
    print('R75_SCIENTIFIC_GATES=11_CLOSED')

if __name__ == '__main__':
    need(
        len(sys.argv) == 3 and sys.argv[1] == 'verify',
        'ARGUMENTS'
    )
    verify(pathlib.Path(sys.argv[2]))
