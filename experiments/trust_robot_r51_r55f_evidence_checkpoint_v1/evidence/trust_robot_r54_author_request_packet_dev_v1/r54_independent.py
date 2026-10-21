"""Independent verification without network, Git mutation or source fetching."""
import hashlib,json,pathlib,sys,urllib.parse
BASE='58e23861811e51c5d00f00f5d22e5cb561c4b43a'
README='c394994a8431426c0bd4b3dcf618faf7b97d119f'
UPSTREAM='5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'
GT_SHA='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
KINDS={'camera_color','camera_imu','handsfree_imu','velodyne_lidar','mocap_reference'}

def need(ok,msg):
 if not ok:raise ValueError('R54_INDEPENDENT_DENIED:'+msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def run(splitp,r43p,oldp,r53p,receipts53p,plan53p,validate53p,invp,packetp,trackp,proofp):
 inputs={'split':splitp,'r43':r43p,'r43_unfilled':oldp,'r53':r53p,'r53_unfilled':receipts53p,'r53_plan':plan53p,'r53_validation':validate53p}
 inv,track=read(invp),read(trackp)
 r43,r53,original,receipts53=map(read,(r43p,r53p,oldp,receipts53p))
 need(inv['frozen_local_sha256']=={k:sha(p) for k,p in inputs.items()},'FROZEN_SOURCE_LINEAGE')
 need(inv['author_repository']=='SJTU-ViSYS/M2DGR' and inv['author_commit']==UPSTREAM and inv['author_readme_git_blob_sha1']==README,'AUTHOR_ID')
 need(inv['author_readme_at_commit_url']=='https://github.com/SJTU-ViSYS/M2DGR/blob/'+UPSTREAM+'/README.md','PINNED_README')
 gt=inv['official_readme_lists_room_02_gt_candidate_url'];u=urllib.parse.urlparse(gt)
 need(u.scheme=='https' and u.hostname=='sjtueducn-my.sharepoint.com' and u.path.startswith('/:t:/g/personal/') and gt.endswith('?e=ifwPHL'),'AUTHOR_GT_URL_SHAPE')
 need(inv['reference_sha256_from_frozen_r43']==GT_SHA==r43['raw_reference_provenance_sha256'],'REFERENCE_HASH')
 need(inv['trajectory_id']=='room_02' and inv['split']=='train' and inv['github_parent']==BASE,'SCOPE')
 need(inv['published_link_status']=='DISCOVERED_IN_AUTHOR_README_NOT_FETCHED_ON_KIOS' and inv['reference_local_content_status']=='NOT_ACQUIRED','CANDIDATE_NOT_PHYSICAL_EVIDENCE')
 for key in ('official_readme_bytes_verified_on_kios','downloaded_gt_sha256_verified','reference_frame_origin_verified','reference_clock_semantics_verified','reference_rotations_validated','physical_source_received','external_network_used','github_modified','original_bag_opened','confirmation_test_accessed','independent_calibration_admitted','reference_scoring_authorized','physical_clock_qualified'):
  need(inv.get(key) is False,'NO_SCIENTIFIC_PROMOTION:'+key)
 for key in ('new_external_source_files','qualified_pose_factors','health_labels','ate_rpe_scores'):
  need(type(inv.get(key)) is int and inv[key]==0,'ZERO:'+key)
 need(inv['next_phase']=='R55_OFFICIAL_ROOM_02_GT_ACQUISITION_AND_SHA_VERIFICATION','NEXT')
 need(len(r43['requests'])==11 and set(track['original_gate_receipts'])==set(r43['requests']),'R43_GATES')
 need(set(track['sensor_receipts'])==KINDS and set(receipts53['receipts'])==KINDS,'R53_SOURCES')
 need(track['external_material_acquired'] is False and track['published_link_is_downloaded_content'] is False and track['physical_source_received'] is False and track['physical_qualification_authorized'] is False,'TRACKER_EMPTY')
 for name,x in track['sensor_receipts'].items():
  need(x['status']=='UNFILLED_AWAITING_SOURCE' and x['file_path'] is None and x['download_sha256'] is None and x['independent_validation_sha256'] is None and x['received_from'] is None and x['room_02_hardware_applicability_verified'] is False and x['clock_and_frame_semantics_verified'] is False and x['qualification_authorized'] is False,'UNFILLED:'+name)
  old=receipts53['receipts'][name]
  need(old['status']=='NO_PHYSICAL_SOURCE_RECEIVED' and all(v is None for v in old['fields'].values()),'R53_RECEIPT_UNCHANGED:'+name)
 for key,x in track['original_gate_receipts'].items():
  need(x['status']=='UNCHANGED_NOT_QUALIFIED' and x['source_sha256'] is None and x['independent_validation_sha256'] is None and x['admission_authorized'] is False,'R43_GATE:'+key)
  need(original['gate_receipts'][key]['status']=='NO_SOURCE_RECEIVED','R43_ORIGINAL_NOT_CHANGED')
 need(r53['frozen_observed_timestamp_count']==48 and r53['camera_imu_negative_record_minus_header_count']==9 and r53['reference_invalid_rotation_count']==90 and r53['admission_decision']=='DENIED_UNFILLED_SOURCE_RECEIPTS','TIMING_REFERENCE')
 need(all(s['verification_status']=='unverified' for item in read(splitp)['records'] if item['trajectory_id']=='room_02' for s in item['synchronization']),'CLOCK_NOT_VERIFIED')
 doc=packetp.read_text()
 need('**Status:** Source request only' in doc and gt in doc and GT_SHA in doc and '90 invalid reference rotations' in doc and 'draft, not sent' in doc and 'R55' in doc,'REQUEST_PACKET')
 proof={'schema':'TRUST_ROBOT_R54_INDEPENDENT_PUBLISHED_REFERENCE_CANDIDATE_VERIFICATION_V1',
 'inventory_sha256':sha(invp),'author_request_packet_sha256':sha(packetp),'acquisition_tracker_sha256':sha(trackp),
 'frozen_inputs_sha256':inv['frozen_local_sha256'],'gt_published_link_verified_in_packet':True,
 'gt_file_fetched_or_authenticated':False,'r53_empty_physical_receipts_verified':5,
 'r43_unqualified_source_gates_verified':11,'frozen_timestamp_evidence_count':48,
 'reference_invalid_rotation_count':90,'original_bag_opened':False,
 'confirmation_test_accessed':False,'github_modified':False,'science_admission':False}
 with proofp.open('x') as h:json.dump(proof,h,sort_keys=True,indent=2);h.write('\n')
 print('R54_INDEPENDENT_SOURCE_HASH_LINEAGE=7_MATCH')
 print('R54_INDEPENDENT_PUBLISHED_GT_URL=CANDIDATE_ONLY')
 print('R54_INDEPENDENT_PHYSICAL_RECEIPTS=5_EMPTY')
 print('R54_INDEPENDENT_R43_GATES=11_CLOSED')
 print('R54_INDEPENDENT_VALIDATION=PASS')
if __name__=='__main__':run(*(pathlib.Path(x) for x in sys.argv[1:12]))
