"""OpenCV-only independent R49 ray check; no primary implementation imported."""
import hashlib,json,math,pathlib,re,statistics,sys
import numpy as np
import cv2

def need(ok,k):
 if not ok:raise ValueError('R49_INDEPENDENT_DENIED:'+k)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def yaml_numbers(text):
 names=('fx','fy','cx','cy','k1','k2','p1','p2')
 result=[]
 for k in names:
  v=re.findall(r'(?m)^\s*'+re.escape(k)+r':\s*([-+\d.eE]+)(?=\s|#|$)',text)
  need(len(v)==1,'YAML:'+k)
  result.append(float(v[0]))
 return result
def unit_cv(points,params,distortion=True,principal_origin=False):
 fx,fy,cx,cy,k1,k2,p1,p2=params
 if principal_origin:cx=0.;cy=0.
 K=np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],np.float64)
 D=np.array([k1,k2,p1,p2,0],np.float64) if distortion else np.zeros(5,np.float64)
 uv=np.asarray(points,np.float64).reshape(-1,1,2)
 if hasattr(cv2,'undistortPointsIter'):
  norm=cv2.undistortPointsIter(uv,K,D,None,None,
   (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,100,1e-14)).reshape(-1,2)
 else:
  norm=cv2.undistortPoints(uv,K,D).reshape(-1,2)
 rays=np.column_stack((norm,np.ones(len(norm))))
 return rays/np.linalg.norm(rays,axis=1)[:,None]
def angular(a,b):
 return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.sum(a*b,axis=1)))
def summarize(values):
 arr=[float(x) for x in values]
 return dict(min=min(arr),median=float(statistics.median(arr)),max=max(arr))

