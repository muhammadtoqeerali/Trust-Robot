"""Portable offline regression for R132 descriptive-only sensor diagnostics."""
import ast
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BRIDGE=ROOT/'r132_diagnostic_bridge.py'
BRIDGE_SHA='735ef8f85023c1f2088ef44d5c3ca946bc85fc8a99128ee68008d9ed267f12fc'
R129_SHA='acdc86114f31e52990a14b74e0787db1fa2d1887dbbd9becd869c02596c838cb'

def require(ok,reason):
    if not ok:
        raise RuntimeError('R132_PORTABLE_DENIED:'+reason)

def denied(fn,exc):
    try:
        fn()
    except exc as error:
        require('DENIED:' in str(error),'WRONG_REJECTION')
        return
    raise RuntimeError('R132_PORTABLE_UNEXPECTED_ADMISSION')

def run(repo):
    raw_src=BRIDGE.read_bytes()
    require(hashlib.sha256(raw_src).hexdigest()==BRIDGE_SHA,'BRIDGE_PIN')
    report_path=repo/'experiments/trust_robot_r129_real_sensor_diagnostics_checkpoint_v1/handoff/r129_b1_aggregate_diagnostics_v1.json'
    require(report_path.is_file() and not report_path.is_symlink(),'REPORT_PATH')
    raw=report_path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==R129_SHA,'REPORT_PIN')

    spec=importlib.util.spec_from_file_location('r132_candidate_bridge',BRIDGE)
    require(spec is not None and spec.loader is not None,'SPEC')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    inv=module.diagnostic_inventory(raw)
    require(len(inv)==7 and sum(len(row[2]) for row in inv)==33,'FEATURE_COUNTS')
    require(
        tuple(sorted(inv))==inv
        and {x[1] for x in inv}=={'camera','lidar','imu'},
        'INVENTORY_STRUCTURE'
    )
    require(
        all(
            type(row) is tuple and len(row)==3
            and type(row[2]) is tuple
            and all(type(v) is str for v in row[2])
            for row in inv
        ),
        'NO_FEATURE_VALUES'
    )
    print('R132_A4_PORTABLE_7_STREAMS_33_FAMILIES=PASS')

    original=json.loads(raw)
    controls=[
        lambda d:d.__setitem__('schema','FAKE'),
        lambda d:d.__setitem__('recording','WRONG'),
        lambda d:d.__setitem__('feature_scope','HEALTH'),
        lambda d:d.__setitem__('decoded_messages',447),
        lambda d:d.__setitem__('sample_limit_per_topic',63),
        lambda d:d['scientific_boundary'].__setitem__('real_factors_authorized',True),
        lambda d:d['scientific_boundary'].__setitem__('health_labels_constructed',True),
        lambda d:d['scientific_boundary'].__setitem__('m2dgr_scientific_gates_closed',10),
        lambda d:d['topics'].pop('/hesai/pandar'),
        lambda d:d['topics']['/alphasense/imu'].__setitem__('frame_ids',['alphasense_imu']),
        lambda d:d['topics']['/alphasense/cam0/image_raw']['feature_statistics'].pop('pixel_mean'),
        lambda d:d['topics']['/hesai/pandar'].__setitem__('sample_count',63),
    ]

    for mutate in controls:
        d=copy.deepcopy(original)
        mutate(d)
        denied(
            lambda x=d:module._structure(x),
            module.DiagnosticBoundaryError
        )
    print('R132_A4_PORTABLE_STRUCTURAL_NEGATIVES=12_PASS')

    for b in (raw+b' ',b'X'+raw[1:],raw[:-1]):
        denied(
            lambda x=b:module.diagnostic_inventory(x),
            module.DiagnosticBoundaryError
        )
    print('R132_A4_PORTABLE_RAW_TAMPERS=3_PASS')

    for entry in ('require_real_factor','require_health_label'):
        for x in (None,{'authorization':'ALLOW'},object()):
            denied(
                lambda f=getattr(module,entry),v=x:f(v),
                module.DiagnosticBoundaryError
            )
    print('R132_A4_PORTABLE_FACTOR_AND_LABEL_DENIALS=6_PASS')

    for rel,name in (
        ('experiments/trust_robot_s1_s5_core_6dof_readiness_v1/code/s3_contract.py','require_real_factor'),
        ('experiments/trust_robot_s1_s5_core_6dof_readiness_v1/code/s4_requirements.py','require_factor_execution'),
    ):
        tree=ast.parse((repo/rel).read_text(encoding='utf-8'))
        functions=[
            n for n in tree.body
            if isinstance(n,ast.FunctionDef) and n.name==name
        ]
        require(len(functions)==1,'GATE_MISSING')
        lines=[
            n for n in functions[0].body
            if not (
                isinstance(n,ast.Expr)
                and isinstance(n.value,ast.Constant)
                and isinstance(n.value.value,str)
            )
        ]
        require(
            len(lines)==1 and isinstance(lines[0],ast.Raise),
            'GATE_MUTATED'
        )

    print('R132_A4_PORTABLE_EXISTING_GATES=2_STATIC_PASS')
    print('R132_A4_PORTABLE_REGRESSION_COMPLETE')

if __name__=='__main__':
    require(len(sys.argv)==2,'REPOSITORY_ARGUMENT')
    run(Path(sys.argv[1]).resolve())
