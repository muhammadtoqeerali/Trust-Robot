"""No raw data: test R76 format against existing recorded-factor guards."""
import copy
import pathlib
import sys
import unittest

import r77_bridge as b

REPO = pathlib.Path(sys.argv[1])
R76 = pathlib.Path(sys.argv[2])
sys.argv = [sys.argv[0]]


class BridgeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gates, cls.timing, cls.snapshot = b.load_state(
            REPO, R76
        )

    def test_all_11_format_candidates(self):
        for claim in self.gates:
            with self.subTest(claim=claim):
                got = b.assess_candidate(
                    b.synthetic_candidate(claim, self.gates),
                    self.gates,
                    self.snapshot
                )
                self.assertFalse(
                    got['recorded_sensor_factor_admitted']
                )
                self.assertFalse(
                    got['multimodal_pose_factor_admitted']
                )

    def test_all_11_filled_author_like_are_nonproof(self):
        for claim in self.gates:
            with self.subTest(claim=claim):
                got = b.assess_candidate(
                    b.synthetic_candidate(
                        claim,
                        self.gates,
                        'author_source_candidate',
                        True
                    ),
                    self.gates,
                    self.snapshot
                )
                self.assertFalse(
                    got['physical_clock_qualified']
                )
                self.assertFalse(
                    got['physical_calibration_qualified']
                )

    def test_original_execution_gates(self):
        self.assertTrue(
            b.assert_real_factor_gates_closed(self.snapshot)
        )

    def test_reject_authorization_and_heldout_claims(self):
        changes = (
            {'factor_execution_authorized': True},
            {'physical_validation_completed': True},
            {'confirmation_test_used': True},
            {'split': 'confirmation_test'},
            {'trajectory_id': 'room_01'},
            {'independent_validation_sha256': 'b' * 64},
        )

        for update in changes:
            with self.subTest(update=update):
                x = b.synthetic_candidate(
                    'mocap_body_to_lidar_physically_verified',
                    self.gates
                )
                x.update(update)

                with self.assertRaises(b.BridgeError):
                    b.assess_candidate(
                        x, self.gates, self.snapshot
                    )

    def test_forged_claim_and_extra_field(self):
        for mode in ('unknown', 'extraneous'):
            with self.subTest(mode=mode):
                x = b.synthetic_candidate(
                    'mocap_body_to_lidar_physically_verified',
                    self.gates
                )

                if mode == 'unknown':
                    x['claim_id'] = 'fake_gate'
                else:
                    x['evidence_fields'][
                        'fake_calibration_status'
                    ] = 'VERIFIED'

                with self.assertRaises(b.BridgeError):
                    b.assess_candidate(
                        x, self.gates, self.snapshot
                    )

    def test_reject_stale_or_edited_contract(self):
        gates, timing = b.intake.frozen_boundary(*[
            b.json_file(REPO / p, sha)
            for p, sha in b.FROZEN.values()
        ])

        contract = b.json_file(
            R76 / 'r76_source_intake_contract_v1.json',
            b.CONTRACT_SHA
        )
        validator = b.json_file(
            R76 / 'r76_independent_validation_v1.json',
            b.VALIDATION_SHA
        )
        pins = {
            name: sha
            for name, (_, sha) in b.FROZEN.items()
        }

        changes = (
            ('new_execution_authorizations', 1),
            ('scientific_gates_closed', 10),
            ('historical_r43_raw_gt_status_not_current', False),
            ('mocap_frame_qualified', True),
        )

        for field, value in changes:
            with self.subTest(field=field):
                forged = copy.deepcopy(contract)
                forged[field] = value

                with self.assertRaises(b.BridgeError):
                    b.check_contract(
                        forged, validator, gates, timing, pins
                    )

    def test_reject_mutated_historical_receipt(self):
        objs = [
            b.json_file(REPO / p, sha)
            for p, sha in b.FROZEN.values()
        ]

        fake = copy.deepcopy(objs)
        name = next(iter(fake[0]['gate_receipts']))

        fake[0]['gate_receipts'][name][
            'physical_qualification_authorized'
        ] = True

        with self.assertRaises(b.intake.IntakeError):
            b.intake.frozen_boundary(*fake)

        fake = copy.deepcopy(objs)
        name = next(iter(fake[1]['receipts']))

        fake[1]['receipts'][name][
            'physical_measurement_qualified'
        ] = True

        with self.assertRaises(b.intake.IntakeError):
            b.intake.frozen_boundary(*fake)

    def test_reject_forged_split(self):
        snapshot = copy.deepcopy(self.snapshot)

        snapshot['by_id']['room_02'][
            'split'
        ] = 'confirmation_test'

        with self.assertRaises(b.BridgeError):
            b.assess_candidate(
                b.synthetic_candidate(
                    'mocap_body_to_lidar_physically_verified',
                    self.gates
                ),
                self.gates,
                snapshot
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
