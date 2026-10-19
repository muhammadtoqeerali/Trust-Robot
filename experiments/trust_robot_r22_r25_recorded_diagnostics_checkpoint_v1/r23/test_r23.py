"""Deterministic selection, fail-closed limits, and summary controls."""
import copy,math,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import r23_coverage as e

def denied(f):
    try:f()
    except (ValueError,TypeError,KeyError):return
    raise AssertionError('R23_NEGATIVE_CONTROL_ACCEPTED')

assert e.positions(8)==list(range(8))
assert e.positions(11)==[0,1,2,4,5,7,8,10]
assert e.positions(100)[0]==0 and e.positions(100)[-1]==99
rows=[(i,{0:1,1:2,2:3,3:4}) for i in range(21)]
selected,counts,offsets=e.design(rows,{'camera':{0},'imu':{1},'second_imu':{2},'lidar':{3}})
assert all(len(v)==8 for v in selected.values()) and len(offsets)==8
assert selected['camera']==selected['imu']==selected['lidar']

sample=[{'descriptive_signal':{'grayscale_mean':float(i),'grayscale_stddev':1.0,'width':640,'height':480}} for i in range(8)]
s=e.summarize('/camera/color/image_raw/compressed',sample)
assert s['observed_image_sizes_px']==['640x480'] and s['grayscale_mean']['mean']==3.5
bad=[lambda:e.positions(7),lambda:e.positions(-1),lambda:e.positions(8.0),
     lambda:e.positions(10,7),lambda:e.positions(1000001),
     lambda:e.design([(1,{0:1})]*7,{'camera':{0}}),
     lambda:e.design(rows,{'no_topic':{77}}),
     lambda:e.limits(sample,'missing'),
     lambda:e.limits([{'descriptive_signal':{'x':float('nan')}}]*8,'x'),
     lambda:e.limits([{'descriptive_signal':{'x':1.0}}]*7,'x'),
     lambda:e.summarize('unknown',sample),
     lambda:e.need(False,'BOUNDARY')]
for f in bad:denied(f)
print('R23_DETERMINISTIC_STRATIFIED_SELECTION_FIXTURES=PASS')
print('R23_NEGATIVE_COVERAGE_AND_DIAGNOSTIC_CONTROLS=12_REJECTED')
