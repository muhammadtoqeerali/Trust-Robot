"""Analytic beam/box design comparison; not a new measured sensor result."""
import hashlib
import json
import math
import re
import sys
from pathlib import Path
import numpy as np

EXPECTED_SCENE = '950a84720a4304fd293cd5d5e8297d56b19dae178d127cf9db390d2da5e7a7ea'
EXPECTED_L2 = '4cad184b44bd9d99ebb762a7dcbe04e0c18bd42265568057aaf7f7a1598922c6'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canon(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def vec(block, name):
    match=re.search(r'\b'+re.escape(name)+r'\s*=\s*\(([^)]+)\)',block)
    assert match is not None, name
    result=np.asarray([float(x.strip()) for x in match.group(1).split(',')],dtype=float)
    assert result.shape==(3,) and np.all(np.isfinite(result))
    return result

def scalar(block, name):
    match=re.search(r'\b'+re.escape(name)+r'\s*=\s*([0-9.]+)',block)
    assert match is not None, name
    return float(match.group(1))

def ray_box_hit(origin, direction, lower, upper):
    near=0.0;far=math.inf
    for i in range(3):
        if abs(direction[i])<1e-12:
            if origin[i]<lower[i] or origin[i]>upper[i]:
                return None
            continue
        a=(lower[i]-origin[i])/direction[i]
        b=(upper[i]-origin[i])/direction[i]
        near=max(near,min(a,b))
        far=min(far,max(a,b))
        if near>far:return None
    if not math.isfinite(near) or near<=0:return None
    return origin+near*direction

def spectrum(cloud):
    centered=cloud-cloud.mean(axis=0)
    sv=np.linalg.svd(centered,compute_uv=False)
    h=np.eye(3)*np.sum(centered*centered)-centered.T@centered
    eigen=np.linalg.eigvalsh((h+h.T)/2)
    assert np.min(eigen)>-1e-10 and eigen[-1]>0
    eigen=np.maximum(eigen,0)
    return {
        'point_count':int(len(cloud)),
        'spatial_rank':int(np.linalg.matrix_rank(centered)),
        'singular_values_m':[float(v) for v in sv],
        'second_to_first_singular_ratio':float(sv[1]/sv[0]),
        'smallest_to_largest_rotational_information_ratio':float(eigen[0]/eigen[-1]),
        'locally_linearized_fixed_correspondence_geometry_only':True,
        'calibrated_covariance':False,
        'six_dof_pose_qualified':False,
    }

def measure(origin,lower,upper,azimuth,elevation):
    hits=[]
    for az,el in zip(azimuth,elevation):
        a=math.radians(float(az));e=math.radians(float(el))
        direction=np.asarray([math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e)])
        point=ray_box_hit(origin,direction,lower,upper)
        assert point is not None, 'Hypothetical analytic ray missed frozen front cube'
        hits.append(point-origin)
    return spectrum(np.asarray(hits))

def parse_scene(text):
    assert 'metersPerUnit = 1' in text and 'upAxis = "Z"' in text
    base=text.split('def Cube "Base"',1)[1].split('def Xform "SensorMounts"',1)[0]
    mount=text.split('def Xform "Lidar3DMount"',1)[1].split('def OmniLidar "PilotRTX"',1)[0]
    front=text.split('def Cube "Front"',1)[1].split('def Cube "Left"',1)[0]
    assert 'xformOpOrder = ["xformOp:translate", "xformOp:scale"]' in base
    scale=vec(base,'xformOp:scale')
    base_origin=vec(base,'xformOp:translate')
    mount_translate=vec(mount,'xformOp:translate')
    sensor=base_origin+scale*mount_translate
    front_center=vec(front,'xformOp:translate')
    front_size=scalar(front,'size')
    lower=front_center-front_size/2
    upper=front_center+front_size/2
    az_match=re.search(r'emitterState:s001:azimuthDeg\s*=\s*\[([^]]+)\]',text)
    el_match=re.search(r'emitterState:s001:elevationDeg\s*=\s*\[([^]]+)\]',text)
    assert az_match is not None and el_match is not None
    az=np.asarray([float(v) for v in az_match.group(1).split(',')])
    el=np.asarray([float(v) for v in el_match.group(1).split(',')])
    assert len(az)==len(el)==16 and np.isfinite(az).all() and np.isfinite(el).all()
    assert np.allclose(sensor,[.48,0,.525],atol=1e-12)
    assert np.allclose(front_center,[2,0,.75],atol=1e-12)
    assert front_size==1.5
    return sensor,lower,upper,az,el

