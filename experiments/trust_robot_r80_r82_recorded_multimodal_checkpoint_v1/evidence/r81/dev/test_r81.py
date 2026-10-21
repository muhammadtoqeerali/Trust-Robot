import io
import json
import unittest
import r81_adapter as m

def line(value):
    return (json.dumps(value,sort_keys=True)+'\n').encode()

def fixture():
    header={
        'record_type':'trajectory_header',
        'trajectory':'room_02',
        'bag_relative_path':'raw/rosbags/room_02.bag',
        'world_frame_id':'phase2_lidar_first_scan_origin',
        'body_frame_id':'velodyne',
        'relative_pose_source_id':m.SOURCE_ID,
        'initial_timestamp_ns':100,
        'initial_pose_world_T_body':{
            'translation_m':[0,0,0],
            'quaternion_wxyz':[1,0,0,0]
        },
        'reference_data_used':False,
        'confirmation_test_data_used':False
    }

    increment={
        'record_type':'relative_pose',
        'trajectory':'room_02',
        'scan_index':1,
        'previous_header_stamp_ns':100,
        'current_header_stamp_ns':200,
        'header_delta_ns':100,
        'delta_prev_lidar_T_current_lidar':{
            'translation_m':[1,0,0],
            'quaternion_wxyz':[1,0,0,0]
        },
        'state_world_T_lidar':{
            'translation_m':[1,0,0],
            'quaternion_wxyz':[1,0,0,0]
        },
        'diagnostics':{
            'source_point_count':10,
            'target_point_count':11,
            'fixed_point_iterations':2,
            'final_correspondence_count':10,
            'final_nearest_neighbor_rmse_m':0.25,
            'correspondence_rejection_used':False,
            'voxel_downsampling_used':False
        },
        'scientific_scope':{
            key:False for key in (
                'reference_data_used',
                'confirmation_test_data_used',
                'scan_temporal_reference_verified',
                'per_point_time_used',
                'deskew_performed',
                'correspondence_rejection_used',
                'voxel_downsampling_used',
                'ate_computed',
                'rpe_computed',
                'trajectory_scoring_performed'
            )
        }
    }

    complete={
        'record_type':'trajectory_complete',
        'trajectory':'room_02',
        'scan_count':2,
        'increment_count':1,
        'final_timestamp_ns':200,
        'final_state_world_T_lidar':{
            'translation_m':[1,0,0],
            'quaternion_wxyz':[1,0,0,0]
        },
        'reference_data_used':False,
        'confirmation_test_data_used':False,
        'trajectory_scoring_performed':False
    }

    return [header,increment,complete]

class TestR81(unittest.TestCase):
    def load(self,change=None):
        data=fixture()
        if change:
            change(data)
        stream=io.BytesIO(b''.join(map(line,data)))
        return m.validate_stream(stream,'room_02',1)

    def reject(self,change):
        with self.assertRaises(
            (m.AdmissionError,ValueError,KeyError,TypeError)
        ):
            self.load(change)

    def test_valid(self):
        result=self.load()
        self.assertEqual(result['increments'],1)
        self.assertEqual(result['scans'],2)

    def test_deterministic(self):
        self.assertEqual(self.load(),self.load())

    def test_rotation_composition(self):
        q=(2**-0.5,0,0,2**-0.5)
        first=m.compose(
            ((0,0,0),(1,0,0,0)),
            ((1,0,0),q)
        )
        second=m.compose(
            first,
            ((1,0,0),(1,0,0,0))
        )
        self.assertAlmostEqual(second[0][0],1.0,places=12)
        self.assertAlmostEqual(second[0][1],1.0,places=12)

    def test_wrong_train(self):
        self.reject(
            lambda a:a[0].update(trajectory='hall_02')
        )

    def test_scan_index(self):
        self.reject(
            lambda a:a[1].update(scan_index=2)
        )

    def test_timestamp_gap(self):
        self.reject(
            lambda a:a[1].update(header_delta_ns=99)
        )

    def test_pose_chain(self):
        self.reject(
            lambda a:a[1]['state_world_T_lidar'].update(
                translation_m=[5,0,0]
            )
        )

    def test_invalid_quaternion(self):
        self.reject(
            lambda a:a[1]['delta_prev_lidar_T_current_lidar'].update(
                quaternion_wxyz=[0,0,0,0]
            )
        )

    def test_gt_claim(self):
        self.reject(
            lambda a:a[1]['scientific_scope'].update(
                ate_computed=True
            )
        )

    def test_heldout_claim(self):
        self.reject(
            lambda a:a[0].update(
                confirmation_test_data_used=True
            )
        )

    def test_truncated(self):
        self.reject(lambda a:a.pop())

    def test_fake_completion(self):
        self.reject(
            lambda a:a[2].update(increment_count=2)
        )

    def test_altered_frontend(self):
        self.reject(
            lambda a:a[1]['diagnostics'].update(
                voxel_downsampling_used=True
            )
        )

if __name__=='__main__':
    unittest.main(verbosity=2)
