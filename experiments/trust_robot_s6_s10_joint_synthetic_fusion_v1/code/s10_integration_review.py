"""S10 full synthetic regression and frozen evidence-chain review.

No raw sensor data, physical scoring, simulator, or runtime actions.
A numerical fixture replay is not an independent physical truth test.
"""
import argparse
from collections import Counter
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
from s6_joint_fusion import canonical, estimate_joint

SCHEMA = 'TRUST_ROBOT_S10_SYNTHETIC_INTEGRATION_REVIEW_V1'
LEGACY = (
    'test_analytic_imu_preintegration',
    'test_analytic_preintegrated_fusion',
    'test_analytic_schur_marginalization',
    'test_analytic_marginalized_fusion',
    'test_analytic_factor_support',
    'test_analytic_marginalization_consistency',
    'test_analytic_three_modality_bridge',
    'test_multimodal_factor_interface',
    'test_m2dgr_sensor_admission',
)
NEW = {'test_s6_joint_fusion':23, 'test_s7_factor_support':22,
       'test_s8_correlated_conflict':27, 'test_s9_adversarial':43}


def need(ok, msg):
    if not ok:
        raise ValueError('S10_FAIL_CLOSED:'+msg)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink() and p.stat().st_size < 5000000, 'UNSAFE_INPUT:'+str(p))
    return json.loads(p.read_text(encoding='utf-8'))


def write(path,obj):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')


def classify_xml(path):
    modules=LEGACY+tuple(NEW)
    cases=list(ET.parse(path).getroot().iter('testcase'))
    need(len(cases)==219,'REGRESSION_TOTAL')
    need(len({(c.get('classname'),c.get('name')) for c in cases})==len(cases),'DUPLICATE_TEST_IDS')
    need(all(not any(ch.tag in ('failure','error','skipped') for ch in c) for c in cases),'FAILED_OR_SKIPPED_TEST')
    counts=Counter()
    for case in cases:
        classname=case.get('classname') or ''
        tokens=classname.split('.')
        match=[x for x in modules if x in tokens]
        need(len(match)==1,'UNRECOGNIZED_TEST_MODULE:'+classname)
        counts[match[0]]+=1
    need(sum(counts[x] for x in LEGACY)==104 and all(counts[x]>0 for x in LEGACY),'LEGACY_NINE_SUITES')
    need(all(counts[x]==y for x,y in NEW.items()),'S6_S9_REGRESSION_COUNTS')
    return dict(sorted(counts.items()))


def historical_lineage(args):
    items={
        's2_report':args.s2_report, 's2_xml':args.s2_xml,
        's6_report':args.s6_report, 's6_validation':args.s6_validation,
        's6_xml':args.s6_xml,
        's7_report':args.s7_report, 's7_validation':args.s7_validation,
        's7_xml':args.s7_xml, 's7_failed_xml':args.s7_failed_xml,
        's8_report':args.s8_report, 's8_validation':args.s8_validation,
        's8_xml':args.s8_xml,
        's9_report':args.s9_report, 's9_validation':args.s9_validation,
        's9_xml':args.s9_xml,
    }
    data={k:read(path) for k,path in items.items() if k.endswith(('report','validation'))}
    s2,s6,s7,s8,s9=(data[f's{i}_report'] for i in (2,6,7,8,9))
    v6,v7,v8,v9=(data[f's{i}_validation'] for i in (6,7,8,9))
    need(s2['regression_test_count']==104 and s2['regression_counts']['passed']==104 and
         s2['m2dgr_scoring_authorized'] is False,'S2_SCIENCE_GATE')
    for count,report,validation in ((23,s6,v6),(22,s7,v7),(27,s8,v8),(43,s9,v9)):
        need(report['unit_tests_passed' if count!=23 else 'test_cases_passed']==count and
             validation['unit_tests_verified']==count,'S6_S9_HISTORICAL_COUNTS')
    need(s6['scenario_count']==4 and s6['real_sensor_factor_execution_authorized'] is False and
         s7['nonlinear_perturbation']['factor_reuse_after_marginalization'] is False and
         s8['scenario_count']==3 and s8['real_sensor_factor_execution_authorized'] is False and
         s9['total_diagnostic_cases']==15 and s9['runtime_action_denials'] ==
         {'drop_camera':'DENIED','drop_lidar':'DENIED','infer_unusable':'DENIED','weight_camera':'DENIED'} and
         s9['real_sensor_factor_execution_authorized'] is False,'S6_S9_BOUNDARIES')
    need(s9['s8_report_sha256']==sha(args.s8_report) and
         s8['s7_report_sha256']==sha(args.s7_report) and
         s7['s6_report_sha256']==sha(args.s6_report),'PRIOR_CHAIN')
    return {k:sha(path) for k,path in items.items()},data


