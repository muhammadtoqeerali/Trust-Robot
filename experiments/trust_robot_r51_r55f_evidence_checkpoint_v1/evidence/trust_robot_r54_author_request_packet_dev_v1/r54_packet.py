"""R54: register author-published reference link as candidate; do not fetch it.

All external links are source *leads* and not physically verified material.
"""
import hashlib,json,pathlib,sys,urllib.parse
BASE='58e23861811e51c5d00f00f5d22e5cb561c4b43a'
BAG='ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1'
UPSTREAM='5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5'
README_BLOB='c394994a8431426c0bd4b3dcf618faf7b97d119f'
GT_SHA='79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d'
GT_URL='https://sjtueducn-my.sharepoint.com/:t:/g/personal/594666_sjtu_edu_cn/ES-9QFWKEeBNqxyMv5dJe7EB5YxfTzi8v3x2Hf1aLObnAg?e=ifwPHL'
README_URL='https://github.com/SJTU-ViSYS/M2DGR/blob/'+UPSTREAM+'/README.md'
SITE_URL='https://sjtu-visys.github.io/M2DGR/'
SCHEMA='TRUST_ROBOT_R54_AUTHOR_SOURCE_CANDIDATE_REQUEST_PACKET_V1'
KINDS=('camera_color','camera_imu','handsfree_imu','velodyne_lidar','mocap_reference')
GENERAL=('source_document_uri','source_sha256','original_publisher_and_version','device_model_and_serial_or_export_identifier','capture_event_definition','header_stamp_timebase_and_epoch','clock_mapping_method_and_parameters','clock_offset_and_drift_uncertainty','independent_validation_source_sha256','room_02_applicability_evidence_sha256')
REF=('mocap_export_file_sha256','mocap_tracked_body_origin_definition','mocap_to_lidar_transform_and_direction','reference_timestamp_export_semantics','invalid_rotation_resolution_evidence_sha256')

def need(ok,label):
 if not ok:raise ValueError('R54_DENIED:'+label)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def expected_tracker(gates):
 return {'schema':'TRUST_ROBOT_R54_UNFILLED_SOURCE_ACQUISITION_TRACKER_V1',
 'trajectory_id':'room_02','split':'train','external_material_acquired':False,
 'published_link_is_downloaded_content':False,'physical_source_received':False,
 'physical_qualification_authorized':False,
 'sensor_receipts':{name:{'status':'UNFILLED_AWAITING_SOURCE','file_path':None,
  'download_sha256':None,'independent_validation_sha256':None,'received_from':None,
  'room_02_hardware_applicability_verified':False,'clock_and_frame_semantics_verified':False,
  'qualification_authorized':False} for name in KINDS},
 'original_gate_receipts':{key:{'status':'UNCHANGED_NOT_QUALIFIED','source_sha256':None,
   'independent_validation_sha256':None,'admission_authorized':False}
   for key in sorted(gates)}}
def inventory():
 return {'schema':SCHEMA,'trajectory_id':'room_02','split':'train',
 'github_parent':BASE,'raw_bag_sha256':BAG,
 'author_repository':'SJTU-ViSYS/M2DGR','author_commit':UPSTREAM,
 'author_readme_git_blob_sha1':README_BLOB,'author_readme_at_commit_url':README_URL,
 'author_dataset_website':SITE_URL,
 'official_readme_lists_room_02_gt_candidate_url':GT_URL,
 'reference_sha256_from_frozen_r43':GT_SHA,
 'published_link_status':'DISCOVERED_IN_AUTHOR_README_NOT_FETCHED_ON_KIOS',
 'reference_local_content_status':'NOT_ACQUIRED',
 'official_readme_bytes_verified_on_kios':False,
 'downloaded_gt_sha256_verified':False,
 'reference_frame_origin_verified':False,
 'reference_clock_semantics_verified':False,
 'reference_rotations_validated':False,
 'physical_source_received':False,
 'external_network_used':False,'github_modified':False,
 'original_bag_opened':False,'confirmation_test_accessed':False,
 'new_external_source_files':0,'qualified_pose_factors':0,
 'health_labels':0,'ate_rpe_scores':0,
 'independent_calibration_admitted':False,
 'reference_scoring_authorized':False,'physical_clock_qualified':False,
 'next_phase':'R55_OFFICIAL_ROOM_02_GT_ACQUISITION_AND_SHA_VERIFICATION'}
