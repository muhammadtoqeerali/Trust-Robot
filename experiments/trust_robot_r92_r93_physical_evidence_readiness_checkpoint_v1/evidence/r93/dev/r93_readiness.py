"""R93 physical evidence outreach and candidate-format readiness.

Builds on R92 and the older unsent R76 author request.
Creates DRAFT documents only. No messaging, external intake,
physical qualification or execution authorization.
"""

import hashlib
import json
import pathlib
import re
import subprocess

SCHEMA='TRUST_ROBOT_R93_PHYSICAL_EVIDENCE_OUTREACH_READINESS_V1'
CANDIDATE='TRUST_ROBOT_R93_UNQUALIFIED_SOURCE_METADATA_CANDIDATE_V1'

HISTORICAL_REQUEST=(
 'experiments/trust_robot_r76_r78_physical_intake_runtime_checkpoint_v1/'
 'evidence/r76/result/r76_author_physical_evidence_request_DRAFT_NOT_SENT.md'
)

class ReadinessError(ValueError):
    pass

def need(ok,why):
    if not ok:
        raise ReadinessError(why)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return (
        json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n'
    ).encode()

def load_inputs(repo,r92_result):
    repo=pathlib.Path(repo)
    r92_result=pathlib.Path(r92_result)

    source=r92_result/'r92_physical_source_gap_decision_v1.json'
    raw=source.read_bytes()
    r92=json.loads(raw)

    need(
        r92.get('status')=='PASS_EXISTING_EVIDENCE_GAP_ANALYSIS_ONLY'
        and r92.get('scientific_gates_closed')==11
        and len(r92.get('gate_matrix',{}))==11
        and len(r92.get('timing_receipt_matrix',{}))==5
        and len(r92.get('priority_actions',[]))==5,
        'R92_LINEAGE'
    )

    need(
        r92.get('new_physically_qualified_sources_established')==0
        and r92.get('real_sensor_factors_authorized') is False
        and r92.get('confirmation_test_accessed') is False,
        'R92_AUTHORIZATION'
    )

    old=repo/HISTORICAL_REQUEST

    need(old.is_file() and not old.is_symlink(),
         'HISTORICAL_REQUEST_MISSING')

    old_raw=old.read_bytes()

    committed=subprocess.check_output([
        'git','-C',str(repo),'show',
        'HEAD:'+HISTORICAL_REQUEST
    ])

    need(old_raw==committed,'HISTORICAL_REQUEST_CHANGED')

    old_text=old_raw.decode('utf-8')

    need(
        'NOT SENT' in old_text
        and 'not requesting another GT download' in old_text
        and 'room_02' in old_text,
        'HISTORICAL_REQUEST_SEMANTICS'
    )

    return r92,sha(raw),sha(old_raw)

def build(r92,r92_hash,old_hash):
    gate_matrix=r92['gate_matrix']
    timing_matrix=r92['timing_receipt_matrix']

    need(
        len(gate_matrix)==11
        and len(timing_matrix)==5,
        'COUNT'
    )

    gates={}

    for name,entry in sorted(gate_matrix.items()):
        need(
            entry['physical_gate_authorized'] is False,
            'GATE_ALREADY_AUTHORIZED'
        )

        fields=entry['historical_required_fields']

        need(
            type(fields) is list
            and len(fields)>0
            and len(set(fields))==len(fields),
            'GATE_FIELDS'
        )

        gates[name]={
            'required_evidence_fields':fields,
            'current_qualification':'NOT_QUALIFIED',
            'physical_authorization':False,
            'independent_validation_received':False
        }

    timing={}

    for name,entry in sorted(timing_matrix.items()):
        need(
            entry['physical_capture_time_qualified'] is False,
            'TIMING_ALREADY_QUALIFIED'
        )

        fields=entry['missing_receipt_fields']

        need(
            type(fields) is list
            and len(fields)>0
            and len(set(fields))==len(fields),
            'TIMING_FIELDS'
        )

        timing[name]={
            'required_evidence_fields':fields,
            'physical_capture_time_qualified':False,
            'independent_validation_received':False
        }

    actions=r92['priority_actions']

    need(
        [x['priority'] for x in actions]==[1,2,3,4,5],
        'ACTION_ORDER'
    )

    need(
        {name for a in actions for name in a['gate_dependencies']}
        ==set(gates),
        'ACTION_GATE_COVERAGE'
    )

    need(
        r92['reference_recovery']['raw_gt_bytes_recovered_locally']
        is True
        and r92['reference_recovery']['reference_physically_qualified']
        is False,
        'GT_RECOVERY_DISTINCTION'
    )

    return {
        'schema':SCHEMA,
        'status':'DRAFT_READY_FOR_USER_REVIEW_NOT_SENT',
        'r92_decision_sha256':r92_hash,
        'historical_r76_unsent_request_sha256':old_hash,
        'trajectory_id':'room_02',
        'split':'train',
        'source_request_target':'M2DGR_RECORDING_AUTHORS_OR_INDEPENDENT_MEASUREMENT_OWNER',
        'request_recipient_address_known':False,
        'request_sent':False,
        'response_received':False,
        'gate_requests':gates,
        'timing_stream_requests':timing,
        'priority_actions':actions,
        'raw_gt_recovery_resolved_locally':True,
        'reference_qualifications_completed':False,
        'raw_gt_re_download_required':False,
        'new_external_source_received':False,
        'source_bytes_independently_verified':False,
        'physical_qualification_authorized':False,
        'real_factor_execution_authorized':False,
        'health_training_authorized':False,
        'ate_rpe_authorized':False,
        'confirmation_test_accessed':False,
        'scientific_gates_closed':11
    }

