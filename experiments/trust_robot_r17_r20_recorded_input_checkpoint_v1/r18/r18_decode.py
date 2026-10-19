"""Read-only, bounded ROS1 bag v2 recorded-message sampler. No factor admission."""
import bz2, hashlib, json, pathlib, struct, sys

NEEDED = {
    '/camera/color/image_raw/compressed': 'sensor_msgs/CompressedImage',
    '/camera/imu': 'sensor_msgs/Imu',
    '/handsfree/imu': 'sensor_msgs/Imu',
    '/velodyne_points': 'sensor_msgs/PointCloud2',
}
MAX_COMPRESSED = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024


def need(ok, msg):
    if not ok: raise ValueError('R18_DENIED:' + msg)


def u32(b):
    need(len(b) == 4, 'UINT32')
    return struct.unpack('<I', b)[0]


def stamp(b):
    need(len(b) == 8, 'TIME_BYTES')
    s, ns = struct.unpack('<II', b)
    need(ns < 1000000000, 'TIME_NSEC')
    return s * 1000000000 + ns


def read_exact(f, n):
    v = f.read(n)
    need(len(v) == n, 'TRUNCATED_FILE')
    return v


def field_map(blob):
    cur, out = 0, {}
    while cur < len(blob):
        need(cur + 4 <= len(blob), 'FIELD_HEADER')
        size = u32(blob[cur:cur+4]); cur += 4
        need(0 < size <= len(blob)-cur, 'FIELD_SIZE')
        value = bytes(blob[cur:cur+size]); cur += size
        k, eq, v = value.partition(b'=')
        need(eq and k and k not in out, 'FIELD_DUPLICATE_OR_FORMAT')
        out[k] = v
    return out


def file_record(f, limit=8*1024*1024):
    n = u32(read_exact(f, 4))
    need(0 < n <= 2*1024*1024, 'RECORD_HEADER_LIMIT')
    h = field_map(read_exact(f, n))
    d = u32(read_exact(f, 4))
    need(d <= limit, 'RECORD_DATA_LIMIT')
    return h, read_exact(f, d)


class Cursor:
    def __init__(self, data): self.data, self.pos = memoryview(data), 0
    def take(self, n):
        need(type(n) is int and 0 <= n <= len(self.data)-self.pos, 'MESSAGE_BOUNDS')
        out = self.data[self.pos:self.pos+n]; self.pos += n
        return out
    def number(self): return u32(self.take(4))
    def text(self, limit=4096):
        n = self.number(); need(n <= limit, 'STRING_LIMIT')
        return self.take(n).tobytes().decode('utf-8')
    def bool(self):
        v = self.take(1)[0]; need(v in (0,1), 'BOOL_VALUE')
        return bool(v)
    def done(self): need(self.pos == len(self.data), 'TRAILING_MESSAGE_DATA')


def header(c):
    seq, time = c.number(), stamp(c.take(8))
    frame = c.text()
    return {'sequence': seq, 'header_stamp_ns': time, 'frame_id': frame}


