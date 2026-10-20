"""Authenticated TRAIN camera tracking. Pixel motion only."""

import hashlib
import json
import pathlib
import sys

import cv2
import numpy as np
import r18_decode as ros

TOPIC = '/camera/color/image_raw/compressed'

FLAGS = (
    'camera_intrinsics_physically_verified',
    'metric_scale_established',
    'six_dof_pose_estimated',
    'essential_matrix_pose_promoted',
    'physical_capture_time_verified',
    'cross_modal_alignment_performed',
    'full_extrinsics_verified',
    'ground_truth_scored',
    'health_label_assigned',
    'health_model_training_authorized',
    'real_sensor_factor_execution_authorized',
    'm2dgr_scoring_authorized',
    'confidence_calibrated',
    'raw_recording_modified',
    'github_modified',
)


def need(condition, reason):
    if not condition:
        raise ValueError('R31_DENIED:' + reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def load_frames(bag, index_path, sample_path, r22_path):
    index, samples, old = (
        load(path)
        for path in (index_path, sample_path, r22_path)
    )

    need(
        index['trajectory_id']
        == samples['trajectory_id']
        == old['trajectory_id']
        == 'room_02'
        and old['split'] == 'train'
        and samples['split'] == 'train',
        'TRAIN_ONLY'
    )

    need(
        index['file_sha256']
        == samples['recording_sha256']
        == old['bag_sha256'],
        'BAG_CHAIN'
    )

    selected = samples['samples'][TOPIC]
    prior = old['signals'][TOPIC]

    need(
        len(selected) == len(prior) == 2
        and selected[0]['chunk_offset']
        != selected[1]['chunk_offset'],
        'TWO_SAMPLES'
    )

    need(
        selected[1]['sequence']
        == selected[0]['sequence'] + 1
        and selected[1]['header_stamp_ns']
        > selected[0]['header_stamp_ns'],
        'CONSECUTIVE_HEADER'
    )

    connections = {
        entry['id']: entry
        for entry in index['connections']
    }

    images = []
    records = []

    with pathlib.Path(bag).open('rb') as handle:
        for i, entry in enumerate(selected):
            raw, mode = ros.chunk_data(
                handle, entry['chunk_offset']
            )

            need(
                mode in samples['compression_methods'],
                'COMPRESSION'
            )

            matches = []

            for cid, stamp, view in ros.messages(
                raw, connections
            ):
                if (
                    cid == entry['connection_id']
                    and stamp == entry['bag_record_time_ns']
                    and sha(view)
                    == entry['serialized_message_sha256']
                ):
                    matches.append(bytes(view))

            need(
                len(matches) == 1,
                'SERIALIZED_MESSAGE_MISMATCH'
            )

            body = matches[0]

            need(
                len(body) == entry['serialized_message_bytes'],
                'SOURCE_LENGTH'
            )

            decoded = ros.decode(TOPIC, body)

            required = (
                'header_stamp_ns',
                'sequence',
                'frame_id',
                'image_payload_sha256',
                'compressed_image_bytes',
                'format',
            )

            need(
                all(
                    decoded[k] == entry[k]
                    for k in required
                ),
                'RECORDED_HEADER_OR_JPEG'
            )

            cursor = ros.Cursor(body)
            header = ros.header(cursor)
            fmt = cursor.text(256)
            length = cursor.number()
            jpeg = cursor.take(length).tobytes()
            cursor.done()

            need(
                'jpeg' in fmt.lower()
                and length == entry['compressed_image_bytes']
                and sha(jpeg) == entry['image_payload_sha256'],
                'JPEG_HASH'
            )

            image = cv2.imdecode(
                np.frombuffer(jpeg, dtype=np.uint8),
                cv2.IMREAD_GRAYSCALE
            )

            need(
                image is not None
                and image.ndim == 2
                and image.dtype == np.uint8
                and image.shape == (480, 640),
                'IMAGE_DECODE'
            )

            previous = prior[i]

            need(
                previous['source']['serialized_message_sha256']
                == sha(body)
                and previous['descriptive_signal']['jpeg_payload_sha256']
                == sha(jpeg)
                and previous['descriptive_signal']['width'] == 640
                and previous['descriptive_signal']['height'] == 480,
                'R22_IMAGE_BIND'
            )

            images.append(image)

            records.append({
                'chunk_offset': entry['chunk_offset'],
                'connection_id': entry['connection_id'],
                'bag_record_time_ns':
                    entry['bag_record_time_ns'],
                'serialized_message_sha256': sha(body),
                'jpeg_payload_sha256': sha(jpeg),
                'decoded_grayscale_sha256':
                    sha(image.tobytes()),
                'frame_id': header['frame_id'],
                'header_stamp_ns':
                    header['header_stamp_ns'],
                'sequence': header['sequence'],
                'width': 640,
                'height': 480,
            })

    return images, records, index['file_sha256']


def track(image0, image1):
    need(
        isinstance(image0, np.ndarray)
        and isinstance(image1, np.ndarray)
        and image0.shape == image1.shape
        and image0.ndim == 2
        and image0.dtype == image1.dtype == np.uint8,
        'IMAGE_SHAPES'
    )

    corners = cv2.goodFeaturesToTrack(
        image0,
        maxCorners=400,
        qualityLevel=0.01,
        minDistance=8,
        blockSize=7,
        useHarrisDetector=False,
    )

    if corners is None:
        corners = np.empty((0, 1, 2), np.float32)

    initial = int(len(corners))
    measurements = []
    forward_count = 0

    if initial:
        parameters = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(
                cv2.TERM_CRITERIA_EPS
                | cv2.TERM_CRITERIA_COUNT,
                30,
                0.01,
            ),
        )

        p1, st1, _ = cv2.calcOpticalFlowPyrLK(
            image0, image1, corners, None, **parameters
        )

        need(
            p1 is not None and st1 is not None,
            'FORWARD_LK'
        )

        pback, stback, _ = cv2.calcOpticalFlowPyrLK(
            image1, image0, p1, None, **parameters
        )

        need(
            pback is not None and stback is not None,
            'BACKWARD_LK'
        )

        start = corners.reshape(-1, 2).astype(np.float64)
        target = p1.reshape(-1, 2).astype(np.float64)
        back = pback.reshape(-1, 2).astype(np.float64)

        height, width = image0.shape

        for i in range(initial):
            if not (
                st1[i, 0]
                and stback[i, 0]
                and np.isfinite(start[i]).all()
                and np.isfinite(target[i]).all()
                and np.isfinite(back[i]).all()
            ):
                continue

            u, v = target[i]
            forward_count += 1

            if not (0 <= u < width and 0 <= v < height):
                continue

            fb = float(
                np.linalg.norm(back[i] - start[i])
            )

            # Engineering tracking filter only.
            # Not a calibrated sensor-health threshold.
            if fb <= 1.5:
                d = target[i] - start[i]

                measurements.append((
                    float(d[0]),
                    float(d[1]),
                    float(np.linalg.norm(d)),
                    fb,
                ))

    accepted = len(measurements)

    result = {
        'method':
            'GFTT_LK_FORWARD_BACKWARD_PIXEL_ONLY',
        'max_candidate_corners': 400,
        'gftt_quality_level_engineering': 0.01,
        'lk_window': 21,
        'lk_pyramid_max_level': 3,
        'forward_backward_filter_px_engineering': 1.5,
        'initial_corner_count': initial,
        'forward_valid_in_bounds_count': forward_count,
        'forward_backward_consistent_count': accepted,
        'feature_coverage_fraction':
            float(accepted / initial) if initial else 0.0,
        'median_dx_px': None,
        'median_dy_px': None,
        'median_displacement_px': None,
        'p90_displacement_px': None,
        'median_forward_backward_error_px': None,
        'tracks_sufficient_for_descriptive_median':
            accepted > 0,
        'metric_translation_m': None,
        'camera_rotation_radians': None,
        'camera_pose_factor': None,
    }

    if accepted:
        values = np.asarray(
            measurements, dtype=np.float64
        )

        for key, value in (
            ('median_dx_px', np.median(values[:, 0])),
            ('median_dy_px', np.median(values[:, 1])),
            ('median_displacement_px',
             np.median(values[:, 2])),
            ('p90_displacement_px',
             np.percentile(values[:, 2], 90)),
            ('median_forward_backward_error_px',
             np.median(values[:, 3])),
        ):
            result[key] = float(value)

    return result


