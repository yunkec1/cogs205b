# PLAN.md

# ABM Implementation Plan: `run_simulation.py`

## 1. Overall implementation strategy

The project will implement one self-contained Python file:

```text
run_simulation.py
```

This file will contain all ABM logic, simulation code, summary code, plotting code, and the command-line entry point.

The implementation will use:

* `numpy`
* `pandas`
* `matplotlib`
* `pathlib.Path`

Core model representation:

* Students are represented as a state vector of length 30.
* State coding:

  * `1 = reads before class`
  * `0 = does not read before class`
* Seating is represented as a `5 x 6` NumPy array where `seating[row, col] = student_id`.
* Each stochastic function will receive an explicit `numpy.random.Generator`.
* The top-level generator will be created inside `run_one_simulation()` with `np.random.default_rng(seed)`.

Scientific constraints to preserve:

* Adoption means `1 -> 0`.
* No un-adoption is allowed; `0` must never become `1`.
* Visibility means detection probability for non-reading behavior, not observing fewer neighbors.
* Social adoption is synchronous and based on Week `t` states.
* Natural decay is applied after social adoption, only to students who remain readers in `post_social_state`.

The implementation should build the model bottom-up:

```text
geometry
-> seating
-> observation
-> social adoption
-> natural decay
-> weekly step
-> one simulation run
-> experiment runner
-> summary and plotting
```

## 2. Structure of `run_simulation.py`

The file should contain the following sections:

1. Module docstring
   Briefly describe the classroom reading norm ABM.

2. Imports
   Import `numpy`, `pandas`, `matplotlib.pyplot`, and `Path`.

3. Constants
   Define defaults:

```python
N_STUDENTS = 30
N_ROWS = 5
N_COLS = 6
N_WEEKS = 20
THRESHOLD = 0.5
P_DECAY = 0.05
N_SEEDS = 100
VISIBILITY_CONDITIONS = {"high": 1.0, "low": 0.5}
```

4. Grid and seating helpers
   Implement `get_neighbors()` and `random_seating()`.

5. Observation and social adoption
   Implement `compute_observed_nonreading_proportion()` and `apply_social_adoption()`.

6. Natural decay
   Implement `apply_natural_decay()`.

7. Weekly update
   Implement `step_week()`.

8. Single simulation run
   Implement `run_one_simulation()`.

9. Experiment runner
   Implement `run_experiment()`.

10. Summary and plotting
    Implement `summarize_results()` and `plot_reading_rates()`.

11. Command-line entry point
    Implement `main()` and:

```python
if __name__ == "__main__":
    main()
```

## 3. Function responsibilities

### `get_neighbors(row, col, n_rows=5, n_cols=6)`

Return a list of valid neighboring seat coordinates in the `3 x 3` window around `(row, col)`, excluding `(row, col)` itself.

Implementation details:

* Loop over `dr` and `dc` in `{-1, 0, 1}`.
* Skip `(dr, dc) = (0, 0)`.
* Skip coordinates outside the grid.
* Use stable ordering for reproducibility.

Expected neighbor counts:

* corner seat: 3 neighbors
* non-corner edge seat: 5 neighbors
* interior seat: 8 neighbors

### `random_seating(n_students, n_rows, n_cols, rng)`

Randomly assign students to seats.

Implementation details:

* Assert that `n_students == n_rows * n_cols`.
* Use `rng.permutation(n_students)`.
* Reshape the permutation to `(n_rows, n_cols)`.
* Return a NumPy array containing each student ID exactly once.

### `compute_observed_nonreading_proportion(student_id, states, seating, visibility, rng)`

Compute the observed proportion of non-reading neighbors for one student.

Implementation details:

* Find the student’s seat location in the seating grid.
* Get the neighboring seats using `get_neighbors()`.
* Use the actual number of neighboring seats as the denominator.
* For each neighboring student:

  * If the neighbor’s state is `1`, treat them as reading.
  * If the neighbor’s state is `0`, detect the non-reading behavior with probability `visibility`.
