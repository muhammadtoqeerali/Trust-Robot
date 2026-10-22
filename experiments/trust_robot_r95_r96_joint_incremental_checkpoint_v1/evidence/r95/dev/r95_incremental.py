"""R95: integrated synthetic-only rolling Schur-prior lifecycle.

Incrementally condenses previously manufactured local Gaussian factors.
It DOES NOT relinearize eliminated nonlinear factors, process measured
sensor data, prove estimator accuracy or qualify physical clock domains.
"""

import hashlib
import json
import math

import numpy as np

import r84_gap_frontend as gap
import r88_schur as schur
import r89_prior as prior
import r90_prior_guard as guard

SCHEMA='TRUST_ROBOT_R95_SYNTHETIC_INCREMENTAL_PRIOR_LIFECYCLE_V1'
CASES=(
    'continuous',
    'single_gap',
    'accel_injection',
    'gyro_injection',
)

class LifecycleError(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise LifecycleError(reason)

def canonical(obj):
    return (
        json.dumps(
            obj,sort_keys=True,indent=2,allow_nan=False
        )+'\n'
    ).encode('utf-8')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def run_case(name, packets=None):
    need(name in CASES,'UNKNOWN_SYNTHETIC_SCENARIO')

    if packets is None:
        packets=gap.fixture(name)

    segments,gap_count=schur.segment_groups(packets)

    need(
        len(segments)==gap_count+1,
        'GAP_SEGMENT_ACCOUNTING'
    )

    rows=[]
    previous_end=None
    total_windows=0
    total_eliminated=0

    for sid,groups in enumerate(segments):
        need(len(groups)>0,'EMPTY_SEGMENT')

        if previous_end is not None:
            need(
                groups[0][0]>previous_end,
                'GAP_NOT_DISCONNECTED'
            )

        # Manufactured linearizations are deterministic fixtures.
        # Their computation before incremental consumption is not
        # presented as a real-time streaming sensor interface.
        factors=schur.synthetic_factors(groups,sid)

        need(
            len(factors)==len(groups),
            'FACTOR_WINDOW_COUNT'
        )

        H=g=c=None
        window_rows=[]
        last_end=None

        for step,((start,end,_),(Ai,Aj,y,_)) in enumerate(
            zip(groups,factors)
        ):
            need(
                start<end,
                'NONPOSITIVE_WINDOW'
            )

            if last_end is not None:
                need(
                    start==last_end,
                    'NONCONTIGUOUS_WITHIN_SEGMENT'
                )

            if step==0:
                # Independent synthetic gauge anchoring
                # at the beginning of EACH continuous segment.
                H=schur.require_spd(
                    Aj.T@Aj + schur.RIDGE**2*np.eye(15)
                )
                g=Aj.T@y
                c=0.5*float(y@y)
            else:
                H,g,c=schur.schur(
                    H,g,c,Ai,Aj,y
                )
                total_eliminated+=1

            need(
                H.shape==(15,15)
                and g.shape==(15,)
                and np.isfinite(H).all()
                and np.isfinite(g).all()
                and math.isfinite(c),
                'CONDENSED_PRIOR_NUMERICS'
            )

            record=guard.make_record(
                H,g,c,sid
            )

            guard.validate(record)

            shift=5e-5*np.sin(
                np.arange(15,dtype=float)+sid+step
            )

            admission=guard.admit(
                record,sid,guard.token(sid),shift
            )

            need(
                admission['real_sensor_factor_executable']
                is False,
                'UNAUTHORIZED_FACTOR'
            )

            need(
                admission['frozen_jacobians_modified']
                is False,
                'NONLINEAR_REFRESH'
            )

            # Independently reconstruct the same prefix using
            # the frozen R89 builder, then compare against R88's
            # separately assembled full-batch least squares.
            Href,gref,cref=prior.construct_condensed_prior(
                groups[:step+1],sid
            )

            h_error=float(np.max(np.abs(H-Href)))
            g_error=float(np.max(np.abs(g-gref)))
            c_error=abs(float(c-cref))

            need(
                h_error<1e-7
                and g_error<1e-7
                and c_error<1e-7,
                'INCREMENTAL_RECONSTRUCTION_MISMATCH'
            )

            batch=schur.solve_segment(
                groups[:step+1],sid
            )

            state_error=batch[
                'schur_vs_batch_state_l2_error'
            ]
            cov_error=batch[
                'schur_vs_batch_covariance_relative_error'
            ]
            cost_error=batch[
                'schur_vs_batch_optimum_cost_abs_error'
            ]

            need(
                state_error<1e-4
                and cov_error<2e-3
                and cost_error<1e-5,
                'INCREMENTAL_BATCH_MISMATCH'
            )

            window_rows.append({
                'index':step,
                'synthetic_start_ns':start,
                'synthetic_end_ns':end,
                'prefix_window_count':step+1,
                'eliminated_old_states':step,
                'information_max_abs_error':h_error,
                'gradient_max_abs_error':g_error,
                'constant_abs_error':c_error,
                'full_batch_state_l2_error':state_error,
                'full_batch_covariance_relative_error':cov_error,
                'full_batch_cost_abs_error':cost_error,
                'prior_condition_number':admission[
                    'condition_number'
                ],
                'real_factors_executed':False,
            })

            total_windows+=1
            last_end=end

        rows.append({
            'segment_id':sid,
            'synthetic_start_ns':groups[0][0],
            'synthetic_end_ns':groups[-1][1],
            'window_count':len(window_rows),
            'first_window_new_anchor':True,
            'prior_copied_from_previous_segment':False,
            'windows':window_rows,
        })

        previous_end=groups[-1][1]

    need(
        total_windows==sum(
            len(segment) for segment in segments
        ),
        'WINDOW_ACCOUNTING'
    )

    return {
        'scenario':name,
        'source':'ANALYTIC_FIXTURE',
        'segments':len(rows),
        'timestamp_gaps':gap_count,
        'incremental_windows':total_windows,
        'marginalized_old_states':total_eliminated,
        'cross_gap_prior_carries':0,
        'real_sensor_factors_executed':False,
        'physical_clock_verified':False,
        'independent_ground_truth_used':False,
        'nonlinear_eliminated_factor_refresh':False,
        'rows':rows,
    }

def execute():
    cases={
        name:run_case(name)
        for name in CASES
    }

    windows=sum(
        x['incremental_windows']
        for x in cases.values()
    )

    eliminated=sum(
        x['marginalized_old_states']
        for x in cases.values()
    )

    gaps=sum(
        x['timestamp_gaps']
        for x in cases.values()
    )

    need(
        windows==16
        and eliminated==11
        and gaps==1,
        'EXPECTED_FIXTURE_ACCOUNTING'
    )

    return {
        'schema':SCHEMA,
        'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':cases,
        'synthetic_scenarios':4,
        'incremental_prefix_windows':windows,
        'marginalized_old_states':eliminated,
        'detected_timestamp_gaps':gaps,
        'cross_gap_prior_carries':0,
        'manufactured_gaussian_stabilization':True,
        'nonlinear_frozen_prior_relinearization':False,
        'sensor_input_origin':'ANALYTIC_FIXTURE_ONLY',
        'real_sensor_factors_executed':False,
        'physical_capture_clock_verified':False,
        'physical_extrinsics_verified':False,
        'independent_ground_truth_used':False,
        'health_labels_generated':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'original_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys
    output=execute()
    with open(sys.argv[1],'x',encoding='utf-8') as f:
        f.write(canonical(output).decode('utf-8'))
    print('R95_SYNTHETIC_SCENARIOS=4_PASS')
    print('R95_INCREMENTAL_PREFIX_WINDOWS=16_PASS')
    print('R95_MARGINALIZED_OLD_STATES=11')
    print('R95_TIMESTAMP_GAPS=1_RESET')
    print('R95_CROSS_GAP_PRIOR_CARRIES=ZERO')
