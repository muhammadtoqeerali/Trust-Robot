import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from trust_robot.real_rosbag2_metadata_adapter_v1 import BagInventoryError, inventory_bag


def make_bag(folder, messages=((1, 10), (1, 20), (2, 15)), valid=True):
    db = folder / 'bag_0.db3'
    c = sqlite3.connect(db)
    c.execute('CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT, type TEXT)')
    if valid:
        c.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY, topic_id INTEGER, timestamp INTEGER, data BLOB)')
    else:
        c.execute('CREATE TABLE invalid(id INTEGER PRIMARY KEY)')
    c.execute('INSERT INTO topics VALUES(1, "/camera", "sensor_msgs/msg/Image")')
    c.execute('INSERT INTO topics VALUES(2, "/imu", "sensor_msgs/msg/Imu")')
    if valid:
        for i, (topic_id, stamp) in enumerate(messages, 1):
            c.execute('INSERT INTO messages VALUES(?,?,?,?)', (i, topic_id, stamp, b'PRIVATE_SENSOR_PAYLOAD'))
    c.commit()
    c.close()
    return db


class AdapterTests(unittest.TestCase):
    def test_two_topics_three_messages(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d))
            result = inventory_bag(Path(d))
            self.assertEqual(result['total_messages'], 3)
            self.assertEqual(len(result['topics']), 2)
            self.assertEqual(result['topics'][0]['first_recorder_timestamp_ns'], 10)
            self.assertEqual(result['topics'][0]['last_recorder_timestamp_ns'], 20)

    def test_empty_topics_are_not_measured(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d), messages=())
            result = inventory_bag(Path(d))
            self.assertEqual(result['total_messages'], 0)
            self.assertIsNone(result['topics'][0]['first_recorder_timestamp_ns'])
            self.assertEqual(result['real_factor_count'], 0)

    def test_invalid_schema_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d), valid=False)
            with self.assertRaises(BagInventoryError):
                inventory_bag(Path(d))

    def test_negative_recorder_stamp_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d), messages=((1, -3),))
            with self.assertRaises(BagInventoryError):
                inventory_bag(Path(d))

    def test_orphan_message_refused(self):
        with tempfile.TemporaryDirectory() as d:
            make_bag(Path(d), messages=((99, 10),))
            with self.assertRaises(BagInventoryError):
                inventory_bag(Path(d))

    def test_symlinked_shard_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / 'original'
            original.mkdir()
            make_bag(original)
            target = root / 'bag'
            target.mkdir()
            (target / 'bag_0.db3').symlink_to(original / 'bag_0.db3')
            with self.assertRaises(BagInventoryError):
                inventory_bag(target)

    def test_symlinked_bag_directory_refused(self):
        with tempfile.TemporaryDirectory() as d:
            original = Path(d) / 'original'
            original.mkdir()
            make_bag(original)
            (Path(d) / 'link').symlink_to(original, target_is_directory=True)
            with self.assertRaises(BagInventoryError):
                inventory_bag(Path(d) / 'link')

    def test_original_bytes_unmodified(self):
        with tempfile.TemporaryDirectory() as d:
            db = make_bag(Path(d))
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            result = inventory_bag(Path(d))
            self.assertEqual(result['total_messages'], 3)
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)

if __name__ == '__main__':
    unittest.main()