* Return:

```python
detected_nonreading_neighbors / actual_number_of_neighboring_seats
```

Do not use 8 as the denominator for all students.

### `apply_social_adoption(states, seating, visibility, threshold, rng)`

Apply the synchronous social adoption rule.

Inputs:

* Week `t` state vector
* Week `t` seating
* visibility
* threshold
* rng

Output:

* `post_social_state`

Rules:

* Do not mutate the input `states`.
* If a student is already `0`, they remain `0`.
* If a student is `1`, compute their observed non-reading proportion.
* If the observed non-reading proportion is greater than or equal to `threshold`, set them to `0` in `post_social_state`.
* Otherwise, keep them as `1`.

Important: all social decisions must be based on the original Week `t` state vector. Do not update sequentially.

### `apply_natural_decay(states, p_decay, rng)`

Apply natural decay after social adoption.

Rules:

* Input is `post_social_state`.
* Students with state `0` remain `0`.
* Students with state `1` independently change to `0` with probability `p_decay`.
* Return a new state vector.

### `step_week(states, visibility, threshold, p_decay, rng)`

Run one weekly transition from Week `t` to Week `t + 1`.

Order:

1. Randomly assign students to seats for Week `t`.
2. Apply social adoption based on Week `t` states and Week `t` seating.
3. Apply natural decay to remaining readers in `post_social_state`.
4. Return final Week `t + 1` states.

### `run_one_simulation(seed, visibility, n_weeks=20, p_decay=0.05, threshold=0.5)`

Run one simulation for one visibility value and one random seed.

Implementation details:

* Create `rng = np.random.default_rng(seed)`.
* Start with all students reading:

```python
states = np.ones(30, dtype=int)
```

* Record Week 1 before any update.
* For each week:

  * record counts and rates
  * if not at the final week, call `step_week()`
* Return a pandas DataFrame.

Required columns:

```text
week
visibility
seed
n_readers
n_nonreaders
reading_rate
nonreading_rate
```

Week indexing:

* Record Week 1 as the initial state.
* For `n_weeks = 20`, return 20 rows.
* There are `n_weeks - 1` transitions.

### `run_experiment(n_seeds=100, n_weeks=20, p_decay=0.05, threshold=0.5)`

Run the full experiment.

Implementation details:

* Run both visibility conditions:

  * `high = 1.0`
  * `low = 0.5`
* Use seeds `0` to `n_seeds - 1`.
* Call `run_one_simulation()` for each condition and seed.
* Add a `visibility_condition` column.
* Concatenate results into one long DataFrame.

Expected raw output columns:

```text
week
visibility_condition
visibility
seed
n_readers
n_nonreaders
reading_rate
nonreading_rate
```

### `summarize_results(df)`

Summarize results across seeds.

Group by:

```text
visibility_condition
week
```

Compute at least:

```text
mean_reading_rate
std_reading_rate
mean_nonreading_rate
n_seeds
```

### `plot_reading_rates(summary_df, output_path)`

Create a line plot of mean reading rate over time.

Implementation details:

* x-axis: week
* y-axis: mean reading rate
* separate line for each visibility condition
* save to `results/reading_rate_by_visibility.png`
* do not call `plt.show()`

### `main()`

Run the full simulation and save outputs.

Implementation details:

1. Create `results/` if it does not exist.
2. Run `run_experiment()`.
3. Summarize results.
4. Save:

```text
results/simulation_results.csv
results/summary_results.csv
results/reading_rate_by_visibility.png
```

## 4. Seating grid and neighbor logic

The classroom grid has:

```text
5 rows x 6 columns = 30 seats
```

Rows are indexed `0` to `4`.
Columns are indexed `0` to `5`.

Examples:

