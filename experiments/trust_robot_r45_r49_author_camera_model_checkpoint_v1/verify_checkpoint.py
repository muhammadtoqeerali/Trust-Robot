"""R45–R49 frozen Git archive audit. No raw recording required."""
import ast,hashlib,json,pathlib,subprocess
A=pathlib.Path(__file__).resolve().parent
R=A.parents[1]
BASE='17536d0e9a03eb4f0b4adfb5056dc7ba63df9921'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
SPLIT='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f'
UPSTREAM='5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'
COUNTS={'r45':6,'r46':15,'r47':6,'r48':6,'r49':6}


def need(ok,reason):
 if not ok:raise ValueError('R50_ARCHIVE_DENIED:'+reason)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def load(path):return json.loads(pathlib.Path(path).read_text())
def disk(path):
 need(path.is_file() and not path.is_symlink() and path.stat().st_nlink==1 and 0<path.stat().st_size<4000000,'UNSAFE_FILE:'+str(path))
 return path.read_bytes()
def unique(pins,name):
 found=[x for x in pins if x.endswith('/'+name)]
 need(len(found)==1,'UNIQUE:'+name)
 return A/found[0]
def denied(d,keys,label):
 for key in keys:need(d.get(key) is False,label+':'+key)
def zeros(d,keys,label):
 for key in keys:need(type(d.get(key)) is int and d[key]==0,label+':'+key)

m=load(A/'checkpoint_manifest_v1.json')
need(m.get('schema')=='TRUST_ROBOT_R45_R49_AUTHOR_CAMERA_MODEL_CHECKPOINT_V1' and m.get('parent_commit')==BASE and m.get('branch')=='kios-isaacsim-v15-integration','ARCHIVE_MANIFEST')
need(m.get('trajectory_id')=='room_02' and m.get('split')=='train' and m.get('bag_sha256')==BAG and m.get('frozen_split_manifest_sha256')==SPLIT,'TRAIN')
need(m.get('phase_counts')==COUNTS and m.get('raw_rosbag_in_archive') is False and m.get('confirmation_test_accessed') is False,'SOURCE_SCOPE')
denied(m,('physical_intrinsics_qualified','physical_extrinsics_qualified','physical_clock_qualified','mocap_reference_qualified','real_sensor_factors_authorized','health_training_authorized','ate_rpe_scoring_authorized'),'MANIFEST')
zeros(m,('real_pose_factors_generated','health_labels_generated','ate_rpe_scores_generated'),'MANIFEST')
phase=m['source_artifact_sha256'];transfer=m['offline_transfer_sha256'];files=m['file_sha256']
need(len(phase)==36 and len(transfer)==3 and len(files)==40 and set(files)==set(phase)|set(transfer)|{'README.md'},'COUNTS')
need(all(files.get(k)==v for k,v in {**phase,**transfer}.items()),'PINS')
need({x:sum(p.startswith(x+'/') for p in files) for x in COUNTS}==COUNTS,'PHASE_COUNTS')
need(not any(p.is_symlink() for p in A.rglob('*')),'ARCHIVE_SYMLINK')
actual={x.relative_to(A).as_posix() for x in A.rglob('*') if x.is_file()}
need(actual==set(files)|{'checkpoint_manifest_v1.json','verify_checkpoint.py'},'EXACT_FILES')
for rel,expected in files.items():
 parts=pathlib.PurePosixPath(rel)
 need(not parts.is_absolute() and '..' not in parts.parts and len(expected)==64,'PATH')
 if rel!='README.md':need(parts.parts[0] in COUNTS and len(parts.parts) in (3,4),'PHASE_PATH')
 data=disk(A/rel)
 need(sha(data)==expected,'SHA:'+rel)
 if rel.endswith(('.py','.py.saved')):ast.parse(data,filename=rel)
 elif rel.endswith('.json'):json.loads(data)
 else:need(rel.endswith(('.md','.txt','.yaml','.b64')),'FILE_EXTENSION:'+rel)
