import copy
import unittest

import numpy as np

import r104_shared_graph as graph
import r107_incremental as m
import s6_joint_fusion as s6

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def estimator(self,recenter=False):
        g=graph.build("clean",True,13)
        return g,m.IncrementalEstimator(
            g,recenter=recenter
        )

    def test_schema(self):
        self.assertEqual(
            self.report["schema"],m.SCHEMA
        )

    def test_status(self):
        self.assertEqual(
            self.report["status"],
            "PASS_SYNTHETIC_SOFTWARE_ONLY"
        )

    def test_three_scenarios(self):
        self.assertEqual(
            self.report["scenarios"],3
        )

    def test_twelve_ordinary_windows(self):
        self.assertEqual(
            self.report[
                "ordinary_incremental_windows"
            ],12
        )

    def test_twelve_recentered_windows(self):
        self.assertEqual(
            self.report[
                "recentered_incremental_windows"
            ],12
        )

    def test_nine_ordinary_schur(self):
        self.assertEqual(
            self.report[
                "ordinary_schur_marginalizations"
            ],9
        )

    def test_nine_recentered_schur(self):
        self.assertEqual(
            self.report[
                "recentered_schur_marginalizations"
            ],9
        )

    def test_nine_transfers(self):
        self.assertEqual(
            self.report[
                "same_graph_prior_transfers"
            ],9
        )

    def test_five_nodes(self):
        for c in self.report["cases"].values():
            self.assertEqual(c["node_count"],5)

    def test_eight_samples(self):
        for c in self.report["cases"].values():
            self.assertEqual(
                c["admitted_sample_indices"],
                list(range(8))
            )

    def test_four_imu_edges(self):
        for c in self.report["cases"].values():
            self.assertEqual(
                c["imu_factor_count"],4
            )

    def test_no_future_factor(self):
        for c in self.report["cases"].values():
            self.assertFalse(
                c["future_factor_consumed"]
            )

            for w in c["window_ledger"]:
                self.assertFalse(
                    w["future_factors_used"]
                )

    def test_full_rank_windows(self):
        for c in self.report["cases"].values():
            for w in c["window_ledger"]:
                self.assertEqual(
                    w["rank"],
                    w["state_dimension"]
                )

    def test_ordinary_equals_s6(self):
        for c in self.report["cases"].values():
            self.assertLess(
                c["ordinary_vs_s6_max_abs_error"],
                1e-8
            )

    def test_recentered_equals_s6_within_budget(self):
        for c in self.report["cases"].values():
            self.assertLess(
                c["recentered_vs_s6_max_abs_error"],
                2e-5
            )

    def test_no_pose_reuse(self):
        for c in self.report["cases"].values():
            seen=set()

            for e in c["elimination_ledger"]:
                ids=set(e["consumed_pose_ids"])
                self.assertTrue(
                    seen.isdisjoint(ids)
                )
                seen.update(ids)

    def test_imu_chronology(self):
        for c in self.report["cases"].values():
            self.assertEqual(
                c["consumed_imu_edges"],
                [[0,1],[1,2],[2,3]]
            )
            self.assertEqual(
                c["remaining_imu_edges"],
                [[3,4]]
            )

    def test_recentered_prior_node_order(self):
        for c in self.report["cases"].values():
            self.assertEqual(
                [
                    e["retained_nodes"]
                    for e in c["transfer_ledger"]
                ],
                [[1,2],[2,3],[3,4]]
            )

    def test_no_r95_import(self):
        self.assertFalse(
            self.report[
                "r95_backend_imported"
            ]
        )

    def test_no_real_factors(self):
        self.assertFalse(
            self.report[
                "real_sensor_factors_authorized"
            ]
        )

    def test_no_health_or_ate(self):
        self.assertFalse(
            self.report[
                "health_training_authorized"
            ]
        )
        self.assertFalse(
            self.report[
                "ate_rpe_authorized"
            ]
        )

    def test_confirmation_sealed(self):
        self.assertFalse(
            self.report[
                "confirmation_test_accessed"
            ]
        )

    def test_scientific_gates(self):
        self.assertEqual(
            self.report[
                "scientific_gates_closed"
            ],11
        )

    def test_out_of_order_node_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,2)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(2,r,i,p)

        self.assertEqual(est.next_node,1)

    def test_missing_imu_readings_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,r[:1],i,p)

    def test_copied_reading_not_declared(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        copied=(
            copy.deepcopy(r[0]),r[1]
        )

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,copied,i,p)

    def test_wrong_imu_factor_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        other=g["imu_factors"][(1,2)]

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,r,other,p)

    def test_missing_pose_factor_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        self.assertGreater(len(p),0)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,r,i,p[1:])

    def test_duplicate_pose_factor_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,r,i,p+(p[0],))

    def test_future_pose_factor_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        later=m.release(g,3)[2]

        self.assertGreater(len(later),0)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(
                1,r,i,p+(later[0],)
            )

    def test_repeated_node_denied(self):
        g,est=self.estimator()

        r,i,p=m.release(g,1)

        est.ingest(1,r,i,p)

        with self.assertRaises(
            m.IncrementalError
        ):
            est.ingest(1,r,i,p)

    def test_wrong_frame_denied(self):
        g=graph.build("clean",True,13)

        bad=copy.copy(g)
        bad["frame_id"]="RECORDED_BODY"

        with self.assertRaises(
            m.IncrementalError
        ):
            m.IncrementalEstimator(bad)

    def test_real_authorization_denied(self):
        g=graph.build("clean",True,13)

        bad=copy.copy(g)
        bad["real_sensor_factors_authorized"]=True

        with self.assertRaises(
            m.IncrementalError
        ):
            m.IncrementalEstimator(bad)

    def test_bad_node_release_denied(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(
            m.IncrementalError
        ):
            m.release(g,5)

    def test_incomplete_run_denied(self):
        _,est=self.estimator()

        with self.assertRaises(
            m.IncrementalError
        ):
            est.finish()

    def test_recenter_mode_type(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(
            m.IncrementalError
        ):
            m.IncrementalEstimator(
                g,recenter="yes"
            )

    def test_no_physical_streaming_claim(self):
        self.assertFalse(
            self.report[
                "actual_physical_online_streaming_tested"
            ]
        )

    def test_repeat_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
