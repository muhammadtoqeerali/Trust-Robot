import ast,copy,pathlib,sys
import r39_qualification as e

for p in pathlib.Path(sys.argv[1]).glob('*.py'):
 ast.parse(p.read_text(),filename=str(p))

print('R39_PYTHON_SOURCES_AST=3_PASS')

mock={
 'schema':'TRUST_ROBOT_R39_TRAIN_RECORDED_SENSOR_QUALIFICATION_PLAN_V1',
 'trajectory_id':'room_02',
 'split':'train',
 'github_baseline':e.BASE,
 'authenticated_bag_sha256':e.BAG,
 'source_sha256':{k:v[1] for k,v in e.PINS.items()},
 'decision':'DIAGNOSTICS_VERIFIED_QUALIFIED_REAL_FACTORS_BLOCKED',
 'metrics':{
  'lidar':{'adjacent_train_pairs':8},
  'camera':{'train_pairs':8},
  'imu':{k:{} for k in e.STREAMS}
 },
 'qualification_gates':{'a':{'status':'NOT_QUALIFIED'}},
 'next_phase':'R40_CALIBRATION_CLOCK_REFERENCE_ASSET_INVENTORY',
 'work_sequence':[{}]*len(e.STEPS),
 'scientific_pose_factors':0,
 'health_labels':0,
 'ate_rpe_scores':0,
 **{k:False for k in e.GATES}
}

e.safety(mock)
rejected=0

for k in e.GATES+e.ZERO:
 changed=copy.deepcopy(mock)
 changed[k]=True if k in e.GATES else 1
 try:
  e.safety(changed)
 except ValueError:
  rejected+=1
 else:
  raise AssertionError('SCIENCE_PROMOTION:'+k)

for k,v in [
 ('split','confirmation_test'),
 ('decision','QUALIFIED'),
 ('next_phase','SCORE_TEST'),
 ('source_sha256',{}),
 ('qualification_gates',{'a':{'status':'QUALIFIED'}}),
 ('authenticated_bag_sha256','0'*64)
]:
 changed=copy.deepcopy(mock)
 changed[k]=v
 try:
  e.safety(changed)
 except ValueError:
  rejected+=1
 else:
  raise AssertionError('NEGATIVE_CONTROL:'+k)

assert rejected==len(e.GATES)+len(e.ZERO)+6

print('R39_NEGATIVE_PROMOTION_AND_SOURCE_CONTROLS=%d_REJECTED'%rejected)