* `(0, 0)` is a corner seat with 3 neighbors.
* `(0, 2)` is a non-corner edge seat with 5 neighbors.
* `(2, 2)` is an interior seat with 8 neighbors.

Observation path:

```text
student ID
-> student seat location
-> neighboring seat coordinates
-> neighboring student IDs
-> neighboring students' reading states
```

The implementation must use the actual neighbor count for each seat location.

## 5. Visibility rule

Visibility is detection probability for non-reading behavior.

For each actual non-reading neighbor:

```text
detected with probability visibility
not detected with probability 1 - visibility
```

If a non-reading neighbor is not detected, the observer treats that neighbor as reading or as not visibly violating the norm.

Reading neighbors are always treated as reading.

Visibility values:

```text
high visibility = 1.0
low visibility = 0.5
```

Additional edge behavior:

* `visibility = 1.0`: all actual non-readers are detected.
* `visibility = 0.5`: each actual non-reader is detected with probability 0.5.
* `visibility = 0.0`: no non-reading behavior is detected; social adoption should not occur at threshold 0.5.

Do not implement visibility as observing fewer neighbors.

## 6. Lagged update timing

The update from Week `t` to Week `t + 1` must follow this order:

```text
Week t states
-> random seating for Week t observation
-> observe neighbors using Week t states
-> synchronous social adoption creates post_social_state
-> natural decay is applied only to remaining readers
-> final Week t+1 states
```

Week 1 starts with all students reading.

Therefore, from Week 1 to Week 2:

* no students are non-readers in Week 1
* no social adoption can occur
* only natural decay can change states

Social adoption must be synchronous. Newly updated Week `t + 1` states must not affect other students during the same social adoption step.

## 7. Simulation settings

Default values:

```python
n_students = 30
n_rows = 5
n_cols = 6
n_weeks = 20
threshold = 0.5
p_decay = 0.05
n_seeds = 100
visibility_conditions = {"high": 1.0, "low": 0.5}
```

The single-run simulation should record 20 rows for `n_weeks = 20`.

The full experiment should run 100 seeds per visibility condition by default.

## 8. Expected qualitative behavior

The scientific hypothesis is not hard-coded as a deterministic test.

Expected pattern:

* high visibility should lead to faster decline in reading rate
* high visibility should cross below 50% reading earlier than low visibility
* low visibility should preserve the reading norm longer
* natural decay alone may eventually reduce reading over 20 weeks, so the key comparison is time course and relative speed of decline

Since Week 1 is recorded before any transition, `n_weeks = 20` corresponds to 19 state transitions. A natural-decay-only expectation at the final recorded week is approximately:

```text
0.95^19 ≈ 0.377
```

## 9. Expected outputs

Running:

```bash
python run_simulation.py
```

from the project root should produce:

```text
results/simulation_results.csv
results/summary_results.csv
results/reading_rate_by_visibility.png
```

## 10. Test-to-implementation mapping

The locked tests in `tests/test_model.py` constrain the following implementation details:

* `test_get_neighbors_counts_for_grid_locations`

  * verifies corner, edge, and interior neighbor counts
  * implementation hook: `get_neighbors()`

* `test_get_neighbors_are_within_grid_bounds`

  * verifies valid grid coordinates
  * implementation hook: `get_neighbors()`

* `test_random_seating_assigns_each_student_once`

  * verifies seating shape and one seat per student
  * implementation hook: `random_seating()`

* `test_random_seating_is_reproducible_with_same_seed`

  * verifies deterministic seating with the same RNG seed
  * implementation hook: `random_seating()`

* `test_social_adoption_uses_actual_neighbor_denominator_for_corner`

  * verifies corner denominator uses 3 neighbors
  * implementation hook: `apply_social_adoption()` and `compute_observed_nonreading_proportion()`

* `test_high_visibility_detects_nonreading_neighbors_and_triggers_adoption`

  * verifies high visibility detects all non-reading neighbors
  * implementation hook: `apply_social_adoption()`

