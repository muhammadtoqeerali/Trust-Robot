import ast,copy,pathlib,sys
import r43_protocol as p
files=list(pathlib.Path(sys.argv[1]).glob('*.py'))
assert len(files)==3
for file in files:ast.parse(file.read_text(),filename=str(file))
model={'schema':'TRUST_ROBOT_R43_SOURCE_ACQUISITION_GATE_PROTOCOL_V1','trajectory_id':'room_02','split':'train','github_baseline':p.BASE,'bag_sha256':p.BAG,'raw_reference_provenance_sha256':p.REF,'split_manifest_sha256':p.SPLIT,'frozen_manifest_sha256':{x:'a'*64 for x in p.MANIFESTS},'requests':{k:{'status':'NOT_QUALIFIED','source_class':v[0],'required_evidence_fields':list(v[1:]),'physical_validation_completed':False} for k,v in p.SPEC.items()},'unresolved_gate_count':11,'room_02_reference_invalid_rotations':90,'existing_d435i_relative_rotation_content_support':True,'full_extrinsic_from_partial_rotation':False,'reference_to_lidar_transform_known':False,'source_acquisition_status':'NOT_ACQUIRED','next_phase':'R44_GUARDED_R39_R43_CHECKPOINT',**{k:False for k in p.CLOSED},**{k:0 for k in p.ZERO}}
receipts={'schema':'TRUST_ROBOT_R43_EMPTY_EVIDENCE_RECEIPTS_V1','intended_split':'train','gate_receipts':{k:{'status':'NO_SOURCE_RECEIVED','source_uri':None,'source_sha256':None,'independent_validation_sha256':None,'physical_qualification_authorized':False,'required_fields':{f:None for f in v[1:]}} for k,v in p.SPEC.items()}}
p.policy(model,receipts)
rejected=0
for key in p.CLOSED+p.ZERO:
 x=copy.deepcopy(model);x[key]=True if key in p.CLOSED else 1
 try:p.policy(x,receipts)
 except ValueError:rejected+=1
 else:raise AssertionError('SCIENCE_PROMOTION:'+key)
for item,value in (('split','confirmation_test'),('source_acquisition_status','ACQUIRED'),('unresolved_gate_count',10),('room_02_reference_invalid_rotations',0),('full_extrinsic_from_partial_rotation',True)):
 x=copy.deepcopy(model);x[item]=value
 try:p.policy(x,receipts)
 except ValueError:rejected+=1
 else:raise AssertionError('UNSAFE_REPORT:'+item)
for variant in ('fake_source_uri','fake_sha','qualified','nonempty_matrix','wrong_spec'):
 x=copy.deepcopy(receipts);a=x['gate_receipts']['camera_lidar_extrinsics_physically_verified']
 if variant=='fake_source_uri':a['source_uri']='https://example.invalid/fake'
 elif variant=='fake_sha':a['source_sha256']='f'*64
 elif variant=='qualified':a['physical_qualification_authorized']=True
 elif variant=='nonempty_matrix':a['required_fields']['T_target_source_SE3']=[1]*16
 else:a['required_fields'].pop('target_frame')
 try:p.policy(model,x)
 except ValueError:rejected+=1
 else:raise AssertionError('UNSAFE_RECEIPT:'+variant)
assert rejected==len(p.CLOSED)+len(p.ZERO)+10==22
print('R43_PYTHON_AST=3_PASS')
print('R43_NEGATIVE_SCIENCE_SOURCE_RECEIPT_CONTROLS=22_REJECTED')
