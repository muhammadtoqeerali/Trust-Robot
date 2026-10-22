"""R104: explicit single-fixture synthetic S6 factor-graph admission.

All modalities derive from one analytic fixture. Synthetic camera packets
are manufactured from hidden generator truth, never estimator input.
This graph is an input/provenance witness around the unchanged S6 solver,
not a new estimator or a physical calibration/synchronization claim.
"""
import hashlib
import inspect
import json
import math
import numpy as np

import s6_joint_fusion as s6
from trust_robot.analytic_inertial_15d import DT, make_fixture
from trust_robot.analytic_preintegrated_fusion import NODE_FRAMES, make_factors
from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_ORIGIN, ANALYTIC_FRAME, CAMERA_SOURCE, LIDAR_SOURCE,
)

SCHEMA='TRUST_ROBOT_R104_SHARED_SYNTHETIC_FACTOR_GRAPH_V1'
IMU_SOURCE='analytic_s6_preintegrated_imu_v1'  # local ledger label, not physical metadata
NODE_TIME_NS=tuple(int(round(i*DT*1e9)) for i in NODE_FRAMES)
SAMPLE_TIME_NS=tuple(int(round(i*DT*1e9)) for i in range(9))
IMU_OWNER={(i,i+1):(2*i,2*i+1) for i in range(4)}
CASES=(('clean',True,13),('lidar_dropout',True,13),('clean',False,13))
FIELDS=frozenset((
    'schema','condition','camera_enabled','seed','fixture','camera_packets',
    'imu_factors','pose_factors','node_times_ns','sample_times_ns','imu_owner',
    'origin','frame_id','source_imu','fixture_digest',
    'physical_clock_verified','physical_extrinsics_verified',
    'real_sensor_factors_authorized','confirmation_test_accessed',
))

class GraphAdmissionError(ValueError):
    pass

def need(flag,reason):
    if not flag:
        raise GraphAdmissionError(reason)

