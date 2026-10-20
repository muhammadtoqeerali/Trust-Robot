import ast,copy,pathlib,sys
import r40_inventory as m
paths=list(pathlib.Path(sys.argv[1]).glob('*.py'))
assert len(paths)==3
for p in paths:ast.parse(p.read_text(),filename=str(p))
print('R40_PYTHON_SOURCES_AST=3_PASS')
example={
 'schema':'TRUST_ROBOT_R40_TRAIN_CALIBRATION_REFERENCE_ASSET_INVENTORY_V1',
 'trajectory_id':'room_02','split':'train','github_baseline':m.BASE,'source_bag_sha256':m.BAG,
 'raw_bag_opened':False,'confirmation_test_accessed':False,'github_modified':False,
 'qualified_real_sensor_factors':0,'health_labels':0,'m2dgr_scoring_authorized':False,
 'repository_evidence_sha256':{x:'a'*64 for x in m.DOCUMENTS},
 'qualification_requirements':{x:{'status':'UNVERIFIED'} for x in m.REQUIREMENTS},
 'room_02_reference_provenance':{'reference_source':'mocap','rotation_invalid_count':90},
 'recorded_stream_clock_domains':[{'synchronization_status':'unverified'} for _ in range(4)],
 'next_phase':'R41_TRAIN_CALIBRATION_CANDIDATE_SEMANTICS_AND_REFERENCE_CONTENT'
}
m.policy(example)
rejected=0
for k,v in [
 ('split','confirmation_test'),('trajectory_id','Circle_02'),('raw_bag_opened',True),
 ('confirmation_test_accessed',True),('github_modified',True),
 ('qualified_real_sensor_factors',1),('health_labels',1),('m2dgr_scoring_authorized',True),
 ('repository_evidence_sha256',{}),('qualification_requirements',{}),
 ('recorded_stream_clock_domains',[]),('next_phase','R42_SKIP'),('source_bag_sha256','0'*64)]:
 row=copy.deepcopy(example);row[k]=v
 try:m.policy(row)
 except ValueError:rejected+=1
 else:raise AssertionError('SCIENCE_PROMOTION:'+k)
for kind in ('wrong_reference','altered_rotation_count','promoted_clock','promoted_calibration'):
 row=copy.deepcopy(example)
 if kind=='wrong_reference':row['room_02_reference_provenance']['reference_source']='rtk_ins'
 elif kind=='altered_rotation_count':row['room_02_reference_provenance']['rotation_invalid_count']=0
 elif kind=='promoted_clock':row['recorded_stream_clock_domains'][0]['synchronization_status']='verified'
 else:row['qualification_requirements']['camera_intrinsics_and_distortion']['status']='QUALIFIED'
 try:m.policy(row)
 except ValueError:rejected+=1
 else:raise AssertionError('UNSAFE_STATE:'+kind)
assert rejected==17
assert m.forbidden(pathlib.PurePosixPath('raw/groundtruth/Circle_02.txt'),{'circle_02'})
assert not m.forbidden(pathlib.PurePosixPath('raw/groundtruth/room_02.txt'),{'circle_02'})
print('R40_NEGATIVE_SCIENTIFIC_HOLDOUT_CONTROLS=17_REJECTED')
