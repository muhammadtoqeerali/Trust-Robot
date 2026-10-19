import importlib.util,struct, pathlib, json,hashlib,tempfile
p=pathlib.Path(__file__).parent
import r18_decode as m
import r18_verify as v
n4=lambda x:struct.pack('<I',x)
n8=lambda x:struct.pack('<Q',x)
def f(fields):
 out=b''
 for a,b in fields.items():
  dat=a+b'='+b;out+=n4(len(dat))+dat
 return out
def rec(h,d=b''):
 head=f(h);return n4(len(head))+head+n4(len(d))+d
def rosheader():return n4(1)+n4(12)+n4(34)+n4(4)+b'body'
img=rosheader()+n4(4)+b'jpeg'+n4(4)+b'\xff\xd8\xff\xd9'
imu=rosheader()+struct.pack('<37d',*([0.5]*37))
field=lambda name,offset,dtype,count: n4(len(name))+name+n4(offset)+bytes([dtype])+n4(count)
payload=b'\x00'*22
lidar=rosheader()+n4(1)+n4(1)+n4(1)+field(b'x',0,7,1)+b'\x00'+n4(22)+n4(22)+n4(22)+payload+b'\x01'
assert m.decode('/camera/color/image_raw/compressed',img)['format']=='jpeg'
assert m.decode('/handsfree/imu',imu)['linear_acceleration_m_s2']==[0.5]*3
assert m.decode('/velodyne_points',lidar)['point_payload_bytes']==22
for topic,message in (('/camera/imu',imu),('/velodyne_points',lidar)):
 for bad in (message[:-1],message+b'x',b''):
  try:m.decode(topic,bad)
  except (ValueError,IndexError,struct.error): pass
  else:raise AssertionError(('bad accepted',topic,bad))
# create valid rosbag synthetic two chunks with all four connection indexes and matching index pos
items=[img,imu,imu,lidar]
topics=list(m.NEEDED)
conns=[]
for i,topic in enumerate(topics):
 conns.append(rec({b'op':b'\x07',b'conn':n4(i),b'topic':topic.encode()},f({b'topic':topic.encode(),b'type':m.NEEDED[topic].encode(),b'md5sum':b'xyz',b'message_definition':b'fixture'})))
chunks=[]
for z in range(2):
 raw=b''
 for i,body in enumerate(items):
  raw+=rec({b'op':b'\x02',b'conn':n4(i),b'time':n4(12+z)+n4(30)},body)
 chunks.append(rec({b'op':b'\x05',b'compression':b'none',b'size':n4(len(raw))},raw))
bag_header=lambda pos:rec({b'op':b'\x03',b'index_pos':n8(pos),b'conn_count':n4(4),b'chunk_count':n4(2)},b' '*100)
prefix=b'#ROSBAG V2.0\n'+bag_header(0)
pos=[len(prefix),len(prefix)+len(chunks[0])]
index_pos=len(prefix)+sum(map(len,chunks))
info=[]
for off in pos:
 info.append(rec({b'op':b'\x06',b'ver':n4(1),b'chunk_pos':n8(off),b'start_time':n4(12)+n4(30),b'end_time':n4(14)+n4(30),b'count':n4(4)},b''.join(n4(i)+n4(1) for i in range(4))))
contents=b'#ROSBAG V2.0\n'+bag_header(index_pos)+b''.join(chunks)+b''.join(conns)+b''.join(info)
with tempfile.TemporaryDirectory() as t:
 t=pathlib.Path(t);bag=t/'a.bag';bag.write_bytes(contents)
 idx={'schema':'TRUST_ROBOT_R17_ROS1_INDEX_READONLY_V1','file_sha256':'a'*64,'trajectory_id':'room_02','index_position':index_pos,'connection_count':4,'chunk_count':2,'connections':[{'id':i,'topic':x,'message_type':m.NEEDED[x]} for i,x in enumerate(topics)]}
 x=t/'r17.json';x.write_text(json.dumps(idx))
 samples,modes,n=m.sample(bag,x)
 assert n==2 and modes==['none'] and len(samples)==4
 report={'schema':'TRUST_ROBOT_R18_BOUNDED_ROS1_RECORDED_MESSAGES_V1','recording_sha256':'a'*64,'r17_report_sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'samples':samples,'sampled_chunks':n,'sampled_message_count':8,'recorded_streams_decoded':4}
 for key in ('bag_record_time_is_capture_time_proof','header_stamp_is_capture_time_proof','cross_stream_alignment_performed','physical_sync_verified','extrinsics_verified','raw_recording_modified','github_modified'):report[key]=False
 report['real_pose_factors_generated']=0;report['health_labels']=0
 y=t/'r18.json';y.write_text(json.dumps(report))
 import sys
 sys.argv=['r18_verify',str(bag),str(x),str(y),'a'*64]
 v.main()
 print('R18_POSITIVE_SYNTHETIC_BAG_FIXTURE=PASS')
 print('R18_NEGATIVE_ROS_MESSAGE_CONTROLS=PASS')
