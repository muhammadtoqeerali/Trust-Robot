"""Synthetic camera-ray model misinterpretation and subpixel perturbation checks.
No images, raw bag, metric motion or calibration admission.
"""
import hashlib,json,math,pathlib,re,statistics,sys
import numpy as np

BASE='17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
CLOSED=(
 'physical_camera_intrinsics_qualified','complete_sensor_extrinsics_qualified',
 'physical_capture_time_verified','independent_metric_scale_established',
 'pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized',
 'confirmation_test_accessed','raw_bag_reopened','github_modified')
ZERO=('qualified_pose_factors','health_labels','ate_rpe_scores','raw_sensor_messages_decoded')
MODEL='PINHOLE_RADTAN_K1_K2_P1_P2_K3_ZERO'

def need(ok,k):
 if not ok:raise ValueError('R49_DENIED:'+k)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def numeric(s,k):
 arr=re.findall(r'(?m)^\s*'+re.escape(k)+r':\s*([-+\d.eE]+)(?=\s|#|$)',s)
 need(len(arr)==1,'YAML:'+k)
 return float(arr[0])
def stats(values):
 v=[float(x) for x in values]
 need(len(v)>0 and all(math.isfinite(x) for x in v),'NONFINITE_STATS')
 return {'min':float(min(v)),'median':float(statistics.median(v)),'max':float(max(v))}
def angle(a,b):
 return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=-1),np.sum(a*b,axis=-1)))
def make_rays(px,params,with_dist=True):
 fx,fy,cx,cy,k1,k2,p1,p2=params
 need(fx>0 and fy>0 and len(px)>0,'MODEL_SCALE')
 xd=(px[:,0]-cx)/fx;yd=(px[:,1]-cy)/fy
 x=xd.copy();y=yd.copy()
 if with_dist:
  for iteration in range(100):
   r2=x*x+y*y
   radial=1+k1*r2+k2*r2*r2
   need(bool(np.all(radial>0.5)),'RADIAL_FACTOR')
   tx=2*p1*x*y+p2*(r2+2*x*x)
   ty=p1*(r2+2*y*y)+2*p2*x*y
   xx=(xd-tx)/radial; yy=(yd-ty)/radial
   err=max(float(np.max(abs(xx-x))),float(np.max(abs(yy-y))))
   x=xx;y=yy
   if err<1e-14:break
  need(err<1e-12,'UNDISTORT_CONVERGENCE')
 ray=np.column_stack((x,y,np.ones(len(x))))
 return ray/np.linalg.norm(ray,axis=1)[:,None]

