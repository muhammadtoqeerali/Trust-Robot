#!/usr/bin/env python3
"""R59: retrieve author README only, authenticate immutable Git blob, never GT."""

import base64
import hashlib
import json
import pathlib
import ssl
import sys
import urllib.error
import urllib.request

BLOB = 'c394994a8431426c0bd4b3dcf618faf7b97d119f'
COMMIT = '5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'

GT = (
    'https://sjtueducn-my.sharepoint.com/:t:/g/'
    'personal/594666_sjtu_edu_cn/'
    'ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL'
)

EXPECTED = '79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'

RAW = (
    'https://raw.githubusercontent.com/SJTU-ViSYS/M2DGR/'
    + COMMIT + '/README.md'
)

API = (
    'https://api.github.com/repos/SJTU-ViSYS/M2DGR/git/blobs/'
    + BLOB
)

LIMIT = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


def gitblob(data):
    return hashlib.sha1(
        b'blob ' + str(len(data)).encode() + b'\0' + data
    ).hexdigest()


def validate_author(data, expected=BLOB, link=GT):
    if not (0 < len(data) <= LIMIT):
        raise ValueError('BOUNDS')

    if data.lstrip().lower().startswith(
        (b'<html', b'<!doctype')
    ):
        raise ValueError('HTML')

    if gitblob(data) != expected:
        raise ValueError('GIT_BLOB_MISMATCH')

    s = data.decode('utf-8')

    rows = [
        line for line in s.splitlines()
        if line.startswith('room_02|')
    ]

    if len(rows) != 1:
        raise ValueError('ROOM_02_ROW_COUNT')

    fields = rows[0].split('|')

    if (
        len(fields) != 7
        or fields[0] != 'room_02'
        or fields[1] != '2021-07-30'
        or fields[3] != '75s'
    ):
        raise ValueError('ROOM_02_ROW_FIELDS')

    if fields[6] != '[GT](' + link + ')':
        raise ValueError('ROOM_02_LINK_CHANGED')

    return {
        'row': rows[0],
        'git_blob_sha1': gitblob(data),
        'readme_sha256': hashlib.sha256(data).hexdigest()
    }


