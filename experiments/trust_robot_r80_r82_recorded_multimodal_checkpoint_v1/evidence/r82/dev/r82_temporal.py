"""R82: deterministic unsupervised stream-local feature windows.

Exploratory successor to frozen SE3, not a modification of SE3.
No cross-sensor association, clock qualification, labels or pose factors.
"""

import hashlib
import json
import math
import pathlib
import sys

SCHEMA = 'TRUST_ROBOT_R82_STREAM_LOCAL_TEMPORAL_DIAGNOSTIC_V1'
REC_SCHEMA = 'TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_RECORD_V1'

RUN_SHA = 'c8eba6d6798ca66a341adc3a872fe53f0268968d903f211b0142e25a3270ad7e'
SUCCESS_SHA = 'e6d62f4441ede9db4d4f5947234a279b8998f2d6a2c61e5f717770023082c28d'
R81_SHA = '4b21db75053e22cba8eeb276635ed194d260a0c4af725cd50c4cbab63c255510'

WINDOW = 256

STREAMS = {
    '/camera/color/image_raw/compressed': (
        'camera_color_image_raw_compressed.jsonl',
        'camera',
        (
            'gray_mean_intensity_8bit',
            'gray_std_intensity_8bit',
            'gray_mean_abs_neighbor_difference_8bit'
        )
    ),
    '/camera/imu': (
        'camera_imu.jsonl',
        'imu',
        (
            'angular_speed_norm_rad_s',
            'linear_acceleration_norm_m_s2'
        )
    ),
    '/handsfree/imu': (
        'handsfree_imu.jsonl',
        'imu',
        (
            'angular_speed_norm_rad_s',
            'linear_acceleration_norm_m_s2'
        )
    ),
}

FIELDS = {
    'schema', 'trajectory_id', 'split_role',
    'source_stream_id', 'modality',
    'selected_reader_index', 'stream_index',
    'bag_record_time_ns', 'header_stamp_ns',
    'feature_values'
}

class EvidenceError(ValueError):
    pass

def need(condition, why):
    if not condition:
        raise EvidenceError(why)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def canon(obj):
    return (
        json.dumps(
            obj, sort_keys=True,
            separators=(',', ':'),
            allow_nan=False
        ) + '\n'
    ).encode()

class Window:
    def __init__(self, n):
        self.n = 0
        self.mean = [0.0]*n
        self.m2 = [0.0]*n
        self.lo = [math.inf]*n
        self.hi = [-math.inf]*n

        self.header_observed = 0
        self.header_positive_intervals = 0
        self.header_zero_intervals = 0
        self.header_backwards_intervals = 0
        self.last_header = None

    def push(self, features, header):
        self.n += 1

        for i, x in enumerate(features):
            delta = x-self.mean[i]
            self.mean[i] += delta/self.n
            self.m2[i] += delta*(x-self.mean[i])
            self.lo[i] = min(x, self.lo[i])
            self.hi[i] = max(x, self.hi[i])

        if header is not None:
            self.header_observed += 1

            if self.last_header is not None:
                delta = header-self.last_header

                if delta > 0:
                    self.header_positive_intervals += 1
                elif delta == 0:
                    self.header_zero_intervals += 1
                else:
                    self.header_backwards_intervals += 1

            self.last_header = header
        else:
            self.last_header = None

    def row(self, trajectory, stream, index):
        need(self.n > 0, 'EMPTY_WINDOW')

        v = {
            'schema': SCHEMA,
            'trajectory_id': trajectory,
            'source_stream_id': stream,
            'window_index': index,
            'record_count': self.n,
            'feature_mean': self.mean,
            'feature_population_std': [
                math.sqrt(max(0.0, x/self.n))
                for x in self.m2
            ],
            'feature_min': self.lo,
            'feature_max': self.hi,
            'header_stamp_observed_count': self.header_observed,
            'within_window_positive_header_deltas':
                self.header_positive_intervals,
            'within_window_zero_header_deltas':
                self.header_zero_intervals,
            'within_window_backwards_header_deltas':
                self.header_backwards_intervals,
            'relative_window_scope':
                'same_stream_record_index_only',
            'cross_modal_clock_alignment': False,
            'health_label': None,
            'health_probability': None,
            'factor_executable': False,
        }

        need(
            all(
                math.isfinite(x)
                for col in (
                    'feature_mean',
                    'feature_population_std',
                    'feature_min',
                    'feature_max'
                )
                for x in v[col]
            ),
            'NONFINITE_WINDOW'
        )

        return v

