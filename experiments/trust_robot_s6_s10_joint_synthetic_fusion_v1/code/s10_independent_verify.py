"""S10 independent artifact, combined JUnit and same-input solver review.

No physical localization, noise calibration or observation claim.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import manufactured_camera_packets
from s6_joint_fusion import canonical, estimate_joint


def need(ok,why):
    if not ok:
        raise AssertionError('S10_INDEPENDENT_FAIL:'+why)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main(a):
    r=load(a.report)
    need(r['schema']=='TRUST_ROBOT_S10_SYNTHETIC_INTEGRATION_REVIEW_V1' and
         r['parent_commit']=='ebe97e3ee3d3c9872b2b5643de5124bb0cfacf43' and
         r['engine_sha256']==sha(a.engine) and r['combined_junit_sha256']==sha(a.xml),'SOURCE_BINDING')
    cases=list(ET.parse(a.xml).getroot().iter('testcase'))
    need(len(cases)==r['regression_total']==219 and
         len({(c.get('classname'),c.get('name')) for c in cases})==219 and
         not any(ch.tag in ('failure','error','skipped') for c in cases for ch in c),'COMPLETE_JUNIT')
    counter=Counter()
    for c in cases:
        classname=(c.get('classname') or '').split('.')
        match=[name for name in r['regression_counts_by_module'] if name in classname]
        need(len(match)==1,'TEST_GROUPING')
        counter[match[0]]+=1
    need(dict(counter)==r['regression_counts_by_module'] and len(counter)==13,'SUITE_GROUPING')
    need(r['legacy_regressions_reexecuted']==104 and
         r['new_regressions_reexecuted']=={'6':23,'7':22,'8':27,'9':43},'PHASE_COUNTS')
    paths={
        's2_report':a.s2_report,'s2_xml':a.s2_xml,
        's6_report':a.s6_report,'s6_validation':a.s6_validation,'s6_xml':a.s6_xml,
        's7_report':a.s7_report,'s7_validation':a.s7_validation,'s7_xml':a.s7_xml,
        's7_failed_xml':a.s7_failed_xml,
        's8_report':a.s8_report,'s8_validation':a.s8_validation,'s8_xml':a.s8_xml,
        's9_report':a.s9_report,'s9_validation':a.s9_validation,'s9_xml':a.s9_xml,
    }
    need(r['original_evidence_sha256']=={key:sha(path) for key,path in paths.items()},'PRIOR_HASHES')
    s2,s6,s7,s8,s9=(load(paths[f's{i}_report']) for i in (2,6,7,8,9))
    need(s2['regression_test_count']==104 and
         s6['test_cases_passed']==23 and s7['unit_tests_passed']==22 and
         s8['unit_tests_passed']==27 and s9['unit_tests_passed']==43,'SOURCE_COUNTERS')
    historical=((2,104),(6,23),(7,22),(8,27),(9,43))
    for phase,num in historical:
        cases_old=list(ET.parse(paths[f's{phase}_xml']).getroot().iter('testcase'))
        need(len(cases_old)==num and not any(ch.tag in ('failure','error','skipped') for case in cases_old for ch in case),'HISTORICAL_JUNIT_'+str(phase))
    failures=list(ET.parse(a.s7_failed_xml).getroot().iter('testcase'))
    need(len(failures)==22 and sum(c.find('failure') is not None for c in failures)==1,'S7_FAILED_EVIDENCE_PRESERVED')
    replay=r['cross_phase_replay']
    fixture,truth=make_fixture('clean')
    packets=manufactured_camera_packets(truth,seed=13)
    records,audit=estimate_joint(fixture,packets)
    fingerprint=hashlib.sha256(canonical(records)).hexdigest()
    s6_clean=[x for x in s6['scenarios'] if x['condition']=='clean' and x['camera_enabled'] is True]
    s9_zero=[x for x in s9['nonlinear_synthetic_scenarios'] if x['camera_shift_m']==0.0]
    need(len(s6_clean)==len(s9_zero)==1 and
         fingerprint==replay['clean_joint_trajectory_sha256']==
         s6_clean[0]['estimated_states_sha256']==
         s7['nonlinear_perturbation']['baseline_states_sha256']==
         s9_zero[0]['estimated_trajectory_sha256'],'CROSS_PHASE_BASELINE')
    ledger=audit['factor_ledger'];ids={x['measurement_id'] for x in ledger}
    consumed=set(audit['consumed_pose_ids']);remaining=set(audit['remaining_pose_ids'])
    need(len(ledger)==len(ids)==9 and audit['camera_factor_count']==2 and
         audit['lidar_factor_count']==7 and audit['same_edge_camera_lidar_count']==2 and
         consumed.isdisjoint(remaining) and consumed|remaining==ids and
         audit['factor_reuse_after_marginalization'] is False,'JOINT_SCHUR_OWNERSHIP')
    need(replay['replay_measured_independent_accuracy'] is False and
         replay['replay_authenticated_recorded_data'] is False and
         r['integration_decision']=='SYNTHETIC_REGRESSION_ONLY_READY_FOR_ARCHIVAL' and
         r['next_work_id']=='S6_S10_GUARDED_GITHUB_CHECKPOINT','SCOPE_AND_NEXT')
    for key in ('independent_physical_pose_accuracy_qualified',
                'cross_modal_noise_independence_empirically_verified',
                'physical_sensor_timestamps_qualified','full_sensor_extrinsics_qualified',
                'real_sensor_factor_execution_authorized','m2dgr_scoring_authorized',
                'health_model_training_authorized','automatic_sensor_suppression_authorized',
                'live_simulator_launch_authorized','git_commit_or_push'):
        need(r[key] is False,'SCIENTIFIC_BOUNDARY:'+key)
    for key in ('new_sensor_acquisitions','scientific_pose_factors','health_labels'):
        need(type(r[key]) is int and r[key]==0,'NO_SCIENTIFIC_COUNTS:'+key)
    v={
        'schema':'TRUST_ROBOT_S10_INDEPENDENT_VALIDATION_V1',
        'engine_sha256':sha(a.engine),'verifier_sha256':sha(__file__),
        'combined_junit_sha256':sha(a.xml),'report_sha256':sha(a.report),
        'total_regression_tests_verified':219,'legacy_regressions_verified':104,
        's6_s9_regressions_verified':{'6':23,'7':22,'8':27,'9':43},
        'cross_phase_replay_recomputed':True,'factor_ledger_verified':True,
        'archived_s7_failure_and_success_both_preserved':True,
        'checkpoint_ready_for_guarded_archival':True,
        'real_sensor_factor_admission':False,
        'm2dgr_scoring_authorized':False,
        'new_sensor_acquisitions':0,'scientific_pose_factors':0,'health_labels':0,
    }
    with Path(a.validation).open('x',encoding='utf-8') as f:
        json.dump(v,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    print('S10_INDEPENDENT_219_TEST_CASES=VERIFIED')
    print('S10_INDEPENDENT_ORIGINAL_JUNIT_CHAIN=VERIFIED')
    print('S10_INDEPENDENT_CLEAN_REPLAY=RECOMPUTED')
    print('S10_INDEPENDENT_SCHUR_OWNERSHIP=VERIFIED')
    print('S10_INDEPENDENT_VALIDATION=PASS')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('engine','xml','s2_report','s2_xml','s6_report','s6_validation','s6_xml',
                 's7_report','s7_validation','s7_xml','s7_failed_xml',
                 's8_report','s8_validation','s8_xml','s9_report','s9_validation',
                 's9_xml','report','validation'):
        p.add_argument('--'+name.replace('_','-'),dest=name,required=True)
    main(p.parse_args())
