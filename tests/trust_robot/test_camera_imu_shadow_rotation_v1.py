"""Independent regression for the untrusted R134 camera-IMU shadow."""
import ast
import dataclasses
import hashlib
import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/trust_robot/camera_imu_shadow_rotation_v1.py'

PIN = (
    '048abce9b63a13176dab1ccb36208195c40baa'
    'ee4ba61f91eb793bccd9a04462'
)

I = ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))

def inputs():
    omega = 0.4
    angle = omega * 0.1
    samples = tuple(
        (i*10_000_000,(0.,0.,omega))
        for i in range(21)
    )
    phases = (0.,.3,.8,1.2,2.,2.8)
    pairs = tuple(
        (
            (math.cos(t),math.sin(t),0.),
            (math.cos(t-angle),math.sin(t-angle),0.)
        )
        for t in phases
    )
    return pairs,samples

def load():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN

    name = 'r134_a39_tracked_shadow_test'
    spec = importlib.util.spec_from_file_location(name,SOURCE)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

class ShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def evaluate(self, pairs=None, samples=None, r=I,
                 a=50_000_000, b=150_000_000, shift=0):
        p,s = inputs()
        return self.m.evaluate(
            p if pairs is None else pairs,
            s if samples is None else samples,
            r,a,b,shift
        )

    def test_source_and_import_boundary(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),PIN)
        tree = ast.parse(raw.decode('utf-8'))

        imports = set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                imports.update(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                imports.add(n.module)

        self.assertEqual(imports,{
            '__future__','math','bisect',
            'dataclasses','statistics'
        })

        public = [
            n.name for n in tree.body
            if isinstance(n,ast.FunctionDef)
            and not n.name.startswith('_')
        ]
        self.assertEqual(public,['evaluate'])

    def test_rotation_sign_and_determinism(self):
        report = self.evaluate()
        residuals = {
            m.name:m.median_deg for m in report.modes
        }
        self.assertLess(residuals['NEGATIVE_GYRO'],1e-8)
        self.assertGreater(residuals['ZERO'],2)
        self.assertGreater(residuals['POSITIVE_GYRO'],4)
        self.assertEqual(report,self.evaluate())

    def test_nonidentity_frame(self):
        r = (
            (1.,0.,0.),
            (0.,0.,-1.),
            (0.,1.,0.)
        )
        angle = .04
        phases = (0.,.3,.8,1.2,2.,2.8)
        pairs = tuple(
            (
                (math.cos(t),math.sin(t),0.),
                (
                    math.cos(angle)*math.cos(t),
                    math.sin(t),
                    -math.sin(angle)*math.cos(t)
                )
            )
            for t in phases
        )
        report = self.evaluate(pairs=pairs,r=r)
        self.assertLess(report.modes[1].median_deg,1e-8)

    def test_constant_gyro_clock_ambiguity(self):
        self.assertEqual(
            self.evaluate().modes,
            self.evaluate(shift=10_000_000).modes
        )

    def test_immutable_but_untrusted_report(self):
        report = self.evaluate()
        self.assertEqual(
            report.status,'UNTRUSTED_DIAGNOSTIC_ONLY'
        )
        self.assertFalse(hasattr(report,'real_factor_authorized'))
        self.assertFalse(hasattr(report,'health_label_authorized'))
        self.assertFalse(hasattr(report,'__dict__'))

        with self.assertRaises(dataclasses.FrozenInstanceError):
            report.status = 'AUTHORIZED'

        forged = self.m.ShadowReport(
            self.m.SCHEMA,
            self.m.STATUS,
            999,
            999,
            (self.m.ModeResidual('FAKE',-5.,-5.),)
        )
        self.assertEqual(forged.bearing_pair_count,999)
        self.assertNotEqual(report,forged)

    def test_duplicate_evidence_rejected(self):
        pairs,_ = inputs()
        cases = (
            (pairs[0],)*5,
            pairs[:1]+((pairs[1][0],pairs[0][1]),)+pairs[2:],
            pairs[:1]+(
                (
                    (math.cos(1e-6),math.sin(1e-6),0.),
                    pairs[1][1]
                ),
            )+pairs[2:]
        )
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(self.m.ShadowInputError):
                    self.evaluate(pairs=candidate)

    def test_input_bounds_rejected(self):
        pairs,samples = inputs()
        cases = (
            {'pairs':pairs[:4]},
            {'pairs':pairs*17},
            {'a':True},
            {'a':150_000_000,'b':50_000_000},
            {'shift':True},
            {'shift':300_000_000},
            {'samples':samples[:8]},
            {'samples':samples[:-1]+(samples[-2],)},
            {'samples':samples[:3]+(
                (30_000_000,(float('nan'),0.,0.)),
            )+samples[4:]},
            {'r':((1.,0.,0.),(0.,1.,0.),(0.,0.,-1.))}
        )
        for c in cases:
            with self.subTest(case=str(c)[:50]):
                with self.assertRaises(self.m.ShadowInputError):
                    self.evaluate(
                        pairs=c.get('pairs'),
                        samples=c.get('samples'),
                        r=c.get('r',I),
                        a=c.get('a',50_000_000),
                        b=c.get('b',150_000_000),
                        shift=c.get('shift',0)
                    )

    def test_step_budget_rejected(self):
        many = tuple(
            (i*1_000_000,(0.,0.,.4))
            for i in range(201)
        )
        with self.assertRaises(self.m.ShadowInputError):
            self.evaluate(samples=many,a=0,b=150_000_000)

    def test_no_factor_interface_dependency(self):
        factor = (
            ROOT/'src/trust_robot/multimodal_factor_interface.py'
        ).read_text()
        admission = (
            ROOT/'src/trust_robot/m2dgr_sensor_admission.py'
        ).read_text()

        self.assertNotIn(
            'camera_imu_shadow_rotation_v1',factor
        )
        self.assertNotIn(
            'camera_imu_shadow_rotation_v1',admission
        )

        tree = ast.parse(admission)
        matches = [
            n for n in tree.body
            if isinstance(n,ast.FunctionDef)
            and n.name == 'require_real_factor_execution'
        ]
        self.assertEqual(len(matches),1)
        self.assertIsInstance(matches[0].body[-1],ast.Raise)
        self.assertFalse(any(
            isinstance(n,ast.Return)
            for n in ast.walk(matches[0])
        ))

        factor_tree = ast.parse(factor)
        matches = [
            n for n in factor_tree.body
            if isinstance(n,ast.FunctionDef)
            and n.name == 'require_recorded_factor_execution'
        ]
        self.assertEqual(len(matches),1)
        self.assertIsInstance(matches[0].body[-1],ast.Raise)
        self.assertFalse(any(
            isinstance(n,ast.Return)
            for n in ast.walk(matches[0])
        ))

if __name__ == '__main__':
    unittest.main(verbosity=2)