def canonical(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def fixture_bytes(fixture):
    need(type(fixture) is dict and set(fixture)=={'scans','imu','available'},'FIXTURE_FIELDS')
    scans=fixture['scans']; imu=fixture['imu']; available=fixture['available']
    need(type(scans) is list and len(scans)==9 and type(imu) is list and len(imu)==8,
         'FIXTURE_LENGTH')
    need(type(available) is list and len(available)==9 and all(type(x) is bool for x in available),
         'AVAILABILITY_SCHEMA')
    encoded=[]
    for scan in scans:
        need(type(scan) is np.ndarray and scan.ndim==2 and scan.shape[1]==3 and
             np.isfinite(scan).all(),'SCAN_ARRAY')
        encoded.append(scan.tolist())
    return canonical({'scans':encoded,'imu':imu,'available':available})

def build(condition='clean',camera_enabled=True,seed=13):
    need(condition in ('clean','lidar_dropout'),'CONDITION')
    need(type(camera_enabled) is bool,'CAMERA_MODE')
    need(type(seed) is int and 0<=seed<=100000,'SEED')
    fixture, generator_truth=make_fixture(condition)
    packets=manufactured_camera_packets(generator_truth,seed=seed) if camera_enabled else ()
    # The generator truth is not stored, and never passed to the S6 estimator.
    imu,lidar,_=make_factors(fixture)
    pose=s6.assemble_joint(lidar,packets)
    graph={
        'schema':SCHEMA,'condition':condition,'camera_enabled':camera_enabled,'seed':seed,
        'fixture':fixture,'camera_packets':tuple(packets),'imu_factors':imu,
        'pose_factors':pose,'node_times_ns':NODE_TIME_NS,'sample_times_ns':SAMPLE_TIME_NS,
        'imu_owner':dict(IMU_OWNER),'origin':ANALYTIC_ORIGIN,'frame_id':ANALYTIC_FRAME,
        'source_imu':IMU_SOURCE,'fixture_digest':hashlib.sha256(fixture_bytes(fixture)).hexdigest(),
        'physical_clock_verified':False,'physical_extrinsics_verified':False,
        'real_sensor_factors_authorized':False,'confirmation_test_accessed':False,
    }
    validate(graph)
    return graph

def validate(g):
    need(type(g) is dict and set(g)==FIELDS,'GRAPH_FIELDS')
    need(g['schema']==SCHEMA,'GRAPH_SCHEMA')
    need(g['condition'] in ('clean','lidar_dropout') and type(g['camera_enabled']) is bool
         and type(g['seed']) is int and 0<=g['seed']<=100000,'GRAPH_SCENARIO')
    need(g['origin']==ANALYTIC_ORIGIN and g['frame_id']==ANALYTIC_FRAME
         and g['source_imu']==IMU_SOURCE,'SOURCE_OR_FRAME')
    for field in ('physical_clock_verified','physical_extrinsics_verified',
                  'real_sensor_factors_authorized','confirmation_test_accessed'):
        need(g[field] is False,'SCIENCE_BOUNDARY:'+field)
    need(type(g['node_times_ns']) is tuple and g['node_times_ns']==NODE_TIME_NS,
         'NODE_CHRONOLOGY')
    need(type(g['sample_times_ns']) is tuple and g['sample_times_ns']==SAMPLE_TIME_NS,
         'SAMPLE_CHRONOLOGY')
    need(type(g['imu_owner']) is dict and g['imu_owner']==IMU_OWNER,'IMU_SAMPLE_OWNERSHIP')
    samples=[j for edge in sorted(g['imu_owner']) for j in g['imu_owner'][edge]]
    need(samples==list(range(8)) and len(set(samples))==8,'IMU_SAMPLE_EXACTLY_ONCE')
    f=g['fixture']
    need(hashlib.sha256(fixture_bytes(f)).hexdigest()==g['fixture_digest'],
         'FIXTURE_TAMPERING')
    # Reproduce the declared fixture from the fixed analytic generator.
    # This is synthetic test validation, never estimator truth input.
    ref_fixture, ref_truth=make_fixture(g['condition'])
    need(hashlib.sha256(fixture_bytes(ref_fixture)).hexdigest()==g['fixture_digest'],
         'NOT_SINGLE_GENERATOR_FIXTURE')
    expected_camera=(manufactured_camera_packets(ref_truth,seed=g['seed'])
                     if g['camera_enabled'] else ())
    need(len(expected_camera)==len(g['camera_packets']),'CAMERA_GENERATOR_COUNT')
    for packet, expected in zip(g['camera_packets'],expected_camera):
        need(type(packet) is type(expected) and
             packet.modality==expected.modality and
             packet.edge==expected.edge and
             packet.measurement_id==expected.measurement_id and
             packet.source_id==expected.source_id and
             packet.frame_id==expected.frame_id and
             packet.origin==expected.origin and
             packet.measurement.translation_m==expected.measurement.translation_m and
             packet.measurement.quaternion_wxyz==expected.measurement.quaternion_wxyz,
             'CAMERA_SINGLE_GENERATOR_ORIGIN')
    for i,reading in enumerate(f['imu']):
        need(type(reading) is dict and set(reading)=={
            'interval_index','dt_s','gyro_rad_s','specific_force_m_s2',
            'physical_clock_verified','measurement_origin'},'IMU_PACKET_FIELDS')
        need(type(reading['interval_index']) is int and reading['interval_index']==i,
             'IMU_INDEX')
        need(type(reading['dt_s']) in (float,int) and math.isclose(
            reading['dt_s'],DT,rel_tol=0,abs_tol=1e-12),'SAMPLE_DURATION')
        need(reading['physical_clock_verified'] is False and
             reading['measurement_origin']==ANALYTIC_ORIGIN,'IMU_SOURCE_DENIED')
        for key in ('gyro_rad_s','specific_force_m_s2'):
            v=reading[key]
            need(type(v) is list and len(v)==3 and all(type(x) in (int,float)
                 and math.isfinite(x) for x in v),'SIGNED_IMU_SAMPLE')
    need(type(g['camera_packets']) is tuple and
         len(g['camera_packets'])==(2 if g['camera_enabled'] else 0),'CAMERA_COUNT')
    need(type(g['imu_factors']) is dict and set(g['imu_factors'])==set(IMU_OWNER),
         'INERTIAL_CHAIN')
    for edge,(pre,L) in g['imu_factors'].items():
        need(type(edge) is tuple and edge in IMU_OWNER,'EDGE_OWNER')
        need(pre['samples']==2 and math.isclose(float(pre['total_dt']),0.2,abs_tol=1e-12),
             'PREINTEGRATION_INTERVAL')
        need(np.shape(L)==(15,15) and np.isfinite(L).all() and
             np.all(np.diag(L)>0),'IMU_WHITENER')
    need(type(g['pose_factors']) is tuple,'POSE_CONTAINER')
    s6.validate_factors(g['pose_factors'])
    expected_imu,expected_lidar,_=make_factors(f)
    expected_pose=s6.assemble_joint(expected_lidar,g['camera_packets'])
    need(set(expected_imu)==set(g['imu_factors']),'REBUILT_IMU_EDGES')
    for edge in expected_imu:
        a=g['imu_factors'][edge]; b=expected_imu[edge]
        need(np.array_equal(np.asarray(a[1]),np.asarray(b[1])),'WHITENER_INTEGRITY')
        for field in ('total_dt','samples'):
            need(a[0][field]==b[0][field],'PREINTEGRATION_METADATA')
        for field in ('delta_p','delta_v','covariance'):
            need(np.array_equal(np.asarray(a[0][field]),np.asarray(b[0][field])),
                 'PREINTEGRATION_CONTENT')
    need(len(expected_pose)==len(g['pose_factors']),'POSE_FACTOR_CARDINALITY')
    seen=set(); ids=set()
    for a,b in zip(g['pose_factors'],expected_pose):
        pa,pb=a.packet,b.packet
        need(type(a) is s6.JointFactor and a.key==b.key and
             pa.edge==pb.edge and pa.modality==pb.modality and
             pa.origin==ANALYTIC_ORIGIN and pa.frame_id==ANALYTIC_FRAME and
             pa.source_id==({'camera':CAMERA_SOURCE,'lidar':LIDAR_SOURCE}[pa.modality]),
             'POSE_PROVENANCE')
        need(np.array_equal(np.asarray(a.covariance),np.asarray(b.covariance)) and
             pa.measurement.translation_m==pb.measurement.translation_m and
             pa.measurement.quaternion_wxyz==pb.measurement.quaternion_wxyz,
             'POSE_MEASUREMENT_INTEGRITY')
        owner=(pa.modality,pa.edge)
        need(owner not in seen and a.key not in ids,'POSE_REUSE')
        seen.add(owner); ids.add(a.key)
        i,j=pa.edge
        need(0<=i<j<len(NODE_FRAMES) and
             g['node_times_ns'][j]>g['node_times_ns'][i],'POSE_EDGE_TIME')
    need(len({f.key for f in g['pose_factors']})==len(g['pose_factors']),
         'POSE_ID_DUPLICATION')
    return True

def summarize(g):
    validate(g)
    if list(inspect.signature(s6.estimate_joint).parameters)!=['fixture','camera_packets']:
        raise GraphAdmissionError('TRUTH_ESTIMATOR_API')
    # Only the single fixture + generated camera packets are passed to solver.
    states,audit=s6.estimate_joint(g['fixture'],g['camera_packets'])
    need(len(states)==5 and audit['accepted_window_count']==4
         and audit['schur_elimination_count']==3,'S6_SOLVER')
    need(audit['real_sensor_factor_admitted'] is False and
         audit['physical_measurements_used'] is False,'REAL_FACTOR_DENIED')
    ids={f.key for f in g['pose_factors']}
    consumed=set(audit['consumed_pose_ids'])
    remaining=set(audit['remaining_pose_ids'])
    need(consumed.isdisjoint(remaining) and consumed|remaining==ids,
         'ESTIMATOR_FACTOR_OWNERSHIP')
    need(audit['unaccounted_factor_count']==0 and
         audit['factor_reuse_after_marginalization'] is False,
         'ESTIMATOR_FACTOR_REUSE')
    ledger=[{
        'measurement_id':factor.key,
        'modality':factor.packet.modality,
        'edge':list(factor.packet.edge),
        'source_id':factor.packet.source_id,
        'frame_id':factor.packet.frame_id,
        'covariance_diagonal':list(np.diag(np.asarray(factor.covariance))),
        'start_ns':g['node_times_ns'][factor.packet.edge[0]],
        'end_ns':g['node_times_ns'][factor.packet.edge[1]],
    } for factor in g['pose_factors']]
    imu_ledger=[{'edge':list(edge),'sample_indices':list(g['imu_owner'][edge]),
                 'start_ns':g['node_times_ns'][edge[0]],
                 'end_ns':g['node_times_ns'][edge[1]],'source_id':IMU_SOURCE}
                for edge in sorted(g['imu_owner'])]
    return {
        'condition':g['condition'],'camera_enabled':g['camera_enabled'],
        'seed':g['seed'] if g['camera_enabled'] else None,
        'node_times_ns':list(g['node_times_ns']),
        'imu_sample_times_ns':list(g['sample_times_ns']),
        'fixture_sha256':g['fixture_digest'],
        'imu_factors':len(g['imu_factors']),
        'pose_factors':len(g['pose_factors']),
        'camera_factors':sum(p['modality']=='camera' for p in ledger),
        'lidar_factors':sum(p['modality']=='lidar' for p in ledger),
        'same_edge_camera_lidar':audit['same_edge_camera_lidar_count'],
        'nonlinear_windows':4,'marginalizations':3,
        'imu_ledger':imu_ledger,'pose_ledger':ledger,
        'pose_factors_consumed':len(consumed),
        'pose_factors_remaining':len(remaining),
        'imu_samples_used_exactly_once':True,
        'truth_passed_to_estimator':False,
        'real_sensor_factors_executed':False,
    }

def execute():
    cases={
        ('clean_joint' if condition=='clean' and camera else
         'clean_camera_off' if not camera else 'lidar_dropout_joint'):
        summarize(build(condition,camera,seed))
        for condition,camera,seed in CASES
    }
    need(len(cases)==3,'SCENARIO_COUNT')
    need(cases['clean_joint']['camera_factors']==2 and
         cases['clean_joint']['same_edge_camera_lidar']==2,'SAME_EDGE_FACTORS')
    need(cases['clean_camera_off']['camera_factors']==0 and
         cases['clean_camera_off']['same_edge_camera_lidar']==0,'CAMERA_ABLATION')
    need(cases['lidar_dropout_joint']['lidar_factors']<
         cases['clean_joint']['lidar_factors'],'LIDAR_DROPOUT')
    return {
        'schema':SCHEMA,'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':cases,'scenario_count':3,'nodes_per_case':5,
        'imu_samples_per_case':8,'imu_edges_per_case':4,
        'total_nonlinear_windows':12,'total_schur_marginalizations':9,
        'single_fixture_per_scenario':True,
        'independent_camera_lidar_factor_ids':True,
        'r95_prior_imported_into_s6':False,
        'new_estimator_backend_implemented':False,
        'physical_sensor_synchronization_verified':False,
        'physical_extrinsics_verified':False,
        'real_sensor_factors_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'original_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys
    with open(sys.argv[1],'x',encoding='utf-8') as f:
        f.write(canonical(execute()).decode())
    print('R104_SHARED_SYNTHETIC_FACTOR_GRAPH=PASS')
    print('R104_NONLINEAR_WINDOWS=12')
    print('R104_IMU_EDGE_OWNERSHIP=PASS')
    print('R104_POSE_FACTOR_OWNERSHIP=PASS')
    print('R104_PHYSICAL_FACTORS=DENIED')
