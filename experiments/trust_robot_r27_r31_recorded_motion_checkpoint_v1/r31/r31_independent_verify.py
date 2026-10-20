"""Independent recorded-frame and optical-flow verification."""

import hashlib
import json
import pathlib
import sys

import cv2
import numpy as np
import r18_decode as ros
import r31_camera as candidate


def need(condition, reason):
    if not condition:
        raise ValueError(
            'R31_INDEPENDENT_DENIED:' + reason
        )


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(a, b):
    if a is None or b is None:
        return a is None and b is None

    return bool(np.isclose(
        a, b, rtol=1e-7, atol=1e-7
    ))


def standalone_lk(x, y):
    features = cv2.goodFeaturesToTrack(
        x, 400, 0.01, 8,
        blockSize=7,
        useHarrisDetector=False
    )

    count = 0 if features is None else len(features)

    result = {
        'initial_corner_count': count,
        'forward_backward_consistent_count': 0,
        'median_dx_px': None,
        'median_dy_px': None,
        'median_displacement_px': None,
        'p90_displacement_px': None,
        'median_forward_backward_error_px': None,
    }

    if not count:
        return result

    args = dict(
        winSize=(21, 21),
        maxLevel=3,
        criteria=(
            cv2.TERM_CRITERIA_EPS
            | cv2.TERM_CRITERIA_COUNT,
            30,
            0.01,
        ),
    )

    next_xy, ok1, _ = cv2.calcOpticalFlowPyrLK(
        x, y, features, None, **args
    )

    back, ok2, _ = cv2.calcOpticalFlowPyrLK(
        y, x, next_xy, None, **args
    )

    a = features.reshape(-1, 2)
    b = next_xy.reshape(-1, 2)
    c = back.reshape(-1, 2)

    valid = []

    for i in range(count):
        if not (ok1[i, 0] and ok2[i, 0]):
            continue

        if not (
            np.isfinite(a[i]).all()
            and np.isfinite(b[i]).all()
            and np.isfinite(c[i]).all()
        ):
            continue

        if not (
            0 <= b[i, 0] < x.shape[1]
            and 0 <= b[i, 1] < x.shape[0]
        ):
            continue

        error = float(np.linalg.norm(
            c[i].astype(np.float64)
            - a[i].astype(np.float64)
        ))

        if error > 1.5:
            continue

        delta = (
            b[i].astype(np.float64)
            - a[i].astype(np.float64)
        )

        valid.append([
            delta[0],
            delta[1],
            np.linalg.norm(delta),
            error,
        ])

    result['forward_backward_consistent_count'] = len(valid)

    if valid:
        values = np.asarray(valid)

        result.update(
            median_dx_px=float(
                np.median(values[:, 0])
            ),
            median_dy_px=float(
                np.median(values[:, 1])
            ),
            median_displacement_px=float(
                np.median(values[:, 2])
            ),
            p90_displacement_px=float(
                np.percentile(values[:, 2], 90)
            ),
            median_forward_backward_error_px=float(
                np.median(values[:, 3])
            ),
        )

    return result


def verify(
    bag, index, samples, r22,
    report_path, destination
):
    report = json.loads(report_path.read_text())
    candidate.guard(report)

    observed_index = json.loads(index.read_text())
    raw_samples = json.loads(samples.read_text())
    prior = json.loads(r22.read_text())

    need(
        report['bag_sha256']
        == observed_index['file_sha256']
        == raw_samples['recording_sha256']
        == prior['bag_sha256'],
        'BAG_CHAIN'
    )

    need(
        report['source_report_sha256'] == {
            'r17': sha(index.read_bytes()),
            'r18': sha(samples.read_bytes()),
            'r22': sha(r22.read_bytes()),
        },
        'REPORT_SOURCE_HASH'
    )

    connections = {
        entry['id']: entry
        for entry in observed_index['connections']
    }

    images = []

    with bag.open('rb') as handle:
        for k, sample in enumerate(
            raw_samples['samples'][candidate.TOPIC]
        ):
            chunk, _ = ros.chunk_data(
                handle, sample['chunk_offset']
            )

            found = [
                (time, bytes(body))
                for cid, time, body in ros.messages(
                    chunk, connections
                )
                if (
                    cid == sample['connection_id']
                    and time == sample['bag_record_time_ns']
                    and sha(body)
                    == sample['serialized_message_sha256']
                )
            ]

            need(
                len(found) == 1,
                'RELOCATION_COUNT'
            )

            body = found[0][1]

            need(
                sha(body)
                == report['frames'][k]['serialized_message_sha256']
                and len(body)
                == sample['serialized_message_bytes'],
                'SERIALIZED_HASH'
            )

            cursor = ros.Cursor(body)
            header = ros.header(cursor)
            fmt = cursor.text(256)
            size = cursor.number()
            jpeg = cursor.take(size).tobytes()
            cursor.done()

            need(
                'jpeg' in fmt.lower()
                and sha(jpeg)
                == sample['image_payload_sha256']
                == report['frames'][k]['jpeg_payload_sha256'],
                'SOURCE_JPEG_HASH'
            )

            gray = cv2.imdecode(
                np.frombuffer(jpeg, dtype=np.uint8),
                cv2.IMREAD_GRAYSCALE
            )

            need(
                gray is not None
                and gray.shape == (480, 640)
                and sha(gray.tobytes())
                == report['frames'][k][
                    'decoded_grayscale_sha256'
                ],
                'SOURCE_PIXELS'
            )

            need(
                header['sequence']
                == report['frames'][k]['sequence']
                and header['header_stamp_ns']
                == report['frames'][k]['header_stamp_ns']
                and header['frame_id']
                == report['frames'][k]['frame_id'],
                'HEADER_LINEAGE'
            )

            images.append(gray)

    recalculated = standalone_lk(*images)
    measured = report['pixel_motion']

    for key, value in recalculated.items():
        need(
            compare(measured[key], value),
            'RECOMPUTED_TRACK:' + key
        )

    result = {
        'schema':
            'TRUST_ROBOT_R31_INDEPENDENT_CAMERA_PIXEL_MOTION_V1',
        'source_report_sha256':
            sha(report_path.read_bytes()),
        'serialized_messages_verified': 2,
        'jpeg_payload_hashes_verified': 2,
        'decoded_grayscale_hashes_verified': 2,
        'independent_lk_numeric_recomputation': True,
        'features_verified':
            recalculated['initial_corner_count'],
        'forward_backward_consistent_tracks_verified':
            recalculated['forward_backward_consistent_count'],
        'visual_odometry_authorized': False,
        'real_sensor_factors_authorized': False,
        'physical_capture_timing_verified': False,
    }

    with destination.open('x', encoding='utf-8') as handle:
        json.dump(
            result,
            handle,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write('\n')

    print('R31_INDEPENDENT_SERIALIZED_IMAGES=2_VERIFIED')
    print('R31_INDEPENDENT_GRAYSCALE_IMAGE_HASHES=2_VERIFIED')
    print(
        'R31_INDEPENDENT_OPTICAL_FLOW_RECOMPUTATION=NUMERIC_MATCH'
    )
    print('R31_INDEPENDENT_VALIDATION=PASS')


if __name__ == '__main__':
    verify(
        *(pathlib.Path(x) for x in sys.argv[1:7])
    )