def request(url):
    # Public GitHub only. No SharePoint requests or credentials.
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.HTTPSHandler(
            context=ssl.create_default_context()
        )
    )

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'TRUST-ROBOT-readme-provenance/1.0',
            'Accept': (
                'application/vnd.github+json'
                if url == API else 'text/plain'
            )
        }
    )

    with opener.open(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError('NON_200')

        length = response.headers.get('Content-Length')

        if length and int(length) > LIMIT * 2:
            raise ValueError('RESPONSE_TOO_LARGE')

        content = response.read(LIMIT * 2 + 1)

        if len(content) > LIMIT * 2:
            raise ValueError('RESPONSE_TOO_LARGE')

        return content


def audit(inv, tracker, r55, r43, receipt, out, stage):
    load = lambda p: json.loads(
        pathlib.Path(p).read_text(encoding='utf-8')
    )

    i, t, f, g, c = map(
        load, (inv, tracker, r55, r43, receipt)
    )

    if not (
        i['author_commit'] == COMMIT
        and i['author_readme_git_blob_sha1'] == BLOB
        and i['official_readme_lists_room_02_gt_candidate_url'] == GT
        and i['reference_sha256_from_frozen_r43'] == EXPECTED
    ):
        raise RuntimeError('PINNED_INVENTORY_DISAGREES')

    if not (
        g['raw_reference_provenance_sha256'] == EXPECTED
        and g['unresolved_gate_count'] == 11
        and len(g['requests']) == 11
        and all(
            x['status'] == 'NOT_QUALIFIED'
            for x in g['requests'].values()
        )
    ):
        raise RuntimeError('R43_GATES_CHANGED')

    if not (
        len(t['original_gate_receipts']) == 11
        and set(t['original_gate_receipts']) == set(g['requests'])
        and all(
            x['admission_authorized'] is False
            and x['source_sha256'] is None
            for x in t['original_gate_receipts'].values()
        )
    ):
        raise RuntimeError('R54_GATE_RECEIPTS_CHANGED')

    if not (
        f['acquisition_status'] == 'NOT_DOWNLOADED'
        and len(f['attempts']) == 2
        and all(
            x['http_status'] == 302
            for x in f['attempts']
        )
    ):
        raise RuntimeError('R55_HISTORY_CHANGED')

    if not (
        c['remote_equal_local'] is True
        and c['remote_commit']
        == 'a800ca91326a51fa0cc86972bed08e99b6b459e5'
    ):
        raise RuntimeError('R58C_PUBLICATION_CHANGED')

    attempts = []
    verified = None
    method = None

    for mode, url in (
        ('GITHUB_RAW_COMMIT', 'raw'),
        ('GITHUB_GIT_BLOB_API', 'api')
    ):
        try:
            payload = request(RAW if url == 'raw' else API)

            if url == 'api':
                obj = json.loads(payload.decode('utf-8'))

                if (
                    obj.get('sha') != BLOB
                    or obj.get('encoding') != 'base64'
                ):
                    raise ValueError('API_BLOB_METADATA')

                payload = base64.b64decode(
                    obj['content'], validate=False
                )

            validate_author(payload)
            verified = payload
            method = mode

            attempts.append({
                'method': mode,
                'result': 'VERIFIED_AUTHOR_README_GIT_BLOB'
            })
            break

        except Exception as exc:
            attempts.append({
                'method': mode,
                'result': 'NOT_VERIFIED',
                'reason_type': type(exc).__name__,
                'http_status': getattr(exc, 'code', None)
            })

    out = pathlib.Path(out)

    if verified is not None:
        dest = out / 'r59_official_readme_original_bytes_v1.md'

        with dest.open('xb') as h:
            h.write(verified)

        if dest.read_bytes() != verified:
            raise RuntimeError('READBACK_MISMATCH')

        details = validate_author(dest.read_bytes())
    else:
        details = None

    staged = pathlib.Path(stage)

    if staged.is_symlink():
        stage_status = 'UNSAFE_SYMLINK_REQUIRES_SEPARATE_REVIEW'
    elif staged.exists():
        stage_status = (
            'PRESENT_NOT_READ_REQUIRES_TARGETED_INDEPENDENT_GT_AUDIT'
        )
    else:
        stage_status = 'ABSENT_AT_EXACT_APPROVED_STAGING_PATH'

    report = {
        'schema': 'TRUST_ROBOT_R59_AUTHOR_README_IDENTITY_V1',
        'publication_baseline':
            'a800ca91326a51fa0cc86972bed08e99b6b459e5',
        'trajectory': 'room_02',
        'split': 'train',
        'author_commit': COMMIT,
        'expected_author_git_blob_sha1': BLOB,
        'gt_link_from_frozen_inventory': GT,
        'historical_expected_gt_sha256_NOT_MATCHED_TO_CURRENT_FILE':
            EXPECTED,
        'readme_verified': verified is not None,
        'verified_readme_details': details,
        'readme_retrieval_method': method,
        'public_github_attempts': attempts,
        'sharepoint_gt_requests_made_in_r59': 0,
        'manual_stage_status': stage_status,
        'official_gt_bytes_acquired_in_r59': False,
        'original_r55_http_302_attempts': 2,
        'r43_gates_closed': sorted(g['requests']),
        'r43_gate_count_closed': 11,
        'physical_frame_clock_qualified': False,
        'real_pose_factors_authorized': False,
        'health_training_authorized': False,
        'ate_rpe_authorized': False,
        'raw_bag_opened': False,
        'confirmation_test_accessed': False,
        'github_modified': False,
        'next':
            'TARGETED_GT_BYTE_AUDIT_ONLY_IF_AUTHORIZED_FILE_IS_STAGED'
            '_OTHERWISE_HUMAN_AUTHOR_ACCESS_REQUEST'
    }

    with (
        out / 'r59_source_identity_report_v1.json'
    ).open('x', encoding='utf-8') as h:
        json.dump(report, h, indent=2, sort_keys=True)
        h.write('\n')

    plan = (
        '# R59 primary-source access decision — no official GT obtained\n\n'
        'The pinned author README is official **link provenance**, '
        'not downloaded GT.\n'
        f'Author README immutable Git blob: `{BLOB}`; '
        f'verified on KIOS: `{verified is not None}`.\n'
        f'Actual SharePoint reference candidate: {GT}\n'
        f'Expected *historical* reference digest '
        f'(not matched to downloaded bytes): `{EXPECTED}`.\n\n'
        f'User-authorized manual staging path: `{stage}`\n'
        f'Staging status at this run: `{stage_status}`.\n\n'
        'Next human action: use the normal institutional '
        'SharePoint browser UI if access is granted;\n'
        'download the original `room_02` GT bytes, without '
        'saving a preview or altering formatting,\n'
        'then request a **new targeted** independent byte '
        'and pose-schema verification.\n'
        'If inaccessible, the R54 author-facing request '
        'remains a DRAFT (not sent).\n'
        'Seek canonical file identity, author checksum, '
        'reference timestamps, export conventions,\n'
        'tracked rigid-body origin, invalid-rotation handling, '
        'clock mapping and sensor extrinsics.\n'
        'No automatic SharePoint retry, GT reconstruction, '
        'source substitution,\n'
        'physical reference qualification, real sensor factors, '
        'health or ATE/RPE.\n'
    )

    (
        out / 'r59_access_next_actions_v1.md'
    ).write_text(plan, encoding='utf-8')

    print(
        'R59_AUTHOR_README_GIT_BLOB='
        + (
            'VERIFIED'
            if verified is not None
            else 'NOT_ACQUIRED_NETWORK_OR_RESPONSE'
        )
    )
    print('R59_GT_MANUAL_STAGE=' + stage_status)
    print('R59_OFFICIAL_GT_BYTES=NOT_ACQUIRED_BY_THIS_PHASE')
    print('R59_AUTHOR_CONTACT=SENT_NO')


if __name__ == '__main__':
    audit(*sys.argv[1:])
