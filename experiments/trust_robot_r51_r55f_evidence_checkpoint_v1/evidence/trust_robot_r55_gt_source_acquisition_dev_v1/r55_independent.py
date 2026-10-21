"""Independent source-byte, report and scientific-admission audit."""
import json
import pathlib
import sys

import r55_core as core

def verify(out, inv, tracker, prior):
    reportp = out / 'r55_acquisition_report_v1.json'
    planp = out / 'r55_acquisition_interpretation_v1.md'

    d = json.loads(reportp.read_text())
    core.check(d)

    sources = {
        'r54_inventory': inv,
        'r54_tracker': tracker,
        'r54_independent': prior
    }

    for key, path in sources.items():
        assert (
            d['r54_source_sha256'][key] ==
            core.sha(path.read_bytes())
        ), key

    source = out / 'room_02_reference_author_bytes.txt'
    quarantine = out / 'unverified_candidate_quarantine.bin'

    if d['acquisition_status'] == 'HASH_VERIFIED':
        assert (
            source.is_file()
            and not source.is_symlink()
            and not quarantine.exists()
        )
        assert core.sha(source.read_bytes()) == core.EXPECTED
        assert any(
            x['classification'] == 'EXACT_SHA256_MATCH'
            and x['response_sha256'] == core.EXPECTED
            for x in d['attempts']
        )

    elif d['acquisition_status'] == 'HASH_MISMATCH':
        assert not source.exists()
        assert quarantine.is_file()
        assert not quarantine.is_symlink()

        h = core.sha(quarantine.read_bytes())
        assert h != core.EXPECTED
        assert any(
            x['response_sha256'] == h
            and x['classification'] ==
            'SHA_MISMATCH_UNVERIFIED_SOURCE'
            for x in d['attempts']
        )

    else:
        assert not source.exists()
        assert not quarantine.exists()

    assert d['r43_scientific_gates_closed'] == 11
    assert d['r53_source_receipts_unfilled'] == 5
    assert d['next_phase'] in planp.read_text()

    proof = {
        'schema':
            'TRUST_ROBOT_R55_INDEPENDENT_SOURCE_ACQUISITION_AUDIT_V1',
        'primary_report_sha256':
            core.sha(reportp.read_bytes()),
        'plan_sha256':
            core.sha(planp.read_bytes()),
        'source_sha256_checked':
            d['acquisition_status'] == 'HASH_VERIFIED',
        'acquisition_status':
            d['acquisition_status'],
        'physically_qualified': False,
        'reference_scoring_authorized': False,
        'real_factors_authorized': False,
        'confirmation_test_accessed': False,
        'github_modified': False
    }

    with (
        out / 'r55_independent_validation_v1.json'
    ).open('x') as f:
        json.dump(proof, f, sort_keys=True, indent=2)
        f.write('\n')

    print(
        'R55_INDEPENDENT_SOURCE_FILE='
        + d['acquisition_status']
    )
    print('R55_INDEPENDENT_SCIENTIFIC_GATE=11_CLOSED')
    print('R55_INDEPENDENT_VALIDATION=PASS')

if __name__ == '__main__':
    verify(*(pathlib.Path(x) for x in sys.argv[1:5]))
