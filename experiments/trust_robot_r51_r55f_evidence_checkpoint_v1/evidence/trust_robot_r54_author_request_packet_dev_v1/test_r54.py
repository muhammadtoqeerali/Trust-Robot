import ast,copy,pathlib,sys
import r54_packet as m
root=pathlib.Path(sys.argv[1]);files=list(root.glob('*.py'))
assert len(files)==3
for f in files:ast.parse(f.read_text(),filename=str(f))
gates=tuple('gate_'+str(i) for i in range(11));base=m.inventory();track=m.expected_tracker(gates)
m.policy(base,track,gates)
count=0
def deny(inv,tracker,label):
 global count
 try:m.policy(inv,tracker,gates)
 except ValueError:count+=1
 else:raise AssertionError('UNSAFE_ACCEPTED:'+label)
for key in ('official_readme_bytes_verified_on_kios','downloaded_gt_sha256_verified','reference_frame_origin_verified','reference_clock_semantics_verified','reference_rotations_validated','physical_source_received','external_network_used','github_modified','original_bag_opened','confirmation_test_accessed','independent_calibration_admitted','reference_scoring_authorized','physical_clock_qualified'):
 p=copy.deepcopy(base);p[key]=True;deny(p,track,key)
for key in ('new_external_source_files','qualified_pose_factors','health_labels','ate_rpe_scores'):
 p=copy.deepcopy(base);p[key]=1;deny(p,track,key)
for key,value in [('trajectory_id','room_03'),('split','confirmation_test'),('github_parent','0'*40),('raw_bag_sha256','0'*64),('author_commit','0'*40),('author_readme_git_blob_sha1','0'*40),('official_readme_lists_room_02_gt_candidate_url','https://evil.invalid/gt'),('reference_sha256_from_frozen_r43','0'*64),('published_link_status','VERIFIED_GT'),('reference_local_content_status','QUALIFIED'),('next_phase','RUN_SCORING')]:
 p=copy.deepcopy(base);p[key]=value;deny(p,track,key)
for kind in m.KINDS:
 p=copy.deepcopy(track);p['sensor_receipts'][kind]['qualification_authorized']=True;deny(base,p,'receipts:'+kind)
for key in ('external_material_acquired','published_link_is_downloaded_content','physical_source_received','physical_qualification_authorized'):
 p=copy.deepcopy(track);p[key]=True;deny(base,p,'tracker:'+key)
assert count==37,count
print('R54_PYTHON_AST=3_PASS')
print('R54_NEGATIVE_SOURCE_AUTHENTICATION_AND_ADMISSION_CONTROLS=37_REJECTED')
