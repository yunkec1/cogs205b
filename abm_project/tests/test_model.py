# tests/test_model.py

"""
Tests for the classroom reading norm ABM.

These tests are intentionally written before implementation. They lock down the
scientific assumptions of the model and should not be modified by the
implementation agent.

The implementation agent should modify run_simulation.py only.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


# Make project root importable when tests are run from abm-project/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import run_simulation as sim  # noqa: E402


def ordered_seating(n_rows=5, n_cols=6):
    """Create deterministic seating: student id = row * n_cols + col."""
    return np.arange(n_rows * n_cols).reshape((n_rows, n_cols))


def test_get_neighbors_counts_for_grid_locations():
    """Corner, edge, and interior seats should have the correct neighbor counts."""
    # Corner seat
    corner_neighbors = sim.get_neighbors(row=0, col=0, n_rows=5, n_cols=6)
    assert len(corner_neighbors) == 3
    assert (0, 0) not in corner_neighbors

    # Non-corner edge seat
    edge_neighbors = sim.get_neighbors(row=0, col=2, n_rows=5, n_cols=6)
    assert len(edge_neighbors) == 5
    assert (0, 2) not in edge_neighbors

    # Interior seat
    interior_neighbors = sim.get_neighbors(row=2, col=2, n_rows=5, n_cols=6)
    assert len(interior_neighbors) == 8
    assert (2, 2) not in interior_neighbors


def test_get_neighbors_are_within_grid_bounds():
    """Neighbor coordinates should always be valid grid positions."""
    for row in range(5):
        for col in range(6):
            neighbors = sim.get_neighbors(row=row, col=col, n_rows=5, n_cols=6)
            for n_row, n_col in neighbors:
                assert 0 <= n_row < 5
                assert 0 <= n_col < 6


def test_random_seating_assigns_each_student_once():
    """Random seating should place every student exactly once in the 5x6 grid."""
    rng = np.random.default_rng(123)
    seating = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng)

    assert isinstance(seating, np.ndarray)
    assert seating.shape == (5, 6)
    assert sorted(seating.ravel().tolist()) == list(range(30))


def test_random_seating_is_reproducible_with_same_seed():
    """Using the same seed should produce the same seating arrangement."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)

    seating1 = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng1)
    seating2 = sim.random_seating(n_students=30, n_rows=5, n_cols=6, rng=rng2)

    np.testing.assert_array_equal(seating1, seating2)


def test_social_adoption_uses_actual_neighbor_denominator_for_corner():
    """
    Corner seats have 3 neighbors, so threshold=0.5 means:
    - 1 detected non-reading neighbor: 1/3 < 0.5, should not adopt.
    - 2 detected non-reading neighbors: 2/3 >= 0.5, should adopt.
    This catches the mistake of using 8 as the denominator for every seat.
    """
    seating = ordered_seating()
    corner_student = seating[0, 0]
    corner_neighbor_ids = [seating[r, c] for r, c in sim.get_neighbors(0, 0, 5, 6)]

    # Case 1: only 1 out of 3 corner neighbors is non-reading
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

    assert post_social[corner_student] == 1

    # Case 2: 2 out of 3 corner neighbors are non-reading
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

    assert post_social[corner_student] == 0


def test_high_visibility_detects_nonreading_neighbors_and_triggers_adoption():
    """
    With high visibility, an interior reader with at least 4/8 non-reading
    neighbors should socially adopt non-reading at threshold=0.5.
    """
    seating = ordered_seating()
    center_student = seating[2, 2]
    center_neighbor_ids = [seating[r, c] for r, c in sim.get_neighbors(2, 2, 5, 6)]

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

    assert post_social[center_student] == 0


def test_visibility_zero_prevents_social_detection():
    """
    Visibility=0 means non-reading behavior is never detected.
    Even if all neighbors are actually non-readers, a reader should not socially
    adopt at threshold=0.5.
    """
    seating = ordered_seating()
    center_student = seating[2, 2]
    center_neighbor_ids = [seating[r, c] for r, c in sim.get_neighbors(2, 2, 5, 6)]

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

    assert post_social[center_student] == 1


def test_no_unadoption_in_social_update():
    """Students who are already non-readers should remain non-readers."""
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

    assert np.all(post_social[already_nonreaders] == 0)


