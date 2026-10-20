"""Synthetic pixel-grid lens-model diagnostics bound to TRAIN-recorded frame dimensions.
No images are decoded. Do not treat any result as calibrated physical pose.
"""
import hashlib,json,math,pathlib,re,statistics,sys
import numpy as np
import cv2

BASE='17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
DENIED=('physical_camera_intrinsics_qualified','complete_sensor_extrinsics_qualified',
 'physical_capture_time_verified','independent_metric_scale_established',
 'pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized',
 'confirmation_test_accessed','raw_bag_reopened','github_modified')

def need(ok,why):
 if not ok:raise ValueError('R48_DENIED:'+why)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(pathlib.Path(path).read_text())
def scalar(text,key):
 values=re.findall(r'(?m)^\s*'+re.escape(key)+r':\s*([-+\d.eE]+)(?=\s|#|$)',text)
 need(len(values)==1,'AUTHOR_CAMERA_SETTING:'+key)
 return float(values[0])
def camera(yaml_path):
 s=yaml_path.read_text()
 x=[scalar(s,k) for k in ('fx','fy','cx','cy','k1','k2','p1','p2')]
 need(all(math.isfinite(a) for a in x) and x[0]>0 and x[1]>0,'INTRINSIC_FINITE')
 need([int(scalar(s,k)) for k in ('image_width','image_height')]==[640,480],'AUTHOR_IMAGE_SIZE')
 return x

def grid():
 # 9 columns x 7 rows + optical-axis principal-point candidate = 64 pixels.
 points=[[639.*a/8,479.*b/6] for b in range(7) for a in range(9)]
 points.append([327.710279392468,253.976983707814])
 return np.array(points,dtype=np.float64)

def rays_manual(points,params):
 fx,fy,cx,cy,k1,k2,p1,p2=params
 xd=(points[:,0]-cx)/fx;yd=(points[:,1]-cy)/fy
 x=xd.copy();y=yd.copy()
 for _ in range(60):
  r2=x*x+y*y;radial=1+k1*r2+k2*r2*r2
  need(np.all(radial>0.75),'RADIAL_STABILITY')
  tx=2*p1*x*y+p2*(r2+2*x*x)
  ty=p1*(r2+2*y*y)+2*p2*x*y
  nxtx=(xd-tx)/radial;nxty=(yd-ty)/radial
  diff=float(max(np.max(abs(nxtx-x)),np.max(abs(nxty-y))))
  x=nxtx;y=nxty
  if diff<1e-14:break
 need(diff<1e-12,'INVERSE_CONVERGENCE')
 vectors=np.column_stack((x,y,np.ones(len(x))))
 return vectors/np.linalg.norm(vectors,axis=1)[:,None]

def cv_camera(params):
 fx,fy,cx,cy,k1,k2,p1,p2=params
 K=np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],dtype=np.float64)
 dist=np.array([k1,k2,p1,p2,0.],dtype=np.float64)
 return K,dist

def angular(a,b):
 cos=np.clip(np.sum(a*b,axis=1),-1.0,1.0)
 # atan2(cross-product magnitude, dot) remains stable for subpixel deltas.
 cross=np.linalg.norm(np.cross(a,b),axis=1)
 return np.degrees(np.arctan2(cross,cos))

def summary(values):
 v=[float(x) for x in values]
 need(len(v)>0 and all(math.isfinite(x) for x in v),'FINITE_SUMMARY')
 return {'min':min(v),'median':statistics.median(v),'max':max(v)}

def sensitivity(points,base,params):
 variants={}
 modified=list(params);modified[0]*=1.01;modified[1]*=1.01
 variants['focal_length_plus_1_percent']=rays_manual(points,modified)
 modified=list(params);modified[2]+=1.0;modified[3]+=1.0
 variants['principal_point_plus_1_pixel_xy']=rays_manual(points,modified)
 modified=list(params);modified[4]*=1.05;modified[5]*=1.05
 variants['radial_coefficients_plus_5_percent']=rays_manual(points,modified)
 return {name:summary(angular(base,value)) for name,value in variants.items()}

def policy(r):
 need(r.get('schema')=='TRUST_ROBOT_R48_TRAIN_INTRINSIC_PIXEL_GRID_NUMERIC_DIAGNOSTICS_V1' and r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('github_baseline')==BASE and r.get('authenticated_bag_sha256')==BAG,'TRAIN_SCOPE')
 need(all(r.get(k) is False for k in DENIED),'SCIENCE_PROMOTION')
 need(all(type(r.get(k)) is int and r[k]==0 for k in ('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_decoded')),'SCIENCE_COUNTS')
 need(r.get('author_calibration_source_is_physical_sensor_qualification') is False and r.get('synthetic_grid_only') is True,'MODEL_SCOPE')
 need(r.get('recorded_frame_dimensions')==[640,480] and r.get('authentic_source_frames_count')==16,'FRAME_COUNTS')
 need(r.get('grid_point_count')==64 and len(r.get('grid',[]))==64,'GRID')
 need(r.get('model')=='PINHOLE_RADTAN_K1_K2_P1_P2_K3_ZERO','MODEL')
 need(r.get('manual_inverse_converged') is True and r.get('cv_projection_roundtrip_max_px',1)>0 and r['cv_projection_roundtrip_max_px']<1e-4,'INVERSE_ROUNDTRIP')
 need(set(r.get('angular_sensitivity_degrees',{}))=={'focal_length_plus_1_percent','principal_point_plus_1_pixel_xy','radial_coefficients_plus_5_percent'},'SENSITIVITY_CASES')
 need(r.get('next_phase')=='R49_TRAIN_CAMERA_MODEL_NUMERIC_DIAGNOSTIC_INDEPENDENT_EXTENSION','NEXT')

