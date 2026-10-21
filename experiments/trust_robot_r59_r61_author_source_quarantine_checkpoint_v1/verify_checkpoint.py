#!/usr/bin/env python3
"""Standalone independent fail-closed archive/hash/semantics verifier."""
import ast,hashlib,json,pathlib,stat
A=pathlib.Path(__file__).resolve().parent
H={
 'r59/dev/r59_primary.py':'e6351c6e25e91bef32662e952ca6c24adb8ca6510d15a4344be5e5da1ca6b36e',
 'r59/dev/r59_independent.py':'760b579623aca9a39c7946f68bea0be6748e005cb2a12dbaac12a9521c941697',
 'r59/dev/test_r59.py':'5aa63e6eefa4b62a472050560a5a715f72eb004a9f83984a49032cbce439034e',
 'r59/result/r59_access_next_actions_v1.md':'8ec591726e67f86c01f467de5f7310c71ecabcbc469dee293f7a7d298de272cf',
 'r59/result/r59_independent_validation_v1.json':'d0182d6532b39c1417cb4a51887b56a0a03daa3b875092e3c44cd8856b66b80b',
 'r59/result/r59_official_readme_original_bytes_v1.md':'dc901f5c46ba30f0c712ee53eb3ffaf6da38ac005c4294c17077d14bc61f36f4',
 'r59/result/r59_source_identity_report_v1.json':'93cee19b48b9e2b839f7a2b95cb39108e45f241ea5433a081e0ff0e192ed1304',
 'r60/dev/r60_packet.py':'ab52e596eb62ad0948beae156018d43e1db755d3dc4409ab2ef0f946e5a3e0d0',
 'r60/dev/r60_independent.py':'74bb7ea259518a407feb64334ce1a7cd021c9c9ce59b3776522e5638af7e6312',
 'r60/result/r60_access_request_receipt_v1.json':'6f6b0951e8efbf9dc580469f672fbde270784aba411f3a4b3bc1b601b6f41bf1',
 'r60/result/r60_author_github_issue_draft_v1.md':'abbe030932540ca26b13b96e0dd9f41faa1e55905192af59c7e0c2c64140c0ee',
 'r60/result/r60_independent_validation_v1.json':'49069f18774bfec9d5404c8a91b425bbf7a78f6a548793586d2675d2de639fb9',
 'r61/dev/r61_quarantine.py':'db33e5066bda19009c2b7b71c9c71d18b4566730a2efe4724c29d0ccad0c8828',
 'r61/dev/r61_independent.py':'788a09c3f4756b92e72e7e239f140dc35160d5b0b3980c3043c32cc1736e669a',
 'r61/dev/test_r61.py':'ba7b4fadae1547f070fce146b422bd693ea2749de158e64f5201f28f5ff0d0ad',
 'r61/result/r61_independent_validation_v1.json':'431400f4e539ad0c003cb9b4f36066424e2ed356fba84c04e438cb32bed37f9a',
 'r61/result/r61_quarantine_receipt_v1.json':'249ca1ce3510c42b3ff1a1440ef0a2eefab90cef16b588e5872bbdbc9ecb2da7',
}
def need(ok,why):
 if not ok:raise ValueError('R62_VERIFY_DENIED:'+why)
def safe(p):
 s=p.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and 0<s.st_size<=1024*1024,'UNSAFE:'+str(p));return p.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def load(rel):return json.loads(safe(A/'evidence'/rel))
