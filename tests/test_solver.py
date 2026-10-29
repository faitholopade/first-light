import hashlib
from pathlib import Path
import unittest

from first_light.examples import examples
from first_light.simulator import Motor, run_solver


EXPECTED_SHA256 = "149cca767952af550ecd75905a1f460d726798a7707d47e2201e9c60ec25b79c"


class SolverTests(unittest.TestCase):
    def test_scored_source_is_unchanged(self):
        source = Path(__file__).resolve().parents[1] / "first_light" / "contestant.py"
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_entry_point_and_physical_final_parking(self):
        for case in examples():
            with self.subTest(case=case.name):
                result = run_solver(case.values)
                self.assertTrue(result.trace)
                self.assertEqual(result.final_index, result.trace[-1])
                self.assertTrue(all(0 <= i < len(case.values) for i in result.trace))
                self.assertLess(result.query_count, 200)
                self.assertLess(result.reversal_count, 7)

    def test_simple_hill_and_flat_target(self):
        for case in (examples()[0], examples()[2]):
            with self.subTest(case=case.name):
                result = run_solver(case.values)
                self.assertEqual(result.final_index, result.target_index)

    def test_motor_bounds(self):
        motor = Motor([0] * 400)
        with self.assertRaises(ValueError):
            motor.read(-1)
        with self.assertRaises(ValueError):
            motor.read(400)
        self.assertEqual(motor.trace, [])

    def test_length_boundaries(self):
        self.assertEqual(len(examples()[0].values), 400)
        self.assertEqual(len(examples()[-1].values), 1000)
        for size in (399, 1001):
            with self.assertRaises(ValueError):
                run_solver([0] * size)


if __name__ == "__main__":
    unittest.main()