def draft(p):
    stream_names=', '.join(
        p['timing_stream_requests']
    )

    return '\n'.join([
        '# DRAFT — NOT SENT',
        '',
        '**Subject:** M2DGR room_02 physical calibration, clock and Vicon evidence request',
        '',
        'Hello M2DGR dataset team,',
        '',
        'We are conducting reproducible, trustworthy multimodal localization research using the released M2DGR training data.',
        'We have already recovered the original room_02 ground-truth file, so we are not requesting another GT download.',
        'Our goal is to establish independently checkable physical timing and frame definitions rather than infer them from numerical correlations.',
        '',
        'Could you please share existing recording-specific documentation, configuration files, calibration exports or measurement logs for:',
        '',
        '1. **Capture time and clock definitions:** the physical event associated with ROS headers, timestamp epoch and units, original publisher/device versions, and any hardware synchronization, offset, drift, mapping-sign convention and uncertainty for each sensor stream.',
        '2. **Five relevant streams:** '+stream_names+'. Please specify any differences in capture-time semantics, including LiDAR scan/point firing time and RGB exposure time.',
        '3. **Vicon geometry:** tracked rigid-body name and marker set, body origin and world reference, the mocap-body-to-LiDAR SE(3) transform with direction and metric units, and evidence applicable to room_02.',
        '4. **Vicon time export:** what ground-truth timestamps represent, the export timebase, any conversion to the recording clock, and its uncertainty.',
        '5. **Sensor calibration:** recording-applicable camera intrinsics/distortion and full camera–IMU, camera–LiDAR and other relevant sensor transforms, with direction, units, source version and any independent checks.',
        '6. **Reference-quality records:** original tracking-validity indicators and recording-specific information about missing poses or invalid rotation records, so that a treatment can be predeclared without arbitrary filtering.',
        '',
        'For each available item, a source file or document, version/date, the recording(s) to which it applies, coordinate conventions and uncertainty or independent verification details would be helpful.',
        'If an item was not recorded or is no longer available, confirmation of that limitation is also valuable; approximate rates or an assumed zero offset are not substitutes for measured physical timing.',
        '',
        'We will not assume these materials establish calibration or scoring readiness until we perform an independent verification.',
        '',
        'Thank you.',
        '',
        '**Status: draft for user review only. Not sent automatically.**',
        ''
    ])

def intake_checklist(p):
    rows=[
        '# R93 physical-source intake checklist — no evidence received',
        '',
        'This checklist is administrative readiness, not physical verification.',
        'All entries currently require new evidence and independent review.',
        '',
        '## Physical timing receipts',
        ''
    ]

    for name,item in p['timing_stream_requests'].items():
        rows.append(
            '- [ ] **'+name+'**: '+
            ', '.join(item['required_evidence_fields'])
        )

    rows.extend(['','## Eleven scientific gate receipts',''])

    for name,item in p['gate_requests'].items():
        rows.append(
            '- [ ] **'+name+'**: '+
            ', '.join(item['required_evidence_fields'])
        )

    rows.extend([
        '',
        '## On receipt of any new source',
        '',
        '- Record the original source and version, acquisition method, applicable TRAIN sequence, bytes and SHA-256 outside Git.',
        '- Independently verify physical event/frame semantics, units, transformation direction, uncertainty and recording applicability.',
        '- Preserve the original evidence without edits; keep raw sources and identifying paths outside Git.',
        '- Distinguish source-format validity from physical qualification and independent scientific authorization.',
        '- Never open confirmation_test or authorize real sensor factors, health training or ATE/RPE from metadata alone.',
        '',
        'Historical R43/R53 receipts are frozen. A later independently checked decision must not rewrite them.',
        'Original room_02 GT bytes are already recovered; reference timing, frame semantics and 90 invalid rotations remain unresolved.',
        ''
    ])

    return '\n'.join(rows)

