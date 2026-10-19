"""Challenge both R18 readers with mixed op-7 connection and op-2 messages."""
import hashlib
from pathlib import Path
import struct
import tempfile
import r18_decode as decoder
import r18_verify as verifier
p4=lambda v:struct.pack('<I',v)
def fmt(fields):
    return b''.join(p4(len(k+b'='+v))+k+b'='+v for k,v in fields.items())
def rec(fields,data):
    head=fmt(fields)
    return p4(len(head))+head+p4(len(data))+data
c_id=3
topic='/handsfree/imu'
msg_type='sensor_msgs/Imu'
md5='abc123'
definition=b'fixture definition, no physical source'
index={c_id:{'topic':topic,'message_type':msg_type,'md5sum':md5,'message_definition_sha256':hashlib.sha256(definition).hexdigest()}}
def connection(cid=c_id,t=topic,m=msg_type,md=md5,d=definition,op=b'\x07'):
    return rec({b'op':op,b'conn':p4(cid),b'topic':t.encode()},fmt({b'topic':t.encode(),b'type':m.encode(),b'md5sum':md.encode(),b'message_definition':d}))
def message():return rec({b'op':b'\x02',b'conn':p4(c_id),b'time':p4(12)+p4(345)},b'fixture bytes')
def check(raw,allowed):
    with tempfile.TemporaryDirectory() as temp:
        file=Path(temp)/'fixture.bag'
        file.write_bytes(rec({b'op':b'\x05',b'compression':b'none',b'size':p4(len(raw))},raw))
        if allowed:
            assert len(list(decoder.messages(raw,index)))==1
            with file.open('rb') as handle:assert len(list(verifier.chunk_messages(handle,0,index)))==1
        else:
            for run in (lambda:list(decoder.messages(raw,index)),lambda:list(verifier.chunk_messages(file.open('rb'),0,index))):
                try:run()
                except (ValueError,KeyError,UnicodeError):pass
                else:raise AssertionError('MALFORMED_RECORD_ACCEPTED')
check(connection()+message(),True)
for wrong in (connection(cid=99),connection(t='/mismatched'),connection(m='sensor_msgs/Image'),connection(md='bad'),connection(d=b'corrupted'),connection(op=b'\x04')):
    check(wrong+message(),False)
print('R18_CONNECTION_OP7_WITH_MESSAGE=SUPPORTED_BY_BOTH_READERS')
print('R18_ADVERSARIAL_CONNECTION_CONTROLS=6_REJECTED_BY_BOTH')