def raw_author_K(path):
 text=path.read_text()
 sect=re.search(r'(?m)^%%\s*Cam-pinhole-color realsense d435i\s*$',text)
 need(sect is not None,'OFFICIAL_CALIB_SECTION')
 tail=text[sect.end():]
 boundary=re.search(r'(?m)^%%\s+',tail)
 if boundary:tail=tail[:boundary.start()]
 values=re.findall(r'\bdata\s*:\s*\[([^\]]+)\]',tail,re.S)
 need(len(values)==4,'OFFICIAL_CALIB_ARRAYS')
 nums=lambda x:[float(n) for n in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?',x)]
 arrays=list(map(nums,values))
 need([len(a) for a in arrays]==[16,9,4,2],'OFFICIAL_CALIB_SHAPES')
 return np.asarray(arrays[1],dtype=np.float64).reshape(3,3),arrays[2],arrays[3]

def policy(r):
 need(r.get('schema')=='TRUST_ROBOT_R49_TRAIN_CAMERA_MODEL_INTERPRETATION_AND_NOISE_DIAGNOSTICS_V1' and r.get('trajectory_id')=='room_02' and r.get('split')=='train' and r.get('github_baseline')==BASE and r.get('authenticated_bag_sha256')==BAG,'TRAIN_SCOPE')
 need(r.get('model')==MODEL and r.get('grid_points')==64 and r.get('synthetic_pixel_perturbations')==256 and r.get('source_recorded_frame_count_dimensions_only')==16,'GRID_SCOPE')
 need(r.get('physical_calibration_not_established') is True and r.get('numeric_simulation_only') is True,'PHYSICAL_GATE')
 need(all(r.get(k) is False for k in CLOSED),'NO_AUTHORIZATION')
 need(all(type(r.get(k)) is int and r[k]==0 for k in ZERO),'NO_SCIENCE_COUNTS')
 need(r.get('author_matrix_orientation')=='RAW_ROW_MAJOR_K_IS_TRANSPOSED_RELATIVE_TO_STANDARD_PINHOLE_K','AUTHOR_MATRIX_LAYOUT')
 need(r.get('raw_matrix_standard_K_interpretation_is_rejected') is True,'WRONG_INTRINSIC_REJECTION')
 need(r.get('numeric_inverse_verified_against_R48') is True and r.get('radial_forward_map_monotonic_on_sampled_domain') is True,'MODEL_CONDITIONING')
 s=r.get('angular_effect_degrees',{})
 need(set(s)=={'ignore_distortion','raw_author_K_wrong_standard_intrinsics','synthetic_half_pixel_xy'},'ANGULAR_CASES')
 need(all(set(x)=={'min','median','max'} and 0<=x['min']<=x['median']<=x['max']<90 for x in s.values()),'ANGULAR_FINITE')
 need(s['raw_author_K_wrong_standard_intrinsics']['max']>10 and s['ignore_distortion']['max']>0 and 0<s['synthetic_half_pixel_xy']['max']<0.2,'INTERPRETATION_DIAGNOSTIC')
 need(r.get('radial_jacobian_min') is not None and 0<r['radial_jacobian_min']<=1.5,'RADIAL_JACOBIAN')
 need(r.get('next_phase')=='R50_GUARDED_R45_R49_GITHUB_CHECKPOINT','NEXT_PHASE')

def run(author,yaml,r48p,v48p,r46p,r47p,report,plan):
 r48=load(r48p);v48=load(v48p);r46=load(r46p);r47=load(r47p)
 need(r48['schema']=='TRUST_ROBOT_R48_TRAIN_INTRINSIC_PIXEL_GRID_NUMERIC_DIAGNOSTICS_V1' and r48['trajectory_id']=='room_02' and r48['split']=='train' and r48['authenticated_bag_sha256']==BAG and r48['github_baseline']==BASE,'R48_SCOPE')
 need(v48['report_sha256']==sha(r48p) and v48['synthetic_grid_points_verified']==64 and v48['physical_calibration_qualified'] is False,'R48_INDEPENDENCE')
 need(r48['source_sha256']['author_camera_yaml']==sha(yaml) and r48['source_sha256']['r46']==sha(r46p) and r48['source_sha256']['r47']==sha(r47p),'R48_LINKS')
 need(r46['physical_calibration_qualified'] is False and r46['source_sha256']['calibration_results.txt']==sha(author),'R46_SOURCE')
 need(r47['compatibility']['authentic_color_frames_checked']==16 and r47['compatibility']['image_transport_decompression_adapter_required'] is True and r47['compatibility']['camera_intrinsics_sensor_identity_physically_qualified'] is False,'R47_SCOPE')
 need(r48['grid_point_count']==64 and len(r48['grid'])==64 and r48['synthetic_grid_only'] is True,'R48_SYNTHETIC')
 need(all(r48[k] is False for k in CLOSED),'R48_GATES')
 params=[numeric(yaml.read_text(),k) for k in ('fx','fy','cx','cy','k1','k2','p1','p2')]
 need(np.max(np.abs(np.asarray(params)-np.asarray(r48['camera_parameters_fx_fy_cx_cy_k1_k2_p1_p2'])))<1e-12,'CAMERA_PARAM_BIND')
 need([int(numeric(yaml.read_text(),k)) for k in ('image_width','image_height')]==[640,480],'FRAME_DIMENSIONS')
 px=np.asarray([g['pixel_xy'] for g in r48['grid']],dtype=np.float64)
 expected=np.asarray([[639.0*i/8,479.0*j/6] for j in range(7) for i in range(9)]+[[params[2],params[3]]])
 need(np.max(abs(px-expected))<1e-12,'SYNTHETIC_GRID')
 need(np.all((px[:,0]>=0)&(px[:,0]<640)&(px[:,1]>=0)&(px[:,1]<480)),'IMAGE_BOUNDS')
 rays=make_rays(px,params)
 baseline=np.asarray([g['unit_ray_camera'] for g in r48['grid']],dtype=np.float64)
 consistency=angle(rays,baseline)
 need(float(np.max(consistency))<1e-6,'INVERSE_TO_R48')
 Kraw,dist,dimensions=raw_author_K(author)
 fx,fy,cx,cy,k1,k2,p1,p2=params
 Kstandard=np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],dtype=np.float64)
 need(np.max(abs(Kraw.T-Kstandard))<1e-9,'AUTHOR_TRANSPOSED_K')
 need(np.max(abs(np.asarray(dist)-np.asarray([k1,k2,p1,p2])))<1e-12 and dimensions==[640,480],'AUTHOR_DISTORTION')
 radial_r2=rays[:,0]**2/rays[:,2]**2+rays[:,1]**2/rays[:,2]**2
 derivative=1+3*k1*radial_r2+5*k2*radial_r2**2
 need(float(np.min(derivative))>0,'RADIAL_MONOTONICITY')
 no_dist=make_rays(px,params,False)
 # Simulates mistakenly taking author's 3x3 flattened array as a standard row-major OpenCV K;
 # that would set cx=cy=0, rather than using Kraw.T.
 wrong_intr=[fx,fy,float(Kraw[0,2]),float(Kraw[1,2]),k1,k2,p1,p2]
 need(wrong_intr[2]==0 and wrong_intr[3]==0,'WRONG_K_MODEL')
 # Isolate the matrix-layout mistake on the same ideal (already undistorted) image pixels.
 # Applying this bad K together with radial inversion can be non-invertible at the corners.
 ideal=np.column_stack((fx*rays[:,0]/rays[:,2]+cx,fy*rays[:,1]/rays[:,2]+cy))
 wrong_rays=make_rays(ideal,wrong_intr,False)
 offsets=[(-.5,-.5),(-.5,.5),(.5,-.5),(.5,.5)]
 jitter_errors=[]
 for dx,dy in offsets:
  perturbed=px+np.asarray([dx,dy])
  jitter_errors.extend(float(z) for z in angle(rays,make_rays(perturbed,params)))
 s={'ignore_distortion':stats(angle(rays,no_dist)),
    'raw_author_K_wrong_standard_intrinsics':stats(angle(rays,wrong_rays)),
    'synthetic_half_pixel_xy':stats(jitter_errors)}
 r={
  'schema':'TRUST_ROBOT_R49_TRAIN_CAMERA_MODEL_INTERPRETATION_AND_NOISE_DIAGNOSTICS_V1',
  'trajectory_id':'room_02','split':'train','github_baseline':BASE,'authenticated_bag_sha256':BAG,
  'source_sha256':{'author_calibration_results':sha(author),'author_camera_yaml':sha(yaml),
                   'r46_author_audit':sha(r46p),'r47_recorded_applicability':sha(r47p),
                   'r48_numeric_projection':sha(r48p),'r48_independent':sha(v48p)},
  'model':MODEL,'grid_points':64,'synthetic_pixel_perturbations':256,
  'source_recorded_frame_count_dimensions_only':16,
  'camera_parameters_fx_fy_cx_cy_k1_k2_p1_p2':params,
  'author_matrix_orientation':'RAW_ROW_MAJOR_K_IS_TRANSPOSED_RELATIVE_TO_STANDARD_PINHOLE_K',
  'raw_matrix_standard_K_interpretation_is_rejected':True,
  'numeric_inverse_verified_against_R48':True,
  'max_ray_replay_difference_deg':float(np.max(consistency)),
  'radial_forward_map_monotonic_on_sampled_domain':True,
  'radial_jacobian_min':float(np.min(derivative)),
  'radial_jacobian_max':float(np.max(derivative)),
  'angular_effect_degrees':s,
  'synthetic_offsets_px':[[float(a),float(b)] for a,b in offsets],
  'physical_calibration_not_established':True,'numeric_simulation_only':True,
  'qualified_pose_factors':0,'health_labels':0,'ate_rpe_scores':0,'raw_sensor_messages_decoded':0,
  'next_phase':'R50_GUARDED_R45_R49_GITHUB_CHECKPOINT',
  **{k:False for k in CLOSED}
 }
 policy(r)
 with report.open('x') as f:json.dump(r,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 lines=[
  '# R49 — Synthetic camera-model interpretation and subpixel robustness', '',
  'Only 64 R48 manufactured pixels and author Git-verified camera model coefficients were used; the 16 recorded R33 frames provide dimensions only. No original sensor image or recording bytes were read.', '',
  'Author-supplied 3x3 intrinsic matrix appears transposed relative to conventional OpenCV row-major K. Treating raw flattened values as conventional K moves the principal point to (0,0) and yields a substantial **model interpretation error**, not a measured sensor error.', '',
  '## Numerical effects (angular ray differences only)', ''
 ]
 for name,value in s.items():lines.append('- '+name+': median %.9g degrees, maximum %.9g degrees.'%(value['median'],value['max']))
 lines += ['','Radial forward model Jacobian on sampled domain: minimum %.9g, maximum %.9g (positive implies local radial monotonicity here only).'%(min(derivative),max(derivative)),'',
  'Synthetic pixel-noise assumption: four deterministic ±0.5 px offsets per point, 256 numerical ray comparisons. These are not recorded tracking errors, camera calibration residuals, or covariance measurements.','',
  '## Scientific restrictions','',
  '**NOT QUALIFIED:** Camera model consistency and robustness checks do **not** establish room_02 physical intrinsics, real pose accuracy, physical timing, metric scale, valid cross-sensor extrinsics, or health supervision. Source author intrinsics are candidate parameters. 11 R43 physical admission gates remain closed. No ATE/RPE or confirmation_test use.','',
  '## Next R50','',
  'SHA-pinned guarded archival of R45–R49, including original and repaired R46 independent verifier and three exact author calibration source files. GitHub commit and push only after complete independent checkpoint verification.',''
 ]
 with plan.open('x') as f:f.write('\n'.join(lines))
 print('R49_R48_SYNTHETIC_PIXEL_GRID=64_RAYS_REPLAY_MATCH')
 print('R49_RADIAL_FORWARD_MAP_JACOBIAN_MIN=%.9g'%min(derivative))
 print('R49_NO_DISTORTION_MAX_RAY_DIFFERENCE_DEG=%.9g'%s['ignore_distortion']['max'])
 print('R49_MISREAD_AUTHOR_K_MAX_RAY_DIFFERENCE_DEG=%.9g'%s['raw_author_K_wrong_standard_intrinsics']['max'])
 print('R49_FOUR_HALF_PIXEL_OFFSETS=256_SYNTHETIC_RAYS')
 print('R49_HALF_PIXEL_OFFSET_MAX_RAY_DIFFERENCE_DEG=%.9g'%s['synthetic_half_pixel_xy']['max'])
 print('R49_PHYSICAL_CALIBRATION_AND_REAL_SENSOR_FACTORS=DENIED')

if __name__=='__main__':run(*(pathlib.Path(p) for p in sys.argv[1:9]))
