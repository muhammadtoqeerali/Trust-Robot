"""R81 frozen M2DGR TRAIN odometry increment adapter.

Verifies source bytes and SE(3) pose-composition consistency.
Never emits real factors, GT scores, health labels or original poses.
"""

from __future__ import annotations
import dataclasses
import hashlib
import json
import math
import pathlib
import stat
import sys

SCHEMA='TRUST_ROBOT_R81_FULL_TRAIN_READ_ONLY_INCREMENT_ADAPTER_V1'
RUN_SHA='3fccd2c4a189e6a0dfec1759338794c10e1c23c9714e583ca338d98752a25f71'
FREEZE_SHA='4f1daa871be72714bd257e22b43e551259d989c391230edfaac3c95f579d9da0'
SOURCE_ID='m2dgr_velodyne_exact_nn_fixed_point_v1'

ORDER=(
    'Circle_01','door_01','gate_01','hall_01','hall_03',
    'hall_04','hall_05','lift_02','lift_04','room_02',
    'room_dark_01','room_dark_02','room_dark_03','room_dark_04',
    'street_01','street_010','street_03','street_04',
    'street_05','street_07','street_09','walk_01'
)

class AdmissionError(ValueError):
    pass

def need(ok, why):
    if not ok:
        raise AdmissionError(why)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def canonical(value):
    return json.dumps(
        value,sort_keys=True,separators=(',',':'),allow_nan=False
    ).encode('utf-8')

def vector(values,n,key):
    need(
        type(values) is list and len(values)==n
        and all(type(v) in (int,float) and math.isfinite(v) for v in values),
        'INVALID_VECTOR:'+key
    )
    return tuple(float(v) for v in values)

def unit_q(values):
    q=vector(values,4,'quaternion')
    n=math.sqrt(sum(x*x for x in q))
    need(n>0 and abs(n-1)<=1e-6,'QUATERNION_NORM')
    return tuple(x/n for x in q)

def qmul(a,b):
    w,x,y,z=a
    u,v,p,r=b
    return (
        w*u-x*v-y*p-z*r,
        w*v+x*u+y*r-z*p,
        w*p-x*r+y*u+z*v,
        w*r+x*p-y*v+z*u
    )

def normalize(q):
    n=math.sqrt(sum(x*x for x in q))
    need(n>0 and math.isfinite(n),'ROTATION_NORM')
    q=tuple(x/n for x in q)
    for x in q:
        if x>0:
            break
        if x<0:
            q=tuple(-v for v in q)
            break
    return q

def rotate(q,v):
    q=normalize(q)
    p=qmul(qmul(q,(0.0,*v)),(q[0],-q[1],-q[2],-q[3]))
    return p[1:]

def pose(value):
    need(type(value) is dict,'POSE_MAPPING')
    return (
        vector(value['translation_m'],3,'translation'),
        unit_q(value['quaternion_wxyz'])
    )

def compose(a,b):
    t,q=a
    u,r=b
    v=rotate(q,u)
    return (
        tuple(t[i]+v[i] for i in range(3)),
        normalize(qmul(q,r))
    )

def error(a,b):
    return max(abs(x-y) for x,y in zip(a,b))

@dataclasses.dataclass(frozen=True)
class DiagnosticIncrement:
    trajectory: str
    scan_index: int
    previous_header_ns: int
    current_header_ns: int
    delta_previous_T_current: tuple
    diagnostics: tuple
    reference_data_used: bool=False
    real_factor_admitted: bool=False

    @classmethod
    def from_record(cls,name,r,index,previous):
        need(r.get('record_type')=='relative_pose','RECORD_TYPE')
        need(r.get('trajectory')==name,'TRAJECTORY')
        need(
            type(r.get('scan_index')) is int
            and r['scan_index']==index,
            'SCAN_INDEX'
        )

        a=r['previous_header_stamp_ns']
        b=r['current_header_stamp_ns']

        need(
            type(a) is int and type(b) is int
            and a==previous and b>a,
            'TIMESTAMP_CHAIN'
        )
        need(
            type(r.get('header_delta_ns')) is int
            and r['header_delta_ns']==b-a,
            'TIMESTAMP_DELTA'
        )

        scope=r['scientific_scope']
        forbidden=(
            'reference_data_used',
            'confirmation_test_data_used',
            'scan_temporal_reference_verified',
            'per_point_time_used',
            'deskew_performed',
            'correspondence_rejection_used',
            'voxel_downsampling_used',
            'ate_computed',
            'rpe_computed',
            'trajectory_scoring_performed'
        )
        for key in forbidden:
            need(scope.get(key) is False,'SCIENCE:'+key)

        d=r['diagnostics']

        for key in (
            'source_point_count',
            'target_point_count',
            'fixed_point_iterations',
            'final_correspondence_count'
        ):
            need(
                type(d.get(key)) is int and d[key]>=1,
                'DIAGNOSTIC:'+key
            )

        rmse=d.get('final_nearest_neighbor_rmse_m')

        need(
            type(rmse) in (float,int)
            and math.isfinite(rmse) and rmse>=0,
            'DIAGNOSTIC_RMSE'
        )

        need(
            d.get('correspondence_rejection_used') is False
            and d.get('voxel_downsampling_used') is False,
            'ALTERED_FRONTEND'
        )

        features=(
            d['source_point_count'],
            d['target_point_count'],
            d['fixed_point_iterations'],
            d['final_correspondence_count'],
            float(rmse)
        )

        return cls(
            name,index,a,b,
            pose(r['delta_prev_lidar_T_current_lidar']),
            features
        )

