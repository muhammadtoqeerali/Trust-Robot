"""TRUST-ROBOT A36-4: synthetic-only time-sequential trust/safety shadow.

Test-fixture health declarations are NOT predictions, labels or calibrations.
No physical time, estimator factors, suppressed real sensors or robot actions.
Entry/recovery counts below are test parameters, NOT operational thresholds.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

SCHEMA = 'TRUST_ROBOT_R135_A36_4_SYNTHETIC_HYSTERETIC_SAFETY_SHADOW_V1'
ORIGIN = 'SYNTHETIC_ORACLE_FIXTURE_ONLY'
MODALITIES = ('camera', 'imu', 'lidar')
HEALTH = frozenset({'healthy', 'degraded', 'unusable', 'unknown'})
DELIVERY = frozenset({'present', 'missing'})
SUPPORT = frozenset({'fixture_sufficient', 'fixture_insufficient', 'unverified'})
TRACKING = frozenset({'fixture_tracking', 'lost', 'unverified'})
SOLVER = frozenset({'fixture_valid', 'invalid', 'unverified'})
CONSISTENCY = frozenset({'fixture_consistent', 'unattributed_disagreement', 'unverified'})
ROUTE = frozenset({'fixture_safe', 'unverified'})
FRAME_KEYS = frozenset({'index', 'origin', 'health', 'delivery', 'support', 'tracking',
                         'solver', 'consistency', 'route', 'return_requested'})

class ShadowTimelineContractError(ValueError):
    """Input violates non-executing synthetic demonstration boundaries."""


def require(ok, message):
    if not ok:
        raise ShadowTimelineContractError(message)


@dataclass(frozen=True)
class TestOnlyWindows:
    entry: int = 2
    recovery: int = 3

    def __post_init__(self):
        require(type(self.entry) is int and 1 <= self.entry <= 64,
                'invalid test-only entry count')
        require(type(self.recovery) is int and 1 <= self.recovery <= 64,
                'invalid test-only recovery count')


def _validate_frame(frame, index):
    require(type(frame) is dict and set(frame) == FRAME_KEYS,
            'missing/unknown frame keys')
    require(type(frame['index']) is int and frame['index'] == index,
            'frame indices must be contiguous from zero')
    require(frame['origin'] == ORIGIN, 'physical or inferred input forbidden')
    for key, allowed in (('health', HEALTH), ('delivery', DELIVERY)):
        values = frame[key]
        require(type(values) is dict and set(values) == set(MODALITIES),
                'exactly three named modalities required')
        require(all(type(v) is str and v in allowed for v in values.values()),
                'invalid declared '+key)
    for key, allowed in (('support', SUPPORT), ('tracking', TRACKING),
                         ('solver', SOLVER), ('consistency', CONSISTENCY), ('route', ROUTE)):
        require(type(frame[key]) is str and frame[key] in allowed,
                'invalid synthetic '+key)
    require(type(frame['return_requested']) is bool, 'invalid return request')


def synth_frame(index, *, health=None, delivery=None,
                support='fixture_sufficient', tracking='fixture_tracking',
                solver='fixture_valid', consistency='fixture_consistent',
                route='fixture_safe', return_requested=False):
    """Construct an explicitly synthetic test fixture, never a live input."""
    return {'index':index, 'origin':ORIGIN,
            'health': dict(health if health is not None else {m:'healthy' for m in MODALITIES}),
            'delivery':dict(delivery if delivery is not None else {m:'present' for m in MODALITIES}),
            'support':support, 'tracking':tracking, 'solver':solver,
            'consistency':consistency, 'route':route,
            'return_requested':return_requested}


def simulate_shadow_timeline(frames, *, windows=TestOnlyWindows()):
    """Evaluate synthetic inputs only. The returned state is NOT executed.

    Missing delivery is *never* promoted into an unusable health label.
    An unusable declaration requires consecutive synthetic frames and
    fixture-proven remaining support before shadow suppression. Recovery
    requires consecutive delivered healthy/degraded fixture states.
    Any unresolved support/tracking/solver/consistency/health requests review.
    """
    require(type(windows) is TestOnlyWindows, 'only test-only windows accepted')
    require(type(frames) is list and 1 <= len(frames) <= 128,
            'frames must be a bounded exact list')
    for i, f in enumerate(frames):
        _validate_frame(f, i)
    original = deepcopy(frames)
    state = {m:{'suppressed':False,'entry_streak':0,'recovery_streak':0}
             for m in MODALITIES}
    trace = []
    for i, frame in enumerate(frames):
        events=[]
        for m in MODALITIES:
            st=state[m]
            h=frame['health'][m]
            present=frame['delivery'][m]=='present'
            if st['suppressed']:
                st['entry_streak']=0
                if h in ('healthy','degraded') and present:
                    st['recovery_streak']+=1
                    if st['recovery_streak']>=windows.recovery:
                        st['suppressed']=False
                        st['recovery_streak']=0
                        events.append('SHADOW_RECOVERY_COMPLETED_'+m.upper())
                    else:
                        events.append('SHADOW_RECOVERY_PENDING_'+m.upper())
                else:
                    st['recovery_streak']=0
            else:
                st['recovery_streak']=0
                if h=='unusable':
                    st['entry_streak']+=1
                    if st['entry_streak']>=windows.entry:
                        alternatives=[n for n in MODALITIES if n!=m and
                                      frame['health'][n] in ('healthy','degraded') and
                                      frame['delivery'][n]=='present' and
                                      not state[n]['suppressed']]
                        if frame['support']=='fixture_sufficient' and alternatives:
                            st['suppressed']=True
                            st['entry_streak']=0
                            events.append('SHADOW_SUPPRESSION_COMPLETED_'+m.upper())
                        else:
                            events.append('SHADOW_SUPPRESSION_BLOCKED_SUPPORT_'+m.upper())
                    else:
                        events.append('SHADOW_SUPPRESSION_PENDING_'+m.upper())
                else:
                    st['entry_streak']=0
        suppressed=sorted(m for m in MODALITIES if state[m]['suppressed'])
        missing=sorted(m for m in MODALITIES if frame['delivery'][m]=='missing')
        unknown=sorted(m for m in MODALITIES if frame['health'][m]=='unknown')
        unresolved_unusable=sorted(m for m in MODALITIES
                                  if frame['health'][m]=='unusable' and not state[m]['suppressed'])
        sufficient_alternatives=[m for m in MODALITIES
                                 if not state[m]['suppressed'] and
                                 frame['health'][m] in ('healthy','degraded') and
                                 frame['delivery'][m]=='present']
        reasons=[]
        if frame['support']!='fixture_sufficient' or not sufficient_alternatives:
            reasons.append('SUFFICIENT_ALTERNATIVE_SUPPORT_NOT_DEMONSTRATED')
        if frame['tracking']!='fixture_tracking': reasons.append('TRACKING_NOT_FIXTURE_VALID')
        if frame['solver']!='fixture_valid': reasons.append('SOLVER_NOT_FIXTURE_VALID')
        if frame['consistency']!='fixture_consistent': reasons.append('CONSISTENCY_UNRESOLVED')
        if unknown: reasons.append('UNKNOWN_HEALTH_NOT_INFERRED')
        if missing: reasons.append('MISSING_DELIVERY_NOT_HEALTH_LABEL')
        if unresolved_unusable: reasons.append('UNUSABLE_WITHOUT_AUTHORIZED_SUPPRESSION')
        if frame['return_requested'] and frame['route']!='fixture_safe':
            reasons.append('RETURN_ROUTE_NOT_VERIFIED')
        if reasons:
            decision='SHADOW_SAFE_HOLD_REVIEW_REQUEST'
        elif frame['return_requested']:
            decision='SHADOW_RETURN_HOME_CANDIDATE_ONLY'
        elif suppressed or any(frame['health'][m]=='degraded' for m in MODALITIES):
            decision='SHADOW_DEGRADED_CONTINUATION_CANDIDATE_ONLY'
        else:
            decision='SHADOW_NOMINAL_CONTINUATION_CANDIDATE_ONLY'
        trace.append({'index':i,'shadow_suppressed_modalities':suppressed,
                      'shadow_events':sorted(events),'decision':decision,
                      'reason_codes':sorted(reasons),
                      'real_health_inference_performed':False,
                      'robot_command':None,
                      'physical_suppression_executed':False,
                      'return_home_execution_authorized':False})
    require(frames==original,'input frames mutated')
    require(all(row['robot_command'] is None and
                row['physical_suppression_executed'] is False for row in trace),
            'non-executing guarantee violated')
    return {'schema':SCHEMA,'origin':ORIGIN,
            'status':'SYNTHETIC_ONLY_HYSTERETIC_SHADOW_NONEXECUTING',
            'test_only_entry_windows':windows.entry,
            'test_only_recovery_windows':windows.recovery,
            'trace':trace,
            'synthetic_health_labels_not_empirical':True,
            'real_health_state':'UNKNOWN_NOT_INFERRED',
            'real_factor_count':0,
            'real_factor_admission':'DENIED',
            'physical_suppression_executed':False,
            'robot_command':None,
            'physical_safety_claim':False}
