# SKILL.md

## Purpose

This file defines the project-specific rules for the classroom reading norm ABM.

The implementation agent must read and follow this file before planning or coding. These rules are intended to preserve the scientific assumptions, update timing, state coding, and verification constraints across prompts.

## Implementation target

The implementation agent may create or modify only:

```text
run_simulation.py
```

The implementation agent must not modify:

```text
PROMPT.md
PLAN.md
SKILL.md
tests/test_model.py
README.md
Dockerfile
agent_loop.py
```

If tests fail, revise `run_simulation.py` only.

Do not weaken, rewrite, delete, bypass, or reinterpret the tests.

If a test appears inconsistent with the scientific assumptions, report the issue instead of modifying the test.

## State coding

Use this exact state coding:

```text
1 = reads before class
0 = does not read before class
```

Adoption means adopting the non-reading behavior:

```text
1 -> 0
```

There is no un-adoption or recovery:

```text
0 must never become 1
```

The model is about collapse of a reading norm, not recovery of the norm.

## Agents and environment

There are 30 students.

Students sit in a `5 x 6` classroom grid.

There are exactly 30 seats.

Each week, all students are randomly assigned to seats.

Seating is randomized independently each week.

Each student observes the surrounding seats in the `3 x 3` neighborhood around their own seat, excluding their own seat.

Neighbor counts depend on seat location:

```text
corner seat: 3 neighbors
non-corner edge seat: 5 neighbors
interior seat: 8 neighbors
```

When computing observed non-reading proportion, always use the actual number of neighboring seats as the denominator.Do not use 8 as the denominator for every student.

## Visibility rule

Visibility controls whether non-reading behavior is detected.

Visibility does not mean observing fewer neighbors.

For each actual non-reading neighbor:

```text
detected as non-reading with probability = visibility
not detected with probability = 1 - visibility
```

If a non-reading neighbor is not detected, the observer treats that neighbor as reading or as not visibly violating the norm.

A reading neighbor is always treated as reading.

Visibility conditions:

```text
high visibility = 1.0
low visibility = 0.5
```

## Update timing

The timing of updates is scientifically important.

A student’s state in Week `t + 1` depends on:

1. social observation from Week `t`, and
2. natural decay applied after the social update.

Use this order for each transition from Week `t` to Week `t + 1`:

```text
Week t states
-> random seating for Week t observation
-> observe neighbors using Week t states
-> apply lagged social adoption to create post_social_state
-> apply natural decay only to remaining readers in post_social_state
-> final Week t+1 states
```

At Week 1, all students read. Since no one is not-reading in Week 1, no one can socially adopt non-reading for Week 2. The only possible change from Week 1 to Week 2 comes from natural decay.

Social adoption must be synchronous. All students’ social adoption decisions must be based on the same Week `t` states and Week `t` observations.

Do not update students sequentially in a way that allows one student’s newly updated state to affect another student during the same social update step.

## Social adoption rule

For each student, compute:

```text
observed_nonreading_proportion =
    detected_nonreading_neighbors / actual_number_of_neighboring_seats
```

A student with Week `t` state `1` changes to `0` in `post_social_state` if:

```text
observed_nonreading_proportion >= threshold
```

Default threshold:

```text
threshold = 0.50
```

A student with Week `t` state `0` remains `0`.

## Natural decay rule

Natural decay is applied after social adoption.

Only students who remain readers in `post_social_state` are eligible for natural decay.

Each remaining reader independently changes from `1` to `0` with probability:

```text
p_decay = 0.05
```

Students already in state `0` remain `0`.

## Simulation settings

Default simulation settings:

```text
n_students = 30
n_rows = 5
n_cols = 6
n_weeks = 20
threshold = 0.50
p_decay = 0.05
visibility conditions = high: 1.0, low: 0.5
```

Run multiple random seeds per visibility condition.

A reasonable default is 100 seeds per condition.

## Required outputs

Running:

```bash
python run_simulation.py
```

should create a `results/` folder if it does not already exist and save:

```text
results/simulation_results.csv
results/summary_results.csv
results/reading_rate_by_visibility.png
```

The raw simulation results should include at least:

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

The summary results should include condition-level summaries across seeds, such as mean reading rate over time and final reading rate.

## Expected qualitative behavior

With natural decay alone and `p_decay = 0.05`, the expected reading rate after 20 weeks is approximately:

```text
0.95^20 ≈ 0.36
```

Therefore, over 20 weeks, natural decay alone may eventually reduce reading below 50%.

The main hypothesis is not simply whether collapse happens, but whether high visibility accelerates collapse compared with low visibility.

Expected pattern:

```text
high visibility:
  faster decline in reading rate
  earlier crossing below 50%
  lower reading rate at many time points

low visibility:
  slower decline in reading rate
  later crossing below 50%
  higher reading rate at many time points
```

## Verification rules

The implementation should satisfy tests for:

```text
binary state values only
exactly 30 students
exactly 30 filled seats
each student seated exactly once
correct neighbor counts for corner, edge, and interior seats
no un-adoption
seed reproducibility
correct lagged update timing
natural decay applied after social adoption
visibility implemented as detection probability
use of actual neighbor count as denominator
```

Edge cases should be supported:

```text
p_decay = 0 and all students start reading -> reading rate remains 1.0
visibility = 0 and p_decay = 0 -> no social diffusion from all-reading initial state
threshold = 0 -> readers should stop immediately or very quickly through social adoption
all students start as non-readers -> reading rate remains 0
visibility = 0 or social adoption disabled -> decline should be driven by natural decay only
```

## Common failure modes to avoid

Do not make any of these mistakes:

```text
Changing state coding so that 1 no longer means reading.
Allowing 0 -> 1 recovery.
Treating visibility as observing fewer neighbors.
Using 8 as the denominator for all seats.
Applying natural decay before social adoption.
Using Week t+1 updated states for Week t social observation.
Updating students sequentially instead of synchronously.
Forgetting that Week 1 starts with everyone reading.
Allowing social adoption from Week 1 to Week 2 when no one was non-reading in Week 1.
Failing to randomize seating each week.
Failing to make simulations reproducible with random seeds.
Writing outputs somewhere other than results/.
Modifying protected files.
```

## Coding expectations

Keep `run_simulation.py` self-contained and readable.

Expose importable functions so tests can inspect the model.

Required function names include:

```python
get_neighbors(row, col, n_rows=5, n_cols=6)
random_seating(n_students, n_rows, n_cols, rng)
compute_observed_nonreading_proportion(student_id, states, seating, visibility, rng)
apply_social_adoption(states, seating, visibility, threshold, rng)
apply_natural_decay(states, p_decay, rng)
step_week(states, visibility, threshold, p_decay, rng)
run_one_simulation(seed, visibility, n_weeks=20, p_decay=0.05, threshold=0.5)
run_experiment(...)
summarize_results(...)
plot_reading_rates(...)
main()
```

Use a seeded random number generator. Prefer passing an explicit `numpy.random.Generator` object rather than relying on global random state.

