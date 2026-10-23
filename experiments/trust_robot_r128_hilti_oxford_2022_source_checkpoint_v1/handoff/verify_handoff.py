"""Standalone sanitized handoff checker; no external dependencies."""
import ast, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TOPICS={**{f'/alphasense/cam{i}/image_raw':'camera' for i in range(5)},'/alphasense/imu':'imu','/hesai/pandar':'lidar'}
NAMES={
 'r128_b11_sanitized_summary_v1.json','r128_b11_source_lineage_v1.json',
 'r128_b11a_r1_failure_lineage_v1.json','r128_b9_sensor_audit.py',
 'r128_b10_timing.py','SCIENTIFIC_SCOPE.md','verify_handoff.py',
}
def require(c,reason):
    if not c: raise ValueError('R128_B11A_R1_VERIFY_DENIED:'+reason)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_text())
def check_scope(s):
    q=s['scientific_boundary']
    return (s['schema']=='TRUST_ROBOT_R128_B11_R1_SANITIZED_SUMMARY_V1' and
      s['source_bag_sha256']=='18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82' and
      s['decoded_message_count']==896 and s['sensor_topic_count']==7 and
      set(s['topics'])==set(TOPICS) and q['m2dgr_scientific_gates_closed']==11 and
      all(q[k] is False for k in ('physical_clock_sync_proven','camera_imu_timeshift_independently_verified','lidar_scan_time_semantics_verified','independent_6dof_reference_proven','groundtruth_accessed','dataset_partition_frozen','training_performed','metric_scoring_authorized','real_localization_factors_admitted','m2dgr_confirmation_test_accessed')))
def main():
    m=read('manifest_v1.json')
    require(m['schema']=='TRUST_ROBOT_R128_B11_R1_MANIFEST_V1','SCHEMA')
    require(set(m['file_sha256'])==NAMES,'PIN_SET')
    require({p.name for p in ROOT.iterdir()}==NAMES|{'manifest_v1.json'},'EXACT_FILE_SET')
    for name,digest in m['file_sha256'].items():
        p=ROOT/name
        require(p.is_file() and not p.is_symlink() and p.stat().st_size<250000,'FILE_'+name)
        require(re.fullmatch('[0-9a-f]{64}',digest) and sha(p)==digest,'SHA_'+name)
    s=read('r128_b11_sanitized_summary_v1.json')
    l=read('r128_b11_source_lineage_v1.json')
    r=read('r128_b11a_r1_failure_lineage_v1.json')
    require(check_scope(s),'SCOPE')
    require(m['scoring_authorized'] is False and m['m2dgr_scientific_gates_closed']==11,'MANIFEST_SCOPE')
    require(l['raw_rosbag_included'] is False and l['raw_gt_included'] is False and l['per_message_sensor_records_included'] is False,'LINEAGE_SCOPE')
    require(r['original_python_line']==167 and r['original_b9_b10_evidence_modified'] is False,'FAILURE_LINEAGE')
    require(r['observed_lidar_unique_width_count']>16,'DIAGNOSIS')
    for topic,kind in TOPICS.items():
        row=s['topics'][topic]
        require(row['modality']==kind and row['sample_count']==128,'SAMPLE_COUNT')
        require(row['header_stamp_count']==128 and row['header_equals_bag_count']==128,'TIMESTAMPS')
        require(row['header_intervals']['count']==127 and row['bag_intervals']['count']==127,'INTERVALS')
        require(type(row['observed_median_rate_hz']) in (float,int) and row['observed_median_rate_hz']>0,'RATE')
        require(1<=len(row['stable_structure_profiles'])<=16,'STABLE_PROFILE_COUNT')
        require('samples' not in row and 'raw_sha256' not in row and 'bag_timestamp_ns' not in row,'NO_MESSAGE_RECORDS')
        if kind=='lidar':
            x=row['lidar_width_aggregate']
            require(x['unique_count']>16 and x['min']>0 and x['min']<=x['median']<=x['max'],'LIDAR_WIDTH_AGGREGATE')
            require(all('width' not in p for p in row['stable_structure_profiles']),'LIDAR_STABLE_ONLY')
        else:require(row['lidar_width_aggregate'] is None,'NO_LIDAR_STATS')
    for name in ('r128_b9_sensor_audit.py','r128_b10_timing.py','verify_handoff.py'):
        ast.parse((ROOT/name).read_text())
    for name in ('r128_b11_sanitized_summary_v1.json','r128_b11_source_lineage_v1.json','r128_b11a_r1_failure_lineage_v1.json','SCIENTIFIC_SCOPE.md'):
        value=(ROOT/name).read_text().lower()
        for bad in ('/mnt/hdd16t/','/home/toqeer/','/home/kios/','toqeer@','kios@'):
            require(bad not in value,'PRIVATE_PATH')
    import copy
    for key in ('metric_scoring_authorized','groundtruth_accessed','physical_clock_sync_proven'):
        changed=copy.deepcopy(s);changed['scientific_boundary'][key]=True
        require(not check_scope(changed),'NEGATIVE_CONTROL')
    print('R128_B11A_R1_VERIFY_SEVEN_TOPICS=PASS')
    print('R128_B11A_R1_VERIFY_896_SAMPLES=PASS')
    print('R128_B11A_R1_VERIFY_FILE_HASHES=7_PASS')
    print('R128_B11A_R1_VERIFY_PRIVACY=PASS')
    print('R128_B11A_R1_NEGATIVE_CONTROLS=3_PASS')
    print('R128_B11A_R1_SCIENTIFIC_GATES=11_CLOSED')
    print('R128_B11A_R1_STANDALONE_VERIFIER=PASS')
if __name__=='__main__':main()
