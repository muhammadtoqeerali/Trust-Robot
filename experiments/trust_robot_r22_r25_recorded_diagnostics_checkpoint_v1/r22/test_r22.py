"""Pure unit/negative checks for destructive input and boundary cases."""
import copy, math, pathlib, struct,sys
import cv2,numpy as np
root=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(root))
import r22_content as e

def denied(call):
    try:call()
    except (ValueError,TypeError,OverflowError):return
    raise AssertionError('R22 negative control accepted')

sample=np.zeros((32,48,3),dtype=np.uint8)
sample[:,:,1]=127
ok,jpg=cv2.imencode('.jpg',sample)
assert ok
cam=e.image_diagnostic(jpg.tobytes())
assert cam['width']==48 and cam['height']==32 and cam['decoded_pixel_count']==1536
assert cam['grayscale_min']<=cam['grayscale_mean']<=cam['grayscale_max']
imu=e.imu_diagnostic(struct.pack('<37d',*([0.0]*37)))
assert imu['angular_velocity_norm_rad_s']==0
xyz=b''.join(struct.pack('<fff',float(i),float(i+1),float(i+2))+b'\x00'*10 for i in range(4))
fields=[{'name':n,'offset':4*i,'datatype':7,'count':1} for i,n in enumerate(('x','y','z'))]
fields += [{'name':'intensity','offset':12,'datatype':7,'count':1},
    {'name':'ring','offset':16,'datatype':4,'count':1},
    {'name':'time','offset':18,'datatype':7,'count':1}]
res=e.lidar_diagnostic(xyz,fields,4,1,22,88,False)
assert res['finite_xyz_count']==4 and res['range_max_m']>res['range_min_m']
negative=[lambda:e.image_diagnostic(b'bad'),
    lambda:e.image_diagnostic(jpg.tobytes()[:-2]),
    lambda:e.image_diagnostic(jpg.tobytes()+b'\x00'),
    lambda:e.imu_diagnostic(b'\x00'*295),
    lambda:e.imu_diagnostic(struct.pack('<37d',*([math.nan]+[0.0]*36))),
    lambda:e.lidar_diagnostic(xyz,fields,4,1,21,88,False),
    lambda:e.lidar_diagnostic(xyz,fields,4,1,22,90,False),
    lambda:e.lidar_diagnostic(xyz,fields,4,1,22,88,True),
    lambda:e.lidar_diagnostic(xyz,fields,4,2,22,88,False),
    lambda:e.lidar_diagnostic(xyz,fields[:5],4,1,22,88,False),
    lambda:e.lidar_diagnostic(xyz[:-1],fields,4,1,22,88,False),
]
for check in negative:denied(check)
print('R22_SYNTHETIC_CAMERA_IMU_LIDAR_DIAGNOSTICS=PASS')
print('R22_NEGATIVE_BINARY_LAYOUT_CONTROLS='+str(len(negative))+'_REJECTED')