def derive(scene_text,l2):
    sensor,lower,upper,az,el=parse_scene(scene_text)
    # Prespecified illustrative beam re-indexing, NOT sensor redesign approval.
    perm=np.asarray([(i*7)%16 for i in range(16)],dtype=int)
    assert len(set(perm))==16
    frozen=measure(sensor,lower,upper,az,el)
    illustration=measure(sensor,lower,upper,az,el[perm])
    assert frozen['point_count']==illustration['point_count']==16
    assert illustration['smallest_to_largest_rotational_information_ratio'] > frozen['smallest_to_largest_rotational_information_ratio']
    actual=l2['geometry_summary']
    assert len(actual)==6 and [r['step'] for r in actual]==[51,61,71,81,91,101]
    assert all(r['six_dof_observability_verified'] is False for r in actual)
    return {
        'schema':'TRUST_ROBOT_L4_ANALYTIC_BEAM_LAYOUT_PROBE_V1',
        'upstream_scene_sha256':EXPECTED_SCENE,
        'upstream_l2_sha256':EXPECTED_L2,
        'scene_sensor_origin_at_unmoved_proxy_m':[float(x) for x in sensor],
        'front_cube_bounds_world_m':{'lower':[float(x) for x in lower],'upper':[float(x) for x in upper]},
        'frozen_azimuth_deg':[float(x) for x in az],
        'frozen_elevation_deg':[float(x) for x in el],
        'hypothetical_elevation_index_permutation':[int(x) for x in perm],
        'frozen_layout_analytic':frozen,
        'illustrative_permuted_layout_analytic':illustration,
        'archived_l2_observed_rotation_information_ratios':[float(r['rotational_information_min_to_max_ratio']) for r in actual],
        'simulation_executed':False,
        'sensor_usd_modified':False,
        'alternative_layout_is_a_proposal_only':True,
        'analytic_intersections_are_not_RTX_GMO_observations':True,
        'sensor_frame_calibration_verified':False,
        'camera_lidar_sync_verified':False,
        'independent_ground_truth_verified':False,
        'health_labels_generated':False,
        'pose_factors_admitted':0,
        'ate_rpe_calculated':False,
        'scientific_threshold_selected':False,
    }

def main():
    assert len(sys.argv)==4
    scene,l2path,out=map(Path,sys.argv[1:])
    for p in (scene,l2path):assert p.is_file() and not p.is_symlink()
    assert out.is_dir() and not out.is_symlink()
    assert sha(scene)==EXPECTED_SCENE and sha(l2path)==EXPECTED_L2
    l2=json.loads(l2path.read_text())
    assert l2['engineering_audit_complete'] is True and l2['pose_factors_accepted']==0
    text=scene.read_text()
    one=derive(text,l2)
    two=derive(text,l2)
    assert canon(one)==canon(two)
    one['deterministic_repeat_identical']=True
    one['implementation_sha256']=sha(Path(__file__))
    target=out/'l4_analytic_beam_layout_report_v1.json'
    with target.open('x') as f:json.dump(one,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print('FROZEN_ANALYTIC_ROTATION_INFORMATION_RATIO=',one['frozen_layout_analytic']['smallest_to_largest_rotational_information_ratio'])
    print('HYPOTHETICAL_ANALYTIC_ROTATION_INFORMATION_RATIO=',one['illustrative_permuted_layout_analytic']['smallest_to_largest_rotational_information_ratio'])
    print('SENSOR_BEAM_COUNT_UNCHANGED=16')
    print('SCENE_AND_EMITTER_SETTINGS_UNCHANGED=YES')
    print('ACTUAL_SIMULATOR_COMPARISON_PERFORMED=NO')
    print('QUALIFIED_POSE_FACTORS=0')
    print('L4_OFFLINE_DESIGN_PROBE=PASS')
    print('L4_REPORT_SHA256='+sha(target))
if __name__=='__main__':main()