def validate(r, trajectory, stream, index, previous_selected):
    need(
        type(r) is dict and set(r) == FIELDS,
        'FEATURE_RECORD_FIELDS'
    )

    name, modality, feature_names = STREAMS[stream]

    need(
        r['schema'] == REC_SCHEMA
        and r['split_role'] == 'train'
        and r['trajectory_id'] == trajectory,
        'FEATURE_SCOPE'
    )

    need(
        r['source_stream_id'] == stream
        and r['modality'] == modality,
        'FEATURE_STREAM'
    )

    need(
        type(r['stream_index']) is int
        and r['stream_index'] == index,
        'FEATURE_INDEX'
    )

    sel = r['selected_reader_index']

    need(
        type(sel) is int and sel >= 0
        and (
            previous_selected is None
            or sel > previous_selected
        ),
        'SELECTED_READER_INDEX'
    )

    bag = r['bag_record_time_ns']
    header = r['header_stamp_ns']

    need(
        type(bag) is int and bag >= 0,
        'BAG_RECORD_STAMP'
    )

    need(
        header is None or (
            type(header) is int and header >= 0
        ),
        'HEADER_STAMP'
    )

    values = r['feature_values']

    need(
        type(values) is list
        and len(values) == len(feature_names),
        'FEATURE_VECTOR_LENGTH'
    )

    need(
        all(
            type(x) in (int, float)
            and math.isfinite(x)
            for x in values
        ),
        'FEATURE_NONFINITE'
    )

    return [float(x) for x in values], header, sel

def process(source, dest, trajectory, stream,
            expected_count, expected_sha):

    need(stream in STREAMS, 'UNSUPPORTED_STREAM')
    need(
        type(expected_count) is int
        and expected_count > 0,
        'EXPECTED_COUNT'
    )
    need(
        source.is_file() and not source.is_symlink(),
        'SOURCE_FILE'
    )
    need(
        not dest.exists() and not dest.is_symlink(),
        'OUTPUT_FILE_EXISTS'
    )

    fname, modality, feature_names = STREAMS[stream]

    h = hashlib.sha256()
    output_digest = hashlib.sha256()

    count = 0
    window_no = 0
    previous_selected = None
    w = Window(len(feature_names))

    with source.open('rb') as inp, dest.open('xb') as out:
        for raw in inp:
            need(
                raw.endswith(b'\n')
                and bool(raw.strip()),
                'SOURCE_LINE'
            )

            h.update(raw)
            r = json.loads(raw)

            values, header, sel = validate(
                r, trajectory, stream,
                count, previous_selected
            )

            previous_selected = sel
            w.push(values, header)
            count += 1

            need(
                count <= expected_count,
                'TOO_MANY_RECORDS'
            )

            if w.n == WINDOW:
                blob = canon(
                    w.row(trajectory, stream, window_no)
                )
                out.write(blob)
                output_digest.update(blob)

                window_no += 1
                w = Window(len(feature_names))

        if w.n:
            blob = canon(
                w.row(trajectory, stream, window_no)
            )
            out.write(blob)
            output_digest.update(blob)
            window_no += 1

    need(count == expected_count, 'RECORD_COUNT')
    need(h.hexdigest() == expected_sha, 'SOURCE_SHA')

    need(
        window_no == (count+WINDOW-1)//WINDOW,
        'WINDOW_COUNT'
    )

    need(
        sha(dest) == output_digest.hexdigest(),
        'WINDOW_SHA'
    )

    return {
        'source_stream_id': stream,
        'availability': 'observed_present',
        'source_record_count': count,
        'derived_window_count': window_no,
        'source_feature_file_sha256': expected_sha,
        'window_file_sha256': output_digest.hexdigest(),
        'window_file_relative_path': str(
            pathlib.PurePosixPath('windows')
            / trajectory
            / (fname+'.windows.jsonl')
        ),
        'feature_names': list(feature_names),
    }