def decode(topic, message):
    c = Cursor(message); h = header(c)
    if topic == '/camera/color/image_raw/compressed':
        fmt = c.text(256); length = c.number(); data = c.take(length)
        need(length > 0, 'EMPTY_CAMERA_PAYLOAD')
        other = {'format': fmt, 'compressed_image_bytes': length,
                 'image_payload_sha256': hashlib.sha256(data).hexdigest()}
    elif topic in ('/camera/imu', '/handsfree/imu'):
        floats = struct.unpack('<37d', c.take(37*8))
        other = {'orientation_xyzw': list(floats[:4]),
                 'angular_velocity_rad_s': list(floats[13:16]),
                 'linear_acceleration_m_s2': list(floats[25:28]),
                 'all_values_finite': all(__import__('math').isfinite(x) for x in floats)}
    elif topic == '/velodyne_points':
        height, width, nf = c.number(), c.number(), c.number()
        need(0 < nf <= 128, 'POINT_FIELDS')
        desc = []
        for _ in range(nf):
            name = c.text(256); offset = c.number()
            dtype = c.take(1)[0]; count = c.number()
            need(dtype in range(1,9) and count > 0, 'POINTFIELD_SCHEMA')
            desc.append({'name': name, 'offset': offset, 'datatype': dtype, 'count': count})
        big = c.bool(); step, row_step = c.number(), c.number()
        count_bytes = c.number()
        need(step > 0 and height > 0 and width > 0, 'CLOUD_SHAPE')
        need(count_bytes == row_step*height and row_step >= step*width, 'CLOUD_LENGTH')
        binary = c.take(count_bytes); dense = c.bool()
        other = {'height':height, 'width':width, 'point_count':height*width,
                 'point_step':step, 'row_step':row_step,
                 'point_fields':desc, 'is_bigendian':big, 'is_dense':dense,
                 'point_payload_bytes':count_bytes,
                 'point_payload_sha256':hashlib.sha256(binary).hexdigest()}
    else:
        raise ValueError('R18_DENIED:UNKNOWN_SENSOR')
    c.done(); return dict(h, **other)


def chunk_data(handle, offset):
    handle.seek(offset)
    h, compressed = file_record(handle, MAX_COMPRESSED)
    need(h.get(b'op') == b'\x05', 'CHUNK_OP')
    compression = h[b'compression'].decode('ascii')
    expected = u32(h[b'size'])
    need(0 < expected <= MAX_EXPANDED, 'DECOMPRESSED_SIZE_LIMIT')
    if compression == 'none':
        raw = compressed
    elif compression == 'bz2':
        dec = bz2.BZ2Decompressor()
        raw = dec.decompress(compressed, max_length=expected+1)
        need(dec.eof and not dec.unused_data, 'BZIP2_COMPLETE')
    else:
        raise ValueError('R18_DENIED:UNSUPPORTED_COMPRESSION:'+compression)
    need(len(raw) == expected, 'CHUNK_SIZE_MISMATCH')
    return raw, compression


def messages(chunk, indexed_connections):
    pos = 0; view = memoryview(chunk)
    while pos < len(view):
        need(len(view)-pos >= 8, 'CHUNK_RECORD_TRUNCATED')
        hsize = u32(view[pos:pos+4]); pos += 4
        need(0 < hsize <= 2*1024*1024 and hsize <= len(view)-pos, 'CHUNK_HEADER')
        h = field_map(view[pos:pos+hsize]); pos += hsize
        need(len(view)-pos >= 4, 'CHUNK_MESSAGE_LENGTH')
        n = u32(view[pos:pos+4]); pos += 4
        need(n <= len(view)-pos, 'CHUNK_MESSAGE_BOUNDS')
        body = view[pos:pos+n]; pos += n
        op = h.get(b'op')
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
        yield u32(h[b'conn']), stamp(h[b'time']), body