def run(yaml,camfile,r46file,r47file,v47file,report,plan):
 ca=load(camfile);r46=load(r46file);r47=load(r47file);v47=load(v47file)
 need(ca['pair_count']==len(ca['pairs'])==8 and ca['trajectory_id']=='room_02' and ca['split']=='train' and ca['authenticated_bag_sha256']==BAG,'R33_AUTHENTIC_SOURCE')
 frames=[f for pair in ca['pairs'] for f in pair['frames']]
 need(len(frames)==16 and len({f['serialized_message_sha256'] for f in frames})==16,'R33_FRAMES')
 need(all([f['width'],f['height']]==[640,480] and f['frame_id']=='camera_color_optical_frame' and f['connection_id']==4 for f in frames),'R33_DIMENSIONS')
 need(r46['physical_calibration_qualified'] is False and r46['source_sha256']['my_params_camera.yaml']==sha(yaml),'R46_AUTHOR_INTEGRITY')
 need(r47['schema']=='TRUST_ROBOT_R47_TRAIN_AUTHOR_RECORDER_APPLICABILITY_V1' and r47['compatibility']['authentic_color_frames_checked']==16 and r47['compatibility']['authentic_color_dimensions']==[640,480] and r47['compatibility']['image_transport_decompression_adapter_required'] is True,'R47_RECORDING')
 need(v47['source_report_sha256']==sha(r47file) and v47['physical_calibration_qualified'] is False,'R47_INDEPENDENT')
 params=camera(yaml);points=grid();rays=rays_manual(points,params);K,d=cv_camera(params)
 uv,_=cv2.projectPoints(rays,np.zeros(3),np.zeros(3),K,d)
 reproj=np.linalg.norm(uv.reshape(-1,2)-points,axis=1)
 need(float(np.max(reproj))<1e-6,'MANUAL_INVERSE_OPENCV_FORWARD_MATCH')
 sens=sensitivity(points,rays,params)
 result={
  'schema':'TRUST_ROBOT_R48_TRAIN_INTRINSIC_PIXEL_GRID_NUMERIC_DIAGNOSTICS_V1',
  'trajectory_id':'room_02','split':'train','github_baseline':BASE,
  'authenticated_bag_sha256':BAG,
  'source_sha256':{'author_camera_yaml':sha(yaml),'recorded_r33':sha(camfile),'r46':sha(r46file),'r47':sha(r47file),'r47_independent':sha(v47file)},
  'author_calibration_source_is_physical_sensor_qualification':False,
  'synthetic_grid_only':True,'model':'PINHOLE_RADTAN_K1_K2_P1_P2_K3_ZERO',
  'camera_parameters_fx_fy_cx_cy_k1_k2_p1_p2':params,
  'recorded_frame_dimensions':[640,480],'authentic_source_frames_count':16,
  'grid_point_count':len(points),'grid':[{'pixel_xy':[float(u),float(v)],'unit_ray_camera':[float(t) for t in ray]} for (u,v),ray in zip(points,rays)],
  'manual_inverse_converged':True,'cv_projection_roundtrip_max_px':float(np.max(reproj)),
  'cv_projection_roundtrip_median_px':float(np.median(reproj)),
  'angular_sensitivity_degrees':sens,
  'qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,'raw_sensor_messages_decoded':0,
  'next_phase':'R49_TRAIN_CAMERA_MODEL_NUMERIC_DIAGNOSTIC_INDEPENDENT_EXTENSION',
  **{name:False for name in DENIED}
 }
 policy(result)
 with report.open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 lines=['# R48 — TRAIN camera intrinsic projection diagnostics','',
  'All image pixels in this experiment form a **manufactured 64-point grid** within the 640×480 dimensions authenticated by 16 recorded R33 images. Original image bytes were not opened.','',
  'Author camera parameters (fx, fy, cx, cy, k1, k2, p1, p2): '+repr(params)+'.','',
  'The numerical camera model uses a standard OpenCV pinhole Brown–Conrady radial-tangential convention with k3 fixed to zero. This is a **candidate interpretation of the author configuration**, not independent physical intrinsics validation.','',
  'Independent forward reprojection and inverse-model residual: max %.12g synthetic pixels.'%max(reproj),'',
  '## Sensitivity on the synthetic pixel grid','']
 for key,s in sens.items():lines.append('- '+key+': median %.9g°, max %.9g° angular ray change'%(s['median'],s['max']))
 lines+=['','## Restrictions','',
  'This numerical exercise does not estimate metric translation, camera motion, 6DoF pose, pose covariance, physical calibration quality, reference accuracy or cross-sensor time synchronization.',
  'The published application requires an image transport adapter for the recorded compressed topic; it is not executed here.',
  '11 scientific gates inherited from R43 remain unqualified. No ATE/RPE, health model training, real sensor factors, original bag access or confirmation_test usage.','',
  '## Next: R49','',
  'Extend the independently checked pixel/ray model with targeted model-misinterpretation and robustness controls, rather than treating numerical consistency as sensor calibration.','']
 with plan.open('x') as f:f.write('\n'.join(lines))
 print('R48_RECORDED_COLOR_SOURCE_FRAMES=16_PINNED_640x480')
 print('R48_SYNTHETIC_GRID_PIXELS=64')
 print('R48_MANUAL_INVERSE_OPENCV_FORWARD_MAX_PX=%.12g'%max(reproj))
 for key,s in sens.items():print('R48_SENSITIVITY_'+key.upper()+'_MAX_DEG=%.9g'%s['max'])
 print('R48_REAL_CAMERA_POSE_OR_PHYSICAL_CALIBRATION=NOT_QUALIFIED')

if __name__=='__main__':run(*(pathlib.Path(p) for p in sys.argv[1:8]))
