"""R107 synthetic sequential-admission nonlinear estimator.

This is a separate incremental fixed-lag implementation
using the existing S6 nonlinear optimization primitives.

An already manufactured R104 graph is released
incrementally, one node at a time.

No real-time acquisition, physical clock qualification,
real factor admission, external prior import, independent
ground truth scoring or calibrated health inference.

All 11 scientific gates remain closed.
"""

import json
import math

import numpy as np

from scipy.optimize import least_squares

import r104_shared_graph as graph
import r105_prior_transfer as transfer
import s6_joint_fusion as s6

from trust_robot.analytic_preintegrated_fusion import (
    NODE_FRAMES,
)

SCHEMA="TRUST_ROBOT_R107_SYNTHETIC_INCREMENTAL_INTEGRATION_V1"

CASES=(
    ("clean_joint","clean",True),
    ("lidar_dropout_joint","lidar_dropout",True),
    ("clean_camera_off","clean",False),
)

class IncrementalError(ValueError):
    pass

def need(ok,reason):
    if not ok:
        raise IncrementalError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+"\n"
    ).encode("utf-8")

def validate_graph(g):
    try:
        graph.validate(g)
    except graph.GraphAdmissionError as exc:
        raise IncrementalError(
            "GRAPH_ADMISSION_DENIED"
        ) from exc

    return True

def release(g,end):
    """Release only the observations due at one node.

    This replays an existing synthetic fixture and
    must not be described as physical online streaming.
    """
    validate_graph(g)

    need(
        type(end) is int and 1<=end<=4,
        "RELEASE_NODE"
    )

    first=NODE_FRAMES[end-1]
    last=NODE_FRAMES[end]

    readings=tuple(
        g["fixture"]["imu"][first:last]
    )

    imu=g["imu_factors"][(end-1,end)]

    pose=tuple(
        f for f in g["pose_factors"]
        if f.packet.edge[1]==end
    )

    return readings,imu,pose