need(sha(disk(R/'manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json'))==SPLIT,'SPLIT_FREEZE')
# Archived documents must be verified from THEIR commit, never from a newer
# worktree whose project-state and AGENTS documents may have since changed.
archivepath=(A/'checkpoint_manifest_v1.json').relative_to(R).as_posix()
commit=subprocess.check_output(['git','-C',str(R),'rev-list','-1','HEAD','--',archivepath],text=True).strip()
if commit:
 parent=subprocess.check_output(['git','-C',str(R),'rev-parse',commit+'^'],text=True).strip()
 need(parent==BASE,'GIT_COMMIT_PARENT')
expected_docs={'AGENTS.md','docs/TRUST_ROBOT_PROJECT_STATE.md','docs/audits/trust_robot/TRUST_ROBOT_KIOS_R45_R49_AUTHOR_CAMERA_MODEL_V1.md'}
need(set(m['documentation_sha256'])==expected_docs,'DOC_PATHS')
for rel,expected in m['documentation_sha256'].items():
 contents=subprocess.check_output(['git','-C',str(R),'show',commit+':'+rel]) if commit else disk(R/rel)
 need(sha(contents)==expected,'DOC_SHA:'+rel)

# Verify immutable author Git blob identity and SHA256 integrity independently.
authors={
 'calibration_results.txt':'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
 'my_params_camera.yaml':'9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
 'my_params_lidar.yaml':'a768b1a8f8baa5649009c941817a51ff3f3e00e9'
}
need(m['official_author_git_sha1']==authors,'AUTHOR_GIT_ID_LIST')
for name,gitsha in authors.items():
 content=disk(unique(phase,name))
 actualsha=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
 need(actualsha==gitsha,'AUTHOR_GIT_BLOB:'+name)
 need(sum(x.endswith('/'+name+'.lzw12.b64') for x in transfer)==1,'ENCODED_TRANSPORT:'+name)

r45=load(unique(phase,'r45_author_upstream_source_discovery_v1.json'))
v45=load(unique(phase,'r45_independent_validation_v1.json'))
r46=load(unique(phase,'r46_author_calibration_content_audit_v1.json'))
v46=load(unique(phase,'r46_independent_validation_v1.json'))
repair=load(unique(phase,'r46_independent_parser_repair_provenance_v1.json'))
r47=load(unique(phase,'r47_recorded_applicability_audit_v1.json'))
v47=load(unique(phase,'r47_independent_validation_v1.json'))
r48=load(unique(phase,'r48_numeric_projection_diagnostics_v1.json'))
v48=load(unique(phase,'r48_independent_validation_v1.json'))
r49=load(unique(phase,'r49_model_robustness_diagnostics_v1.json'))
v49=load(unique(phase,'r49_independent_validation_v1.json'))

for number,report,validation,reportname,validation_key in (
 ('45',r45,v45,'r45_author_upstream_source_discovery_v1.json','source_report_sha256'),
 ('46',r46,v46,'r46_author_calibration_content_audit_v1.json','source_report_sha256'),
 ('47',r47,v47,'r47_recorded_applicability_audit_v1.json','source_report_sha256'),
 ('48',r48,v48,'r48_numeric_projection_diagnostics_v1.json','report_sha256'),
 ('49',r49,v49,'r49_model_robustness_diagnostics_v1.json','source_report_sha256')
):
 need(validation[validation_key]==sha(disk(unique(phase,reportname))),'INDEPENDENT_LINK_R'+number)
 need(report.get('trajectory_id')=='room_02' and report.get('split')=='train','SCOPE_R'+number)
 need(report.get('github_parent',report.get('github_baseline',report.get('local_github_parent')))==BASE,'GITHUB_R'+number)
 need(report.get('bag_sha256',report.get('authenticated_bag_sha256',report.get('source_bag_sha256')))==BAG,'BAG_R'+number)