def verify(author,yaml,r48p,v48p,r46p,r47p,reportp,planp,out):
 r=load(reportp);up=load(r48p);v=load(v48p);previous=load(r46p);recorded=load(r47p)
 need(r['schema']=='TRUST_ROBOT_R49_TRAIN_CAMERA_MODEL_INTERPRETATION_AND_NOISE_DIAGNOSTICS_V1' and r['trajectory_id']=='room_02' and r['split']=='train','R49_SCOPE')
 need(r['source_sha256']=={
  'author_calibration_results':sha(author),'author_camera_yaml':sha(yaml),
  'r46_author_audit':sha(r46p),'r47_recorded_applicability':sha(r47p),
  'r48_numeric_projection':sha(r48p),'r48_independent':sha(v48p)},'PINS')
 need(v['report_sha256']==sha(r48p) and previous['physical_calibration_qualified'] is False and recorded['compatibility']['authentic_color_frames_checked']==16,'UPSTREAM')
 params=yaml_numbers(yaml.read_text())
 need(max(abs(x-y) for x,y in zip(params,r['camera_parameters_fx_fy_cx_cy_k1_k2_p1_p2']))<1e-12,'AUTHOR_PARAMS')
 need(up['grid_point_count']==64 and up['synthetic_grid_only'] is True and len(up['grid'])==64,'R48_GRID')
 points=np.asarray([x['pixel_xy'] for x in up['grid']],dtype=np.float64)
 expected=np.asarray([[639*i/8,479*j/6] for j in range(7) for i in range(9)]+[[params[2],params[3]]])
 need(np.max(abs(expected-points))<1e-12,'POINT_COORDS')
 rays=unit_cv(points,params)
 previous_rays=np.asarray([x['unit_ray_camera'] for x in up['grid']],np.float64)
 need(max(angular(rays,previous_rays))<1e-5,'R48_RAY_MATCH')
 no_dist=unit_cv(points,params,False)
 # Compare the same ideal pixel rays under the wrong row-major principal point.
 fx,fy,cx,cy,k1,k2,p1,p2=params
 ideal=np.column_stack((fx*rays[:,0]/rays[:,2]+cx,fy*rays[:,1]/rays[:,2]+cy))
 wrong_intr=unit_cv(ideal,params,False,True)
 noise=[]
 for dx,dy in ((-.5,-.5),(-.5,.5),(.5,-.5),(.5,.5)):
  noise.extend(float(x) for x in angular(rays,unit_cv(points+np.asarray([dx,dy]),params)))
 measured={
  'ignore_distortion':summarize(angular(rays,no_dist)),
  'raw_author_K_wrong_standard_intrinsics':summarize(angular(rays,wrong_intr)),
  'synthetic_half_pixel_xy':summarize(noise)}
 for key,summary in measured.items():
  need(key in r['angular_effect_degrees'],'ANGULAR_CASE:'+key)
  for field,value in summary.items():
   need(abs(value-r['angular_effect_degrees'][key][field])<1e-5,'ANGULAR_'+key+'_'+field)
 need(r['synthetic_pixel_perturbations']==256 and r['source_recorded_frame_count_dimensions_only']==16,'SIMULATED_ONLY')
 text=author.read_text()
 fragment=re.split(r'(?m)^%%\s*Cam-pinhole-color realsense d435i\s*$',text)
 need(len(fragment)==2,'AUTHOR_CAMERA_SECTION')
 tail=re.split(r'(?m)^%%\s+',fragment[1])[0]
 values=re.findall(r'\bdata\s*:\s*\[([^\]]+)\]',tail,re.S)
 need(len(values)==4,'MATRIX_RECEIPT')
 K=np.asarray([float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?',values[1])],np.float64).reshape(3,3)
 fx,fy,cx,cy,k1,k2,p1,p2=params
 need(np.max(abs(K.T-np.asarray([[fx,0,cx],[0,fy,cy],[0,0,1]])))<1e-9,'K_AUTHOR_TRANSPOSE')
 xyn=rays[:,:2]/rays[:,2,None]
 r2=np.sum(xyn**2,axis=1)
 deriv=1+3*k1*r2+5*k2*r2*r2
 need(min(deriv)>0 and abs(min(deriv)-r['radial_jacobian_min'])<1e-9 and abs(max(deriv)-r['radial_jacobian_max'])<1e-9,'RADIAL_JACOBIAN')
 need(all(r.get(k) is False for k in ('physical_camera_intrinsics_qualified','complete_sensor_extrinsics_qualified','physical_capture_time_verified','pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized','confirmation_test_accessed','raw_bag_reopened','github_modified')),'SCIENCE')
 need(all(r[k]==0 for k in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_decoded')),'SCIENCE_ZERO')
 md=planp.read_text()
 need('R50' in md and '64 R48 manufactured pixels' in md and 'NOT' in md and 'not a measured sensor error' in md,'PLAN_DOC')
 proof={
  'schema':'TRUST_ROBOT_R49_INDEPENDENT_OPENCV_MODEL_INTERPRETATION_V1',
  'source_report_sha256':sha(reportp),'plan_sha256':sha(planp),
  'r48_source_report_sha256':sha(r48p),
  'synthetic_camera_rays_replayed':64,
  'synthetic_pixel_perturbation_rays_replayed':256,
  'model_interpretation_cases_rechecked':3,
  'independent_radial_jacobian_checked':True,
  'physical_camera_intrinsics_qualified':False,
  'real_pose_factors_authorized':False,
  'raw_bag_opened':False,'confirmation_test_accessed':False,'github_modified':False
 }
 with out.open('x') as f:json.dump(proof,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print('R49_INDEPENDENT_OPENCV_RAYS=64_MATCH')
 print('R49_INDEPENDENT_HALF_PIXEL_CASES=256_MATCH')
 print('R49_INDEPENDENT_THREE_MODEL_INTERPRETATIONS=MATCH')
 print('R49_INDEPENDENT_RADIAL_JACOBIAN=POSITIVE_SAMPLED_DOMAIN')
 print('R49_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*(pathlib.Path(p) for p in sys.argv[1:10]))
