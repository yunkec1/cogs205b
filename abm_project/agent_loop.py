#!/usr/bin/env python
"""
Bounded AI implementation loop for the classroom reading norm ABM.

This script reads:
- PROMPT.md
- SKILL.md
- PLAN.md
- tests/test_model.py

It asks the Gemini implementation agent to create or revise:
- run_simulation.py

It then runs:
- python -m unittest discover -s tests -p "test_*.py" -v

If tests fail, the test output is appended to the next prompt.
The loop repeats until tests pass or MAX_ATTEMPTS is reached.

The implementation agent is only allowed to modify run_simulation.py.
"""

import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent

PROMPT_FILE = TASK_DIR / "PROMPT.md"
SKILL_FILE = TASK_DIR / "SKILL.md"
PLAN_FILE = TASK_DIR / "PLAN.md"
TEST_FILE = TASK_DIR / "tests" / "test_model.py"
SOURCE_FILE = TASK_DIR / "run_simulation.py"
LOG_DIR = TASK_DIR / "agent_logs"

API_KEY_FILE = Path("/workspace/secrets/gemini_api_key.json")

if str(TASK_DIR) not in sys.path:
    sys.path.insert(0, str(TASK_DIR))

from gemini_simple_api import GeminiSimpleAPI  # noqa: E402


MAX_ATTEMPTS = 10
MAX_RETRIES_PER_ATTEMPT = 3
WAIT_SECONDS = 10

MODEL_NAME = "gemma-4-31b-it"

PROTECTED_FILES = [
    PROMPT_FILE,
    SKILL_FILE,
    PLAN_FILE,
    TEST_FILE,
    TASK_DIR / "README.md",
    TASK_DIR / "Dockerfile",
    TASK_DIR / "agent_loop.py",
]

ALLOWED_SOURCE_FILE = SOURCE_FILE


def require_file(path: Path) -> None:
    """Fail early if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def file_hash(path: Path) -> str | None:
    """Return a stable hash for a file, or None if it does not exist."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_files(paths: list[Path]) -> dict[Path, str | None]:
    """Record hashes of protected files before an agent call."""
    return {path: file_hash(path) for path in paths}


def assert_protected_files_unchanged(before: dict[Path, str | None]) -> None:
    """Abort if any protected file changed during an agent attempt."""
    changed = []
    for path, old_hash in before.items():
        new_hash = file_hash(path)
        if new_hash != old_hash:
            changed.append(path)

    if changed:
        changed_str = "\n".join(str(path) for path in changed)
        raise RuntimeError(
            "Protected files were modified. Aborting.\n"
            f"Changed protected files:\n{changed_str}\n\n"
            "Restore these files from git before continuing."
        )


def run_tests() -> tuple[int, str]:
    """Run the locked unittest suite."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ],
        cwd=TASK_DIR,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode, output


def read_project_context() -> str:
    """Read the project context files into one prompt string."""
    prompt = PROMPT_FILE.read_text()
    skill = SKILL_FILE.read_text()
    plan = PLAN_FILE.read_text()
    tests = TEST_FILE.read_text()

    current_source = (
        SOURCE_FILE.read_text()
        if SOURCE_FILE.exists()
        else "# run_simulation.py does not exist yet.\n"
    )

    return f"""
# Implementation task

You are the implementation agent for this ABM project.

Your job is to create or revise exactly one file:

run_simulation.py

Do not modify any other file.

You must follow the project prompt, skill file, plan, and locked tests below.

The implementation must be self-contained in run_simulation.py.
It must expose the importable functions required by tests/test_model.py.
It must pass the locked tests.

# Protected files

You must not modify:

PROMPT.md
SKILL.md
PLAN.md
tests/test_model.py
README.md
Dockerfile
agent_loop.py

If tests fail, revise run_simulation.py only.

# PROMPT.md

{prompt}

# SKILL.md

{skill}

# PLAN.md

{plan}

# Locked tests: tests/test_model.py

{tests}

# Current run_simulation.py

{current_source}

# Output requirements

Create or revise run_simulation.py only.

