"""R108: bounded synthetic event-order replay and fault admission.

Wraps the existing R107 sequential estimator.

No physical transport, timestamps from hardware,
real-time deadline guarantees, authenticated delivery,
or R95 Gaussian prior imports are tested.
"""

from dataclasses import dataclass
from dataclasses import replace
import hashlib
import json

import numpy as np

import r104_shared_graph as graph
import r107_incremental as incremental
import s6_joint_fusion as s6

SCHEMA="TRUST_ROBOT_R108_BOUNDED_SYNTHETIC_DELIVERY_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

SCHEDULES={
    "ordered":(1,2,3,4),
    "bounded_reorder":(3,2,1,4),
}

class DeliveryError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise DeliveryError(reason)

def canonical(value):
    return (
        json.dumps(
            value,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode()

def validate_graph(g):
    try:
        graph.validate(g)
    except graph.GraphAdmissionError as exc:
        raise DeliveryError("GRAPH_ADMISSION_DENIED") from exc

    return True

def session_id(g):
    validate_graph(g)

    payload={
        "schema":SCHEMA,
        "fixture_digest":g["fixture_digest"],
        "condition":g["condition"],
        "camera_enabled":g["camera_enabled"],
        "seed":g["seed"],
        "origin":g["origin"],
        "frame_id":g["frame_id"],
        "node_times_ns":list(g["node_times_ns"]),
    }

    # Local deterministic correlation label.
    # Not a digital signature or authentication token.
    return hashlib.sha256(canonical(payload)).hexdigest()

@dataclass(frozen=True)
class Packet:
    node: int
    session: str
    fixture_digest: str
    node_time_ns: int
    sample_indices: tuple
    readings: tuple
    imu_factor: object
    pose_factors: tuple
    origin: str
    frame_id: str
    physical_clock_verified: bool=False
    real_sensor_factors_authorized: bool=False

def make_packet(g,node):
    validate_graph(g)

    need(
        type(node) is int
        and 1<=node<=4,
        "PACKET_NODE"
    )

    readings,imu,pose=incremental.release(
        g,node
    )

    return Packet(
        node=node,
        session=session_id(g),
        fixture_digest=g["fixture_digest"],
        node_time_ns=g["node_times_ns"][node],
        sample_indices=tuple(
            g["imu_owner"][(node-1,node)]
        ),
        readings=readings,
        imu_factor=imu,
        pose_factors=pose,
        origin=g["origin"],
        frame_id=g["frame_id"],
    )

class DeliveryBuffer:
    """Deterministic bounded reorder buffer.

    A rejected packet does not enter the queue or
    invoke the estimator. Numerical estimator failures
    are fail-stop; transactional rollback is NOT claimed.
    """

    def __init__(
        self,g,*,recenter=False,
        max_ahead=2,max_pending=2
    ):
        validate_graph(g)

        need(
            type(recenter) is bool,
            "RECENTER_TYPE"
        )

        need(
            type(max_ahead) is int
            and 0<=max_ahead<=2,
            "AHEAD_BOUND"
        )

        need(
            type(max_pending) is int
            and 1<=max_pending<=2,
            "PENDING_BOUND"
        )

        self.g=g
        self.session=session_id(g)

        self.estimator=incremental.IncrementalEstimator(
            g,recenter=recenter
        )

        self.max_ahead=max_ahead
        self.max_pending=max_pending

        self.pending={}
        self.received=set()

        self.arrival_order=[]
        self.processed_order=[]

        self.peak_pending=0
        self.closed=False

    def validate_packet(self,p):
        validate_graph(self.g)

        need(
            type(p) is Packet,
            "PACKET_TYPE"
        )

        need(
            type(p.node) is int
            and 1<=p.node<=4,
            "PACKET_NODE"
        )

        need(
            p.session==self.session
            and p.fixture_digest==
                self.g["fixture_digest"],
            "SESSION_OR_FIXTURE_MISMATCH"
        )

        need(
            p.origin==graph.ANALYTIC_ORIGIN
            and p.frame_id==graph.ANALYTIC_FRAME,
            "UNAUTHORIZED_SOURCE_FRAME"
        )

        need(
            p.physical_clock_verified is False
            and p.real_sensor_factors_authorized is False,
            "PHYSICAL_AUTHORIZATION_DENIED"
        )

        need(
            type(p.node_time_ns) is int
            and p.node_time_ns==
                self.g["node_times_ns"][p.node],
            "SYNTHETIC_NODE_TIME_MISMATCH"
        )

        need(
            type(p.sample_indices) is tuple
            and p.sample_indices==tuple(
                self.g["imu_owner"][
                    (p.node-1,p.node)
                ]
            ),
            "IMU_SAMPLE_IDENTITY_MISMATCH"
        )

        readings,imu,poses=incremental.release(
            self.g,p.node
        )

        need(
            type(p.readings) is tuple
            and len(p.readings)==2
            and all(
                a is b
                for a,b in zip(
                    p.readings,readings
                )
            ),
            "IMU_READING_IDENTITY"
        )

        need(
            p.imu_factor is imu,
            "IMU_FACTOR_IDENTITY"
        )

        need(
            type(p.pose_factors) is tuple
            and len(p.pose_factors)==len(poses)
            and all(
                a is b
                for a,b in zip(
                    p.pose_factors,poses
                )
            ),
            "POSE_FACTOR_IDENTITY"
        )

        return True

    def submit(self,p):
        need(
            not self.closed,
            "SESSION_CLOSED"
        )

        # Validate entire packet BEFORE queue mutation.
        self.validate_packet(p)

        expected=self.estimator.next_node

        need(
            p.node>=expected
            and p.node not in self.received,
            "DUPLICATE_OR_STALE_NODE"
        )

        need(
            p.node-expected<=self.max_ahead,
            "ARRIVAL_OUTSIDE_REORDER_HORIZON"
        )

        if p.node!=expected:
            need(
                len(self.pending)<self.max_pending,
                "REORDER_BUFFER_FULL"
            )

        self.pending[p.node]=p
        self.received.add(p.node)
        self.arrival_order.append(p.node)

        self.peak_pending=max(
            self.peak_pending,
            len(self.pending)
        )

        processed=[]

        while self.estimator.next_node in self.pending:
            node=self.estimator.next_node
            current=self.pending[node]

            # R107 validates all factor ownership again.
            self.estimator.ingest(
                node,
                current.readings,
                current.imu_factor,
                current.pose_factors
            )

            del self.pending[node]

            self.processed_order.append(node)
            processed.append(node)

        return tuple(processed)

    def finish(self):
        need(
            not self.closed,
            "SESSION_CLOSED"
        )

        need(
            self.estimator.next_node==5
            and not self.pending
            and self.received=={1,2,3,4},
            "MISSING_OR_DELAYED_NODE"
        )

        result=self.estimator.finish()

        need(
            self.processed_order==[1,2,3,4],
            "PROCESSING_ORDER"
        )

        self.closed=True

        return result

def state_error(data,reference):
    fields=(
        ("position_m",0),
        ("rotation_vector_rad",3),
        ("velocity_m_s",6),
        ("gyro_bias",9),
        ("accel_bias",12),
    )

    largest=0.

    for row in reference:
        node=row["node"]

        for key,start in fields:
            a=data["states"][node][
                start:start+3
            ]

            b=np.asarray(
                row[key],dtype=float
            )

            largest=max(
                largest,
                float(
                    np.max(np.abs(a-b))
                )
            )

    return largest

def run_case(condition,camera):
    need(
        condition in ("clean","lidar_dropout"),
        "CONDITION"
    )

    need(
        type(camera) is bool,
        "CAMERA_MODE"
    )

    g=graph.build(condition,camera,13)
    validate_graph(g)

    reference,audit=s6.estimate_joint(
        g["fixture"],
        g["camera_packets"]
    )

    need(
        audit["accepted_window_count"]==4
        and audit["schur_elimination_count"]==3,
        "REFERENCE_S6"
    )

    rows={}

    for schedule_name,order in SCHEDULES.items():
        for rebase in (False,True):
            b=DeliveryBuffer(
                g,recenter=rebase
            )

            for node in order:
                b.submit(make_packet(g,node))

            data=b.finish()

            err=state_error(data,reference)

            need(
                err<(2e-5 if rebase else 1e-8),
                "S6_ESTIMATOR_EQUIVALENCE"
            )

            need(
                data["consumed_pose_ids"]==
                    audit["consumed_pose_ids"]
                and data["remaining_pose_ids"]==
                    audit["remaining_pose_ids"],
                "POSE_LEDGER_EQUIVALENCE"
            )

            need(
                data["consumed_imu_edges"]==
                    [[0,1],[1,2],[2,3]]
                and data["remaining_imu_edges"]==
                    [[3,4]],
                "INERTIAL_LEDGER"
            )

            need(
                data["admitted_sample_indices"]==
                    list(range(8))
                and data["future_factor_usage"] is False
                and data["factor_reuse"] is False,
                "SAMPLE_OR_FUTURE_FACTOR"
            )

            need(
                len(data["windows"])==4
                and len(data["eliminations"])==3
                and len(data["transfer_events"])==
                    (3 if rebase else 0),
                "SOLVER_EVENT_COUNTS"
            )

            key=(
                schedule_name+
                ("_recentered" if rebase else "_ordinary")
            )

            rows[key]={
                "arrival_order":b.arrival_order,
                "processed_order":b.processed_order,
                "peak_pending":b.peak_pending,
                "windows":len(data["windows"]),
                "marginalizations":
                    len(data["eliminations"]),
                "prior_transfers":
                    len(data["transfer_events"]),
                "max_abs_error_vs_s6":err,
                "pose_ledger_equal":True,
                "imu_sample_identity_preserved":True,
                "future_factor_consumed":False,
                "duplicate_factor_consumed":False,
                "physical_online_streaming_tested":False,
            }

    return {
        "condition":condition,
        "camera_enabled":camera,
        "runs":rows,
        "run_count":len(rows),
        "synthetic_only":True,
    }

def execute():
    cases={
        name:run_case(condition,camera)
        for name,condition,camera in CASES
    }

    all_runs=[
        row
        for case in cases.values()
        for row in case["runs"].values()
    ]

    need(
        len(cases)==3
        and len(all_runs)==12,
        "EXECUTION_COUNT"
    )

    windows=sum(r["windows"] for r in all_runs)
    marginalizations=sum(
        r["marginalizations"]
        for r in all_runs
    )
    transfers=sum(
        r["prior_transfers"]
        for r in all_runs
    )

    need(
        windows==48
        and marginalizations==36
        and transfers==18,
        "TOTAL_COUNTS"
    )

    need(
        all(
            r["processed_order"]==[1,2,3,4]
            for r in all_runs
        ),
        "CHRONOLOGY"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_SOFTWARE_ONLY",
        "cases":cases,
        "synthetic_scenarios":3,
        "delivery_schedules_per_scenario":2,
        "solver_modes_per_schedule":2,
        "total_solver_runs":12,
        "nonlinear_windows":windows,
        "schur_marginalizations":marginalizations,
        "same_graph_prior_transfers":transfers,
        "bounded_reordering_preserves_estimates":True,
        "exactly_once_factor_ownership":True,
        "future_factor_execution":False,
        "r95_gaussian_backend_imported":False,
        "actual_hardware_capture_tested":False,
        "physical_arrival_jitter_measured":False,
        "execution_deadlines_verified":False,
        "transport_authentication_verified":False,
        "transactional_solver_rollback_proven":False,
        "real_sensor_factors_authorized":False,
        "physical_clock_or_extrinsics_verified":False,
        "health_training_authorized":False,
        "ate_rpe_authorized":False,
        "confirmation_test_accessed":False,
        "raw_gt_or_rosbags_opened":False,
        "scientific_gates_closed":11,
    }

if __name__=="__main__":
    import sys

    result=execute()

    with open(
        sys.argv[1],"x",encoding="utf-8"
    ) as f:
        f.write(
            canonical(result).decode()
        )

    print("R108_BOUNDED_DELIVERY_AUDIT=PASS")
    print("R108_SYNTHETIC_SCENARIOS=3")
    print("R108_SOLVER_RUNS=12")
    print("R108_NONLINEAR_WINDOWS=48")
    print("R108_SCHUR_EVENTS=36")
    print("R108_RECENTERED_PRIOR_TRANSFERS=18")
    print("R108_REORDERED_FACTOR_OWNERSHIP=PASS")
    print("R108_ORIGINAL_S6_EQUIVALENCE=PASS")
    print("R108_PHYSICAL_STREAMING=NOT_TESTED")
