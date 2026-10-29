import unittest

from first_light.simulator import main_peak, score_trace


class SimulatorTests(unittest.TestCase):
    def test_published_worked_trace(self):
        values = [10, 14, 15, 16, 17, 12, 10, 8, 8, 9, 6, 5]
        result = score_trace(values, [1, 4, 6, 5, 4])
        self.assertEqual((result.target_index, result.final_index), (4, 4))
        self.assertEqual((result.query_count, result.travel, result.search_cost), (5, 8, 13))
        self.assertEqual((result.reversal_count, result.overshoot, result.score), (1, 2, 2955))

    def test_static_repeated_read_has_no_travel_or_new_reversal(self):
        values = [0] * 400
        values[1] = 9
        result = score_trace(values, [1, 1, 2, 2, 1])
        self.assertEqual((result.query_count, result.travel, result.reversal_count), (5, 3, 1))
        self.assertEqual(result.final_index, 1)

    def test_ties_resolve_toward_middle(self):
        values = [6, 8, 10, 9, 8, 10, 4, 7, 10, 4]
        self.assertEqual(main_peak(values), 5)
        self.assertEqual(main_peak([4] * 400), 199)  # local convention for an exact midpoint tie

    def test_hard_boundaries(self):
        values = [0] * 400
        values[0] = 1
        self.assertGreater(score_trace(values, [199, 0]).score, 0)
        self.assertEqual(score_trace(values, [200, 0]).score, 0)
        self.assertGreater(score_trace(values, [0] * 199).score, 0)
        self.assertEqual(score_trace(values, [0] * 200).score, 0)
        self.assertGreater(score_trace(values, [3]).score, 0)
        self.assertEqual(score_trace(values, [4]).score, 0)
        self.assertGreater(score_trace(values, [0], elapsed_seconds=10).score, 0)
        self.assertEqual(score_trace(values, [0], elapsed_seconds=10.0001).score, 0)

        values[0] = 0
        values[1] = 1
        self.assertGreater(score_trace(values, [1, 2, 1, 2, 1, 2, 1, 2]).score, 0)
        self.assertEqual(score_trace(values, [1, 2, 1, 2, 1, 2, 1, 2, 1]).score, 0)

    def test_invalid_index_and_values(self):
        with self.assertRaises(ValueError):
            score_trace([1, 2], [2])
        with self.assertRaises(ValueError):
            score_trace([-1, 2], [1])


if __name__ == "__main__":
    unittest.main()
