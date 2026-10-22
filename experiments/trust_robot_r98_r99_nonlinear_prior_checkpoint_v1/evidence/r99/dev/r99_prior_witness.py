"""R99 synthetic nonlinear fixed-lag prior lifecycle witness.

Temporarily instruments the existing S6 marginalizer.
Does not modify the S6 code or replace its numerical solver.

Every actual marginalization is independently linearized
and checked against explicit Schur normal equations.

The local digest chain detects ordinary archive changes;
it is not hardware attestation or trusted source signing.
"""

import hashlib
import inspect
import json
from unittest.mock import patch

import numpy as np

import s6_joint_fusion as s6

from trust_robot.analytic_inertial_15d import make_fixture
from trust_robot.analytic_three_modality_bridge import (
    manufactured_camera_packets,
)
from trust_robot.analytic_schur_marginalization import (
    finite_difference_linearization,
    marginalize_one as original_marginalize,
)
from trust_robot.multimodal_factor_interface import (
    ANALYTIC_ORIGIN,
    CAMERA_SOURCE,
    LIDAR_SOURCE,
)

SCHEMA = 'TRUST_ROBOT_R99_SYNTHETIC_NONLINEAR_PRIOR_WITNESS_V1'
DIM = 15
GENESIS = hashlib.sha256(
    b'R99_SYNTHETIC_LOCAL_WITNESS_GENESIS_V1'
).hexdigest()

