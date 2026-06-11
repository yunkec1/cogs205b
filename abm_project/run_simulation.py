import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Constants
N_STUDENTS = 30
N_ROWS = 5
N_COLS = 6
N_WEEKS = 20
THRESHOLD = 0.5
P_DECAY = 0.05
N_SEEDS = 100
VISIBILITY_CONDITIONS = {"high": 1.0, "low": 0.5}


def get_neighbors(row, col, n_rows=5, n_cols=6):
    """
    Returns a list of valid neighboring seat coordinates in the 3x3 window,
    excluding the seat itself.
    """
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < n_rows and 0 <= nc < n_cols:
                neighbors.append((nr, nc))
    return neighbors


def random_seating(n_students, n_rows, n_cols, rng):
    """
    Randomly assigns students to seats.
    """
    assert n_students == n_rows * n_cols
    students = rng.permutation(n_students)
    return students.reshape((n_rows, n_cols))


def compute_observed_nonreading_proportion(student_id, states, seating, visibility, rng):
    """
    Computes the observed non-reading proportion for a student based on visibility.
    """
    # Find where the student is sitting
    row, col = np.where(seating == student_id)
    row, col = row[0], col[0]

    neighbors_coords = get_neighbors(row, col)
    num_neighbors = len(neighbors_coords)

    detected_nonreaders = 0
    for nr, nc in neighbors_coords:
        neighbor_id = seating[nr, nc]
        neighbor_state = states[neighbor_id]

        if neighbor_state == 0:
            # Non-reader is detected with probability 'visibility'
            if rng.random() < visibility:
                detected_nonreaders += 1
        # Readers are always treated as reading (detected_nonreaders doesn't increase)

    return detected_nonreaders / num_neighbors


def apply_social_adoption(states, seating, visibility, threshold, rng):
    """
    Synchronously applies the social adoption rule.
    """
    post_social_state = states.copy()

    for student_id in range(len(states)):
        if states[student_id] == 1:
            prop = compute_observed_nonreading_proportion(
                student_id, states, seating, visibility, rng
            )
            if prop >= threshold:
                post_social_state[student_id] = 0

    return post_social_state


def apply_natural_decay(states, p_decay, rng):
    """
    Applies natural decay to students who are still readers.
    """
    final_state = states.copy()
    for student_id in range(len(states)):
        if states[student_id] == 1:
            if rng.random() < p_decay:
                final_state[student_id] = 0
    return final_state


def step_week(states, visibility, threshold, p_decay, rng):
    """
    Performs one weekly transition from Week t to Week t+1.
    """
    # 1. Random seating for Week t observation
    seating = random_seating(N_STUDENTS, N_ROWS, N_COLS, rng)

    # 2. Social adoption based on Week t states
    post_social_state = apply_social_adoption(states, seating, visibility, threshold, rng)

    # 3. Natural decay applied to post_social_state
    next_states = apply_natural_decay(post_social_state, p_decay, rng)

    return next_states


def run_one_simulation(seed, visibility, n_weeks=20, p_decay=0.05, threshold=0.5):
    """
    Runs a single simulation trajectory for a given seed and visibility.
    """
    rng = np.random.default_rng(seed)
    states = np.ones(N_STUDENTS, dtype=int)

    results = []
    for week in range(1, n_weeks + 1):
        # Record current state (Week t)
        n_readers = np.sum(states == 1)
        n_nonreaders = N_STUDENTS - n_readers
        reading_rate = n_readers / N_STUDENTS
        nonreading_rate = n_nonreaders / N_STUDENTS

        results.append({
            "week": week,
            "visibility": visibility,
            "seed": seed,
            "n_readers": n_readers,
            "n_nonreaders": n_nonreaders,
            "reading_rate": reading_rate,
            "nonreading_rate": nonreading_rate,
        })

        # Step to Week t+1
        if week < n_weeks:
            states = step_week(states, visibility, threshold, p_decay, rng)

    return pd.DataFrame(results)


def run_experiment(n_seeds=100, n_weeks=20, p_decay=0.05, threshold=0.5):
    """
    Runs the full experiment across visibility conditions and seeds.
    """
    all_results = []
    for cond_name, vis_val in VISIBILITY_CONDITIONS.items():
        for seed in range(n_seeds):
            df = run_one_simulation(seed, vis_val, n_weeks, p_decay, threshold)
            df["visibility_condition"] = cond_name
            all_results.append(df)

    return pd.concat(all_results, ignore_index=True)


def summarize_results(df):
    """
    Summarizes results by visibility condition and week.
    """
    summary = df.groupby(["visibility_condition", "week"]).agg(
        mean_reading_rate=("reading_rate", "mean"),
        std_reading_rate=("reading_rate", "std"),
        mean_nonreading_rate=("nonreading_rate", "mean"),
        n_seeds=("seed", "count"),
    ).reset_index()

    return summary


def plot_reading_rates(summary_df, output_path):
    """
    Plots the mean reading rate over time for different visibility conditions.
    """
    plt.figure(figsize=(10, 6))
    for condition in summary_df["visibility_condition"].unique():
        subset = summary_df[summary_df["visibility_condition"] == condition]
        plt.plot(subset["week"], subset["mean_reading_rate"], label=condition)

    plt.xlabel("Week")
    plt.ylabel("Mean Reading Rate")
    plt.title("Collapse of Reading Norm by Visibility")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_path)
    plt.close()


def main():
    """
    Entry point to run the simulation and save results.
    """
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # Run experiment
    raw_df = run_experiment(n_seeds=N_SEEDS)
    summary_df = summarize_results(raw_df)

    # Save results
    raw_df.to_csv(results_dir / "simulation_results.csv", index=False)
    summary_df.to_csv(results_dir / "summary_results.csv", index=False)
    plot_reading_rates(summary_df, results_dir / "reading_rate_by_visibility.png")

    print("Simulation complete. Results saved to results/ folder.")


if __name__ == "__main__":
    main()