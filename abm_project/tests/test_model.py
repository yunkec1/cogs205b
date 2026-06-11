"""
Unit tests for the classroom reading norm ABM.

These tests are intentionally written before implementation. They lock down the
scientific assumptions of the model and should not be modified by the
implementation agent.

The implementation agent should modify run_simulation.py only.
"""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import run_simulation as sim  # noqa: E402


def ordered_seating(n_rows=5, n_cols=6):
    """Create deterministic seating: student id = row * n_cols + col."""
    return np.arange(n_rows * n_cols).reshape((n_rows, n_cols))


class TestClassroomReadingABM(unittest.TestCase):
    def test_get_neighbors_counts_for_grid_locations(self):
        corner_neighbors = sim.get_neighbors(row=0, col=0, n_rows=5, n_cols=6)
        self.assertEqual(len(corner_neighbors), 3)
        self.assertNotIn((0, 0), corner_neighbors)

        edge_neighbors = sim.get_neighbors(row=0, col=2, n_rows=5, n_cols=6)
        self.assertEqual(len(edge_neighbors), 5)
        self.assertNotIn((0, 2), edge_neighbors)

        interior_neighbors = sim.get_neighbors(row=2, col=2, n_rows=5, n_cols=6)
        self.assertEqual(len(interior_neighbors), 8)
        self.assertNotIn((2, 2), interior_neighbors)

    def test_get_neighbors_are_within_grid_bounds(self):
        for row in range(5):
            for col in range(6):
                neighbors = sim.get_neighbors(row=row, col=col, n_rows=5, n_cols=6)
                for n_row, n_col in neighbors:
                    self.assertGreaterEqual(n_row, 0)
                    self.assertLess(n_row, 5)
                    self.assertGreaterEqual(n_col, 0)
                    self.assertLess(n_col, 6)

    def test_random_seating_assigns_each_student_once(self):
        rng = np.random.default_rng(123)
        seating = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng)

        self.assertIsInstance(seating, np.ndarray)
        self.assertEqual(seating.shape, (5, 6))
        self.assertEqual(sorted(seating.ravel().tolist()), list(range(30)))

    def test_random_seating_is_reproducible_with_same_seed(self):
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)

        seating1 = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng1)
        seating2 = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng2)

        np.testing.assert_array_equal(seating1, seating2)

    def test_social_adoption_uses_actual_neighbor_denominator_for_corner(self):
        seating = ordered_seating()
        corner_student = seating[0, 0]
        corner_neighbor_ids = [
            seating[r, c] for r, c in sim.get_neighbors(0, 0, 5, 6)
        ]

        states = np.ones(30, dtype=int)
        states[corner_neighbor_ids[0]] = 0

        rng = np.random.default_rng(1)
        post_social = sim.apply_social_adoption(
            states=states,
            seating=seating,
            visibility=1.0,
            threshold=0.5,
            rng=rng,
        )

        self.assertEqual(post_social[corner_student], 1)

        states = np.ones(30, dtype=int)
        states[corner_neighbor_ids[0]] = 0
        states[corner_neighbor_ids[1]] = 0

        rng = np.random.default_rng(1)
        post_social = sim.apply_social_adoption(
            states=states,
            seating=seating,
            visibility=1.0,
            threshold=0.5,
            rng=rng,
        )

        self.assertEqual(post_social[corner_student], 0)

    def test_high_visibility_detects_nonreading_neighbors_and_triggers_adoption(self):
        seating = ordered_seating()
        center_student = seating[2, 2]
        center_neighbor_ids = [
            seating[r, c] for r, c in sim.get_neighbors(2, 2, 5, 6)
        ]

        states = np.ones(30, dtype=int)
        for student_id in center_neighbor_ids[:4]:
            states[student_id] = 0

        rng = np.random.default_rng(10)
        post_social = sim.apply_social_adoption(
            states=states,
            seating=seating,
            visibility=1.0,
            threshold=0.5,
            rng=rng,
        )

        self.assertEqual(post_social[center_student], 0)

    def test_visibility_zero_prevents_social_detection(self):
        seating = ordered_seating()
        center_student = seating[2, 2]
        center_neighbor_ids = [
            seating[r, c] for r, c in sim.get_neighbors(2, 2, 5, 6)
        ]

        states = np.ones(30, dtype=int)
        for student_id in center_neighbor_ids:
            states[student_id] = 0

        rng = np.random.default_rng(10)
        post_social = sim.apply_social_adoption(
            states=states,
            seating=seating,
            visibility=0.0,
            threshold=0.5,
            rng=rng,
        )

        self.assertEqual(post_social[center_student], 1)

    def test_no_unadoption_in_social_update(self):
        seating = ordered_seating()
        states = np.ones(30, dtype=int)
        already_nonreaders = [0, 5, 17]
        states[already_nonreaders] = 0

        rng = np.random.default_rng(12)
        post_social = sim.apply_social_adoption(
            states=states,
            seating=seating,
            visibility=1.0,
            threshold=0.5,
            rng=rng,
        )

        self.assertTrue(np.all(post_social[already_nonreaders] == 0))

    def test_natural_decay_changes_only_readers_and_never_recovers_nonreaders(self):
        states = np.ones(30, dtype=int)
        states[[0, 3, 12]] = 0

        rng = np.random.default_rng(5)
        decayed = sim.apply_natural_decay(states=states, p_decay=1.0, rng=rng)

        self.assertTrue(np.all(decayed == 0))

    def test_natural_decay_zero_leaves_states_unchanged(self):
        states = np.ones(30, dtype=int)
        states[[0, 3, 12]] = 0

        rng = np.random.default_rng(5)
        decayed = sim.apply_natural_decay(states=states, p_decay=0.0, rng=rng)

        np.testing.assert_array_equal(decayed, states)

    def test_step_week_all_reading_no_decay_stays_all_reading(self):
        states = np.ones(30, dtype=int)
        rng = np.random.default_rng(99)

        next_states = sim.step_week(
            states=states,
            visibility=1.0,
            threshold=0.5,
            p_decay=0.0,
            rng=rng,
        )

        np.testing.assert_array_equal(next_states, np.ones(30, dtype=int))

    def test_threshold_zero_causes_immediate_social_adoption(self):
        states = np.ones(30, dtype=int)
        rng = np.random.default_rng(99)

        next_states = sim.step_week(
            states=states,
            visibility=1.0,
            threshold=0.0,
            p_decay=0.0,
            rng=rng,
        )

        self.assertTrue(np.all(next_states == 0))

    def test_states_remain_binary_after_step_week(self):
        states = np.ones(30, dtype=int)
        states[[1, 7, 20]] = 0
        rng = np.random.default_rng(100)

        next_states = sim.step_week(
            states=states,
            visibility=0.5,
            threshold=0.5,
            p_decay=0.05,
            rng=rng,
        )

        self.assertTrue(set(np.unique(next_states)).issubset({0, 1}))

    def test_run_one_simulation_is_reproducible_with_same_seed(self):
        result1 = sim.run_one_simulation(
            seed=123,
            visibility=0.5,
            n_weeks=20,
            p_decay=0.05,
            threshold=0.5,
        )

        result2 = sim.run_one_simulation(
            seed=123,
            visibility=0.5,
            n_weeks=20,
            p_decay=0.05,
            threshold=0.5,
        )

        self.assertIsInstance(result1, pd.DataFrame)
        self.assertIsInstance(result2, pd.DataFrame)

        pd.testing.assert_frame_equal(result1, result2)

    def test_run_one_simulation_records_required_columns(self):
        result = sim.run_one_simulation(
            seed=123,
            visibility=1.0,
            n_weeks=20,
            p_decay=0.05,
            threshold=0.5,
        )

        required_columns = {
            "week",
            "visibility",
            "seed",
            "n_readers",
            "n_nonreaders",
            "reading_rate",
            "nonreading_rate",
        }

        self.assertTrue(required_columns.issubset(set(result.columns)))

    def test_run_one_simulation_starts_with_all_students_reading(self):
        result = sim.run_one_simulation(
            seed=123,
            visibility=1.0,
            n_weeks=20,
            p_decay=0.05,
            threshold=0.5,
        )

        first_row = result.sort_values("week").iloc[0]

        self.assertEqual(first_row["n_readers"], 30)
        self.assertEqual(first_row["n_nonreaders"], 0)
        self.assertEqual(first_row["reading_rate"], 1.0)
        self.assertEqual(first_row["nonreading_rate"], 0.0)

    def test_step_week_all_nonreaders_stay_all_nonreaders(self):
        states = np.zeros(30, dtype=int)
        rng = np.random.default_rng(101)

        next_states = sim.step_week(
            states=states,
            visibility=1.0,
            threshold=0.5,
            p_decay=0.05,
            rng=rng,
        )

        np.testing.assert_array_equal(next_states, np.zeros(30, dtype=int))

    def test_run_experiment_returns_expected_small_output(self):
        result = sim.run_experiment(
            n_seeds=2,
            n_weeks=3,
            p_decay=0.05,
            threshold=0.5,
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 12)

        required_columns = {
            "week",
            "visibility_condition",
            "visibility",
            "seed",
            "n_readers",
            "n_nonreaders",
            "reading_rate",
            "nonreading_rate",
        }

        self.assertTrue(required_columns.issubset(set(result.columns)))
        self.assertEqual(set(result["visibility_condition"]), {"high", "low"})
        self.assertEqual(set(result["visibility"]), {1.0, 0.5})

    def test_summarize_results_returns_condition_week_summary(self):
        raw = sim.run_experiment(
            n_seeds=2,
            n_weeks=3,
            p_decay=0.05,
            threshold=0.5,
        )

        summary = sim.summarize_results(raw)

        self.assertIsInstance(summary, pd.DataFrame)

        required_columns = {
            "week",
            "visibility_condition",
            "mean_reading_rate",
            "std_reading_rate",
            "mean_nonreading_rate",
            "n_seeds",
        }

        self.assertTrue(required_columns.issubset(set(summary.columns)))
        self.assertEqual(len(summary), 6)
        self.assertEqual(set(summary["visibility_condition"]), {"high", "low"})


if __name__ == "__main__":
    unittest.main()