FIELDS={
    'schema','receipt_category','receipt_id',
    'trajectory_id','split','source_reference',
    'source_sha256','evidence_fields',
    'independent_validation_sha256',
    'source_bytes_verified','physical_validation_completed',
    'factor_execution_authorized','confirmation_test_accessed'
}

SHA=re.compile(r'[0-9a-f]{64}\Z')

def validate_candidate(packet,package):
    """Metadata shape only. Even PASS never authorizes physics."""

    need(
        type(packet) is dict and set(packet)==FIELDS,
        'CANDIDATE_FIELDS'
    )

    need(
        packet['schema']==CANDIDATE,
        'CANDIDATE_SCHEMA'
    )

    category=packet['receipt_category']
    ident=packet['receipt_id']

    need(
        type(category) is str
        and category in ('gate','timing'),
        'CATEGORY'
    )

    expected=(
        package['gate_requests']
        if category=='gate'
        else package['timing_stream_requests']
    )

    need(
        type(ident) is str and ident in expected,
        'RECEIPT_ID'
    )

    need(
        packet['trajectory_id']=='room_02'
        and packet['split']=='train',
        'SPLIT_OR_SEQUENCE'
    )

    ref=packet['source_reference']

    need(
        type(ref) is str
        and 0<len(ref)<=300
        and all(c.isprintable() and not c.isspace() for c in ref)
        and (
            ref.startswith('https://')
            or ref.startswith('author-source:')
        )
        and '/home/' not in ref
        and '/mnt/' not in ref,
        'SOURCE_REFERENCE'
    )

    digest=packet['source_sha256']

    need(
        type(digest) is str
        and SHA.fullmatch(digest) is not None
        and digest!='0'*64,
        'SOURCE_SHA_FORMAT'
    )

    evidence=packet['evidence_fields']

    need(
        type(evidence) is dict
        and set(evidence)==set(
            expected[ident]['required_evidence_fields']
        ),
        'REQUIRED_FIELD_SET'
    )

    for key,value in evidence.items():
        need(
            value is None
            or (
                type(value) is str
                and 0<len(value)<=300
                and value.isprintable()
                and '/home/' not in value
                and '/mnt/' not in value
            ),
            'UNVERIFIED_FIELD:'+key
        )

    need(
        packet['independent_validation_sha256'] is None,
        'UNVERIFIED_INDEPENDENT_CHECK'
    )

    for key in (
        'source_bytes_verified',
        'physical_validation_completed',
        'factor_execution_authorized',
        'confirmation_test_accessed'
    ):
        need(
            packet[key] is False,
            'UNAUTHORIZED_CANDIDATE:'+key
        )

    return {
        'status':'METADATA_FORMAT_ONLY_NOT_PHYSICALLY_QUALIFIED',
        'receipt_category':category,
        'receipt_id':ident,
        'source_bytes_verified':False,
        'physical_qualification_established':False,
        'factor_execution_authorized':False
    }

def run(repo,r92_result,out):
    r92,r92hash,oldhash=load_inputs(
        repo,r92_result
    )

    package=build(r92,r92hash,oldhash)
    out=pathlib.Path(out)

    with (out/'r93_outreach_readiness_v1.json').open('xb') as f:
        f.write(canonical(package))

    (out/'r93_author_evidence_request_DRAFT_NOT_SENT.md').write_text(
        draft(package),encoding='utf-8'
    )

    (out/'r93_source_intake_checklist_v1.md').write_text(
        intake_checklist(package),encoding='utf-8'
    )

    print('R93_EVIDENCE_REQUEST=DRAFT_NOT_SENT')
    print('R93_GATE_RECEIPT_REQUIREMENTS=11')
    print('R93_PHYSICAL_TIMING_RECEIPT_REQUIREMENTS=5')
    print('R93_EXISTING_R76_DRAFT=ACKNOWLEDGED_NOT_DUPLICATED')

if __name__=='__main__':
    import sys
    run(*sys.argv[1:])
