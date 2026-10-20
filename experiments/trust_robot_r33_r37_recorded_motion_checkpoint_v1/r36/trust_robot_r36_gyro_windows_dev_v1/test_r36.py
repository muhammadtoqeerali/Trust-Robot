import ast,copy,math,pathlib,sys
import numpy as np
import r36_gyro_windows as m
import r36_independent_verify as v
from scipy.spatial.transform import Rotation

for f in pathlib.Path(sys.argv[1]).glob('*.py'):
    ast.parse(
        f.read_text(),
        filename=str(f)
    )

q=v.multiply(
    v.quaternion([0,.003,0]),
    v.quaternion([.005,0,0])
)
mat=(
    Rotation.from_rotvec([0,.003,0])
    *Rotation.from_rotvec([.005,0,0])
).as_matrix()

assert np.allclose(
    mat,v.rotmat(q),atol=1e-12
)
assert np.allclose(
    v.rotmat(v.quaternion([0,0,0])),
    np.eye(3),
    atol=1e-12
)

print('R36_PYTHON_AST_AND_INDEPENDENT_SO3_MANUFACTURED=PASS')

example={
    'schema':
        'TRUST_ROBOT_R36_TRAIN_GYRO_THREE_SAMPLE_WINDOWS_V1',
    'trajectory_id':'room_02',
    'split':'train',
    'window_count_per_stream':8,
    'source_message_count':48,
    'total_time_intervals':32,
    'real_pose_factors_generated':0,
    'health_labels_generated':0,
    'new_sensor_acquisitions':0,
    **{key:False for key in m.FLAGS}
}
example['streams']={}

for ti,topic in enumerate(m.TOPICS):
    rows=[]
    for k in range(8):
        records=[
            {
                'chunk_offset':ti*100+k,
                'frame_id':m.FRAMES[topic],
                'sequence':3*k+j,
                'header_stamp_ns':
                    1_000_000*k+5_000*j,
                'serialized_message_sha256':
                    '%064x'%(1+ti*100+3*k+j)
            }
            for j in range(3)
        ]
        rows.append({
            'window_index':k,
            'messages':records,
            'samples':[{}, {}, {}],
            'gyro_numerics':{
                'factor':None,
                'translation_m':None,
                'velocity_m_s':None,
                'rotation_is_calibrated_robot_pose':False,
                'two_step_composed_rotation_matrix_diagnostic':
                    np.eye(3).tolist()
            },
            'physically_qualified_rotation':False
        })
    example['streams'][topic]=rows

m.safety(example)

count=0
for key in (
    *m.FLAGS,
    'real_pose_factors_generated',
    'health_labels_generated',
    'new_sensor_acquisitions'
):
    challenge=copy.deepcopy(example)
    challenge[key]=(
        True if key in m.FLAGS else 1
    )
    try:
        m.safety(challenge)
    except ValueError:
        count+=1
    else:
        raise AssertionError(
            'PROMOTION_ACCEPTED:'+key
        )

for change in (
    'test_split',
    'source_repeat',
    'pose_factor',
    'not_so3',
    'gap_reversed'
):
    challenge=copy.deepcopy(example)
    w=challenge['streams'][m.TOPICS[0]][0]

    if change=='test_split':
        challenge['split']='confirmation_test'

    elif change=='source_repeat':
        for j in range(3):
            challenge['streams'][m.TOPICS[0]][1][
                'messages'
            ][j]['chunk_offset']=w['messages'][0]['chunk_offset']
        challenge['streams'][m.TOPICS[0]][1][
            'messages'
        ][0]['serialized_message_sha256']=w['messages'][0][
            'serialized_message_sha256'
        ]

    elif change=='pose_factor':
        w['gyro_numerics']['factor']=[1,2,3]

    elif change=='not_so3':
        w['gyro_numerics'][
            'two_step_composed_rotation_matrix_diagnostic'
        ][0][0]=2.0

    else:
        w['messages'][1]['header_stamp_ns']=w[
            'messages'
        ][0]['header_stamp_ns']

    try:
        m.safety(challenge)
    except ValueError:
        count+=1
    else:
        raise AssertionError(
            'CONTROL_ACCEPTED:'+change
        )

assert count==len(m.FLAGS)+3+5

print(
    'R36_NEGATIVE_SCIENTIFIC_GEOMETRIC_CONTROLS=%d_REJECTED'
    %count
)