class WitnessError(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise WitnessError(reason)

def canonical(value):
    return (
        json.dumps(
            value,sort_keys=True,indent=2,
            allow_nan=False
        )+'\n'
    ).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def prior_digest(prior):
    return digest({
        'nodes':list(prior.node_ids),
        'reference':np.asarray(
            prior.reference
        ).tolist(),
        'information_square_root':np.asarray(
            prior.square_root_information
        ).tolist(),
        'residual_offset':np.asarray(
            prior.residual_offset
        ).tolist(),
    })

def verify_chain(events):
    need(
        type(events) is list
        and len(events)==3,
        'EVENT_COUNT'
    )

    previous_digest=GENESIS
    prior_out=None
    used_pose=set()
    used_imu=set()

    for i,event in enumerate(events):
        need(type(event) is dict,'EVENT_TYPE')
        body=dict(event)
        claimed=body.pop('event_digest',None)

        need(
            type(claimed) is str
            and claimed==digest(body),
            'EVENT_INTEGRITY'
        )

        need(
            event['event_index']==i
            and event['eliminated_node']==i
            and event['input_nodes']==[i,i+1,i+2]
            and event['retained_nodes']==[i+1,i+2],
            'EVENT_CHRONOLOGY'
        )

        need(
            event['previous_event_digest']==previous_digest,
            'EVENT_CHAIN'
        )

        if prior_out is not None:
            need(
                event['input_prior_digest']==prior_out,
                'PRIOR_CONTINUITY'
            )

        need(
            event['synthetic_only'] is True
            and event['real_sensor_factor_executable'] is False
            and event['physical_clock_verified'] is False,
            'SCIENCE_BOUNDARY'
        )

        pose=event['consumed_pose_ids']
        imu=event['consumed_imu_edges']

        need(
            type(pose) is list
            and len(pose)==len(set(pose))
            and not (set(pose)&used_pose),
            'POSE_DOUBLE_COUNT'
        )

        imu_tokens={tuple(x) for x in imu}

        need(
            len(imu_tokens)==len(imu)
            and not (imu_tokens&used_imu),
            'IMU_DOUBLE_COUNT'
        )

        used_pose.update(pose)
        used_imu.update(imu_tokens)

        need(
            event['information_relative_error']<1e-6
            and event['gradient_relative_error']<1e-6
            and event['energy_difference_error']<1e-5,
            'NUMERICAL_DISAGREEMENT'
        )

        previous_digest=claimed
        prior_out=event['output_prior_digest']

    need(
        used_imu=={(0,1),(1,2),(2,3)},
        'INERTIAL_FACTOR_ACCOUNTING'
    )

    return True

def run_case(condition,camera_enabled=True,seed=13):
    need(
        condition in ('clean','lidar_dropout'),
        'CONDITION'
    )
    need(type(camera_enabled) is bool,'CAMERA_MODE')
    need(type(seed) is int and 0<=seed<=100000,'SEED')

    fixture,truth=make_fixture(condition)

    camera=(
        manufactured_camera_packets(
            truth,seed=seed
        )
        if camera_enabled else ()
    )

    events=[]
    last_prior=None
    seen_pose=set()
    seen_imu=set()

    def witness(nodes,refs,residual_fn,oldest):
        nonlocal last_prior

        nodes=tuple(nodes)

        need(
            nodes==(
                len(events),
                len(events)+1,
                len(events)+2
            ) and oldest==nodes[0],
            'ACTUAL_WINDOW_ORDER'
        )

        captured=inspect.getclosurevars(
            residual_fn
        ).nonlocals

        need(
            {'previous','ii','pp'}.issubset(captured),
            'S6_CLOSURE_CONTRACT'
        )

        previous=captured['previous']
        ii=captured['ii']
        pp=captured['pp']

        need(
            type(ii) is dict
            and type(pp) is dict,
            'FACTOR_COLLECTIONS'
        )

        need(
            len(ii)==1
            and set(ii)=={(oldest,oldest+1)},
            'DEPARTING_INERTIAL_FACTOR'
        )

        if last_prior is None:
            need(
                previous.node_ids==(0,),
                'FIRST_GAUGE_ANCHOR'
            )
        else:
            need(
                previous is last_prior,
                'PRIOR_OBJECT_NOT_INHERITED'
            )

        pose_ids=sorted(pp)
        imu_edges=sorted(ii)

        need(
            not (set(pose_ids)&seen_pose)
            and not (set(imu_edges)&seen_imu),
            'FACTOR_REUSED'
        )

        for ident,f in pp.items():
            need(
                type(f) is s6.JointFactor
                and f.key==ident
                and f.packet.origin==ANALYTIC_ORIGIN
                and f.packet.source_id=={
                    'camera':CAMERA_SOURCE,
                    'lidar':LIDAR_SOURCE
                }[f.packet.modality],
                'UNTRUSTED_POSE_SOURCE'
            )

        reference=np.concatenate([
            np.asarray(refs[n],dtype=float)
            for n in nodes
        ])

        need(
            reference.shape==(45,)
            and np.isfinite(reference).all(),
            'REFERENCE_SHAPE'
        )

        def flattened(x):
            state={
                node:x[k*DIM:(k+1)*DIM]
                for k,node in enumerate(nodes)
            }
            return residual_fn(state)

        r0,J=finite_difference_linearization(
            flattened,reference
        )

        need(
            J.shape[1]==45
            and np.isfinite(J).all()
            and np.isfinite(r0).all(),
            'JACOBIAN'
        )

        H=J.T@J
        g=J.T@r0

        Hmm=H[:DIM,:DIM]
        Hmk=H[:DIM,DIM:]
        Hkm=H[DIM:,:DIM]
        Hkk=H[DIM:,DIM:]

        gm=g[:DIM]
        gk=g[DIM:]

        eig=np.linalg.eigvalsh(Hmm)
        need(
            eig[0]>max(
                1e-11,
                1e-11*eig[-1]
            ),
            'INFORMATION_PIVOT'
        )

        Hr=Hkk-Hkm@np.linalg.solve(
            Hmm,Hmk
        )
        Hr=0.5*(Hr+Hr.T)

        gr=gk-Hkm@np.linalg.solve(
            Hmm,gm
        )

        # Invoke the original nonlinear solver's
        # production marginalization primitive.
        out,diagnostics=original_marginalize(
            nodes,refs,residual_fn,oldest
        )

        need(
            out.node_ids==nodes[1:],
            'PRIOR_RETAINED_OWNERSHIP'
        )

        Ho,go=out.normal_equations()

        herr=float(
            np.linalg.norm(Ho-Hr)
            /max(1.,np.linalg.norm(Hr))
        )

        gerr=float(
            np.linalg.norm(go-gr)
            /max(1.,np.linalg.norm(gr))
        )

        delta=1e-5*np.sin(
            np.arange(30,dtype=float)+oldest+0.31
        )

        def batch_energy(d):
            xm=-np.linalg.solve(
                Hmm,gm+Hmk@d
            )
            return 0.5*float(
                np.linalg.norm(
                    r0+J@np.r_[xm,d]
                )**2
            )

        def prior_energy(d):
            mapping={
                node:np.asarray(
                    refs[node],dtype=float
                )+d[k*DIM:(k+1)*DIM]
                for k,node in enumerate(nodes[1:])
            }
            e=out.residual(mapping)
            return 0.5*float(e@e)

        zero=np.zeros(30)

        eerr=abs(
            (batch_energy(delta)-batch_energy(zero))
            -(prior_energy(delta)-prior_energy(zero))
        )

        need(
            herr<1e-6
            and gerr<1e-6
            and eerr<1e-5,
            'SCHUR_NORMAL_EQUATION_MISMATCH'
        )

        need(
            diagnostics[
                'fixed_first_estimate_linearization'
            ] is True
            and diagnostics[
                'physical_observability_proven'
            ] is False
            and diagnostics[
                'probabilistic_consistency_proven'
            ] is False,
            'UNSUPPORTED_SCIENCE_CLAIM'
        )

        payload={
            'event_index':len(events),
            'input_nodes':list(nodes),
            'eliminated_node':oldest,
            'retained_nodes':list(out.node_ids),
            'input_prior_digest':prior_digest(previous),
            'output_prior_digest':prior_digest(out),
            'previous_event_digest':(
                events[-1]['event_digest']
                if events else GENESIS
            ),
            'consumed_pose_ids':pose_ids,
            'consumed_imu_edges':[
                list(x) for x in imu_edges
            ],
            'input_residual_dimension':int(r0.size),
            'information_relative_error':herr,
            'gradient_relative_error':gerr,
            'energy_difference_error':eerr,
            'synthetic_only':True,
            'physical_clock_verified':False,
            'real_sensor_factor_executable':False,
        }

        payload['event_digest']=digest(payload)

        events.append(payload)
        last_prior=out
        seen_pose.update(pose_ids)
        seen_imu.update(imu_edges)

        return out,diagnostics

    original_symbol=s6.marginalize_one

    # Intercept only within this run. The archived
    # S6 implementation and import are never edited.
    with patch.object(
        s6,'marginalize_one',side_effect=witness
    ):
        states,audit=s6.estimate_joint(
            fixture,camera
        )

    need(
        s6.marginalize_one is original_symbol,
        'PATCH_NOT_RESTORED'
    )

    verify_chain(events)

    need(
        len(states)==5
        and audit['accepted_window_count']==4
        and audit['schur_elimination_count']==3,
        'NONLINEAR_ESTIMATOR_RUN'
    )

    need(
        seen_pose==set(audit['consumed_pose_ids']),
        'POSE_LEDGER_DISAGREEMENT'
    )

    ledger_ids={
        f['measurement_id']
        for f in audit['factor_ledger']
    }

    remaining=set(audit['remaining_pose_ids'])

    need(
        seen_pose.isdisjoint(remaining)
        and seen_pose|remaining==ledger_ids,
        'POSE_LEDGER_NOT_COMPLETE'
    )

    need(
        audit['unaccounted_factor_count']==0
        and audit['factor_reuse_after_marginalization']
        is False
        and audit['real_sensor_factor_admitted']
        is False
        and audit['physical_measurements_used']
        is False,
        'ESTIMATOR_AUDIT'
    )

    # Non-invasive instrumentation must preserve the
    # numerical behavior of the original estimator.
    plain_states,plain_audit=s6.estimate_joint(
        fixture,camera
    )

    discrepancy=0.

    for a,b in zip(states,plain_states):
        for key in (
            'position_m','rotation_vector_rad',
            'velocity_m_s','gyro_bias','accel_bias'
        ):
            discrepancy=max(
                discrepancy,
                float(np.max(np.abs(
                    np.asarray(a[key])
                    -np.asarray(b[key])
                )))
            )

    need(
        discrepancy<1e-8
        and audit==plain_audit,
        'INSTRUMENTATION_CHANGED_SOLVER'
    )

    return {
        'condition':condition,
        'camera_enabled':camera_enabled,
        'events':events,
        'nonlinear_windows':4,
        'marginalization_events':3,
        'pose_factors_consumed':len(seen_pose),
        'remaining_pose_factors':len(remaining),
        'unconsumed_imu_edges':[[3,4]],
        'factor_reuse_count':0,
        'same_edge_camera_lidar_count':
            audit['same_edge_camera_lidar_count'],
        'instrumented_vs_uninstrumented_state_max_error':
            discrepancy,
        'witness_is_trusted_hardware_attestation':False,
        'real_factor_executed':False,
    }

def execute():
    cases={
        'clean_joint':run_case('clean',True,13),
        'dropout_joint':run_case('lidar_dropout',True,13),
        'clean_camera_off':run_case('clean',False,13),
    }

    for case in cases.values():
        verify_chain(case['events'])

    need(
        cases['clean_joint'][
            'same_edge_camera_lidar_count'
        ]==2,
        'JOINT_MODALITY_OVERLAP'
    )

    need(
        cases['clean_camera_off'][
            'same_edge_camera_lidar_count'
        ]==0,
        'CAMERA_ABLATION'
    )

    return {
        'schema':SCHEMA,
        'status':'PASS_SYNTHETIC_SOFTWARE_ONLY',
        'cases':cases,
        'nonlinear_solver_scenarios':3,
        'nonlinear_windows':12,
        'actual_marginalizations_independently_checked':9,
        'all_prior_inheritance_checks_passed':True,
        'all_schur_normal_equations_checked':True,
        'instrumentation_restored':True,
        'r95_gaussian_backend_merged_into_s6':False,
        'event_digest_is_trusted_source_authentication':False,
        'recorded_source_factors_executed':False,
        'physical_clock_or_extrinsics_verified':False,
        'independent_ground_truth_scoring':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'raw_gt_or_rosbags_opened':False,
        'scientific_gates_closed':11,
    }

if __name__=='__main__':
    import sys

    output=execute()

    with open(
        sys.argv[1],'x',encoding='utf-8'
    ) as f:
        f.write(canonical(output).decode())

    print('R99_NONLINEAR_ESTIMATOR_LIFECYCLE=PASS')
    print('R99_SCENARIOS=3')
    print('R99_NONLINEAR_WINDOWS=12')
    print('R99_INDEPENDENT_SCHUR_EVENTS=9')
    print('R99_PRIOR_INHERITANCE=PASS')
    print('R99_FACTOR_OWNERSHIP=PASS')
    print('R99_UNINSTRUMENTED_EQUIVALENCE=PASS')
    print('R99_RECORDED_SENSOR_FACTORS=DENIED')