def cross_phase_replay(data):
    fixture, manufactured_truth=make_fixture('clean')
    camera_packets=manufactured_camera_packets(manufactured_truth,seed=13)
    records,audit=estimate_joint(fixture,camera_packets)
    actual=hashlib.sha256(canonical(records)).hexdigest()
    s6=data['s6_report'];s7=data['s7_report'];s9=data['s9_report']
    matched=[row for row in s6['scenarios'] if row['condition']=='clean' and row['camera_enabled'] is True]
    zero=[row for row in s9['nonlinear_synthetic_scenarios'] if row['camera_shift_m']==0.0]
    need(len(matched)==len(zero)==1,'REPLAY_BASELINES')
    need(actual==matched[0]['estimated_states_sha256']==
         s7['nonlinear_perturbation']['baseline_states_sha256']==
         zero[0]['estimated_trajectory_sha256'],'CROSS_PHASE_REPLAY_HASH')
    ledger=audit['factor_ledger']
    ids={row['measurement_id'] for row in ledger}
    consumed=set(audit['consumed_pose_ids'])
    remaining=set(audit['remaining_pose_ids'])
    need(len(records)==5 and len(ledger)==len(ids)==9 and
         audit['camera_factor_count']==2 and audit['lidar_factor_count']==7 and
         audit['same_edge_camera_lidar_count']==2 and audit['accepted_window_count']==4 and
         audit['schur_elimination_count']==3 and
         consumed.isdisjoint(remaining) and consumed | remaining==ids and
         audit['factor_reuse_after_marginalization'] is False and
         audit['real_sensor_factor_admitted'] is False,'REPLAY_FACTOR_OWNERSHIP')
    need(all(np.isfinite(row['position_m']).all() for row in records),'NONFINITE_REPLAY')
    return {'clean_joint_trajectory_sha256':actual,
            'matching_phase_artifacts':['S6','S7','S9'],
            'nodes':5,'synthetic_pose_factors':9,
            'same_edge_camera_lidar_pairs':2,
            'schur_eliminations':3,
            'replay_measured_independent_accuracy':False,
            'replay_authenticated_recorded_data':False}


def main(args):
    counts=classify_xml(args.xml)
    hashes,data=historical_lineage(args)
    replay=cross_phase_replay(data)
    result={
        'schema':SCHEMA,
        'parent_commit':'ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43',
        'engine_sha256':sha(__file__),
        'combined_junit_sha256':sha(args.xml),
        'original_evidence_sha256':hashes,
        'regression_counts_by_module':counts,
        'regression_total':sum(counts.values()),
        'legacy_regressions_reexecuted':sum(counts[x] for x in LEGACY),
        'new_regressions_reexecuted':{str(i):counts[f'test_s{i}_'+
              {6:'joint_fusion',7:'factor_support',8:'correlated_conflict',9:'adversarial'}[i]] for i in (6,7,8,9)},
        'cross_phase_replay':replay,
        'archived_s7_failed_junit_preserved':True,
        'next_work_id':'S6_S10_GUARDED_GITHUB_CHECKPOINT',
        'integration_decision':'SYNTHETIC_REGRESSION_ONLY_READY_FOR_ARCHIVAL',
        'independent_physical_pose_accuracy_qualified':False,
        'cross_modal_noise_independence_empirically_verified':False,
        'physical_sensor_timestamps_qualified':False,
        'full_sensor_extrinsics_qualified':False,
        'real_sensor_factor_execution_authorized':False,
        'm2dgr_scoring_authorized':False,
        'health_model_training_authorized':False,
        'automatic_sensor_suppression_authorized':False,
        'live_simulator_launch_authorized':False,
        'new_sensor_acquisitions':0,'scientific_pose_factors':0,'health_labels':0,
        'git_commit_or_push':False,
    }
    write(args.report,result)
    print('S10_COMBINED_REGRESSION_TESTS=219_PASSED')
    print('S10_LEGACY_ESTIMATOR_SUITES=9_104_PASSED')
    print('S10_S6_S9_TESTS=23_22_27_43_PASSED')
    print('S10_CLEAN_JOINT_REPLAY=S6_S7_S9_HASH_MATCH')
    print('S10_FACTOR_OWNERSHIP_AND_SCHUR=VERIFIED')
    print('S10_RESEARCH_CHECKPOINT_REVIEW=PASS')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('xml','s2_report','s2_xml','s6_report','s6_validation','s6_xml',
                 's7_report','s7_validation','s7_xml','s7_failed_xml',
                 's8_report','s8_validation','s8_xml','s9_report','s9_validation',
                 's9_xml','report'):
        p.add_argument('--'+name.replace('_','-'),dest=name,required=True)
    main(p.parse_args())
