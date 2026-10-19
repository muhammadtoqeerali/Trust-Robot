"""Independent bounded readback: recompute sampled raw bytes and timestamps."""
import bz2, hashlib, json, pathlib, struct, sys
NEEDED=('/camera/color/image_raw/compressed','/camera/imu','/handsfree/imu','/velodyne_points')
def need(ok,s):
    if not ok:raise ValueError('R18_INDEPENDENT_DENIED:'+s)
def u32(b):return struct.unpack('<I',b)[0]
def read(h,n):
    x=h.read(n);need(len(x)==n,'TRUNCATED');return x
def fields(b):
    p=0;v={}
    while p<len(b):
        need(p+4<=len(b),'FIELD');k=u32(b[p:p+4]);p+=4
        need(0<k<=len(b)-p,'FIELD_LENGTH');item=b[p:p+k];p+=k
        x,sep,y=item.partition(b'=');need(sep and x not in v,'FIELD_VALUE');v[x]=y
    return v
def rec(h):
    sz=u32(read(h,4));need(0<sz<=2097152,'HEADER_LIMIT')
    f=fields(read(h,sz));n=u32(read(h,4));need(n<=33554432,'DATA_LIMIT')
    return f,read(h,n)
def timestamp(b):
    sec,ns=struct.unpack('<II',b);need(ns<1000000000,'NANOSECOND');return sec*1000000000+ns
def chunk_messages(file,offset,indexed_connections):
    file.seek(offset);hdr,comp=rec(file)
    need(hdr[b'op']==b'\x05','CHUNK')
    expected=u32(hdr[b'size']);need(0<expected<=67108864,'CHUNK_LIMIT')
    mode=hdr[b'compression']
    if mode==b'none':raw=comp
    elif mode==b'bz2':
        dec=bz2.BZ2Decompressor();raw=dec.decompress(comp,max_length=expected+1)
        need(dec.eof and not dec.unused_data,'BZIP2_COMPLETE')
    else:raise ValueError('R18_INDEPENDENT_DENIED:COMPRESSION:'+repr(mode))
    need(len(raw)==expected,'CHUNK_LENGTH')
    pos=0
    while pos<len(raw):
        need(len(raw)-pos>=8,'RECORD_BOUNDS')
        hs=u32(raw[pos:pos+4]);pos+=4
        need(0<hs<=2097152 and hs<=len(raw)-pos,'RECORD_HEADER')
        hd=fields(raw[pos:pos+hs]);pos+=hs
        length=u32(raw[pos:pos+4]);pos+=4
        need(length<=len(raw)-pos,'RECORD_DATA')
        msg=raw[pos:pos+length];pos+=length
        op=hd.get(b'op')
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
        yield u32(hd[b'conn']), timestamp(hd[b'time']), msg

def main():
    bag,r17_path,report_path=map(pathlib.Path,sys.argv[1:4]); expected=sys.argv[4]
    r17=json.loads(r17_path.read_text());r18=json.loads(report_path.read_text())
    need(r18['schema']=='TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1','SCHEMA')
    need(r18['recording_sha256']==expected==r17['file_sha256'],'SOURCE')
    need(r18['r17_report_sha256']==hashlib.sha256(r17_path.read_bytes()).hexdigest(),'R17_LINEAGE')
    need(set(r18['samples'])==set(NEEDED),'TOPICS')
    targets={}
    for topic,group in r18['samples'].items():
        need(len(group)==2 and group[0]['chunk_offset']!=group[1]['chunk_offset'],'SAMPLE_COUNTS')
        for s in group:
            key=(s['chunk_offset'],s['connection_id'],s['bag_record_time_ns'],s['serialized_message_sha256'])
            targets.setdefault(s['chunk_offset'],[]).append((key,s,topic))
    need(len(targets)==r18['sampled_chunks']<=8,'CHUNKS')
    indexed_connections={c['id']:c for c in r17['connections']}
    need(len(indexed_connections)==r17['connection_count'],'R17_CONNECTION_INVENTORY')
    conn={c['id']:c['topic'] for c in r17['connections']}
    matched=set()
    with bag.open('rb') as file:
        for off in sorted(targets):
            candidates=targets[off]
            for cid,t,body in chunk_messages(file,off,indexed_connections):
                h=hashlib.sha256(body).hexdigest()
                key=(off,cid,t,h)
                for expected_key,s,topic in candidates:
                    if key==expected_key:
                        need(conn[cid]==topic,'CONNECTION_ID')
                        need(len(body)==s['serialized_message_bytes'],'SERIALIZED_LENGTH')
                        need(len(body)>=16,'ROS_HEADER')
                        seq,sec,ns,n=struct.unpack_from('<IIII',body,0)
                        need(ns<1000000000 and n<=len(body)-16,'ROS_HEADER_BOUNDS')
                        frame=body[16:16+n].decode('utf-8')
                        need(seq==s['sequence'] and sec*1000000000+ns==s['header_stamp_ns'] and frame==s['frame_id'],'MESSAGE_HEADER')
                        matched.add(expected_key)
    need(len(matched)==8,'INDEPENDENT_BYTES')
    need(r18['sampled_message_count']==8 and r18['recorded_streams_decoded']==4,'TOTALS')
    for key in ('bag_record_time_is_capture_time_proof','header_stamp_is_capture_time_proof','cross_stream_alignment_performed','physical_sync_verified','extrinsics_verified','raw_recording_modified','github_modified'):
        need(r18[key] is False,'SCIENCE_GATE:'+key)
    need(r18['real_pose_factors_generated']==0 and r18['health_labels']==0,'NO_FACTORS')
    print('R18_INDEPENDENT_SAMPLED_MESSAGE_HASHES=8_VERIFIED')
    print('R18_INDEPENDENT_TIMESTAMP_AND_FRAME_HEADERS=VERIFIED')
    print('R18_INDEPENDENT_VALIDATION=PASS')
if __name__=='__main__':main()
