"""Fixed-width 12-bit offline LZW; validate immutable Git object SHA1."""
import base64
import hashlib
import pathlib
import sys

BLOBS = {
 'calibration_results.txt':'f2b1180f9cdef4e665332a09973f9acba9d9d34e',
 'my_params_camera.yaml':'9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6',
 'my_params_lidar.yaml':'a768b1a8f8baa5649009c941817a51ff3f3e00e9'
}

def decode(encoded):
    data=base64.b64decode(''.join(encoded.split()),validate=True)
    if len(data)%3:
        raise ValueError('INVALID_12_BIT_PACKING')

    table={i:bytes([i]) for i in range(256)}
    previous=None
    nextcode=258
    out=bytearray()
    finished=False

    for i in range(0,len(data),3):
        a,b,c=data[i:i+3]
        for code in ((a<<4)|(b>>4),((b&15)<<8)|c):
            if code==257:
                finished=True
                break

            if code==256:
                table={i:bytes([i]) for i in range(256)}
                previous=None
                nextcode=258
                continue

            if code in table:
                current=table[code]
            elif previous is not None and code==nextcode:
                current=previous+previous[:1]
            else:
                raise ValueError('INVALID_LZW_SEQUENCE')

            out.extend(current)

            if len(out)>200000:
                raise ValueError('SOURCE_SIZE_BOUND')

            if previous is not None and nextcode<=4095:
                table[nextcode]=previous+current[:1]
                nextcode+=1
            previous=current

        if finished:
            break

    if not finished:
        raise ValueError('MISSING_LZW_END')

    return bytes(out)

def run(encoded_dir,out_dir):
    out_dir.mkdir(mode=0o700)

    for name,expected in BLOBS.items():
        encoded=(encoded_dir/(name+'.lzw12.b64')).read_text()
        original=decode(encoded)
        gitblob=hashlib.sha1(
            b'blob '+str(len(original)).encode()+b'\x00'+original
        ).hexdigest()

        if gitblob!=expected:
            raise ValueError(
                'UPSTREAM_GIT_BLOB_MISMATCH:'+name+':'+gitblob
            )
        if len(original)>15000 or not original:
            raise ValueError('SOURCE_FILE_LIMIT')

        with (out_dir/name).open('xb') as handle:
            handle.write(original)

        print('R46_GIT_BLOB_VERIFIED='+name+' '+expected)

if __name__=='__main__':
    run(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
