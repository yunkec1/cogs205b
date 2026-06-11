# Model specification 
This project implements an agent-based model of how a classroom norm around doing assigned reading before class can collapse over time.

The core question is:
How does visibility of non-reading behavior affect the speed at which a reading norm collapses?

The model compares two conditions:
High visibility: non-reading behavior is always detected by neighbors.
Low visibility: non-reading behavior is detected with probability 0.5.

The main hypothesis is that higher visibility makes non-reading behavior spread faster, leading to a faster collapse of the reading norm.

## Key files:
PROMPT.md: project prompt and modeling assumptions
SKILL.md: project-specific implementation constraints and failure modes
PLAN.md: curated implementation plan generated with Cursor Plan Mode
agent_loop.py: API-based implementation loop that generated and tested run_simulation.py
run_simulation.py: final ABM implementation
tests/test_model.py: locked unit tests for model mechanisms
results/simulation_results.csv: raw simulation output
results/summary_results.csv: summarized simulation output
results/reading_rate_by_visibility.png: plot of reading-rate trajectories
Dockerfile: reproducible container environment

## Agents
The model contains 30 student agents.

Each student has a binary state:
1: reads before class
0: does not read before class

Non-reading is an absorbing state. Once a student becomes a non-reader, they cannot become a reader again.

## Environment
Students are seated in a 5 x 6 classroom grid.

Each week, students are randomly reseated. A student observes the surrounding 3 x 3 neighborhood around their own seat, excluding themselves.

The number of possible neighbors depends on seat location:
corner seat: 3 neighbors
non-corner edge seat: 5 neighbors
interior seat: 8 neighbors

The model always uses the actual number of neighboring seats as the denominator when computing observed non-reading proportion.

## Visibility
Visibility is implemented as detection probability for actual non-reading behavior.

For each non-reading neighbor:
    in the high visibility condition, the non-reading behavior is detected with probability 1.0
    in the low visibility condition, the non-reading behavior is detected with probability 0.5

Reading neighbors are always treated as reading.

Visibility does not mean observing fewer neighbors. It only changes whether actual non-reading behavior is detected.

## Weekly update rule

Each week follows this order:

Students are randomly seated.
Each student observes visible non-reading behavior among their neighbors.
Social adoption is applied synchronously:
    if a reader observes that at least 50% of their neighbors are non-readers, they stop reading
    already non-reading students remain non-readers
Natural decay is applied:
    each remaining reader has probability 0.05 of stopping reading

The social threshold is: threshold = 0.5

The natural decay probability is: p_decay = 0.05

The model runs for 20 weeks. Week 1 is the initial state, where all students read before class.

# How to run

## dockerfile
The Dockerfile installs the Python packages needed for the simulation and tests:
    numpy
    pandas
    matplotlib

Build the Docker image from the project directory:
    docker build -t abm-reading-norm .

Run the simulation in Docker:
    docker run --rm abm-reading-norm python3 run_simulation.py

Run the tests in Docker:
    docker run --rm abm-reading-norm python3 -m unittest discover -s tests -p "test_*.py" -v

## tests
python3 -m unittest discover -s tests -p "test_*.py" -v

## simulation
python3 run_simulation.py

This creates the results/ directory and writes:
    results/simulation_results.csv
    results/summary_results.csv
    results/reading_rate_by_visibility.png

# Results
The simulation shows that in both conditions, natural decay eventually reduces reading behavior. However, high visibility accelerates the spread of non-reading because students are more likely to detect nearby norm violations.

The resulting plot shows:
    high visibility: rapid decline in reading rate, reaching near-zero by the later weeks
    low visibility: slower decline, with the reading norm persisting longer before collapsing

This supports the main hypothesis: visibility of norm-violating behavior accelerates norm collapse.

# Reflection 
My workflow:
    wrote PROMPT.md, SKILL.md, and tests/test_model.py
    curated PLAN.md using Cursor Plan Mode and inspected the plan
    wrote tests/test_model.py and agent_loop.py
    ran agent_loop.py and inspect the genrated run_simulation.py codes
    ran run_simulation.py and inspect the results
    wrote README.md

To safeguard the process, I specified the scientific assumptions and constraints in PROMPT.md and SKILL.md. The implementation agent was constrained to modify only run_simulation.py, and I backed up the other files (prompt, skill, and test) and verified that they were not modified by the implementation. 

I wrote the tests before the implementation to check the scientific assumptions and edge cases. They verified that the simulation implements hte stated assumptions consistently. 

The first attempt of the agent loop passed all the tests. The run_simulation.py codes were inspected for reasonable implementation. The simulation outputs were inspected for expected structure and qualitative behavior. 

As a result, we now trust that the model showed in a simplified, toy ABM how a local updating rule of norm violation visibility could boost the norm collapse. 