The final run_simulation.py must:
- implement the ABM exactly as specified
- expose the functions used by the tests
- run with python run_simulation.py
- save results to results/
- not require modifying the tests
""".strip()


def prompt_with_retries(client, prompt: str, verbose: bool = True):
    """Call the Gemini client with retries."""
    last_error = None

    for retry in range(1, MAX_RETRIES_PER_ATTEMPT + 1):
        try:
            return client.prompt(
                prompt=prompt,
                attachments=[TEST_FILE],
                verbose=verbose,
            )
        except RuntimeError as error:
            last_error = error
            print(f"\nModel call failed ({retry}/{MAX_RETRIES_PER_ATTEMPT}): {error}")
            if retry < MAX_RETRIES_PER_ATTEMPT:
                print(f"Retrying in {WAIT_SECONDS} seconds...")
                time.sleep(WAIT_SECONDS)

    raise last_error


def archive_attempt(
    attempt: int,
    prompt_text: str,
    test_output: str,
    generated_files: list[Path],
    notes,
) -> None:
    """Save prompt, test output, generated files, and notes for provenance."""
    attempt_dir = LOG_DIR / f"attempt_{attempt:02d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)

    (attempt_dir / "prompt.txt").write_text(prompt_text)
    (attempt_dir / "test_output.txt").write_text(test_output)

    if notes is not None:
        (attempt_dir / "notes.txt").write_text(str(notes))

    if SOURCE_FILE.exists():
        shutil.copy(SOURCE_FILE, attempt_dir / "run_simulation.py")

    for file_path in generated_files:
        file_path = Path(file_path)
        if file_path.exists() and file_path.resolve() != SOURCE_FILE.resolve():
            with (attempt_dir / "unexpected_files.txt").open("a") as handle:
                handle.write(str(file_path) + "\n")


def check_generated_files(generated_files: list[Path]) -> None:
    """Warn if the API client reports files other than run_simulation.py."""
    unexpected = []
    for path in generated_files:
        path = Path(path).resolve()
        if path != SOURCE_FILE.resolve():
            unexpected.append(path)

    if unexpected:
        unexpected_str = "\n".join(str(path) for path in unexpected)
        print(
            "\nWarning: The API client reported unexpected generated files:\n"
            f"{unexpected_str}\n"
            "Protected-file hashes will also be checked."
        )


def main() -> None:
    for required in [PROMPT_FILE, SKILL_FILE, PLAN_FILE, TEST_FILE]:
        require_file(required)

    LOG_DIR.mkdir(exist_ok=True)

    # Soft guardrail. This is not enough by itself when running as root,
    # so we also compare protected-file hashes after each agent call.
    TEST_FILE.chmod(0o444)

    client = GeminiSimpleAPI(
        api_key_file=str(API_KEY_FILE),
        model=MODEL_NAME,
        working_dir=TASK_DIR,
        protected_directories=[TASK_DIR / "tests"],
    )

    prompt_text = read_project_context()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Attempt {attempt} ===")

        protected_before = snapshot_files(PROTECTED_FILES)

        generated_files, notes = prompt_with_retries(
            client=client,
            prompt=prompt_text,
            verbose=True,
        )

        generated_files = [Path(path) for path in generated_files]
        check_generated_files(generated_files)
        assert_protected_files_unchanged(protected_before)

        code, test_output = run_tests()
        print("\n--- unittest output ---")
        print(test_output)

        archive_attempt(
            attempt=attempt,
            prompt_text=prompt_text,
            test_output=test_output,
            generated_files=generated_files,
            notes=notes,
        )

        if code == 0:
            print(f"\nTests passed on attempt {attempt}.")
            print("Now manually inspect run_simulation.py and run:")
            print("    python run_simulation.py")
            return

        prompt_text = (
            read_project_context()
            + f"""

# Previous attempt failed

Attempt {attempt} failed with the following unittest output:

{test_output}

Fix the failures above.

Rules:
- Modify run_simulation.py only.
- Do not modify tests.
- Do not modify PROMPT.md, SKILL.md, PLAN.md, README.md, Dockerfile, or agent_loop.py.
- Do not change the scientific assumptions.
- Do not weaken tests.
"""
        ).strip()

    print(f"\nStopped after {MAX_ATTEMPTS} attempts; tests still failing.")
    sys.exit(1)


if __name__ == "__main__":
    main()