def execute(src, r81_path, out):
    need(
        src.is_dir() and not src.is_symlink(),
        'SE3_DIR'
    )

    run_file = src/'run_manifest.json'

    need(
        run_file.is_file()
        and not run_file.is_symlink()
        and sha(run_file) == RUN_SHA,
        'SE3_RUN_SHA'
    )

    need(
        sha(src/'SUCCESS.json') == SUCCESS_SHA,
        'SE3_SUCCESS_SHA'
    )

    need(
        sha(r81_path) == R81_SHA,
        'R81_SOURCE_SHA'
    )

    run = json.loads(run_file.read_bytes())
    r81 = json.loads(r81_path.read_bytes())

    need(
        run['schema'] ==
        'TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_RUN_V1',
        'SE3_RUN_SCHEMA'
    )

    need(
        run['train_trajectory_count'] == 22
        and run['total_feature_records'] == 2816957,
        'SE3_COUNTS'
    )

    need(
        run['total_camera_feature_records'] == 107675
        and run['total_imu_feature_records'] == 2709282,
        'SE3_MODALITY_COUNTS'
    )

    need(
        r81['status'] == 'PASS'
        and r81['trajectory_count'] == 22
        and r81['increment_count'] == 90992,
        'R81_COUNTS'
    )

    train = [
        x['trajectory']
        for x in r81['trajectory_results']
    ]

    tr = run['trajectory_records']

    need(
        type(tr) is list and len(tr) == 22,
        'SE3_TRAJECTORIES'
    )

    need(
        [x['trajectory_id'] for x in tr] == train,
        'CROSS_STAGE_TRAIN_SCOPE'
    )

    records = []
    total = 0
    windows = 0
    files = 0

    for traj_info, lidar_info in zip(
        tr, r81['trajectory_results']
    ):
        trajectory = traj_info['trajectory_id']
        p = src/'trajectories'/(trajectory+'.json')

        need(
            p.is_file() and not p.is_symlink(),
            'SOURCE_TRAJECTORY_FILE'
        )

        need(
            sha(p) == traj_info['trajectory_file_sha256'],
            'SOURCE_TRAJECTORY_SHA'
        )

        summary = json.loads(p.read_bytes())

        need(
            summary['schema'] ==
            'TRUST_ROBOT_SE3_MULTIMODAL_FEATURE_TRAJECTORY_V1'
            and summary['trajectory_id'] == trajectory
            and summary['split_role'] == 'train',
            'TRAJECTORY_SCOPE'
        )

        for k in (
            'reference_data_used',
            'confirmation_data_used',
            'cross_modal_alignment_performed',
            'health_labels_assigned',
            'model_training_performed',
            'ate_rpe_computed'
        ):
            need(
                summary['scientific_boundary'].get(k) is False,
                'TRAJECTORY_SCIENCE:'+k
            )

        per = {}

        for stream, (
            filename, modality, feature_names
        ) in STREAMS.items():

            s = summary['streams'][stream]
            num = s['feature_record_count']

            need(
                type(num) is int and num >= 0,
                'STREAM_COUNT'
            )

            need(
                s['feature_names'] == list(feature_names)
                and s['source_stream_id'] == stream,
                'STREAM_CONTRACT'
            )

            if num == 0:
                need(
                    s['availability'] == 'observed_absent'
                    and s['feature_file_relative_path'] is None
                    and s['feature_file_sha256'] is None,
                    'ABSENT_STREAM'
                )

                per[stream] = {
                    'source_stream_id': stream,
                    'availability': 'observed_absent',
                    'source_record_count': 0,
                    'derived_window_count': 0,
                    'window_file_relative_path': None,
                    'window_file_sha256': None,
                }
                continue

            need(
                s['availability'] == 'observed_present',
                'PRESENT_STREAM'
            )

            rel = (
                pathlib.PurePosixPath('features')
                / trajectory
                / filename
            )

            need(
                s['feature_file_relative_path'] == str(rel),
                'FEATURE_SOURCE_PATH'
            )

            p_feature = src/str(rel)
            folder = out/'windows'/trajectory

            folder.mkdir(
                parents=True, exist_ok=True
            )

            target = folder/(filename+'.windows.jsonl')

            result = process(
                p_feature, target, trajectory,
                stream, num, s['feature_file_sha256']
            )

            per[stream] = result
            files += 1
            windows += result['derived_window_count']
            total += num

        need(
            sum(
                s['source_record_count']
                for s in per.values()
            ) == summary['selected_feature_record_count'],
            'TRAJECTORY_FEATURE_COUNT'
        )

        records.append({
            'trajectory': trajectory,
            'lidar_source_increment_count':
                lidar_info['increments'],
            'camera_imu_streams': per,
            'shared_clock_domain_verified': False,
            'lidar_to_imu_factor_admitted': False,
        })

        print(
            'R82_TRAIN_WINDOW_PASS='
            + trajectory
            + ' records='
            + str(summary['selected_feature_record_count']),
            flush=True
        )

    need(
        total == 2816957 and files == 62,
        'FINAL_RECORD_COUNTS'
    )

    need(
        sum(
            x['lidar_source_increment_count']
            for x in records
        ) == 90992,
        'LIDAR_LINEAGE'
    )

    need(
        all(
            records[i]['trajectory'] == train[i]
            for i in range(22)
        ),
        'TRAIN_ORDER'
    )

    return {
        'schema': SCHEMA,
        'status': 'PASS',
        'source_SE3_run_sha256': RUN_SHA,
        'source_R81_result_sha256': R81_SHA,
        'window_size_source_records': WINDOW,
        'trajectory_count': 22,
        'source_feature_records': total,
        'source_feature_files': files,
        'derived_window_count': windows,
        'trajectory_summaries': records,
        'new_raw_sensor_processing': False,
        'SE3_feature_extraction_rerun': False,
        'per_record_feature_or_timestamp_exported': False,
        'stream_local_temporal_aggregation_only': True,
        'physical_clock_or_cross_modal_sync_assumed': False,
        'health_label_or_probability_emitted': False,
        'real_factors_authorized': False,
        'ate_rpe_computed': False,
        'reference_or_confirmation_accessed': False,
        'scientific_gates_closed': 11,
    }

if __name__ == '__main__':
    src, r81, out = map(pathlib.Path, sys.argv[1:])

    result = execute(src, r81, out)

    p = out/'r82_temporal_window_manifest_v1.json'

    with p.open('xb') as f:
        f.write(
            json.dumps(
                result, sort_keys=True,
                indent=2, allow_nan=False
            ).encode() + b'\n'
        )

    print('R82_FULL_SE3_STREAM_LOCAL_DIAGNOSTICS=PASS')
