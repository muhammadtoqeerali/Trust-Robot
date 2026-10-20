"""R49 fail-closed policy and synthetic camera-model regression tests."""
import ast,copy,pathlib,sys
import numpy as np
import r49_model as m

root=pathlib.Path(sys.argv[1])
for name in ('r49_model.py','r49_independent.py','test_r49.py'):
 ast.parse((root/name).read_text(),filename=name)
params=[617.971050917033,616.445131524790,327.710279392468,253.976983707814,0.148000794688248,-0.217835187249065,0,0]
points=np.asarray([[0.,0.],[639.,479.],[params[2],params[3]]],np.float64)
rays=m.make_rays(points,params)
assert np.max(abs(np.linalg.norm(rays,axis=1)-1))<1e-12
assert m.angle(rays,rays).max()<1e-9
assert all(np.isfinite(m.make_rays(points+0.5,params).ravel()))
example={
 'schema':'TRUST_ROBOT_R49_TRAIN_CAMERA_MODEL_INTERPRETATION_AND_NOISE_DIAGNOSTICS_V1',
 'trajectory_id':'room_02','split':'train','github_baseline':m.BASE,
 'authenticated_bag_sha256':m.BAG,'model':m.MODEL,
 'grid_points':64,'synthetic_pixel_perturbations':256,
 'source_recorded_frame_count_dimensions_only':16,
 'physical_calibration_not_established':True,'numeric_simulation_only':True,
 'author_matrix_orientation':'RAW_ROW_MAJOR_K_IS_TRANSPOSED_RELATIVE_TO_STANDARD_PINHOLE_K',
 'raw_matrix_standard_K_interpretation_is_rejected':True,
 'numeric_inverse_verified_against_R48':True,'radial_forward_map_monotonic_on_sampled_domain':True,
 'radial_jacobian_min':0.9,
 'angular_effect_degrees':{
  'ignore_distortion':{'min':0.,'median':.5,'max':1.},
  'raw_author_K_wrong_standard_intrinsics':{'min':20.,'median':30.,'max':40.},
  'synthetic_half_pixel_xy':{'min':.01,'median':.04,'max':.09}},
 'qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,
 'raw_sensor_messages_decoded':0,
 'next_phase':'R50_GUARDED_R45_R49_GITHUB_CHECKPOINT',
 **{k:False for k in m.CLOSED}
}
m.policy(example)
rejected=0
for k in m.CLOSED:
 invalid=copy.deepcopy(example);invalid[k]=True
 try:m.policy(invalid)
 except ValueError:rejected+=1
 else:raise AssertionError('SCIENCE_PROMOTION_'+k)
for k in m.ZERO:
 invalid=copy.deepcopy(example);invalid[k]=1
 try:m.policy(invalid)
 except ValueError:rejected+=1
 else:raise AssertionError('NONZERO_'+k)
for key,value in (
 ('split','confirmation_test'),('trajectory_id','room_03'),('github_baseline','0'*40),
 ('authenticated_bag_sha256','0'*64),('grid_points',63),
 ('synthetic_pixel_perturbations',255),('source_recorded_frame_count_dimensions_only',1),
 ('numeric_simulation_only',False),('physical_calibration_not_established',False),
 ('author_matrix_orientation','AS_PUBLISHED_STANDARD_K'),
 ('raw_matrix_standard_K_interpretation_is_rejected',False),
 ('radial_forward_map_monotonic_on_sampled_domain',False),
 ('radial_jacobian_min',-.1),('next_phase','SCORE')):
 invalid=copy.deepcopy(example);invalid[key]=value
 try:m.policy(invalid)
 except ValueError:rejected+=1
 else:raise AssertionError('SCOPE_'+key)
for case in ('misread_k','jitter','distortion','wrong_case'):
 invalid=copy.deepcopy(example)
 if case=='misread_k':invalid['angular_effect_degrees']['raw_author_K_wrong_standard_intrinsics']['max']=1.
 elif case=='jitter':invalid['angular_effect_degrees']['synthetic_half_pixel_xy']['max']=2.
 elif case=='distortion':invalid['angular_effect_degrees']['ignore_distortion']['max']=0.
 else:invalid['angular_effect_degrees']['unverified_real_pose']={'min':0,'median':1,'max':2}
 try:m.policy(invalid)
 except ValueError:rejected+=1
 else:raise AssertionError('CASE_'+case)
assert rejected==len(m.CLOSED)+len(m.ZERO)+14+4==32
print('R49_PYTHON_SOURCES_AST=3_PASS')
print('R49_SYNTHETIC_RAY_INVERSION_CONTROL=PASS')
print('R49_NEGATIVE_SCIENCE_SOURCE_INTERPRETATION_CONTROLS=32_REJECTED')
