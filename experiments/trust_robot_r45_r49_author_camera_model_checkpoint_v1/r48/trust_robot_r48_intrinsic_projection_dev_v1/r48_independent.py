"""Independent OpenCV undistortion from 64 source pixels; no imported primary engine."""
import hashlib,json,math,pathlib,re,statistics,sys
import cv2,numpy as np

def need(ok,why):
 if not ok:raise ValueError('R48_INDEPENDENT_DENIED:'+why)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def scalar(s,name):
 r=re.findall(r'(?m)^\s*'+re.escape(name)+r':\s*([-+\d.eE]+)(?=\s|#|$)',s)
 need(len(r)==1,'SCALAR:'+name)
 return float(r[0])
def rays_cv(points,params):
 fx,fy,cx,cy,k1,k2,p1,p2=params
 K=np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],np.float64)
 D=np.array([k1,k2,p1,p2,0],np.float64)
 uv=points.reshape(-1,1,2).astype(np.float64)
 if hasattr(cv2,'undistortPointsIter'):
  norm=cv2.undistortPointsIter(uv,K,D,None,None,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-14)).reshape(-1,2)
 else:norm=cv2.undistortPoints(uv,K,D).reshape(-1,2)
 vec=np.column_stack((norm,np.ones(len(norm))))
 return vec/np.linalg.norm(vec,axis=1)[:,None],K,D

def angle_deg(a,b):
 return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.sum(a*b,axis=1)))

def verify(yaml,camfile,r47file,report,plan,out):
 r=json.loads(report.read_text());c=json.loads(camfile.read_text());r47=json.loads(r47file.read_text())
 need(r['schema']=='TRUST_ROBOT_R48_TRAIN_INTRINSIC_PIXEL_GRID_NUMERIC_DIAGNOSTICS_V1' and r['split']=='train' and r['trajectory_id']=='room_02','SOURCE_SCOPE')
 need(r['source_sha256']=={'author_camera_yaml':sha(yaml),'recorded_r33':sha(camfile),'r46':r['source_sha256']['r46'],'r47':sha(r47file),'r47_independent':r['source_sha256']['r47_independent']},'SOURCE_LINK')
 need(len(c['pairs'])==8 and all([f['width'],f['height']]==[640,480] for pair in c['pairs'] for f in pair['frames']),'AUTHENTIC_SOURCE_DIMENSIONS')
 need(r47['compatibility']['authentic_color_frames_checked']==16 and r47['compatibility']['camera_intrinsics_sensor_identity_physically_qualified'] is False,'RECORDING_COMPATIBILITY')
 yamltext=yaml.read_text()
 params=[scalar(yamltext,n) for n in ('fx','fy','cx','cy','k1','k2','p1','p2')]
 need(len(r['grid'])==64 and r['grid_point_count']==64 and all(math.isclose(a,b,rel_tol=0,abs_tol=1e-12) for a,b in zip(params,r['camera_parameters_fx_fy_cx_cy_k1_k2_p1_p2'])),'PARAMETER_MATCH')
 points=np.asarray([p['pixel_xy'] for p in r['grid']],np.float64)
 expected=np.asarray([[639*a/8,479*b/6] for b in range(7) for a in range(9)]+[[params[2],params[3]]],np.float64)
 need(np.max(abs(points-expected))<1e-12,'GRID_POINTS')
 rays,K,d=rays_cv(points,params)
 manually=np.asarray([g['unit_ray_camera'] for g in r['grid']],np.float64)
 delta=angle_deg(rays,manually)
 need(np.max(delta)<1e-5,'INDEPENDENT_CAMERA_RAY_REPLAY')
 uv,_=cv2.projectPoints(rays,np.zeros(3),np.zeros(3),K,d)
 err=np.linalg.norm(uv.reshape(-1,2)-points,axis=1)
 need(float(max(err))<1e-4 and r['cv_projection_roundtrip_max_px']<1e-4,'OPENCV_REPROJECTION')
 variants={}
 change=list(params);change[0]*=1.01;change[1]*=1.01
 variants['focal_length_plus_1_percent']=change
 change=list(params);change[2]+=1;change[3]+=1
 variants['principal_point_plus_1_pixel_xy']=change
 change=list(params);change[4]*=1.05;change[5]*=1.05
 variants['radial_coefficients_plus_5_percent']=change
 for name,values in variants.items():
  shifted,_,_=rays_cv(points,values)
  a=angle_deg(rays,shifted)
  stored=r['angular_sensitivity_degrees'][name]
  need(abs(max(a)-stored['max'])<1e-5 and abs(statistics.median(a)-stored['median'])<1e-5,'INDEPENDENT_SENSITIVITY:'+name)
 need(all(r[x] is False for x in ('physical_camera_intrinsics_qualified','complete_sensor_extrinsics_qualified','physical_capture_time_verified','pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized','raw_bag_reopened','confirmation_test_accessed','github_modified')),'SCIENCE_GATES')
 need(all(r[k]==0 for k in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_decoded')),'ZERO_FACTORS')
 need('64-point grid' in plan.read_text() and 'R49' in plan.read_text() and 'not independent physical intrinsics validation' in plan.read_text(),'PLAN_SCIENCE')
 proof={'schema':'TRUST_ROBOT_R48_INDEPENDENT_OPENCV_GRID_VALIDATION_V1','report_sha256':sha(report),'plan_sha256':sha(plan),'synthetic_grid_points_verified':64,'opencV_independently_reprojected_points':64,'independent_ray_max_angle_difference_deg':float(max(delta)),'independent_roundtrip_max_px':float(max(err)),'sensitivity_cases_rechecked':3,'physical_calibration_qualified':False,'real_pose_factors_authorized':False,'raw_bag_opened':False,'confirmation_test_accessed':False,'github_modified':False}
 with out.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print('R48_INDEPENDENT_OPENCV_RAYS=64_MATCH')
 print('R48_INDEPENDENT_PROJECT_UNPROJECT_MAX_PX=%.12g'%max(err))
 print('R48_INDEPENDENT_THREE_SENSITIVITY_CASES=MATCH')
 print('R48_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*(pathlib.Path(p) for p in sys.argv[1:7]))
