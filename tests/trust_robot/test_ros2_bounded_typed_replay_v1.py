"""Synthetic tests for private bounded replay only, never physical qualification."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from trust_robot import ros2_bounded_typed_replay_v1 as m

PLAN = (
    ('/imu', 'sensor_msgs/msg/Imu', 2),
    ('/left/camera_info', 'sensor_msgs/msg/CameraInfo', 1),
    ('/right/camera_info', 'sensor_msgs/msg/CameraInfo', 1),
    ('/left/image', 'sensor_msgs/msg/Image', 1),
    ('/right/image', 'sensor_msgs/msg/Image', 1),
    ('/lidar', 'sensor_msgs/msg/PointCloud2', 1),
)

def header(frame='fixture',sec=1,nanosec=2):
    return NS(stamp=NS(sec=sec,nanosec=nanosec),frame_id=frame)

def fake(typ):
    h=header()
    if typ.endswith('/Imu'): return NS(header=h,linear_acceleration=NS(x=123))
    if typ.endswith('/CameraInfo'): return NS(header=h,width=1920,height=1200,k=[100])
    if typ.endswith('/Image'): return NS(header=h,width=2,height=1,step=6,encoding='rgb8',data=b'x'*6)
    if typ.endswith('/PointCloud2'):
        return NS(header=h,width=128000,height=1,point_step=26,row_step=3328000,
                  data=b'x'*3328000,fields=[NS(name='x',datatype=7,offset=0,count=1),
                                           NS(name='time',datatype=8,offset=18,count=1)])
    raise ValueError('Unknown fixture type')

def make_bag(folder):
    db=folder/'bag_0.db3'
    c=sqlite3.connect(db)
    c.execute('CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT,type TEXT,serialization_format TEXT)')
    c.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER,timestamp INTEGER,data BLOB)')
    rid=0
    for tid,(topic,typ,take) in enumerate(PLAN,1):
        c.execute('INSERT INTO topics VALUES(?,?,?,?)',(tid,topic,typ,'cdr'))
        for i in range(take):
            rid+=1
            c.execute('INSERT INTO messages VALUES(?,?,?,?)',(rid,tid,100+tid*10+i,b'CDRFIXTURE'))
    c.commit();c.close()
    return db

class ReplayTests(unittest.TestCase):
    def test_7_message_private_replay(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_bag(Path(d))
            before=hashlib.sha256(db.read_bytes()).hexdigest()
            result=m.inspect(Path(d),lambda blob,typ:fake(typ),PLAN)
            self.assertEqual((result['decoded_count'],result['sample_count']),(7,7))
            self.assertTrue(result['recorder_order_monotonic'])
            self.assertEqual(len({x['recorder_envelope_row_id'] for x in result['samples']}),7)
            self.assertEqual(result['timestamp_provenance']['ros_header'],'ROS_MESSAGE_HEADER_UNVERIFIED')
            self.assertTrue(result['raw_measurements_exported'] is False)
            self.assertEqual(result['real_factor_admission'],'DENIED')
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),before)
            self.assertNotIn('123',str(result))
            self.assertNotIn('CDRFIXTURE',str(result))
    def test_no_ros_decoder_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d))
            r=m.inspect(Path(d),None,PLAN)
            self.assertEqual(r['decoded_count'],0)
            self.assertTrue(all(x['status']=='NOT_DECODED_MISSING_TYPED_ROS' for x in r['samples']))
    def test_image_stride_mismatch(self):
        msg=fake('sensor_msgs/msg/Image');msg.step=5
        with self.assertRaises(m.ReplayError):m.extract_record(msg,'sensor_msgs/msg/Image',10)
    def test_real_lidar_shape_accepted(self):
        r=m.extract_record(fake('sensor_msgs/msg/PointCloud2'),'sensor_msgs/msg/PointCloud2',10)
        self.assertEqual((r['width'],r['point_step']),(128000,26))
        self.assertNotIn('data',r)
    def test_cloud_field_out_of_bounds(self):
        msg=fake('sensor_msgs/msg/PointCloud2');msg.fields[1].offset=22
        with self.assertRaises(m.ReplayError):m.extract_record(msg,'sensor_msgs/msg/PointCloud2',10)
    def test_cloud_row_stride_wrong(self):
        msg=fake('sensor_msgs/msg/PointCloud2');msg.row_step-=1
        with self.assertRaises(m.ReplayError):m.extract_record(msg,'sensor_msgs/msg/PointCloud2',10)
    def test_cloud_data_length_wrong(self):
        msg=fake('sensor_msgs/msg/PointCloud2');msg.data=b'x'*27
        with self.assertRaises(m.ReplayError):m.extract_record(msg,'sensor_msgs/msg/PointCloud2',10)
    def test_invalid_header_nano(self):
        msg=fake('sensor_msgs/msg/Imu');msg.header.stamp.nanosec=1_000_000_000
        with self.assertRaises(m.ReplayError):m.extract_record(msg,'sensor_msgs/msg/Imu',10)
    def test_non_cdr_refused(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_bag(Path(d))
            c=sqlite3.connect(db);c.execute("UPDATE topics SET serialization_format='x' WHERE id=1");c.commit();c.close()
            with self.assertRaises(m.ReplayError):m.inspect(Path(d),lambda blob,typ:fake(typ),PLAN)
    def test_symlink_bag_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);orig=root/'original';orig.mkdir();make_bag(orig)
            (root/'link').symlink_to(orig,target_is_directory=True)
            with self.assertRaises(m.ReplayError):m.inspect(root/'link',lambda blob,typ:fake(typ),PLAN)
    def test_symlink_shard_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);orig=root/'original';orig.mkdir();make_bag(orig)
            folder=root/'bag';folder.mkdir();(folder/'bag_0.db3').symlink_to(orig/'bag_0.db3')
            with self.assertRaises(m.ReplayError):m.inspect(folder,lambda blob,typ:fake(typ),PLAN)
    def test_extra_large_cdr_skips_without_read(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_bag(Path(d));c=sqlite3.connect(db)
            c.execute('UPDATE messages SET data=zeroblob(?) WHERE id=1',(m.MAX_MESSAGE_BYTES+1,))
            c.commit();c.close()
            r=m.inspect(Path(d),lambda blob,typ:fake(typ),PLAN)
            self.assertEqual(r['decoded_count'],6)
            self.assertEqual(r['samples'][0]['status'],'SKIPPED_STRICT_CDR_BYTE_BUDGET')
    def test_readonly_recorder_time_out_of_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            db=make_bag(Path(d));c=sqlite3.connect(db)
            c.execute('UPDATE messages SET timestamp=-1 WHERE id=1');c.commit();c.close()
            with self.assertRaises(m.ReplayError):m.inspect(Path(d),lambda blob,typ:fake(typ),PLAN)

    def test_empty_plan_refused(self):
        with self.assertRaises(m.ReplayError): m.validate_plan(())

    def test_duplicate_plan_topic_refused(self):
        with self.assertRaises(m.ReplayError): m.validate_plan((PLAN[0], PLAN[0]))

    def test_plan_exceeds_seven_refused(self):
        with self.assertRaises(m.ReplayError): m.validate_plan((('/imu', 'sensor_msgs/msg/Imu', 7),
                                                                 ('/lidar', 'sensor_msgs/msg/PointCloud2', 1)))

    def test_wrong_expected_topic_inventory_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d))
            with self.assertRaises(m.ReplayError):
                m.inspect(Path(d), lambda blob, typ: fake(typ), PLAN,
                          expected_topics={'/fake': ('sensor_msgs/msg/Imu', 2)})

    def test_wrong_expected_shard_size_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d))
            with self.assertRaises(m.ReplayError):
                m.inspect(Path(d), lambda blob, typ: fake(typ), PLAN,
                          expected_shard_bytes=123)

    def test_missing_metadata_for_pin_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d))
            with self.assertRaises(m.ReplayError):
                m.inspect(Path(d), lambda blob, typ: fake(typ), PLAN,
                          expected_metadata_sha256='0' * 64)

    def test_valid_expected_metadata_and_shard_size(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db = make_bag(root)
            meta = root / 'metadata.yaml'
            meta.write_text('fixture')
            result = m.inspect(root, lambda blob, typ: fake(typ), PLAN,
                               expected_shard_bytes=db.stat().st_size,
                               expected_metadata_sha256=hashlib.sha256(meta.read_bytes()).hexdigest())
            self.assertEqual(result['decoded_count'], 7)

    def test_unsupported_message_type_rejected(self):
        with self.assertRaises(m.ReplayError):
            m.validate_plan((('/custom', 'std_msgs/msg/String', 1),))

if __name__=='__main__':unittest.main()