class IncrementalEstimator:
    """Bounded 3-node sequential synthetic optimization."""

    def __init__(self,g,*,recenter=False):
        validate_graph(g)

        need(
            type(recenter) is bool,
            "RECENTER_MODE"
        )

        self.g=g
        self.recenter=recenter

        self.next_node=1

        self.states={0:s6.initial_state()}

        self.prior=s6.synthetic_initial_anchor(
            self.states[0],sigma=0.01
        )

        self.live=[0]

        self.admitted_imu={}
        self.admitted_pose={}

        self.consumed_imu=set()
        self.consumed_pose=set()

        self.admitted_samples=set()

        self.windows=[]
        self.eliminations=[]
        self.transfer_events=[]

    def ingest(self,end,readings,imu_factor,pose_factors):
        """Accept and solve exactly the next manufactured node."""

        need(
            type(end) is int
            and end==self.next_node
            and 1<=end<=4,
            "OUT_OF_ORDER_NODE"
        )

        validate_graph(self.g)

        expected_readings,expected_imu,expected_pose=release(
            self.g,end
        )

        need(
            type(readings) is tuple
            and len(readings)==2
            and all(
                actual is expected
                for actual,expected
                in zip(readings,expected_readings)
            ),
            "IMU_READINGS_NOT_DECLARED"
        )

        need(
            imu_factor is expected_imu,
            "IMU_FACTOR_NOT_DECLARED"
        )

        need(
            type(pose_factors) is tuple,
            "POSE_FACTOR_CONTAINER"
        )

        expected_by_id={
            factor.key:factor
            for factor in expected_pose
        }

        actual_by_id={}

        for f in pose_factors:
            need(
                type(f) is s6.JointFactor,
                "POSE_FACTOR_TYPE"
            )

            need(
                f.key not in actual_by_id,
                "POSE_FACTOR_DUPLICATION"
            )

            actual_by_id[f.key]=f

        need(
            set(actual_by_id)==set(expected_by_id),
            "POSE_FACTOR_RELEASE_SET"
        )

        need(
            all(
                actual_by_id[key] is expected_by_id[key]
                for key in expected_by_id
            ),
            "POSE_FACTOR_NOT_DECLARED"
        )

        edge=(end-1,end)

        samples=set(
            self.g["imu_owner"][edge]
        )

        need(
            not samples.intersection(self.admitted_samples),
            "IMU_SAMPLE_REUSE"
        )

        need(
            edge not in self.admitted_imu,
            "IMU_EDGE_REUSE"
        )

        need(
            not set(actual_by_id).intersection(
                self.admitted_pose
            ),
            "POSE_ID_REUSE"
        )

        # No future measurement is put into the
        # optimization factor dictionaries.
        self.admitted_imu[edge]=imu_factor
        self.admitted_pose.update(actual_by_id)
        self.admitted_samples.update(samples)

        predicted=self.states[end-1].copy()

        for sample in readings:
            predicted=s6.predict_imu(
                predicted,sample
            )

        self.states[end]=predicted
        self.live.append(end)

        need(
            len(self.live)<=s6.WINDOW,
            "WINDOW_OVERFLOW"
        )

        ai=s6.active_imu(
            self.admitted_imu,
            self.live,
            self.consumed_imu
        )

        ap=s6.active_pose(
            tuple(self.admitted_pose.values()),
            self.live,
            self.consumed_pose
        )

        need(
            len(ai)==len(self.live)-1,
            "IMU_CHAIN_INCOMPLETE"
        )

        need(
            all(
                max(edge)<=end
                for edge in ai
            )
            and all(
                max(f.packet.edge)<=end
                for f in ap.values()
            ),
            "FUTURE_FACTOR_USED"
        )

        live=tuple(self.live)
        n=15*len(live)

        x0=np.concatenate([
            self.states[k]
            for k in live
        ])

        current_prior=self.prior

        def unpack(x):
            need(
                np.shape(x)==(n,),
                "OPTIMIZER_SHAPE"
            )

            return {
                k:x[i*15:(i+1)*15]
                for i,k in enumerate(live)
            }

        def objective(x):
            return s6.selected_residuals(
                unpack(x),
                current_prior,
                ai,
                ap,
            )

        fit=least_squares(
            objective,
            x0,
            method="trf",
            loss="linear",
            max_nfev=80,
            ftol=1e-9,
            xtol=1e-9,
            gtol=1e-9,
        )

        rank=int(
            np.linalg.matrix_rank(
                fit.jac,tol=1e-7
            )
        )

        need(
            bool(fit.success)
            and np.isfinite(fit.x).all()
            and math.isfinite(float(fit.cost))
            and rank==n,
            "NONLINEAR_WINDOW_FAILURE"
        )

        for i,k in enumerate(live):
            self.states[k]=fit.x[
                i*15:(i+1)*15
            ].copy()

        window={
            "end_node":end,
            "state_dimension":n,
            "rank":rank,
            "active_imu_edges":[
                list(e) for e in sorted(ai)
            ],
            "active_pose_ids":sorted(ap),
            "latest_admitted_node":end,
            "future_factors_used":False,
            "accepted":True,
        }

        self.windows.append(window)

        if len(live)==3:
            oldest=live[0]

            ii={
                k:v for k,v in ai.items()
                if oldest in k
            }

            pp={
                k:f for k,f in ap.items()
                if oldest in f.packet.edge
            }

            need(
                set(ii)=={(oldest,oldest+1)},
                "DEPARTING_IMU"
            )

            need(
                not set(ii).intersection(
                    self.consumed_imu
                )
                and not set(pp).intersection(
                    self.consumed_pose
                ),
                "DOUBLE_CONSUMPTION"
            )

            # Every declared factor incident to the
            # departing node must already be released.
            for edge in self.g["imu_factors"]:
                need(
                    not (
                        oldest in edge
                        and max(edge)>end
                    ),
                    "PREMATURE_IMU_ELIMINATION"
                )

            for f in self.g["pose_factors"]:
                need(
                    not (
                        oldest in f.packet.edge
                        and max(f.packet.edge)>end
                    ),
                    "PREMATURE_POSE_ELIMINATION"
                )

            previous=self.prior

            def elimination(candidate):
                return s6.selected_residuals(
                    candidate,
                    previous,
                    ii,
                    pp,
                )

            prior,diagnostics=s6.marginalize_one(
                live,
                {
                    k:self.states[k].copy()
                    for k in live
                },
                elimination,
                oldest,
            )

            need(
                diagnostics[
                    "fixed_first_estimate_linearization"
                ] is True
                and diagnostics[
                    "physical_observability_proven"
                ] is False
                and diagnostics[
                    "probabilistic_consistency_proven"
                ] is False,
                "SCIENTIFIC_PRIOR_BOUNDARY"
            )

            if self.recenter:
                prior,event=transfer.transfer(
                    prior,
                    self.g,
                    oldest,
                    tuple(sorted(pp)),
                    tuple(sorted(ii)),
                    transfer.shift_vector(oldest)
                )

                self.transfer_events.append(event)

            self.prior=prior

            self.consumed_imu.update(ii)
            self.consumed_pose.update(pp)

            self.live.pop(0)

            need(
                self.prior.node_ids==tuple(self.live),
                "PRIOR_NODE_OWNERSHIP"
            )

            self.eliminations.append({
                "oldest_node":oldest,
                "retained_nodes":list(self.live),
                "consumed_imu_edges":[
                    list(e) for e in sorted(ii)
                ],
                "consumed_pose_ids":sorted(pp),
                "frozen_jacobian_refresh":False,
            })

        self.next_node+=1
        return window

    def finish(self):
        need(
            self.next_node==5
            and len(self.windows)==4
            and len(self.eliminations)==3,
            "INCREMENTAL_RUN_INCOMPLETE"
        )

        need(
            self.admitted_samples==set(range(8)),
            "SAMPLE_LEDGER_INCOMPLETE"
        )

        need(
            set(self.admitted_imu)==
            set(self.g["imu_factors"]),
            "IMU_LEDGER_INCOMPLETE"
        )

        all_pose={
            f.key
            for f in self.g["pose_factors"]
        }

        need(
            set(self.admitted_pose)==all_pose,
            "POSE_LEDGER_INCOMPLETE"
        )

        remaining_imu=s6.active_imu(
            self.admitted_imu,
            self.live,
            self.consumed_imu
        )

        remaining_pose=s6.active_pose(
            tuple(self.admitted_pose.values()),
            self.live,
            self.consumed_pose
        )

        need(
            self.consumed_imu.isdisjoint(remaining_imu)
            and self.consumed_pose.isdisjoint(remaining_pose)
            and self.consumed_imu|set(remaining_imu)
            ==set(self.admitted_imu)
            and self.consumed_pose|set(remaining_pose)
            ==all_pose,
            "FACTOR_OWNERSHIP_INCOMPLETE"
        )

        need(
            self.live==[3,4],
            "FINAL_WINDOW"
        )

        need(
            len(self.transfer_events)==(
                3 if self.recenter else 0
            ),
            "TRANSFER_EVENT_COUNT"
        )

        return {
            "states":{
                k:v.copy()
                for k,v in self.states.items()
            },
            "windows":self.windows,
            "eliminations":self.eliminations,
            "transfer_events":self.transfer_events,
            "consumed_pose_ids":sorted(
                self.consumed_pose
            ),
            "remaining_pose_ids":sorted(
                remaining_pose
            ),
            "consumed_imu_edges":[
                list(e)
                for e in sorted(self.consumed_imu)
            ],
            "remaining_imu_edges":[
                list(e)
                for e in sorted(remaining_imu)
            ],
            "admitted_sample_indices":sorted(
                self.admitted_samples
            ),
            "future_factor_usage":False,
            "factor_reuse":False,
        }

