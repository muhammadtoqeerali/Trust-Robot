import ast
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import r27_lidar_motion as eng
import r27_independent_verify as ind

def must_fail(func,*args):
    try:func(*args)
    except (ValueError,TypeError,AssertionError):return
    raise AssertionError('Expected negative control to be denied')

def main():
    root=Path(__file__).parent
    for f in ('r27_lidar_motion.py','r27_independent_verify.py','test_r27.py'):
        ast.parse((root/f).read_text())
    rng=np.random.default_rng(1527)
    previous=rng.normal(size=(eng.N,3))*np.array([2.,1.,.7])
    translation=np.array([.012,-.018,.008])
    current=previous+translation
    result=eng.candidate(previous,current)
    independent=ind.brute(previous,current)
    assert np.allclose(result['rotation_previous_from_current'],independent[0],atol=1e-8)
    assert np.allclose(result['translation_previous_from_current_m'],independent[1],atol=1e-8)
    assert result['candidate_nearest_neighbor_rmse_m']<1e-9
    assert np.allclose(independent[1],-translation,atol=1e-8)
    selected,idx=eng.select_points(np.vstack([previous,previous+100]))
    assert selected.shape==(512,3) and len(np.unique(idx))==512
    cases=[
        (eng.select_points,np.zeros((5,3))),
        (eng.select_points,np.zeros((600,2))),
        (eng.select_points,np.ones((512,3))*np.nan),
        (eng.candidate,previous[:100],current[:100]),
        (eng.candidate,previous,current[:511]),
        (eng.candidate,np.ones((512,3))*np.inf,current),
        (eng.rigid,previous[:200],current[:200]),
        (eng.rigid,previous,current[:511]),
        (ind.need,False,'REQUIRED'),
        (eng.need,False,'REQUIRED'),
    ]
    for item in cases:must_fail(item[0],*item[1:])
    print('R27_AST_THREE_PYTHON_SOURCES=PASS')
    print('R27_MANUFACTURED_SE3_REGISTRATION_AND_BRUTE_FORCE=PASS')
    print('R27_NEGATIVE_NUMERIC_CONTROLS=10_REJECTED')

if __name__=='__main__':main()