def sample(bag, index):
    info = json.loads(index.read_text())
    need(info['schema']=='TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1', 'R17_SCHEMA')
    indexed_connections = {c['id']: c for c in info['connections']}
    need(len(indexed_connections)==info['connection_count'], 'INDEX_CONNECTION_INVENTORY')
    conn = {c['id']: c['topic'] for c in info['connections'] if c['topic'] in NEEDED}
    need(len(conn)==4, 'REQUIRED_CONNECTION_COUNT')
    need({conn[c['id']]:c['message_type'] for c in info['connections'] if c['id'] in conn}==NEEDED, 'REQUIRED_TYPES')
    chunks = {}
    picks = {topic: [] for topic in NEEDED}
    with bag.open('rb') as f:
        need(read_exact(f,13)==b'#ROSBAG V2.0\n', 'BAG_VERSION')
        h,_=file_record(f,8192)
        need(h.get(b'op')==b'\x03','FILE_HEADER')
        pos=struct.unpack('<Q',h[b'index_pos'])[0]
        need(pos == info['index_position'], 'R17_INDEX_POS')
        f.seek(pos)
        for _ in range(info['connection_count']):
            hh,_=file_record(f)
            need(hh.get(b'op')==b'\x07','CONNECTION_INDEX')
        for _ in range(info['chunk_count']):
            hh, data=file_record(f)
            need(hh.get(b'op')==b'\x06','CHUNK_INFO')
            off=struct.unpack('<Q',hh[b'chunk_pos'])[0]
            n=u32(hh[b'count']); need(len(data)==8*n,'CHUNK_COUNTS')
            ledger={}
            for j in range(n):
                cid, cnt=struct.unpack_from('<II',data,8*j)
                ledger[cid]=cnt
                if cid in conn and len(picks[conn[cid]])<2:
                    picks[conn[cid]].append(off)
            if any(off in x for x in picks.values()): chunks[off]=ledger
        need(all(len(v)==2 for v in picks.values()),'INSUFFICIENT_INDEX_SAMPLES')
        need(len(chunks)<=8,'SAMPLE_CHUNK_LIMIT')
        samples={topic: [] for topic in NEEDED}
        modes=set()
        for off in sorted(chunks):
            raw, mode=chunk_data(f, off); modes.add(mode)
            observed={}
            for cid, bag_time, body in messages(raw, indexed_connections):
                observed[cid]=observed.get(cid,0)+1
                if cid in conn and off in picks[conn[cid]] and not any(x['chunk_offset']==off for x in samples[conn[cid]]):
                    topic=conn[cid]
                    decoded=decode(topic,body)
                    samples[topic].append(dict(decoded, chunk_offset=off,
                        connection_id=cid, bag_record_time_ns=bag_time,
                        serialized_message_bytes=len(body),
                        serialized_message_sha256=hashlib.sha256(body).hexdigest()))
            need(observed==chunks[off], 'CHUNK_INDEX_COUNT_MISMATCH')
        need(all(len(v)==2 for v in samples.values()),'MISSING_SAMPLES')
    return samples, sorted(modes), len(chunks)


def main():
    bag,index,manifest,output=map(pathlib.Path,sys.argv[1:5]); pin=sys.argv[5]
    r17=json.loads(index.read_text())
    need(r17['file_sha256']==pin and r17['trajectory_id']=='room_02', 'R17_BAG_PIN')
    md=json.loads(manifest.read_text()); train=[x for x in md['records'] if x['trajectory_id']=='room_02']
    need(len(train)==1 and train[0]['split']=='train', 'TRAIN_SOURCE')
    pins=[x['sha256'] for x in train[0]['calibration_artifacts'] if x.get('source_path')=='raw/rosbags/room_02.bag']
    need(pins==[pin], 'MANIFEST_BAG_PIN')
    samples,modes,nchunks=sample(bag,index)
    report={'schema':'TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1',
        'trajectory_id':'room_02','split':'train','recording_sha256':pin,
        'r17_report_sha256':hashlib.sha256(index.read_bytes()).hexdigest(),
        'samples':samples,'sampling_rule':'first message in first two distinct indexed chunks per required topic',
        'sampled_chunks':nchunks,'compression_methods':modes,
        'recorded_streams_decoded':4,'sampled_message_count':sum(map(len,samples.values())),
        'bag_record_time_is_capture_time_proof':False,'header_stamp_is_capture_time_proof':False,
        'cross_stream_alignment_performed':False,'physical_sync_verified':False,
        'extrinsics_verified':False,'real_pose_factors_generated':0,'health_labels':0,
        'raw_recording_modified':False,'github_modified':False}
    with output.open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('R18_RECORDED_SENSOR_MESSAGE_DECODING=PASS')
    print('R18_SELECTED_CHUNKS='+str(nchunks))
    print('R18_COMPRESSION_METHODS='+','.join(modes))
    for topic, values in samples.items():
        print('R18_SAMPLES='+topic+' COUNT='+str(len(values)))
        print('R18_SAMPLE_HEADER_FRAME='+topic+' FRAME='+repr(values[0]['frame_id']))
    print('R18_TOTAL_SAMPLED_MESSAGES=8')
    print('R18_PHYSICAL_ADMISSION=DENIED')

if __name__=='__main__':main()