def run_case(condition,camera):
    need(
        condition in ("clean","lidar_dropout"),
        "CONDITION"
    )

    need(type(camera) is bool,"CAMERA_MODE")

    g=graph.build(condition,camera,13)

    validate_graph(g)

    executions={}

    for rebase in (False,True):
        estimator=IncrementalEstimator(
            g,recenter=rebase
        )

        for node in range(1,5):
            readings,imu,pose=release(g,node)
            estimator.ingest(
                node,readings,imu,pose
            )

        executions[rebase]=estimator.finish()

    original_states,original_audit=s6.estimate_joint(
        g["fixture"],
        g["camera_packets"],
    )

    need(
        original_audit[
            "accepted_window_count"
        ]==4
        and original_audit[
            "schur_elimination_count"
        ]==3,
        "REFERENCE_RUN"
    )

    errors={}

    fields=(
        ("position_m",0),
        ("rotation_vector_rad",3),
        ("velocity_m_s",6),
        ("gyro_bias",9),
        ("accel_bias",12),
    )

    for rebase,data in executions.items():
        max_error=0.

        for row in original_states:
            node=row["node"]

            for name,start in fields:
                actual=data["states"][node][
                    start:start+3
                ]

                expected=np.asarray(
                    row[name],dtype=float
                )

                max_error=max(
                    max_error,
                    float(np.max(np.abs(
                        actual-expected
                    )))
                )

        bound=2e-5 if rebase else 1e-8

        need(
            max_error<bound,
            "S6_REFERENCE_DISAGREEMENT"
        )

        need(
            data["consumed_pose_ids"]==
            original_audit[
                "consumed_pose_ids"
            ]
            and data["remaining_pose_ids"]==
            original_audit[
                "remaining_pose_ids"
            ],
            "REFERENCE_POSE_LEDGER"
        )

        errors[
            "recentered" if rebase else "ordinary"
        ]=max_error

    ordinary=executions[False]
    recentered=executions[True]

    need(
        ordinary["consumed_imu_edges"]==
        recentered["consumed_imu_edges"]
        and ordinary["remaining_imu_edges"]==
        recentered["remaining_imu_edges"]
        and ordinary["consumed_pose_ids"]==
        recentered["consumed_pose_ids"],
        "PRIOR_TRANSFER_FACTOR_HISTORY"
    )

    return {
        "condition":condition,
        "camera_enabled":camera,
        "node_count":5,
        "imu_sample_count":8,
        "imu_factor_count":4,
        "ordinary_windows":len(
            ordinary["windows"]
        ),
        "recentered_windows":len(
            recentered["windows"]
        ),
        "ordinary_marginalizations":len(
            ordinary["eliminations"]
        ),
        "recentered_marginalizations":len(
            recentered["eliminations"]
        ),
        "recentered_prior_transfers":len(
            recentered["transfer_events"]
        ),
        "ordinary_vs_s6_max_abs_error":
            errors["ordinary"],
        "recentered_vs_s6_max_abs_error":
            errors["recentered"],
        "consumed_pose_ids":
            ordinary["consumed_pose_ids"],
        "remaining_pose_ids":
            ordinary["remaining_pose_ids"],
        "consumed_imu_edges":
            ordinary["consumed_imu_edges"],
        "remaining_imu_edges":
            ordinary["remaining_imu_edges"],
        "admitted_sample_indices":
            ordinary["admitted_sample_indices"],
        "window_ledger":
            ordinary["windows"],
        "elimination_ledger":
            ordinary["eliminations"],
        "transfer_ledger":
            recentered["transfer_events"],
        "factor_ownership_equivalent":True,
        "future_factor_consumed":False,
        "recorded_sensor_factor_executed":False,
    }