need(r45['author_repository']=='SJTU-ViSYS/M2DGR' and r45['author_repository_commit']==UPSTREAM and len(r45['upstream_candidates'])==4 and r45['unfilled_r43_source_receipts']==11,'R45_SOURCES')
need(v45['upstream_immutable_git_blob_candidates']==4 and v45['r43_missing_evidence_gate_receipts_verified']==11,'R45_INDEPENDENT')
need(r46['source_git_blobs']==authors and r46['upstream_commit']==UPSTREAM and r46['physical_calibration_qualified'] is False,'R46_AUTHOR')
for name in authors:
 need(r46['source_sha256'][name]==sha(disk(unique(phase,name))),'R46_SOURCE_SHA:'+name)
need(r46['comparisons']['realsense_intrinsics_numeric_agreement'] is True and r46['comparisons']['realsense_distortion_numeric_agreement'] is True,'R46_INTRINSICS')
need(r46['comparisons']['camera_noise_matches_xsens_scaled_10x'] is True and r46['comparisons']['handsfree_noise_lidar_config_equal'] is True,'R46_IMU_NOISE')
need(abs(r46['comparisons']['translation_difference_norm_m']-0.000241868)<1e-8,'R46_TRANSLATION_NUMERIC')
need(v46['author_git_blob_files_verified']==3 and v46['physical_calibration_authorized'] is False,'R46_INDEPENDENT')
need(repair['original_failed_reader_sha256']==sha(disk(unique(phase,'r46_independent_initial_failed_v1.py.saved'))),'REPAIR_ORIGINAL_SHA')
need(repair['repaired_reader_sha256']==sha(disk(unique(phase,'r46_independent.py'))),'REPAIR_FINAL_SHA')
need(repair['preserved_primary_report_sha256']==sha(disk(unique(phase,'r46_author_calibration_content_audit_v1.json'))),'REPAIR_REPORT_SHA')
need(repair['preserved_plan_sha256']==sha(disk(unique(phase,'r46_source_comparison_plan_v1.md'))),'REPAIR_PLAN_SHA')
denied(repair,('sensor_payload_reprocessed','source_calibration_values_modified','github_modified','physical_calibration_qualified','pose_factors_authorized'),'R46_REPAIR')
need(r47['r46_report_sha256']==sha(disk(unique(phase,'r46_author_calibration_content_audit_v1.json'))) and r47['r46_independent_sha256']==sha(disk(unique(phase,'r46_independent_validation_v1.json'))),'R47_R46_LINEAGE')
compat=r47['compatibility']
need(compat['authentic_color_frames_checked']==16 and compat['authentic_color_dimensions']==[640,480] and compat['image_transport_decompression_adapter_required'] is True,'R47_CAMERA_ADAPTER')
need(compat['camera_yaml_selected_imu_topic']==compat['lidar_yaml_selected_imu_topic_normalized']=='/handsfree/imu' and compat['camera_imu_recorded_frame_id']=='camera_imu_optical_frame' and compat['handsfree_recorded_frame_id']=='base_link','R47_IMU_FRAMES')
need(v47['verified_color_frames']==16 and v47['verified_connection_topics']==15 and v47['physical_calibration_qualified'] is False,'R47_INDEPENDENT')
need(r48['source_sha256']['r46']==sha(disk(unique(phase,'r46_author_calibration_content_audit_v1.json'))) and r48['source_sha256']['r47']==sha(disk(unique(phase,'r47_recorded_applicability_audit_v1.json'))),'R48_LINEAGE')
need(r48['grid_point_count']==len(r48['grid'])==64 and r48['synthetic_grid_only'] is True and r48['authentic_source_frames_count']==16,'R48_GRID')
need(r48['cv_projection_roundtrip_max_px']<1e-4 and v48['synthetic_grid_points_verified']==64 and v48['sensitivity_cases_rechecked']==3,'R48_MODEL')
need(r49['source_sha256']['r48_numeric_projection']==sha(disk(unique(phase,'r48_numeric_projection_diagnostics_v1.json'))),'R49_R48_LINEAGE')
need(r49['source_sha256']['r48_independent']==sha(disk(unique(phase,'r48_independent_validation_v1.json'))),'R49_R48_PROOF')
need(r49['source_sha256']['r47_recorded_applicability']==sha(disk(unique(phase,'r47_recorded_applicability_audit_v1.json'))),'R49_R47_PROOF')
need(r49['grid_points']==64 and r49['synthetic_pixel_perturbations']==256 and r49['numeric_simulation_only'] is True and r49['physical_calibration_not_established'] is True,'R49_SYNTHETIC')
need(r49['author_matrix_orientation']=='RAW_ROW_MAJOR_K_IS_TRANSPOSED_RELATIVE_TO_STANDARD_PINHOLE_K' and r49['radial_forward_map_monotonic_on_sampled_domain'] is True,'R49_MODEL')
need(r49['angular_effect_degrees']['raw_author_K_wrong_standard_intrinsics']['max']>30 and r49['angular_effect_degrees']['synthetic_half_pixel_xy']['max']<0.2,'R49_MODEL_MAGNITUDE')
need(v49['synthetic_camera_rays_replayed']==64 and v49['synthetic_pixel_perturbation_rays_replayed']==256 and v49['model_interpretation_cases_rechecked']==3,'R49_INDEPENDENT')
need(r45['r43_gate_statuses'] and len(r45['r43_gate_statuses'])==11 and all(x=='NOT_QUALIFIED' for x in r45['r43_gate_statuses'].values()),'ELEVEN_PRIOR_GATES')
need(len(r46['qualification_gates'])==11 and all(x=='NOT_QUALIFIED' for x in r46['qualification_gates'].values()),'ELEVEN_R46_GATES')
for label,report,flags in (
 ('R45',r45,('raw_bag_opened','confirmation_test_accessed','github_modified','physical_calibration_loaded','external_calibration_loaded')),
 ('R46',r46,('raw_bag_opened','confirmation_test_accessed','github_modified','physical_calibration_qualified','calibrated_sensor_factors_authorized','health_training_authorized','m2dgr_scoring_authorized')),
 ('R47',r47,('raw_bag_reopened','confirmation_test_accessed','github_modified','real_pose_factors_authorized','health_training_authorized','ate_rpe_scoring_authorized')),
 ('R48',r48,('raw_bag_reopened','confirmation_test_accessed','github_modified','physical_camera_intrinsics_qualified','pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized')),
 ('R49',r49,('raw_bag_reopened','confirmation_test_accessed','github_modified','physical_camera_intrinsics_qualified','pose_factors_authorized','health_training_authorized','m2dgr_scoring_authorized'))
):
 # Some older reports have narrower vocabularies; only inspect their declared keys.
 denied(report,tuple(k for k in flags if k in report),label)
