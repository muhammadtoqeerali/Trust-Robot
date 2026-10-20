"""R28 non-sensor positive and 12 explicit fail-closed software controls."""
import copy
import numpy as np
import r28_sensitivity as r

rng=np.random.default_rng(28001)
a=rng.uniform(-3,3,(512,3)).astype(np.float64)
b=a+np.array([.02,-.01,.005])
base=r.register(a,b,'identity')
assert base['final_rmse_m']<base['initial_rmse_m']
assert base['iterations']==10 and base['is_pose_factor'] is False
assert r.numerical_geometry(a)['numerical_rank']==3
assert r.numerical_geometry(np.column_stack((a[:,0],a[:,1],np.zeros(512))))['numerical_rank']==2
assert r.numerical_geometry(np.column_stack((a[:,0],np.zeros((512,2)))))['numerical_rank']==1
for kind in r.SUBSETS:
    idx=r.indices(600,kind)
    assert len(idx)==512 and len(set(idx))==512
print('R28_MANUFACTURED_SENSITIVITY_AND_GEOMETRY_FIXTURE=PASS')

up={k:False for k in ('real_sensor_factor_execution_authorized','physical_capture_semantics_verified',
  'cross_modal_synchronization_verified','full_extrinsics_verified','independent_ground_truth_scored',
  'm2dgr_scoring_authorized','health_training_authorized','raw_sensor_modified','git_modified')}
up.update(new_raw_sensor_acquisitions=0,real_pose_factors_generated=0,health_labels_generated=0)
r.false_gates(up)
ref={'registration_diagnostic':{'rotation_previous_from_current':base['rotation_previous_from_current'],
    'translation_previous_from_current_m':base['translation_previous_from_current_m'],
    'identity_nearest_neighbor_rmse_m':base['initial_rmse_m'],
    'candidate_nearest_neighbor_rmse_m':base['final_rmse_m'],
    'candidate_median_nn_distance_m':base['final_median_nn_m']}}

bad=[]
bad.append(lambda:r.indices(511,'linspace'))
bad.append(lambda:r.indices(600,'unknown'))
bad.append(lambda:r.register(a[:-1],b,'identity'))
bad.append(lambda:r.register(a,np.full_like(b,np.nan),'identity'))
bad.append(lambda:r.register(a,b,'unknown'))
bad.append(lambda:r.numerical_geometry(np.full_like(a,np.nan)))
bad.append(lambda:r.false_gates(dict(up,real_sensor_factor_execution_authorized=True)))
bad.append(lambda:r.false_gates(dict(up,health_labels_generated=1)))
bad.append(lambda:r.false_gates(dict(up,m2dgr_scoring_authorized=True)))
bad.append(lambda:r.false_gates(dict(up,physical_capture_semantics_verified=True)))
bad.append(lambda:r.baseline_check(ref,dict(base,initial_rmse_m=base['initial_rmse_m']+1.)))
bad.append(lambda:r.baseline_check(ref,dict(base,translation_previous_from_current_m=[42,0,0])))
assert len(bad)==12
for k,case in enumerate(bad):
    try:case()
    except (ValueError,TypeError,np.linalg.LinAlgError):continue
    raise AssertionError('R28_NEGATIVE_NOT_REJECTED:'+str(k))
print('R28_NEGATIVE_NUMERIC_SCIENTIFIC_CONTROLS=12_REJECTED')