def guard(report):
    need(
        report.get('schema')
        == 'TRUST_ROBOT_R31_TRAIN_CAMERA_PIXEL_MOTION_V1'
        and report.get('trajectory_id') == 'room_02'
        and report.get('split') == 'train',
        'SCOPE'
    )

    need(
        report.get('frame_count') == 2
        and len(report.get('frames', [])) == 2
        and report.get('pair_count') == 1,
        'FRAME_COUNT'
    )

    need(
        report['frames'][1]['sequence']
        == report['frames'][0]['sequence'] + 1
        and report['frames'][1]['header_stamp_ns']
        > report['frames'][0]['header_stamp_ns'],
        'ORDER'
    )

    need(
        all(report.get(flag) is False for flag in FLAGS)
        and type(report.get('real_pose_factors_generated'))
        is int
        and report['real_pose_factors_generated'] == 0
        and type(report.get('health_labels_generated'))
        is int
        and report['health_labels_generated'] == 0,
        'SCIENCE_GATES'
    )

    diagnostic = report['pixel_motion']

    need(
        diagnostic['metric_translation_m'] is None
        and diagnostic['camera_rotation_radians'] is None
        and diagnostic['camera_pose_factor'] is None,
        'NO_POSE'
    )

    need(
        type(diagnostic['initial_corner_count']) is int
        and type(
            diagnostic['forward_backward_consistent_count']
        ) is int
        and 0 <= diagnostic[
            'forward_backward_consistent_count'
        ] <= diagnostic['initial_corner_count'] <= 400,
        'TRACK_COUNTS'
    )