def validate_stream(stream,name,expected):
    need(name in ORDER,'NOT_TRAIN')

    digest=hashlib.sha256()
    count=0
    state=None
    previous=None
    finished=False
    max_translation=0.0
    max_rotation=0.0

    for lineno,raw in enumerate(stream,1):
        need(
            raw.endswith(b'\n') and bool(raw.strip()),
            'BAD_LINE'
        )
        rec=json.loads(raw)
        need(type(rec) is dict,'BAD_RECORD')
        kind=rec.get('record_type')

        if lineno==1:
            need(
                kind=='trajectory_header'
                and rec.get('trajectory')==name,
                'HEADER'
            )
            need(
                rec.get('bag_relative_path')==
                f'raw/rosbags/{name}.bag',
                'BAG_ID'
            )
            need(
                rec.get('body_frame_id')=='velodyne'
                and rec.get('world_frame_id')==
                    'phase2_lidar_first_scan_origin',
                'FRAME'
            )
            need(
                rec.get('relative_pose_source_id')==SOURCE_ID,
                'SOURCE_ID'
            )
            need(
                rec.get('reference_data_used') is False
                and rec.get('confirmation_test_data_used') is False,
                'HEADER_SCIENCE'
            )

            previous=rec['initial_timestamp_ns']
            need(type(previous) is int,'INITIAL_TIMESTAMP')

            state=pose(rec['initial_pose_world_T_body'])

            need(
                error(state[0],(0.,0.,0.))==0
                and error(state[1],(1.,0.,0.,0.))==0,
                'INITIAL_POSE'
            )
            continue

        need(state is not None and not finished,'RECORD_ORDER')

        if kind=='relative_pose':
            inc=DiagnosticIncrement.from_record(
                name,rec,count+1,previous
            )

            state=compose(state,inc.delta_previous_T_current)
            observed=pose(rec['state_world_T_lidar'])

            et=error(state[0],observed[0])
            eq=error(state[1],observed[1])

            need(
                et<=1e-6 and eq<=1e-6,
                'POSE_COMPOSITION_MISMATCH'
            )

            max_translation=max(max_translation,et)
            max_rotation=max(max_rotation,eq)

            packet={
                'trajectory':name,
                'scan_index':inc.scan_index,
                'previous_header_ns':inc.previous_header_ns,
                'current_header_ns':inc.current_header_ns,
                'delta':rec['delta_prev_lidar_T_current_lidar'],
                'diagnostics':inc.diagnostics,
                'real_factor_admitted':False
            }

            digest.update(
                hashlib.sha256(canonical(packet)).digest()
            )

            count+=1
            previous=inc.current_header_ns

            need(count<=expected,'TOO_MANY_INCREMENTS')

        elif kind=='trajectory_complete':
            need(count==expected,'INCREMENT_COUNT')
            need(rec.get('trajectory')==name,'COMPLETION_NAME')
            need(
                rec.get('increment_count')==count
                and rec.get('scan_count')==count+1,
                'COMPLETION_COUNT'
            )
            need(
                rec.get('final_timestamp_ns')==previous,
                'COMPLETION_TIMESTAMP'
            )
            need(
                rec.get('reference_data_used') is False
                and rec.get('confirmation_test_data_used') is False
                and rec.get('trajectory_scoring_performed') is False,
                'COMPLETION_SCIENCE'
            )

            final=pose(rec['final_state_world_T_lidar'])

            need(
                error(state[0],final[0])<=1e-6
                and error(state[1],final[1])<=1e-6,
                'COMPLETION_POSE'
            )
            finished=True

        else:
            raise AdmissionError('UNKNOWN_RECORD_TYPE')

    need(finished and count==expected,'INCOMPLETE_TRAJECTORY')

    return {
        'trajectory':name,
        'increments':count,
        'scans':count+1,
        'max_translation_replay_error_m':max_translation,
        'max_rotation_replay_error':max_rotation,
        'typed_increment_stream_sha256':digest.hexdigest()
    }