m=json.loads(safe(A/'checkpoint_manifest_v1.json'))
need(m['schema']=='TRUST_ROBOT_R59_R61_AUTHOR_SOURCE_QUARANTINE_ARCHIVE_V1','SCHEMA')
need(m['parent_commit']=='a800ca91326a51fa0cc86972bed08e99b6b459e5' and m['branch']=='kios-isaacsim-v15-integration','GIT_PARENT')
need(m['source_artifact_sha256']==H and len(H)==17,'FROZEN_PINS')
need(m['readme_sha256']==sha(safe(A/'README.md')),'README')
need(m['frozen_split_sha256']=='017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f','SPLIT')
need(m['scientific_gates_closed']==11,'GATES')
for flag in ('raw_bag_archived','gt_bytes_acquired','author_communication_sent','confirmation_test_accessed','pose_factors_authorized','health_training_authorized','ate_rpe_authorized'):
 need(m[flag] is False,'SCIENCE:'+flag)
actual=set();bytes_total=0
for p in A.rglob('*'):
 need(not p.is_symlink(),'SYMLINK')
 if p.is_file():actual.add(p.relative_to(A).as_posix())
need(actual=={'README.md','build_checkpoint.py','verify_checkpoint.py','checkpoint_manifest_v1.json'}|{'evidence/'+p for p in H},'EXACT_INVENTORY')
for rel,h in sorted(H.items()):
 p=A/'evidence'/rel;b=safe(p);need(sha(b)==h,'SHA:'+rel);bytes_total+=len(b)
 if p.suffix=='.py':ast.parse(b,filename=str(p))
 if p.suffix=='.json':json.loads(b)
need(bytes_total==m['total_evidence_bytes'],'BYTES_TOTAL')
readme=safe(A/'evidence/r59/result/r59_official_readme_original_bytes_v1.md')
gitblob=hashlib.sha1(b'blob '+str(len(readme)).encode()+b'\0'+readme).hexdigest()
need(gitblob=='c394994a8431426c0bd4b3dcf618faf7b97d119f','AUTHOR_README_BLOB')
rows=[x for x in readme.decode().splitlines() if x.startswith('room_02|')]
need(len(rows)==1 and len(rows[0].split('|'))==7 and rows[0].split('|')[1]=='2021-07-30','OFFICIAL_ROW')
r59=load('r59/result/r59_source_identity_report_v1.json')
need(r59['readme_verified'] is True and r59['official_gt_bytes_acquired_in_r59'] is False and r59['r43_gate_count_closed']==11,'R59_SCIENCE')
need(r59['verified_readme_details']['readme_sha256']==sha(readme),'READ_ME_REPORT_SHA')
need(rows[0].split('|')[-1]=='[GT]('+r59['gt_link_from_frozen_inventory']+')','GT_LINK')
need(load('r59/result/r59_independent_validation_v1.json')['status']=='PASS','R59_INDEPENDENT')
r60=load('r60/result/r60_access_request_receipt_v1.json')
need(r60['draft_status']=='PREPARED_NOT_POSTED' and r60['author_contacted'] is False and r60['official_ground_truth_acquired'] is False,'R60_UNSENT')
need(r60['draft_sha256']==sha(safe(A/'evidence/r60/result/r60_author_github_issue_draft_v1.md')),'R60_DRAFT_SHA')
need(load('r60/result/r60_independent_validation_v1.json')['status']=='PASS','R60_INDEPENDENT')
r61=load('r61/result/r61_quarantine_receipt_v1.json')
need(r61['candidate']['status']=='ABSENT' and r61['candidate']['observed_sha256'] is None and r61['science_gates_opened']==0,'R61_ABSENT')
need(r61['official_ground_truth_independently_authenticated'] is False and r61['raw_bag_opened'] is False and r61['confirmation_test_accessed'] is False,'R61_SCIENCE')
need(load('r61/result/r61_independent_validation_v1.json')['status']=='PASS','R61_INDEPENDENT')
print('R62_ARCHIVE_STANDALONE_VERIFIER=PASS')
print('R62_IMMUTABLE_SOURCE_BYTES=17_SHA_VERIFIED')
print('R62_AUTHOR_README_GIT_BLOB=VERIFIED')
print('R62_AUTHOR_ISSUE=UNSENT GT=ABSENT SCIENCE_GATES=11_CLOSED')
