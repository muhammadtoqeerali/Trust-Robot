import ast,copy,pathlib,sys
import r48_numeric as p
root=pathlib.Path(sys.argv[1]);names=('r48_numeric.py','r48_independent.py','test_r48.py')
for name in names:ast.parse((root/name).read_text(),filename=name)
example={'schema':'TRUST_ROBOT_R48_TRAIN_INTRINSIC_PIXEL_GRID_NUMERIC_DIAGNOSTICS_V1','trajectory_id':'room_02','split':'train','github_baseline':p.BASE,'authenticated_bag_sha256':p.BAG,'author_calibration_source_is_physical_sensor_qualification':False,'synthetic_grid_only':True,'recorded_frame_dimensions':[640,480],'authentic_source_frames_count':16,'grid_point_count':64,'grid':[{}]*64,'model':'PINHOLE_RADTAN_K1_K2_P1_P2_K3_ZERO','manual_inverse_converged':True,'cv_projection_roundtrip_max_px':1e-7,'angular_sensitivity_degrees':{k:{} for k in ('focal_length_plus_1_percent','principal_point_plus_1_pixel_xy','radial_coefficients_plus_5_percent')},'qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,'raw_sensor_messages_decoded':0,'next_phase':'R49_TRAIN_CAMERA_MODEL_NUMERIC_DIAGNOSTIC_INDEPENDENT_EXTENSION',**{k:False for k in p.DENIED}}
p.policy(example)
count=0
for key in p.DENIED:
 row=copy.deepcopy(example);row[key]=True
 try:p.policy(row)
 except ValueError:count+=1
 else:raise AssertionError('GATE_PROMOTED:'+key)
for key in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_decoded'):
 row=copy.deepcopy(example);row[key]=1
 try:p.policy(row)
 except ValueError:count+=1
 else:raise AssertionError('SCORING_PROMOTED:'+key)
for key,value in (('split','confirmation_test'),('trajectory_id','room_03'),('github_baseline','0'*40),('authenticated_bag_sha256','0'*64),('synthetic_grid_only',False),('author_calibration_source_is_physical_sensor_qualification',True),('recorded_frame_dimensions',[1280,720]),('authentic_source_frames_count',0),('grid_point_count',63),('model','UNKNOWN'),('manual_inverse_converged',False),('cv_projection_roundtrip_max_px',1),('angular_sensitivity_degrees',{}),('next_phase','SCORE_NOW')):
 row=copy.deepcopy(example);row[key]=value
 try:p.policy(row)
 except ValueError:count+=1
 else:raise AssertionError('INPUT_PROMOTED:'+key)
assert count==28
print('R48_PYTHON_AST=3_PASS')
print('R48_NEGATIVE_SCIENCE_AND_INPUT_CONTROLS=28_REJECTED')
