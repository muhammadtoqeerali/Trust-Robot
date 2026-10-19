"""Repair only embedded ROS bag v2 connection-record handling; never edit data."""
import ast
from pathlib import Path
import shutil
import sys
root=Path(sys.argv[1])
reader=root/'r18_decode.py'
verifier=root/'r18_verify.py'

def replace_once(text, before, after, which):
    if text.count(before)!=1:raise ValueError('R18_PATCH_ANCHOR:'+which)
    return text.replace(before,after,1)

rs=reader.read_text()
vs=verifier.read_text()
rs=replace_once(rs,'def messages(chunk):','def messages(chunk, indexed_connections):','decoder signature')
rs=replace_once(rs,r"""        need(h.get(b'op') == b'\x02', 'NON_MESSAGE_IN_CHUNK')
        yield u32(h[b'conn']), stamp(h[b'time']), body""",r"""        op = h.get(b'op')
        if op == b'\x07':
            need(b'conn' in h and b'topic' in h, 'CONNECTION_HEADER')
            cid = u32(h[b'conn'])
            need(cid in indexed_connections, 'UNKNOWN_CHUNK_CONNECTION')
            metadata = field_map(body)
            need(all(k in metadata for k in (b'type', b'md5sum', b'message_definition')), 'CONNECTION_METADATA')
            expected = indexed_connections[cid]
            need(h[b'topic'].decode('utf-8') == expected['topic'], 'CHUNK_CONNECTION_TOPIC')
            need(metadata[b'type'].decode('utf-8') == expected['message_type'], 'CHUNK_CONNECTION_TYPE')
            need(metadata[b'md5sum'].decode('ascii') == expected['md5sum'], 'CHUNK_CONNECTION_MD5')
            need(hashlib.sha256(metadata[b'message_definition']).hexdigest() == expected['message_definition_sha256'], 'CHUNK_CONNECTION_DEFINITION')
            continue
        need(op == b'\x02', 'UNKNOWN_IN_CHUNK_OP')
        yield u32(h[b'conn']), stamp(h[b'time']), body""",'decoder op handling')
rs=replace_once(rs,"    conn = {c['id']: c['topic'] for c in info['connections'] if c['topic'] in NEEDED}","    indexed_connections = {c['id']: c for c in info['connections']}\n    need(len(indexed_connections)==info['connection_count'], 'INDEX_CONNECTION_INVENTORY')\n    conn = {c['id']: c['topic'] for c in info['connections'] if c['topic'] in NEEDED}",'decoder index')
rs=replace_once(rs,'for cid, bag_time, body in messages(raw):','for cid, bag_time, body in messages(raw, indexed_connections):','decoder reader call')
vs=replace_once(vs,'def chunk_messages(file,offset):','def chunk_messages(file,offset,indexed_connections):','verifier signature')
vs=replace_once(vs,r"""        need(hd[b'op']==b'\x02','MSG_OP')
        yield u32(hd[b'conn']), timestamp(hd[b'time']), msg""",r"""        op=hd.get(b'op')
        if op==b'\x07':
            need(b'conn' in hd and b'topic' in hd,'CONNECTION_HEADER')
            cid=u32(hd[b'conn'])
            need(cid in indexed_connections,'UNKNOWN_CHUNK_CONNECTION')
            metadata=fields(msg)
            need(all(x in metadata for x in (b'type',b'md5sum',b'message_definition')),'CONNECTION_FIELDS')
            reference=indexed_connections[cid]
            need(hd[b'topic'].decode('utf-8')==reference['topic'],'CONNECTION_TOPIC')
            need(metadata[b'type'].decode('utf-8')==reference['message_type'],'CONNECTION_TYPE')
            need(metadata[b'md5sum'].decode('ascii')==reference['md5sum'],'CONNECTION_MD5')
            need(hashlib.sha256(metadata[b'message_definition']).hexdigest()==reference['message_definition_sha256'],'CONNECTION_DEFINITION')
            continue
        need(op==b'\x02','MSG_OP')
        yield u32(hd[b'conn']), timestamp(hd[b'time']), msg""",'verifier op handling')
vs=replace_once(vs,"    conn={c['id']:c['topic'] for c in r17['connections']}","    indexed_connections={c['id']:c for c in r17['connections']}\n    need(len(indexed_connections)==r17['connection_count'],'R17_CONNECTION_INVENTORY')\n    conn={c['id']:c['topic'] for c in r17['connections']}",'verifier index')
vs=replace_once(vs,'for cid,t,body in chunk_messages(file,off):','for cid,t,body in chunk_messages(file,off,indexed_connections):','verifier read call')
for name,source in (('decoder',rs),('verifier',vs)):
    ast.parse(source,filename=name)
shutil.copyfile(reader,root/'r18_decode_original_failed_v1.py.saved')
shutil.copyfile(verifier,root/'r18_verify_original_failed_v1.py.saved')
reader.write_text(rs)
verifier.write_text(vs)
print('R18_ORIGINAL_FAILED_SOURCE_BACKUPS=PRESERVED')
print('R18_TARGETED_ROSBAG_CONNECTION_OP7_PATCH=APPLIED')
