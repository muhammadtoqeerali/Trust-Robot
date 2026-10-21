#!/usr/bin/env python3
"""R62 strictly allowlisted immutable byte copy. No raw bags or GT touched."""
import hashlib, json, os, pathlib, stat, sys
E,A=map(pathlib.Path,sys.argv[1:])
DIRS={
 'r59/dev':'trust_robot_r59_author_readme_identity_dev_v1',
 'r59/result':'trust_robot_r59_author_readme_identity_result_v1',
 'r60/dev':'trust_robot_r60_official_gt_author_access_packet_dev_v1',
 'r60/result':'trust_robot_r60_official_gt_author_access_packet_result_v1',
 'r61/dev':'trust_robot_r61_reference_quarantine_dev_v1',
 'r61/result':'trust_robot_r61_reference_quarantine_result_v1',
}
PINS={
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
def need(ok,reason):
 if not ok:raise ValueError('R62_BUILD_DENIED:'+reason)
def sha(d):return hashlib.sha256(d).hexdigest()
def safe_read(p):
 b=p.lstat()
 need(stat.S_ISREG(b.st_mode) and b.st_nlink==1 and 0<b.st_size<=1024*1024,'UNSAFE:'+str(p))
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC),'rb') as f:
  opened=os.fstat(f.fileno());data=f.read(1024*1024+1);closed=os.fstat(f.fileno())
 after=p.lstat()
 identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 need(identity(b)==identity(opened)==identity(closed)==identity(after) and len(data)==b.st_size,'CHANGED:'+str(p))
 need(b'\x00' not in data,'BINARY:'+str(p))
 data.decode('utf-8');return data
need(len(PINS)==17 and set(DIRS)=={str(pathlib.PurePosixPath(k).parent) for k in PINS},'INVENTORY')
for prefix,dirname in DIRS.items():
 root=E/dirname
 need(stat.S_ISDIR(root.lstat().st_mode),'UNSAFE_DIR:'+dirname)
 found={p.name for p in root.iterdir()}
 expected={pathlib.PurePosixPath(k).name for k in PINS if str(pathlib.PurePosixPath(k).parent)==prefix}
 need(found==expected,'SOURCE_DIR_CONTENTS:'+dirname)
total=0
for rel,expected in sorted(PINS.items()):
 parts=pathlib.PurePosixPath(rel).parts
 root=E/DIRS['/'.join(parts[:2])]
 data=safe_read(root/parts[2]);need(sha(data)==expected,'FROZEN_SHA:'+rel)
 dest=A/'evidence'/rel
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() or dest.is_symlink():
  need(safe_read(dest)==data,'PRESERVED_PARTIAL_COPY_MISMATCH:'+rel)
 else:
  with dest.open('xb') as f:f.write(data)
 need(safe_read(dest)==data,'COPY_SHA:'+rel)
 total+=len(data)
need(total<2*1024*1024,'TOTAL_SIZE')
manifest={
 'schema':'TRUST_ROBOT_R59_R61_AUTHOR_SOURCE_QUARANTINE_ARCHIVE_V1',
 'parent_commit':'a800ca91326a51fa0cc86972bed08e99b6b459e5',
 'branch':'kios-isaacsim-v15-integration',
 'source_artifact_sha256':PINS,
 'readme_sha256':sha(safe_read(A/'README.md')),
 'raw_bag_archived':False,'gt_bytes_acquired':False,
 'author_communication_sent':False,'confirmation_test_accessed':False,
 'scientific_gates_closed':11,'pose_factors_authorized':False,
 'health_training_authorized':False,'ate_rpe_authorized':False,
 'frozen_split_sha256':'017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f',
 'total_evidence_bytes':total,
}
with (A/'checkpoint_manifest_v1.json').open('x',encoding='utf-8') as f:
 json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
print('R62_FROZEN_SOURCE_FILES=17_COPIED_SHA_VERIFIED')
print('R62_R59_SOURCE_FILES=7 R60=5 R61=5')
print('R62_ARCHIVED_SOURCE_BYTES='+str(total))
