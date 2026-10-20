"""Independently verify R43 immutable source inventory, empty receipts and science gates."""
import hashlib,json,pathlib,subprocess,sys
import r43_protocol as p

def need(ok,reason):
 if not ok:raise ValueError('R43_INDEPENDENT_DENIED:'+reason)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def load(path):return json.loads(pathlib.Path(path).read_text())

def verify(repo,r39p,r40p,r41p,r42p,v42p,reportp,receiptp,planp,out):
 report=load(reportp);receipts=load(receiptp)
 p.policy(report,receipts)
 need(report['unresolved_gate_count']==11 and receipts['source_data_present'] is False,'NO_ACQUISITION')
 originals={'r39':r39p,'r40':r40p,'r41':r41p,'r42':r42p,'r42_independent':v42p}
 for name,file in originals.items():need(report['upstream_report_sha256'][name]==sha(file.read_bytes()),'UPSTREAM_SHA:'+name)
 prior=load(r42p)
 need(prior['connection_count']==15 and prior['camera_info_topic_count']==prior['tf_topic_count']==prior['mocap_or_pose_reference_topic_count']==0,'ROS_HEADER_EVIDENCE')
 need(prior['unresolved_requirements']=={k:'NOT_PHYSICALLY_QUALIFIED' for k in p.SPEC},'R42_GATE_MAP')
 for name in p.MANIFESTS:
  disk=repo/'manifests'/name
  committed=subprocess.check_output(['git','-C',str(repo),'show',p.BASE+':manifests/'+name])
  need(disk.is_file() and not disk.is_symlink() and sha(committed)==sha(disk.read_bytes())==report['frozen_manifest_sha256'][name],'FROZEN_SNAPSHOT:'+name)
 raw=load(repo/'manifests/m2dgr_reference_quality_index_v1.json')
 room=[x for x in raw['artifacts'] if x['trajectory_id']=='room_02']
 need(len(room)==1 and room[0]['raw_reference_sha256']==p.REF and room[0]['rotation_invalid_count']==90,'MOCAP_REF')
 need(report['source_acquisition_status']=='NOT_ACQUIRED' and not any(receipts['gate_receipts'][k]['source_uri'] for k in p.SPEC),'NO_SOURCE_FABRICATION')
 md=planp.read_text()
 need('NOT QUALIFIED' in md and 'R44' in md and '90 invalid rotation' in md,'PLAN')
 proof={'schema':'TRUST_ROBOT_R43_INDEPENDENT_ACQUISITION_PROTOCOL_V1','r43_protocol_sha256':sha(reportp.read_bytes()),'unfilled_receipts_sha256':sha(receiptp.read_bytes()),'plan_sha256':sha(planp.read_bytes()),'commit_frozen_manifests_verified':10,'prior_artifacts_verified':len(originals),'missing_evidence_gates_verified':11,'nonempty_source_receipts':0,'real_factors_authorized':False,'health_training_authorized':False,'confirmation_test_accessed':False,'github_modified':False}
 with out.open('x') as h:json.dump(proof,h,sort_keys=True,indent=2,allow_nan=False);h.write('\n')
 print('R43_INDEPENDENT_GIT_MANIFESTS=10_SHA_MATCH')
 print('R43_INDEPENDENT_R39_R42_PROVENANCE=5_LINKS_VERIFIED')
 print('R43_INDEPENDENT_UNFILLED_RECEIPTS=11_CONFIRMED')
 print('R43_INDEPENDENT_VALIDATION=PASS')

if __name__=='__main__':verify(*(pathlib.Path(x) for x in sys.argv[1:11]))
