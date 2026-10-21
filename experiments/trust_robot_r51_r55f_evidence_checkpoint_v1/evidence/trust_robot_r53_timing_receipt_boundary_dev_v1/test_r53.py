import ast,copy,hashlib,json,pathlib,sys
import r53_boundary as m
root=pathlib.Path(sys.argv[1]);paths=list(root.glob('*.py'))
assert len(paths)==3
for p in paths:ast.parse(p.read_text(),filename=str(p))
receipts=m.make_receipts()
sha=lambda obj:hashlib.sha256((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()).hexdigest()
report={'schema':m.SCHEMA,'trajectory_id':'room_02','split':'train','github_parent':m.BASE,'bag_sha256':m.BAG,'receipt_policy':'SOURCE_INTAKE_ONLY_ZERO_PHYSICAL_ADMISSION','admission_decision':'DENIED_UNFILLED_SOURCE_RECEIPTS','topic_frame_pairs':[{'topic':a,'frame_id':b} for a,b in zip(m.TOPICS,m.FRAMES)],'frozen_observed_timestamp_count':48,'hypothetical_nearest_header_distances':224,'hypothetical_record_header_residuals':144,'camera_imu_negative_record_minus_header_count':9,'reference_invalid_rotation_count':90,'physical_offset_seconds':None,'clock_drift_model':None,'temporal_association_tolerance_seconds':None,'source_status_by_gate':{k:'NOT_QUALIFIED' for k in m.GATES},'frozen_clock_domain_count':4,'original_r43_receipts_unchanged':True,'receipt_schema_sha256':sha(receipts),**{k:False for k in m.NO},**{k:0 for k in m.ZERO},'next_phase':'R54_AUTHOR_SOURCE_ACQUISITION_AND_PROVENANCE_REQUEST_PACKET'}
m.policy(report,receipts)
rejected=0
def deny(r,rec,label):
 global rejected
 try:m.policy(r,rec)
 except (ValueError,KeyError,TypeError):rejected+=1
 else:raise AssertionError('UNSAFE_ACCEPTED:'+label)
for k in m.NO:
 bad=copy.deepcopy(report);bad[k]=True;deny(bad,receipts,k)
for k in m.ZERO:
 bad=copy.deepcopy(report);bad[k]=1;deny(bad,receipts,k)
for k in m.GATES:
 bad=copy.deepcopy(report);bad['source_status_by_gate'][k]='QUALIFIED';deny(bad,receipts,k)
for kind in m.KIND:
 bad=copy.deepcopy(receipts);bad['receipts'][kind]['fields']['source_sha256']='f'*64;badreport=copy.deepcopy(report);badreport['receipt_schema_sha256']=sha(bad);deny(badreport,bad,kind+'_FORGED_RECEIPT')
for k,value in [('split','confirmation_test'),('trajectory_id','room_03'),('github_parent','0'*40),('physical_offset_seconds',0.0),('frozen_observed_timestamp_count',49),('camera_imu_negative_record_minus_header_count',0),('reference_invalid_rotation_count',0),('frozen_clock_domain_count',3),('original_r43_receipts_unchanged',False),('next_phase','SCORE_NOW')]:
 bad=copy.deepcopy(report);bad[k]=value;deny(bad,receipts,k)
assert rejected==len(m.NO)+len(m.ZERO)+len(m.GATES)+len(m.KIND)+10==42,rejected
print('R53_PYTHON_AST=3_PASS')
print('R53_NEGATIVE_SOURCE_PROMOTION_AND_HOLDOUT_CONTROLS=42_REJECTED')