* `test_visibility_zero_prevents_social_detection`

  * verifies visibility is detection probability
  * implementation hook: `apply_social_adoption()`

* `test_no_unadoption_in_social_update`

  * verifies existing non-readers remain non-readers
  * implementation hook: `apply_social_adoption()`

* `test_natural_decay_changes_only_readers_and_never_recovers_nonreaders`

  * verifies natural decay cannot recover non-readers
  * implementation hook: `apply_natural_decay()`

* `test_natural_decay_zero_leaves_states_unchanged`

  * verifies `p_decay = 0` does not change states
  * implementation hook: `apply_natural_decay()`

* `test_step_week_all_reading_no_decay_stays_all_reading`

  * verifies no non-reading source means no decline when `p_decay = 0`
  * implementation hook: `step_week()`

* `test_threshold_zero_causes_immediate_social_adoption`

  * verifies threshold edge case
  * implementation hook: `step_week()` and `apply_social_adoption()`

* `test_states_remain_binary_after_step_week`

  * verifies binary states
  * implementation hook: `step_week()`

* `test_run_one_simulation_is_reproducible_with_same_seed`

  * verifies full-trajectory reproducibility
  * implementation hook: `run_one_simulation()`

* `test_run_one_simulation_records_required_columns`

  * verifies output columns
  * implementation hook: `run_one_simulation()`

* `test_run_one_simulation_starts_with_all_students_reading`

  * verifies Week 1 initial state
  * implementation hook: `run_one_simulation()`

* `test_step_week_all_nonreaders_stay_all_nonreaders`

  * verifies all-non-reader absorbing state
  * implementation hook: `step_week()`

* `test_run_experiment_returns_expected_small_output`

  * verifies full experiment output structure
  * implementation hook: `run_experiment()`

* `test_summarize_results_returns_condition_week_summary`

  * verifies summary structure
  * implementation hook: `summarize_results()`

## 11. Implementation risks and mitigations

### Risk: using 8 as denominator for every seat

Mitigation:

* always use `len(get_neighbors(row, col))`
* tests check the corner case directly

### Risk: treating visibility as observing fewer neighbors

Mitigation:

* implement visibility only as Bernoulli detection for actual non-reading neighbors
* tests include `visibility = 0`

### Risk: applying natural decay before social adoption

Mitigation:

* `step_week()` must call `apply_social_adoption()` first
* then call `apply_natural_decay()` on `post_social_state`

### Risk: sequential social updates

Mitigation:

* read from the original Week `t` state vector
* write to a separate `post_social_state`

### Risk: non-reproducible trajectories

Mitigation:

* use a single explicit RNG per simulation
* pass it into all stochastic functions
* keep iteration order stable

### Risk: `apply_social_adoption()` randomizes seating internally

Mitigation:

* do not randomize seating inside `apply_social_adoption()`
* tests pass a fixed seating grid

### Risk: incorrect week indexing

Mitigation:

* record Week 1 initial state first
* run only `n_weeks - 1` transitions

### Risk: import failure

Mitigation:

* implement all required functions in `run_simulation.py`
* do not leave `run_simulation.py` as a stub

### Risk: allowing recovery from non-reading

Mitigation:

* no function may convert `0` to `1`

## 12. Implementation sequence for execution stage

The API-based implementation agent should implement `run_simulation.py` in this order:

1. Implement `get_neighbors()` and `random_seating()`.
2. Implement `compute_observed_nonreading_proportion()` and `apply_social_adoption()`.
3. Implement `apply_natural_decay()` and `step_week()`.
4. Implement `run_one_simulation()`.
5. Implement `run_experiment()` and `summarize_results()`.
6. Implement `plot_reading_rates()` and `main()`.
7. Run:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

8. If tests fail, revise `run_simulation.py` only.
9. After tests pass, run:

```bash
python run_simulation.py
```

10. Inspect the generated files in `results/`.
