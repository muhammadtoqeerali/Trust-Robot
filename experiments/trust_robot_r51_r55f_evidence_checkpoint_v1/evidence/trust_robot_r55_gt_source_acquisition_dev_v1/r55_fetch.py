"""Bounded unauthenticated HTTPS retrieval; never executes source content."""
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

import r55_core as core

MAX_BYTES = 16 * 1024 * 1024
ALLOWED_SUFFIXES = (
    '.sharepoint.com',
    '.sharepointonline.com',
    '.sharepoint-df.com'
)

def safe_url(url):
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ''

    if (
        p.scheme != 'https'
        or p.username is not None
        or p.password is not None
        or p.port not in (None, 443)
    ):
        raise ValueError('R55_DISALLOWED_REDIRECT_SCHEME')

    if (
        host != 'sjtueducn-my.sharepoint.com'
        and not any(host.endswith(s) for s in ALLOWED_SUFFIXES)
    ):
        raise ValueError('R55_DISALLOWED_REDIRECT_HOST:' + host)

    return host

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(
            req, fp, code, msg, headers, newurl
        )

def get(url):
    safe_url(url)

    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(
        url,
        headers={
            'User-Agent':
                'Mozilla/5.0 (compatible; TRUST-ROBOT-R55-Source-Verification/1.0)',
            'Accept':
                'text/plain,application/octet-stream,*/*;q=0.5'
        }
    )

    with opener.open(request, timeout=16) as res:
        body = bytearray()
        content_type = res.headers.get(
            'Content-Type', ''
        ).lower()
        http_status = res.status
        last_host = safe_url(res.geturl())

        while True:
            chunk = res.read(
                min(65536, MAX_BYTES + 1 - len(body))
            )
            if not chunk:
                break

            body += chunk
            if len(body) > MAX_BYTES:
                raise ValueError(
                    'R55_DOWNLOAD_OVERSIZE_BOUND_16MIB'
                )

        return bytes(body), http_status, content_type, last_host

def run(out, inventory, tracker, independent):
    out.mkdir(mode=0o700, parents=False, exist_ok=True)

    source_files = {
        'r54_inventory': inventory,
        'r54_tracker': tracker,
        'r54_independent': independent
    }
    parents = {
        key: core.sha(path.read_bytes())
        for key, path in source_files.items()
    }

    inv = json.loads(inventory.read_text())
    tr = json.loads(tracker.read_text())
    iv = json.loads(independent.read_text())

    combined = (
        json.dumps(inv, sort_keys=True)
        + json.dumps(tr, sort_keys=True)
    )

    if (
        core.URL not in combined
        or core.EXPECTED not in combined
    ):
        raise ValueError(
            'R55_R54_OFFICIAL_URL_OR_EXPECTED_HASH_UNBOUND'
        )
    if not iv:
        raise ValueError('R55_R54_INDEPENDENT_EMPTY')

    attempts = []
    candidate = None
    status = 'NOT_DOWNLOADED'

    urls = (
        core.URL,
        core.URL + '&download=1'
    )

    for idx, url in enumerate(urls):
        rec = {
            'variant':
                'official_url' if idx == 0
                else 'official_url_download_parameter',
            'http_status': None,
            'content_type': None,
            'final_host': None,
            'bytes_received': 0,
            'response_sha256': None,
            'classification': 'NO_RESPONSE',
            'error': None
        }

        try:
            data, code, mime, host = get(url)

            rec.update({
                'http_status': code,
                'content_type': mime[:100],
                'final_host': host,
                'bytes_received': len(data),
                'response_sha256': core.sha(data)
            })

            if core.sha(data) == core.EXPECTED:
                rec['classification'] = 'EXACT_SHA256_MATCH'
                with (
                    out / 'room_02_reference_author_bytes.txt'
                ).open('xb') as fp:
                    fp.write(data)

                status = 'HASH_VERIFIED'

            else:
                prefix = data[:256].lstrip().lower()
                html = (
                    'text/html' in mime
                    or prefix.startswith(b'<!doctype html')
                    or prefix.startswith(b'<html')
                    or b'<html' in prefix[:128]
                )

                if html:
                    rec['classification'] = (
                        'HTML_OR_AUTHENTICATION_PAGE_NOT_GT'
                    )
                elif not data:
                    rec['classification'] = 'EMPTY_NOT_GT'
                else:
                    rec['classification'] = (
                        'SHA_MISMATCH_UNVERIFIED_SOURCE'
                    )
                    if candidate is None:
                        candidate = data

        except (
            OSError,
            ValueError,
            urllib.error.URLError,
            urllib.error.HTTPError
        ) as exc:
            rec['error'] = (
                type(exc).__name__ + ': ' + str(exc)
            )[:360]
            rec['classification'] = (
                'ERROR_OR_AUTH_REQUIRED'
            )

            if isinstance(exc, urllib.error.HTTPError):
                rec['http_status'] = exc.code

        attempts.append(rec)

        print(
            'R55_ATTEMPT_' + str(idx + 1)
            + '=' + rec['classification']
            + ' HTTP=' + str(rec['http_status'])
        )

        if status == 'HASH_VERIFIED':
            break

    if status != 'HASH_VERIFIED' and candidate is not None:
        with (
            out / 'unverified_candidate_quarantine.bin'
        ).open('xb') as fp:
            fp.write(candidate)
        status = 'HASH_MISMATCH'

    report = core.record_template(
        status,
        attempts,
        parents,
        'room_02_reference_author_bytes.txt'
        if status == 'HASH_VERIFIED' else None
    )

    (out / 'r55_acquisition_report_v1.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n'
    )

    lines = [
        '# R55 official room_02 reference acquisition attempt',
        '',
        'Status: **' + status + '**.',
        '',
        'Expected reference SHA256: `' + core.EXPECTED + '`.',
        '',
        'Outcome is source-byte authentication only, '
        'not physical reference qualification.',
        '',
        'The ROS bag and confirmation-test data were not opened.',
        '',
        'No pose, health or ATE/RPE authorization; '
        'all 11 qualification gates remain closed.',
        '',
        'Next phase: `' + report['next_phase'] + '`.',
        ''
    ]

    if status == 'NOT_DOWNLOADED':
        lines += [
            'The published SharePoint URL did not yield a '
            'matching reference file.',
            '',
            'Use an authorized browser session to obtain '
            'the exact author-linked file if needed. '
            'No substitute may be accepted without '
            'independent SHA256 verification.',
            ''
        ]

    if status == 'HASH_MISMATCH':
        lines += [
            'A non-HTML response was preserved in '
            'off-Git quarantine.',
            '',
            'Investigate exact source identity and '
            'SHA256 discrepancy before any ingestion.',
            ''
        ]

    if status == 'HASH_VERIFIED':
        lines += [
            'The retrieved source bytes exactly match '
            'the pinned expected SHA256.',
            '',
            'Next inspect format, frame, timestamp semantics '
            'and invalid rotations before considering '
            'scientific reference qualification.',
            ''
        ]

    (out / 'r55_acquisition_interpretation_v1.md').write_text(
        '\n'.join(lines) + '\n'
    )

    print('R55_ACQUISITION_STATUS=' + status)
    print(
        'R55_ACTUAL_SHA256_MATCH='
        + ('YES' if status == 'HASH_VERIFIED' else 'NO')
    )
    print('NEXT=' + report['next_phase'])

if __name__ == '__main__':
    run(*(pathlib.Path(x) for x in sys.argv[1:5]))
