
from pathlib import Path
import tempfile
import unittest

from trust_robot.m2dgr_manifest_builder import (
    build_records,
)


class M2DGRManifestBuilderTests(unittest.TestCase):

    def test_real_dataset_record_generation(self):

        root = Path(
            "/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR"
        )

        records, synchronization = build_records(
            root
        )

        self.assertEqual(
            len(records),
            36,
        )

        self.assertEqual(
            set(records[0].streams[0].stream_id),
            set(records[0].streams[0].stream_id),
        )

        self.assertEqual(
            len(synchronization),
            36,
        )


if __name__ == "__main__":
    unittest.main()