for label,report in (('R45',r45),('R46',r46),('R47',r47),('R48',r48),('R49',r49)):
 zeros(report,tuple(k for k in ('qualified_pose_factors','real_pose_factors_generated','health_labels','health_labels_generated','ate_rpe_scores','ate_rpe_scores_generated') if k in report),label)
print('R45_R49_ARCHIVE_STANDALONE_VERIFIER=PASS')
print('R45_R49_FROZEN_ARTIFACT_SHA256=39_VERIFIED')
print('R45_R49_UPSTREAM_AUTHOR_GIT_BLOBS=3_VERIFIED')
print('R45_R49_R46_ORIGINAL_FAILURE_AND_REPAIR=PRESERVED')
print('R45_R49_INDEPENDENT_REPORT_LINEAGE=5_VERIFIED')
print('R45_R49_SYNTHETIC_CAMERA_RAYS=64_VERIFIED')
print('R45_R49_SYNTHETIC_PIXEL_PERTURBATIONS=256_VERIFIED')
print('R45_R49_COMMIT_SCOPED_DOCUMENTATION=VERIFIED')
print('R45_R49_RAW_SENSOR_BAG_IN_GIT=NO')
print('R45_R49_REAL_POSE_FACTORS_HEALTH_SCORING=DENIED')
