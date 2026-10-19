"""Metadata and serialized-byte adversarial negative controls."""
import copy,hashlib,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r24_stress as m

def denied(call):
    try:call()
    except (ValueError,TypeError,KeyError,IndexError):return
    raise AssertionError('R24_NEGATIVE_CONTROL_NOT_REJECTED')

payload=b'\x00'*4+b'\x01\x00\x00\x00'+b'\x02\x00\x00\x00'+b'\x04\x00\x00\x00'+b'test'+b'full_body'
class Cursor:
    def __init__(self,data):self.data=data
class Decode:
    Cursor=Cursor
    @staticmethod
    def header(c):
        p=c.data
        return {'header_stamp_ns':int.from_bytes(p[4:8],'little')*10**9+int.from_bytes(p[8:12],'little'),
                'frame_id':p[16:20].decode(),'sequence':int.from_bytes(p[:4],'little')}
source={'serialized_message_bytes':len(payload),'serialized_message_sha256':hashlib.sha256(payload).hexdigest(),
 'connection_id':2,'bag_record_time_ns':123,'chunk_offset':456,'header_stamp_ns':10**9+2,'frame_id':'test','sequence':0}
expected={'header_stamp_ns':10**9+2,'frame_id':'test','sequence':0}
assert m.envelope(m.TOPICS[0],payload,source,2,123,456,expected,Decode)
cases=[
 lambda:m.envelope(m.TOPICS[0],payload+b'0',source,2,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],m.mutate_byte(payload,0),source,2,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],m.mutate_byte(payload,4),source,2,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],m.mutate_byte(payload,16),source,2,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],payload,source,3,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],payload,source,2,124,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],payload,source,2,123,457,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],payload,source,2,123,456,dict(expected,frame_id='fake'),Decode),
 lambda:m.envelope('unknown',payload,source,2,123,456,expected,Decode),
 lambda:m.envelope(m.TOPICS[0],None,source,2,123,456,expected,Decode),
 lambda:m.mutate_byte(payload,-1),
 lambda:m.mutate_byte(payload,len(payload)),
]
for f in cases:denied(f)
print('R24_POSITIVE_SOURCE_ENVELOPE_FIXTURE=PASS')
print('R24_LOCAL_NEGATIVE_CONTROLS=12_REJECTED')