def execute():
    cases={
        name:run_case(condition,camera)
        for name,condition,camera in CASES
    }

    need(
        len(cases)==3,
        "CASE_COUNT"
    )

    need(
        sum(
            c["ordinary_windows"]
            for c in cases.values()
        )==12,
        "ORDINARY_WINDOW_COUNT"
    )

    need(
        sum(
            c["recentered_windows"]
            for c in cases.values()
        )==12,
        "RECENTERED_WINDOW_COUNT"
    )

    need(
        sum(
            c["recentered_prior_transfers"]
            for c in cases.values()
        )==9,
        "TRANSFER_COUNT"
    )

    return {
        "schema":SCHEMA,
        "status":"PASS_SYNTHETIC_SOFTWARE_ONLY",
        "cases":cases,
        "scenarios":3,
        "ordinary_incremental_windows":12,
        "recentered_incremental_windows":12,
        "ordinary_schur_marginalizations":9,
        "recentered_schur_marginalizations":9,
        "same_graph_prior_transfers":9,
        "node_admission_is_sequential":True,
        "future_measurements_excluded_from_solver":True,
        "original_s6_source_modified":False,
        "r95_backend_imported":False,
        "actual_physical_online_streaming_tested":False,
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
            canonical(result).decode("utf-8")
        )

    print("R107_INCREMENTAL_ESTIMATOR=PASS")
    print("R107_SCENARIOS=3")
    print("R107_ORDINARY_WINDOWS=12")
    print("R107_RECENTERED_WINDOWS=12")
    print("R107_SCHUR_EVENTS_PER_MODE=9")
    print("R107_SAME_GRAPH_PRIOR_TRANSFERS=9")
    print("R107_FACTOR_LEDGER=PASS")
    print("R107_FUTURE_FACTOR_CONSUMPTION=DENIED")
    print("R107_ORIGINAL_S6_EQUIVALENCE=PASS")
    print("R107_REAL_SENSOR_FACTORS=DENIED")
