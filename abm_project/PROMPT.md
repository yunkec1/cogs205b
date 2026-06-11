# PROMPT.md

## Project title

Collapse of classroom reading norm: an agent-based model of behavior visibility

## Workflow overview

This project will use a two-stage AI-assisted workflow:

1. **Planning stage**
   Use Cursor Plan Mode to read `PROMPT.md`, `SKILL.md`, and `tests/test_model.py`, then produce a detailed implementation plan. The curated plan will be saved as `PLAN.md`.

2. **Implementation stage**
   Use a separate API-based `agent_loop.py` to implement the ABM. The implementation agent will read `PROMPT.md`, `SKILL.md`, `PLAN.md`, and `tests/test_model.py`. It may only create or modify `run_simulation.py`. It should iterate until the locked tests pass or until a maximum number of attempts is reached.

The implementation agent must not modify the scientific assumptions, the tests, the prompt, the skill file, the plan, the README, the Dockerfile, or the agent loop.

## Scientific goal

Model the collapse of a classroom reading norm.

At the beginning, all students complete the assigned reading before class. Over time, some students stop reading due to natural decay. Non-reading can also spread socially if students notice that nearby classmates are not reading.

The model asks whether the visibility of non-reading behavior affects how quickly the classroom reading norm collapses.

## Research question

Does higher visibility of non-reading behavior accelerate the collapse of a classroom reading norm?

## Hypothesis

Higher visibility of non-reading behavior will cause faster collapse of the reading norm than lower visibility.

When non-reading is more visible, students are more likely to notice local norm violations and stop reading themselves. 
When non-reading is less visible, students may fail to detect that nearby classmates are not reading, so the reading norm should persist longer.

## Model assumptions

### Agents

* There are 30 students.
* Each student is an agent.
* Each student has a binary reading state:

  * `1 = reads before class`
  * `0 = does not read before class`

### Initial state

* All students start as readers.
* At Week 1, every student has state `1`.

### Adoption definition

* Adoption means adopting the non-reading behavior.
* In state terms, adoption means changing from `1` to `0`.
* There is no un-adoption or recovery.
* Once a student changes to `0`, they must remain `0` for the rest of the simulation.

### Classroom environment

* Students are seated in a `5 x 6` classroom grid.
* There are exactly 30 seats.
* Each week, students are randomly assigned to seats.
* Seating is randomized independently each week.
* Each student observes the surrounding seats in the `3 x 3` neighborhood around their own seat, excluding their own seat.

Depending on seat location:

* corner seats have 3 neighboring seats
* non-corner edge seats have 5 neighboring seats
* interior seats have 8 neighboring seats

Use the actual number of neighboring seats as the denominator when computing observed non-reading proportion. Do not use 8 as the denominator for every student.

## Key mechanism: lagged social observation followed by natural decay

The timing of updates is important.

A student’s state in Week `t + 1` depends on:

1. what they observed in Week `t`, and
2. new natural decay that occurs after the social update.

Social observation is lagged by one week.

At Week 1, all students read. Since no one is not-reading in Week 1, no student can socially adopt non-reading for Week 2. Therefore, the only possible change from Week 1 to Week 2 comes from natural decay.

From Week 2 onward, students may observe non-reading behavior during class. Those Week `t` observations affect the next week’s state through social adoption. Then natural decay is applied to the students who remain readers after the social adoption step.

## Weekly update rules

For each transition from Week `t` to Week `t + 1`, use the following order.

### Step 1: Random seating for Week `t` observation

Randomly assign all 30 students to the `5 x 6` classroom grid for Week `t`.

This seating determines who each student observes during Week `t`.

### Step 2: Social observation based on Week `t` states

Each student observes the surrounding seats in their local `3 x 3` neighborhood, excluding their own seat.

Visibility controls whether non-reading behavior is detected.

Visibility conditions:

* high visibility: `visibility = 1.0`
* low visibility: `visibility = 0.5`

For each neighboring student:

* If the neighbor’s actual Week `t` state is `0`, that non-reading behavior is detected with probability equal to `visibility`.
* If the non-reading behavior is not detected, the observer treats that neighbor as reading or as not visibly violating the norm.
* If the neighbor’s actual Week `t` state is `1`, the observer treats that neighbor as reading.

For each student, compute:

observed_nonreading_proportion = detected_nonreading_neighbors / actual_number_of_neighboring_seats

The denominator must be the actual number of neighboring seats for that student’s seat location.

### Step 3: Lagged social adoption creates `post_social_state`

Create an intermediate state called `post_social_state`.

For each student:

* If the student’s Week `t` state is already `0`, they remain `0`.
* If the student’s Week `t` state is `1`, they change to `0` in `post_social_state` if their observed non-reading proportion from Week `t` is greater than or equal to `threshold = 0.50`.
* Otherwise, they remain `1` in `post_social_state`.

This social update must be synchronous. All students’ social adoption decisions must be based on the same Week `t` state vector and Week `t` observations. Do not update students sequentially in a way that allows one student’s newly updated state to affect another student in the same social update step.

### Step 4: Natural decay after social adoption

After `post_social_state` is created, apply natural decay only to students who are still readers.

Each student with `post_social_state = 1` independently changes to `0` with probability: p_decay = 0.05

Students with `post_social_state = 0` remain `0`.

The result is the final Week `t + 1` state.

### Step 5: Record outcomes

For each week, record:

* week number
* visibility condition
* random seed
* number of readers
* number of non-readers
* reading rate
* non-reading rate

## Planned comparison

Compare two visibility conditions:

* high visibility: `visibility = 1.0`
* low visibility: `visibility = 0.5`

Use the same model assumptions and parameters for both conditions.

## Simulation settings

Default simulation settings:

* `n_students = 30`
* `n_rows = 5`
* `n_cols = 6`
* `n_weeks = 20`
* `threshold = 0.50`
* `p_decay = 0.05`
* `visibility_conditions = {"high": 1.0, "low": 0.5}`
* run multiple random seeds per visibility condition

The exact number of seeds can be chosen during implementation, but it should be large enough to summarize variability across runs. A reasonable default is 100 seeds per condition.

## Outcomes

Primary outcome:

* Reading rate over 20 weeks.

Secondary outcomes:

* Final reading rate at Week 20.
* Time until reading rate falls below 50%, if it happens.
* Non-reading rate over time.

## Expected qualitative behavior

With natural decay alone, reading rate should decline slowly.

Because `p_decay = 0.05`, if there were no social adoption, the expected reading rate after 20 weeks would be approximately:

0.95^19 ≈ 0.377

Therefore, natural decay alone should push the reading rate to around 0.36 after 20 weeks. We could include this in the test.

In the high-visibility condition, students are more likely to detect nearby non-reading behavior. Once some students stop reading, their neighbors are more likely to observe enough non-reading behavior to cross the social threshold. Therefore, reading rate should decline faster and reach 50% earlier than low visibility / natural decay alone..

In the low-visibility condition, students may fail to notice some nearby non-reading behavior. This lowers the observed non-reading proportion and should make social threshold crossing less likely. Therefore, reading rate should decline more slowly and may remain above 50% for longer.

## Implementation target

The implementation agent should create or modify only one file:

run_simulation.py

This file should be self-contained and should include:

* all ABM logic
* grid and neighborhood functions
* random seating
* weekly update functions
* one-run simulation function
* multiple-seed simulation runner
* summary calculations
* plot generation
* result saving
* a `main()` entry point

The script must be runnable with:

```bash
python run_simulation.py
```

It must save outputs to a `results/` folder.

Expected output files:

```text
results/simulation_results.csv
results/summary_results.csv
results/reading_rate_by_visibility.png
```

The implementation may include additional result files if useful, but these three should be produced.

## Required functions for `run_simulation.py`