def run(bag, index_path, samples_path, r22_path, out):
    images, frames, bag_sha = load_frames(
        bag, index_path, samples_path, r22_path
    )

    result = {
        'schema':
            'TRUST_ROBOT_R31_TRAIN_CAMERA_PIXEL_MOTION_V1',
        'trajectory_id': 'room_02',
        'split': 'train',
        'github_baseline':
            'd1c8aa7811619d096865f9b5f23a0ca7e940fa81',
        'bag_sha256': bag_sha,
        'source_report_sha256': {
            'r17': sha(index_path.read_bytes()),
            'r18': sha(samples_path.read_bytes()),
            'r22': sha(r22_path.read_bytes()),
        },
        'frame_count': 2,
        'pair_count': 1,
        'frames': frames,
        'header_gap_ns_observed_not_physically_verified':
            frames[1]['header_stamp_ns']
            - frames[0]['header_stamp_ns'],
        'pixel_motion': track(*images),
        'interpretation':
            'unscaled_2d_image_tracking_candidate_only_not_visual_odometry',
        'real_pose_factors_generated': 0,
        'health_labels_generated': 0,
        **{key: False for key in FLAGS},
    }

    guard(result)

    with out.open('x', encoding='utf-8') as handle:
        json.dump(
            result,
            handle,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write('\n')

    tracking = result['pixel_motion']

    print('R31_CAMERA_AUTHENTIC_FRAMES=2')
    print(
        'R31_CAMERA_GFTT_FEATURES='
        + str(tracking['initial_corner_count'])
    )
    print(
        'R31_CAMERA_FB_CONSISTENT_TRACKS='
        + str(tracking['forward_backward_consistent_count'])
    )
    print(
        'R31_CAMERA_MEDIAN_DISPLACEMENT_PX='
        + str(tracking['median_displacement_px'])
    )
    print('R31_CAMERA_RELATIVE_POSE=NOT_ESTIMATED')


if __name__ == '__main__':
    run(
        *(pathlib.Path(x) for x in sys.argv[1:6])
    )