def execute(source,freeze_path):
    source=pathlib.Path(source)
    freeze_path=pathlib.Path(freeze_path)

    need(source.is_dir() and not source.is_symlink(),'SOURCE_DIR')
    root=source/'trajectories'
    need(root.is_dir() and not root.is_symlink(),'TRAJECTORY_DIR')

    manifest=source/'run_manifest.json'
    need(
        manifest.is_file() and not manifest.is_symlink()
        and sha(manifest)==RUN_SHA,
        'RUN_MANIFEST_SHA'
    )

    need(
        freeze_path.is_file() and not freeze_path.is_symlink()
        and sha(freeze_path)==FREEZE_SHA,
        'FROZEN_MANIFEST_SHA'
    )

    freeze=json.loads(freeze_path.read_bytes())
    ev=freeze['execution_evidence']

    need(
        ev['run_manifest_file_sha256']==RUN_SHA,
        'FROZEN_RUN_BINDING'
    )
    need(ev['trajectory_order']==list(ORDER),'FROZEN_ORDER')
    need(
        ev['trajectory_count']==22
        and ev['total_increment_count']==90992
        and ev['total_scan_count']==91014,
        'FROZEN_COUNTS'
    )

    pins=ev['trajectory_jsonl_sha256']
    need(set(pins)==set(ORDER),'FROZEN_PINS')

    summary_path=source/'summary.json'

    need(
        summary_path.is_file() and not summary_path.is_symlink()
        and sha(summary_path)==ev['summary_file_sha256'],
        'SOURCE_SUMMARY_SHA'
    )

    summary=json.loads(summary_path.read_bytes())

    need(
        summary['trajectory_count']==22
        and summary['total_increment_count']==90992
        and summary['total_scan_count']==91014,
        'SOURCE_SUMMARY_COUNTS'
    )

    entries=summary['trajectories']
    need(
        type(entries) is list and len(entries)==22,
        'SOURCE_SUMMARY_TRAJECTORIES'
    )

    counts={
        row['trajectory']:row['increment_count']
        for row in entries
    }

    need(
        set(counts)==set(ORDER)
        and sum(counts.values())==90992,
        'SOURCE_SUMMARY_PER_TRAJECTORY_COUNTS'
    )

    run=json.loads(manifest.read_bytes())
    need(
        run.get('schema')==
        'TRUST_ROBOT_PHASE2_CLEAN_LIDAR_TRAIN_RUN_V1',
        'RUN_SCHEMA'
    )
    need(run.get('trajectory_order')==list(ORDER),'RUN_TRAIN')
    need(run.get('trajectory_count')==22,'RUN_COUNT')

    expected_files={f'{name}.jsonl' for name in ORDER}

    need(
        {
            p.name for p in root.iterdir()
            if p.name.endswith('.jsonl')
        }==expected_files,
        'TRAJECTORY_FILE_SET'
    )

    rows=[]

    for name in ORDER:
        path=root/(name+'.jsonl')
        info=path.lstat()

        need(stat.S_ISREG(info.st_mode),'UNSAFE_FILE:'+name)

        expected_sha=pins[name]
        expected_count=counts[name]

        need(
            sha(path)==expected_sha,
            'SOURCE_SHA:'+name
        )

        with path.open('rb') as stream:
            row=validate_stream(
                stream,name,expected_count
            )

        row['source_file_sha256']=expected_sha
        rows.append(row)

        print(
            f'R81_TRAIN_TRAJECTORY_PASS={name} '
            f'increments={expected_count}',
            flush=True
        )

    need(
        sum(row['increments'] for row in rows)==90992,
        'TOTAL_INCREMENTS'
    )
    need(
        sum(row['scans'] for row in rows)==91014,
        'TOTAL_SCANS'
    )

    return {
        'schema':SCHEMA,
        'status':'PASS',
        'frozen_source_manifest_sha256':RUN_SHA,
        'trajectory_count':22,
        'increment_count':90992,
        'scan_count':91014,
        'read_only_typed_adapter':True,
        'trajectory_results':rows,
        'full_train_recorded_registration_rerun':False,
        'per_record_pose_or_timestamp_exported':False,
        'raw_rosbags_or_gt_opened':False,
        'confirmation_test_accessed':False,
        'cross_sensor_synchronization_verified':False,
        'real_pose_factors_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'scientific_gates_closed':11
    }

def main():
    source,freeze,out=map(pathlib.Path,sys.argv[1:])
    report=execute(source,freeze)
    path=out/'r81_full_train_increment_adapter_v1.json'

    with path.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')

    print('R81_FULL_FROZEN_TRAIN_REPLAY=PASS')

if __name__=='__main__':
    main()
