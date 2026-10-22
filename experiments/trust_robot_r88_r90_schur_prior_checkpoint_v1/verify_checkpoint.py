"""R91 stand-alone byte integrity, lineage, semantic and science verifier."""

import hashlib,json,pathlib,stat,sys

SCHEMA='TRUST_ROBOT_R88_R90_SCHUR_PRIOR_CHECKPOINT_V1'
BASE='c147ccaba711b8a600294b2df2b8f64f6ef6bcd4'
PHASES=('r88','r89','r90')

NAMES={
 'r88':('r88_schur.py','test_r88.py','r88_synthetic_schur_fixed_lag_v1.json','r88_independent_validation_v1.json'),
 'r89':('r89_prior.py','test_r89.py','r89_prior_relinearization_consistency_v1.json','r89_independent_validation_v1.json'),
 'r90':('r90_prior_guard.py','test_r90.py','r90_fixed_lag_prior_failure_audit_v1.json','r90_independent_validation_v1.json')
}

def need(ok,reason):
 if not ok:raise ValueError('R91_CHECKPOINT_DENIED:'+reason)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def obj(root,rel):return json.loads((root/rel).read_bytes())

def verify(root):
 need(root.is_dir() and not root.is_symlink(),'ROOT')
 m=obj(root,'checkpoint_manifest_v1.json')
 need(m.get('schema')==SCHEMA and m.get('parent_commit')==BASE,'IDENTITY')
 need(m.get('branch')=='kios-isaacsim-v15-integration','BRANCH')

 pins=m.get('source_sha256')
 meta=m.get('metadata_sha256')

 need(type(pins) is dict and len(pins)==12 and m.get('source_count')==12,'SOURCE_COUNT')
 need(type(meta) is dict and set(meta)=={'README.md','verify_checkpoint.py'},'META')

 allowed=set()
 for phase, (engine,test,report,receipt) in NAMES.items():
  allowed.update((
   f'evidence/{phase}/dev/{engine}',
   f'evidence/{phase}/dev/{test}',
   f'evidence/{phase}/result/{report}',
   f'evidence/{phase}/result/{receipt}'
  ))

 need(set(pins)==allowed,'SOURCE_ALLOWLIST')
 expected=set(pins)|set(meta)|{'checkpoint_manifest_v1.json'}
 need(len(expected)==15,'FILE_COUNT')

 dirs=set()
 for rel in expected:
  parts=pathlib.PurePosixPath(rel)
  need(not parts.is_absolute() and '..' not in parts.parts,'PATH')
  dirs.update('/'.join(parts.parts[:j]) for j in range(1,len(parts.parts)))

 need(
  {str(p.relative_to(root)) for p in root.rglob('*')}==expected|dirs,
  'EXACT_DIRECTORY_ALLOWLIST'
 )

 for d in dirs:
  need((root/d).is_dir() and not (root/d).is_symlink(),'DIRECTORY:'+d)

 for rel in expected:
  s=(root/rel).lstat()
  need(
   stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=4000000,
   'REGULAR_FILE:'+rel
  )

 for rel,pin in {**pins,**meta}.items():
  need(
   type(pin) is str and len(pin)==64 and sha((root/rel).read_bytes())==pin,
   'SHA:'+rel
  )
  raw=(root/rel).read_bytes()
  need(
   not any(marker in raw for marker in ((b'/mnt/' + b'hdd16T/'),(b'/home/' + b'kios/'),b'C:\\Users\\')),
   'PRIVATE_PATH:'+rel
  )

 data={}
 receipts={}
 report_rels={}

 for phase,(engine,test,report,receipt) in NAMES.items():
  p=f'evidence/{phase}/result/{report}'
  q=f'evidence/{phase}/result/{receipt}'
  d=obj(root,p)
  r=obj(root,q)

  data[phase]=d
  receipts[phase]=r
  report_rels[phase]=p

  need(
   d.get('status')=='PASS_SOFTWARE_ONLY'
   and d.get('scientific_gates_closed')==11,
   phase+':STATUS'
  )
  need(
   r.get('status')=='PASS'
   and r.get('scientific_gates_closed')==11,
   phase+':RECEIPT_STATUS'
  )
  need(
   r.get('engine_sha256')==pins[f'evidence/{phase}/dev/{engine}'],
   phase+':ENGINE_SHA'
  )
  need(
   r.get('tests_sha256')==pins[f'evidence/{phase}/dev/{test}'],
   phase+':TEST_SHA'
  )

  receipt_hash_key='result_sha256' if phase=='r89' else 'report_sha256'
  need(r.get(receipt_hash_key)==pins[p],phase+':REPORT_SHA')

  need(
   d.get('scenario_count')==4
   and set(d.get('scenarios',{}))=={
    'continuous','single_gap','accel_injection','gyro_injection'
   },
   phase+':SCENARIOS'
  )

 r88,r89,r90=(data[p] for p in PHASES)

 need(
  r89['r88_report_sha256']==pins[report_rels['r88']],
  'R88_R89_LINEAGE'
 )
 need(
  r90['r88_report_sha256']==pins[report_rels['r88']]
  and r90['r89_report_sha256']==pins[report_rels['r89']],
  'R88_R90_LINEAGE'
 )
 need(
  receipts['r89']['r88_result_sha256']==pins[report_rels['r88']],
  'R89_RECEIPT_LINEAGE'
 )
 need(
  receipts['r90']['r88_report_sha256']==pins[report_rels['r88']]
  and receipts['r90']['r89_report_sha256']==pins[report_rels['r89']],
  'R90_RECEIPT_LINEAGE'
 )

 need(
  r88.get('actual_schur_complement_information_elimination_executed') is True
  and r88.get('mathematically_equivalent_full_batch_linearized_gaussian_checked') is True,
  'SCHUR'
 )
 need(
  r89.get('exact_coordinate_recentering_verified') is True
  and r89.get('fresh_nonlinear_jacobian_changes_measured') is True,
  'RECENTERING'
 )
 need(
  r90.get('segment_count')==5
  and r90.get('adversarial_rejections')==30
  and r90.get('accepted_local_recentering_trials')==15,
  'ATTACK_TOTALS'
 )
 need(
  receipts['r90'].get('adversarial_rejections')==30,
  'ATTACK_RECEIPT'
 )
 need(
  m.get('archived_regression_tests')==69
  and m.get('r90_adversarial_rejections')==30
  and m.get('r90_accepted_recentering_trials')==15,
  'CHECKPOINT_COUNTS'
 )

 for phase in PHASES:
  need(
   data[phase].get('confirmation_test_accessed') is False,
   'CONFIRMATION:'+phase
  )

 for case in ('continuous','single_gap','accel_injection','gyro_injection'):
  a=r88['scenarios'][case]
  b=r89['scenarios'][case]
  c=r90['scenarios'][case]

  need(
   a['segments']==b['segments']==c['segments'],
   'SEGMENT_BINDING:'+case
  )
  need(
   a['rejected_gap_pairs']==b['timestamp_gaps_rejected']==c['rejected_timestamp_gaps'],
   'GAP_BINDING:'+case
  )
  need(
   a['cross_gap_schur_prior_carry_count']
   ==b['cross_gap_prior_carry_count']
   ==c['cross_gap_prior_carry_count']==0,
   'GAP_PRIOR:'+case
  )
  need(
   len(c['segment_results'])==a['segments']
   and c['adversarial_rejections']==6*c['segments']
   and c['accepted_local_recentering_trials']==3*c['segments'],
   'ATTACK_SEGMENTS:'+case
  )
  need(
   set(c['attack_classes'])=={
    'CROSS_SEGMENT','STALE_LINEARIZATION','EXCESSIVE_RECENTER',
    'NONLINEAR_REFRESH','MATRIX_TAMPER','REAL_SOURCE'
   },
   'ATTACK_CLASSES:'+case
  )

  for row in c['segment_results']:
   need(
    row['information_matrix_dimension']==15
    and row['max_condition_number']<=r90['synthetic_condition_limit'],
    'NUMERIC_GUARD:'+case
   )
   need(
    row['max_optimum_transform_error']<1e-6
    and row['max_covariance_invariance_error']<1e-12
    and row['max_quadratic_energy_error']<1e-5,
    'RECENTER_ERRORS:'+case
   )
   need(
    row['information_crossing_timestamp_gap'] is False
    and row['nonlinear_eliminated_factors_relinearized'] is False,
    'NO_PRIOR_REUSE:'+case
   )

 need(
  r90['scenarios']['single_gap']['segments']==2
  and r90['scenarios']['single_gap']['rejected_timestamp_gaps']==1,
  'EXPECTED_GAP'
 )

 for phase,fields in {
  'r88':(
   'real_sensor_factor_admission',
   'independent_reference_or_observability_verified',
   'health_training_or_labels_authorized',
   'ate_rpe_computed',
   'original_rosbags_or_gt_opened'
  ),
  'r89':(
   'marginalized_prior_relinearization_authorized',
   'real_pose_factors_authorized',
   'health_training_authorized',
   'ate_rpe_authorized',
   'raw_rosbags_or_gt_opened'
  ),
  'r90':(
   'thresholds_are_empirical_safety_limits',
   'nonlinear_marginal_prior_refresh_authorized',
   'real_sensor_factors_authorized',
   'health_training_authorized',
   'ate_rpe_authorized',
   'rosbags_or_gt_opened'
  )
 }.items():
  for field in fields:
   need(
    data[phase].get(field) is False,
    'SCIENTIFIC_DENIAL:'+phase+':'+field
   )

 for field in (
  'real_sensor_factor_execution',
  'independent_gt_scoring_or_ate_rpe',
  'physical_clock_or_extrinsic_calibration_qualified',
  'nonlinear_marginal_prior_relinearization_authorized',
  'health_labels_or_training_authorized',
  'original_gt_or_rosbags_archived',
  'private_verona_reports_archived',
  'confirmation_test_accessed'
 ):
  need(
   m.get(field) is False,
   'CHECKPOINT_SCIENCE:'+field
  )

 need(m.get('scientific_gates_closed')==11,'GATES')

 print('R91_STANDALONE_CHECKPOINT_VERIFIER=PASS')
 print('R91_SHA_PINNED_SOURCE_ARTIFACTS=12_PASS')
 print('R91_R88_R90_NUMERICAL_AND_LINEAGE_BOUNDARIES=PASS')
 print('R91_ALL_11_SCIENTIFIC_GATES=CLOSED')

if __name__=='__main__':
 need(len(sys.argv)==3 and sys.argv[1]=='verify','ARGUMENTS')
 verify(pathlib.Path(sys.argv[2]))
