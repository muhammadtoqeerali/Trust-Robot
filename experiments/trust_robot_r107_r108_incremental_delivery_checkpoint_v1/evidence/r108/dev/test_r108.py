import copy
from dataclasses import replace
import unittest

import r104_shared_graph as graph
import r108_delivery as m

class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report=m.execute()

    def setup_buffer(self,**kwargs):
        g=graph.build("clean",True,13)
        return g,m.DeliveryBuffer(g,**kwargs)

    def reject(self,buffer,packet):
        before=(
            tuple(buffer.arrival_order),
            tuple(buffer.processed_order),
            tuple(sorted(buffer.pending)),
            buffer.estimator.next_node,
        )

        with self.assertRaises(m.DeliveryError):
            buffer.submit(packet)

        after=(
            tuple(buffer.arrival_order),
            tuple(buffer.processed_order),
            tuple(sorted(buffer.pending)),
            buffer.estimator.next_node,
        )

        self.assertEqual(before,after)

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
            self.report["synthetic_scenarios"],3
        )

    def test_twelve_runs(self):
        self.assertEqual(
            self.report["total_solver_runs"],12
        )

    def test_forty_eight_windows(self):
        self.assertEqual(
            self.report["nonlinear_windows"],48
        )

    def test_thirty_six_schur(self):
        self.assertEqual(
            self.report["schur_marginalizations"],36
        )

    def test_eighteen_transfers(self):
        self.assertEqual(
            self.report["same_graph_prior_transfers"],18
        )

    def test_ordered_delivery(self):
        for c in self.report["cases"].values():
            for key,row in c["runs"].items():
                if key.startswith("ordered"):
                    self.assertEqual(
                        row["arrival_order"],
                        [1,2,3,4]
                    )

    def test_reordered_delivery(self):
        for c in self.report["cases"].values():
            for key,row in c["runs"].items():
                if key.startswith("bounded_reorder"):
                    self.assertEqual(
                        row["arrival_order"],
                        [3,2,1,4]
                    )
                    self.assertEqual(
                        row["processed_order"],
                        [1,2,3,4]
                    )

    def test_reorder_peak_bound(self):
        for c in self.report["cases"].values():
            for row in c["runs"].values():
                self.assertLessEqual(
                    row["peak_pending"],3
                )

    def test_reference_accuracy(self):
        for c in self.report["cases"].values():
            for key,row in c["runs"].items():
                threshold=(
                    2e-5 if key.endswith("recentered")
                    else 1e-8
                )

                self.assertLess(
                    row["max_abs_error_vs_s6"],
                    threshold
                )

    def test_no_future_factors(self):
        for c in self.report["cases"].values():
            for row in c["runs"].values():
                self.assertFalse(
                    row["future_factor_consumed"]
                )

    def test_no_duplicate_factors(self):
        for c in self.report["cases"].values():
            for row in c["runs"].values():
                self.assertFalse(
                    row["duplicate_factor_consumed"]
                )

    def test_valid_immediate_delivery(self):
        g,b=self.setup_buffer()

        self.assertEqual(
            b.submit(m.make_packet(g,1)),
            (1,)
        )

    def test_buffered_delivery_drains(self):
        g,b=self.setup_buffer()

        self.assertEqual(
            b.submit(m.make_packet(g,3)),()
        )

        self.assertEqual(
            b.submit(m.make_packet(g,2)),()
        )

        self.assertEqual(
            b.submit(m.make_packet(g,1)),
            (1,2,3)
        )

        self.assertEqual(
            b.submit(m.make_packet(g,4)),
            (4,)
        )

        b.finish()

    def test_duplicate_pending_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,2)

        b.submit(p)
        self.reject(b,p)

    def test_duplicate_consumed_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        b.submit(p)
        self.reject(b,p)

    def test_future_horizon_denied(self):
        g,b=self.setup_buffer()
        self.reject(
            b,m.make_packet(g,4)
        )

    def test_pending_capacity_denied(self):
        g,b=self.setup_buffer(
            max_pending=1
        )

        b.submit(m.make_packet(g,3))

        self.reject(
            b,m.make_packet(g,2)
        )

        b.submit(m.make_packet(g,1))
        b.submit(m.make_packet(g,2))
        b.submit(m.make_packet(g,4))
        b.finish()

    def test_missing_node_finish_denied(self):
        g,b=self.setup_buffer()

        b.submit(m.make_packet(g,1))
        b.submit(m.make_packet(g,2))
        b.submit(m.make_packet(g,4))

        with self.assertRaises(m.DeliveryError):
            b.finish()

        self.assertFalse(b.closed)

        b.submit(m.make_packet(g,3))
        b.finish()

    def test_missing_imu_reading_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,readings=p.readings[:1]
            )
        )

    def test_copied_reading_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,
                readings=(
                    copy.deepcopy(p.readings[0]),
                    p.readings[1]
                )
            )
        )

    def test_wrong_imu_factor_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,
                imu_factor=g["imu_factors"][(1,2)]
            )
        )

    def test_missing_pose_factor_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.assertGreater(
            len(p.pose_factors),0
        )

        self.reject(
            b,replace(
                p,
                pose_factors=p.pose_factors[1:]
            )
        )

    def test_duplicate_pose_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,
                pose_factors=(
                    p.pose_factors+
                    p.pose_factors[:1]
                )
            )
        )

    def test_future_pose_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)
        future=m.make_packet(g,3)

        self.assertGreater(
            len(future.pose_factors),0
        )

        self.reject(
            b,replace(
                p,
                pose_factors=(
                    p.pose_factors+
                    future.pose_factors[:1]
                )
            )
        )

    def test_wrong_frame_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,frame_id="recorded_base_link"
            )
        )

    def test_wrong_origin_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,origin="RECORDED_SENSOR"
            )
        )

    def test_false_physical_clock_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,physical_clock_verified=True
            )
        )

    def test_false_real_source_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,real_sensor_factors_authorized=True
            )
        )

    def test_wrong_node_time_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,node_time_ns=p.node_time_ns+1
            )
        )

    def test_wrong_imu_sample_ids_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,sample_indices=(0,2)
            )
        )

    def test_wrong_session_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        self.reject(
            b,replace(
                p,session="UNTRUSTED_SESSION"
            )
        )

    def test_cross_graph_object_denied(self):
        g,b=self.setup_buffer()

        other=graph.build("clean",True,13)
        p=m.make_packet(other,1)

        self.reject(b,p)

    def test_graph_mutation_denied(self):
        g,b=self.setup_buffer()
        p=m.make_packet(g,1)

        bad=copy.copy(g)
        bad["real_sensor_factors_authorized"]=True

        with self.assertRaises(m.DeliveryError):
            m.DeliveryBuffer(bad)

        self.assertEqual(
            b.submit(p),(1,)
        )

    def test_invalid_packet_type_denied(self):
        _,b=self.setup_buffer()
        self.reject(b,{})

    def test_bad_pending_bound_denied(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(m.DeliveryError):
            m.DeliveryBuffer(
                g,max_pending=3
            )

    def test_bad_ahead_bound_denied(self):
        g=graph.build("clean",True,13)

        with self.assertRaises(m.DeliveryError):
            m.DeliveryBuffer(
                g,max_ahead=3
            )

    def test_closed_session_denied(self):
        g,b=self.setup_buffer()

        for node in range(1,5):
            b.submit(m.make_packet(g,node))

        b.finish()

        with self.assertRaises(m.DeliveryError):
            b.submit(m.make_packet(g,4))

    def test_no_physical_claims(self):
        for key in (
            "actual_hardware_capture_tested",
            "physical_arrival_jitter_measured",
            "execution_deadlines_verified",
            "transport_authentication_verified",
            "transactional_solver_rollback_proven",
            "real_sensor_factors_authorized",
            "health_training_authorized",
            "ate_rpe_authorized",
            "confirmation_test_accessed",
            "raw_gt_or_rosbags_opened",
        ):
            self.assertFalse(self.report[key])

    def test_scientific_gates(self):
        self.assertEqual(
            self.report["scientific_gates_closed"],
            11
        )

    def test_determinism(self):
        self.assertEqual(
            m.canonical(self.report),
            m.canonical(m.execute())
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