def policy(inv,tracker,gates):
 need(inv==inventory(),'INVENTORY_EXACT')
 url=urllib.parse.urlparse(inv['official_readme_lists_room_02_gt_candidate_url'])
 need(url.scheme=='https' and url.hostname=='sjtueducn-my.sharepoint.com' and '/:t:/' in url.path,'GT_HOST')
 need(urllib.parse.urlparse(inv['author_readme_at_commit_url']).hostname=='github.com','AUTHOR_HOST')
 need(tracker==expected_tracker(gates),'EMPTY_RECEIPTS_11_AND_5')

def build(splitp,r43p,empty43p,r53p,empty53p,plan53p,v53p,invp,packetp,trackp):
 p={'split':splitp,'r43':r43p,'r43_unfilled':empty43p,'r53':r53p,'r53_unfilled':empty53p,'r53_plan':plan53p,'r53_validation':v53p}
 need(all(path.is_file() and not path.is_symlink() for path in p.values()),'SOURCE_MISSING')
 need(sha(splitp)=='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f','SPLIT')
 r43,r53,empty43,empty53,v53=map(read,(r43p,r53p,empty43p,empty53p,v53p))
 split=read(splitp)
 room=[x for x in split['records'] if x['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['split']=='train' and sum(x['split']=='confirmation_test' for x in split['records'])==7,'SEALED_SPLIT')
 need(r43['raw_reference_provenance_sha256']==GT_SHA and r43['room_02_reference_invalid_rotations']==90 and r43['unresolved_gate_count']==11 and r43['source_acquisition_status']=='NOT_ACQUIRED','R43_REFERENCE')
 gates=set(r43['requests'])
 need(len(gates)==11 and gates==set(empty43['gate_receipts']) and all(x['status']=='NOT_QUALIFIED' and not x['physical_validation_completed'] for x in r43['requests'].values()),'R43_GATES')
 need(not empty43['source_data_present'] and all(x['status']=='NO_SOURCE_RECEIVED' and x['source_uri'] is None and x['source_sha256'] is None for x in empty43['gate_receipts'].values()),'R43_EMPTY')
 need(r53['receipt_policy']=='SOURCE_INTAKE_ONLY_ZERO_PHYSICAL_ADMISSION' and r53['admission_decision']=='DENIED_UNFILLED_SOURCE_RECEIPTS' and r53['frozen_observed_timestamp_count']==48 and r53['camera_imu_negative_record_minus_header_count']==9 and r53['reference_invalid_rotation_count']==90,'R53_POLICY')
 need(r53['receipt_schema_sha256']==sha(empty53p) and r53['github_parent']==BASE and r53['original_r43_receipts_unchanged'] is True,'R53_BINDING')
 need(v53['source_report_sha256']==sha(r53p) and v53['source_receipts_sha256']==sha(empty53p) and v53['request_plan_sha256']==sha(plan53p) and v53['independently_empty_physical_receipts']==5 and v53['r43_empty_gates_verified']==11,'R53_INDEPENDENT')
 need(not empty53['source_data_present'] and set(empty53['receipts'])==set(KINDS),'R53_EMPTY_INVENTORY')
 for name,entry in empty53['receipts'].items():
  required=set(GENERAL)|(set(REF) if name=='mocap_reference' else set())
  need(entry['status']=='NO_PHYSICAL_SOURCE_RECEIVED' and entry['physical_measurement_qualified'] is False and entry['independently_validated'] is False and set(entry['fields'])==required and all(v is None for v in entry['fields'].values()),'R53_NULL:'+name)
 need(all(s['verification_status']=='unverified' and s['fixed_offset_seconds'] is None and s['tolerance_seconds'] is None for s in room[0]['synchronization']),'CLOCKS')
 inv=inventory();inv['frozen_local_sha256']={k:sha(path) for k,path in p.items()}
 tracker=expected_tracker(gates)
 policy({k:v for k,v in inv.items() if k!='frozen_local_sha256'},tracker,gates)
 with invp.open('x') as h:json.dump(inv,h,sort_keys=True,indent=2);h.write('\n')
 with trackp.open('x') as h:json.dump(tracker,h,sort_keys=True,indent=2);h.write('\n')
 lines=[
 '# M2DGR `room_02` source provenance / timing request — draft, not sent',
 '',
 '**Status:** Source request only. No email or GitHub issue was posted. No external ground-truth file was acquired, parsed, or qualified.',
 '',
 '## First actionable public lead (still unverified as local data)',
 '',
 f'- Author repository README pinned at commit `{UPSTREAM}` (Git blob SHA1 `{README_BLOB}`): {README_URL}',
 f'- Published `room_02` GT link appearing in that README: {GT_URL}',
 f'- Author dataset website: {SITE_URL}',
 f'- Expected existing raw `room_02` reference SHA256 from frozen R43: `{GT_SHA}`.',
 '- **Do not presume** the linked download matches that SHA. In R55, validate the response content type, exact bytes, SHA256, document format and correspondence to this room recording before any use.',
 '',
 '## Author-facing message (review and send manually if source provenance remains unresolved)',
 '',
 '**Subject: M2DGR room_02 — GT reference export, clock mapping and calibration provenance**',
 '',
 'Hello M2DGR team,',
 '',
 'We are conducting reproducible TRAIN-only research using the published `room_02` recording (2021-07-30) and would appreciate primary-source clarification before using sensor calibrations or computing ATE/RPE.',
 '',
 '1. Could you confirm that the `room_02` GT link in your pinned README is the correct original mocap export, and provide its canonical filename, original SHA256, format, row field meanings, quaternion ordering, coordinate handedness, units and timestamp source?',
 '2. Which physical tracked marker cluster or rigid body does the Vicon mocap pose represent? What are the tracked-body origin and the direction/units of the rigid transform from mocap body to Velodyne LiDAR and relevant robot `base_link` frame?',
 '3. Our existing source audit flags 90 invalid reference rotation rows; can you clarify the export convention, missing/invalid markers and a documented policy for these samples?',
 '4. For `/camera/color/image_raw/compressed`, `/camera/imu`, `/handsfree/imu`, and `/velodyne_points`, which physical event does `header.stamp` represent, on which hardware or host timebase, and were any time offsets/drift corrections or scan-time transformations applied in the `room_02` recording pipeline?',
 '5. Does `calibration_results.txt` and the `my_params_camera.yaml` / `my_params_lidar.yaml` published at this commit apply to the same `room_02` hardware devices and recording date? Could you provide serials, firmware, calibration version and physically validated camera/IMU/LiDAR extrinsic directions and measurement uncertainty?',
 '6. The camera application points at `/handsfree/imu` but its four IMU noise parameters numerically match 10 times the published Xsens values; please clarify intended physical IMU and parameter units. Is the published camera-to-IMU translation the intended `room_02` transform?',
 '7. Can you provide independent validation receipts for any timebase mappings, reference transform and calibration values, particularly the interpretation of the motion-capture reference export clock?',
 '',
 'We can supply a description of our source audit if useful. We will cite your official source and preserve your original files byte-for-byte.',
 '',
 'Thank you.',
 '',
 '## Required provenance for any returned evidence',
 '',
 'Keep response and downloaded files **outside Git** until authenticated. Save source URL, originating person/organization, retrieval timestamp, exact bytes SHA256, byte size, media type, hardware/trajectory applicability, author version and independent check. Reject HTML login pages and redirects as GT content. Do not interpret this request or a matching hash as sufficient physical qualification.',
 '',
 'All five R53 physical source receipts remain explicitly null; all eleven R43 qualification receipts remain empty. Four physical clock domains unverified, 90 invalid reference rotations unresolved, and the frozen 22/7/7 split (including sealed confirmation_test) remains unchanged.',
 '',
 '## Next: R55',
 '',
 'Attempt controlled acquisition of only the published `room_02` GT candidate, never the raw rosbag or confirmation_test; compare against the expected reference SHA256. If inaccessible, record a transport failure and use this request packet, without fabricating a reference.',
 ''
 ]
 with packetp.open('x') as h:h.write('\n'.join(lines))
 print('R54_AUTHOR_PUBLISHED_ROOM_02_GT_LINK=DISCOVERED_NOT_DOWNLOADED')
 print('R54_AUTHOR_README_GIT_BLOB=c394994a8431426c0bd4b3dcf618faf7b97d119f')
 print('R54_EXPECTED_REFERENCE_SHA256='+GT_SHA)
 print('R54_FIVE_SOURCE_RECEIPTS=STILL_UNFILLED')
 print('R54_ELEVEN_R43_GATES=STILL_CLOSED')
 print('R54_AUTHOR_FACING_PACKET=DRAFT_NOT_SENT')
 print('R54_NETWORK_DOWNLOADS=0')
if __name__=='__main__':build(*(pathlib.Path(x) for x in sys.argv[1:11]))