The exact implementation can vary, but `run_simulation.py` should expose clear, importable functions so that tests can inspect the model.

Functions should include:

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

Tests may rely on these or similar functions. Keep function behavior clear and deterministic when a seeded random number generator is provided.

## Protected files

The implementation agent must not modify any of the following files:

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

Do not weaken, delete, rewrite, or bypass tests.

Do not change the scientific assumptions to make tests pass.

Do not change the state coding.

Do not change the update timing.

Do not change visibility into “observing fewer neighbors.” Visibility means detection probability for non-reading behavior.

## Verification requirements

The project should include simulation-specific checks. These will be implemented mainly through `tests/test_model.py` and through manual inspection of outputs.

### State and population invariants

* All reading states must always be either `0` or `1`.
* There must always be exactly 30 students.
* Each weekly seating arrangement must place every student in exactly one seat.
* The `5 x 6` grid must contain exactly 30 filled seats.

### Neighborhood checks

Check that neighborhood counts are correct:

* corner seats have 3 neighbors
* non-corner edge seats have 5 neighbors
* interior seats have 8 neighbors

### No-un-adoption check

Once a student changes from `1` to `0`, they must never return to `1`.

### Timing check

Social adoption for Week `t + 1` must be based on Week `t` states and Week `t` observations.

Natural decay must be applied after the social adoption step, and only to students who remain readers in `post_social_state`.

### Seed reproducibility

Running the same condition with the same random seed should produce exactly the same trajectory.

### Edge cases

The implementation should support checks for the following cases:

1. If `p_decay = 0` and all students start reading, reading rate should remain 1.0 because there is no initial source of non-reading behavior.
2. If `visibility = 0` and `p_decay = 0`, social diffusion should not occur from an all-reading initial state.
3. If `threshold = 0`, readers should stop reading immediately or very quickly because the social threshold is always satisfied.
4. If all students start as non-readers, reading rate should remain 0 throughout the simulation.
5. With social adoption disabled or visibility set to 0, the model should approximate natural decay only.

### Robustness

Run multiple random seeds for each visibility condition, not just one simulation. Summarize the mean reading rate and variability across seeds.

## What would make the result untrustworthy

I would distrust the result if:

* the visibility effect appears only for one random seed,
* the effect disappears under small changes to `p_decay` or `threshold`,
* natural decay alone produces the same qualitative collapse as the high-visibility condition,
* the code applies social adoption and natural decay in the wrong order,
* the code uses the wrong denominator for edge and corner seats,
* the code treats visibility as observing fewer neighbors instead of detecting non-reading behavior,
* the code updates students sequentially instead of synchronously,
* or the code allows students to return from `0` to `1`.

## Instructions for Cursor Plan Mode

For the planning stage, use Cursor Plan Mode only.

Read:

```text
PROMPT.md
SKILL.md
tests/test_model.py
```

Create a detailed implementation plan to satisfy this prompt and the tests.

Do not create or modify files during the planning stage.

The plan should include:

1. the intended structure of `run_simulation.py`
2. functions to implement and their responsibilities
3. simulation workflow
4. how the update timing will be implemented
5. how visibility will be implemented
6. how tests map onto implementation
7. expected output files
8. possible implementation risks and how to avoid them

Do not change the scientific assumptions unless you explicitly flag the issue and ask for approval.

I will manually inspect the plan. 

If I approve the plan, it will be curated and saved manually as `PLAN.md`.

## Instructions for the API-based implementation agent

For the implementation stage, the API-based `agent_loop.py` will read:

```text
PROMPT.md
SKILL.md
PLAN.md
tests/test_model.py
```

The implementation agent should generate or revise only:

run_simulation.py

The implementation agent should not modify any protected files.

The implementation agent should use test failures to improve `run_simulation.py` only.

If a test appears inconsistent with the scientific assumptions, the implementation agent should report the issue rather than modifying the test.

The goal is to produce a correct, self-contained `run_simulation.py` that passes the locked tests and runs the simulation reproducibly.