def test_natural_decay_changes_only_readers_and_never_recovers_nonreaders():
    """
    With p_decay=1.0, all remaining readers should become non-readers.
    Existing non-readers should stay non-readers.
    """
    states = np.ones(30, dtype=int)
    states[[0, 3, 12]] = 0

    rng = np.random.default_rng(5)
    decayed = sim.apply_natural_decay(states=states, p_decay=1.0, rng=rng)

    assert np.all(decayed == 0)


def test_natural_decay_zero_leaves_states_unchanged():
    """With p_decay=0, natural decay should not change any states."""
    states = np.ones(30, dtype=int)
    states[[0, 3, 12]] = 0

    rng = np.random.default_rng(5)
    decayed = sim.apply_natural_decay(states=states, p_decay=0.0, rng=rng)

    np.testing.assert_array_equal(decayed, states)


def test_step_week_all_reading_no_decay_stays_all_reading():
    """
    If everyone reads and p_decay=0, there is no source of non-reading behavior.
    Reading rate should remain 1 after one weekly transition.
    """
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


def test_threshold_zero_causes_immediate_social_adoption():
    """
    If threshold=0, then observed_nonreading_proportion >= threshold is always
    true for readers. With p_decay=0, all readers should become non-readers
    through social adoption in one weekly transition.
    """
    states = np.ones(30, dtype=int)
    rng = np.random.default_rng(99)

    next_states = sim.step_week(
        states=states,
        visibility=1.0,
        threshold=0.0,
        p_decay=0.0,
        rng=rng,
    )

    assert np.all(next_states == 0)


def test_states_remain_binary_after_step_week():
    """A weekly update should never create state values other than 0 or 1."""
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

    assert set(np.unique(next_states)).issubset({0, 1})


def test_run_one_simulation_is_reproducible_with_same_seed():
    """The same seed and parameters should produce the same simulation trajectory."""
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

    assert isinstance(result1, pd.DataFrame)
    assert isinstance(result2, pd.DataFrame)

    pd.testing.assert_frame_equal(result1, result2)


def test_run_one_simulation_records_required_columns():
    """Simulation output should contain the columns needed for analysis."""
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

    assert required_columns.issubset(set(result.columns))


def test_run_one_simulation_starts_with_all_students_reading():
    """The first recorded week should have all students reading."""
    result = sim.run_one_simulation(
        seed=123,
        visibility=1.0,
        n_weeks=20,
        p_decay=0.05,
        threshold=0.5,
    )

    first_row = result.sort_values("week").iloc[0]

    assert first_row["n_readers"] == 30
    assert first_row["n_nonreaders"] == 0
    assert first_row["reading_rate"] == 1.0
    assert first_row["nonreading_rate"] == 0.0

def test_step_week_all_nonreaders_stay_all_nonreaders():
    """
    If all students are already non-readers, they should remain non-readers.
    This checks the absorbing 0 state at the weekly-update level.
    """
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


def test_run_experiment_returns_expected_small_output():
    """
    run_experiment should support small test runs and return one row per
    week x seed x visibility condition.
    """
    result = sim.run_experiment(
        n_seeds=2,
        n_weeks=3,
        p_decay=0.05,
        threshold=0.5,
    )

    assert isinstance(result, pd.DataFrame)

    # 2 visibility conditions x 2 seeds x 3 weeks
    assert len(result) == 12

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

    assert required_columns.issubset(set(result.columns))
    assert set(result["visibility_condition"]) == {"high", "low"}
    assert set(result["visibility"]) == {1.0, 0.5}

def test_summarize_results_returns_condition_week_summary():
    """
    summarize_results should summarize reading-rate trajectories by
    visibility condition and week.
    """
    raw = sim.run_experiment(
        n_seeds=2,
        n_weeks=3,
        p_decay=0.05,
        threshold=0.5,
    )

    summary = sim.summarize_results(raw)

    assert isinstance(summary, pd.DataFrame)

    required_columns = {
        "week",
        "visibility_condition",
        "mean_reading_rate",
        "std_reading_rate",
        "mean_nonreading_rate",
        "n_seeds",
    }

    assert required_columns.issubset(set(summary.columns))

    # 2 visibility conditions x 3 weeks
    assert len(summary) == 6

    assert set(summary["visibility_condition"]) == {"high", "low"}