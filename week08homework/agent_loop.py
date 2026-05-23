#!/usr/bin/env python3
"""
Programmatic prompt -> generate -> test -> feedback loop for bayes_factor.py.

Script for homework07.
Run from inside week08homework/.

Setup:
    pip install numpy
    export GEMINI_API_KEY=...

Usage:
    python3 agent_loop.py
"""

import subprocess
import sys
import shutil
import time
from pathlib import Path

# paths
TASK_DIR = Path(__file__).resolve().parent
TEST_DIR = TASK_DIR / "tests"
TEST_FILE = TEST_DIR / "test_bayes_factor.py"
SOURCE_FILE = TASK_DIR / "bayes_factor.py"
PROMPT_FILE = TASK_DIR / "task.txt"
API_KEY_FILE = Path("/workspace/secrets/gemini_api_key.json")

# parameters
MAX_ATTEMPTS = 10
INCLUDE_TEST_FILE = True

# Set test_bayes_factor.py to read-only(!)
# Note this won't do anything if the agent can run as root.
TEST_FILE.chmod(0o444)

def run_tests() -> tuple[int, str]:
    result = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
        cwd=TASK_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()

# agent client
_FILES_DIR = TASK_DIR / "gemini_simple_api.py"
if str(_FILES_DIR) not in sys.path:
    sys.path.insert(0, str(_FILES_DIR))

from gemini_simple_api import GeminiSimpleAPI  # noqa: E402

client = GeminiSimpleAPI(
    api_key_file=str(API_KEY_FILE),
    model="gemma-4-31b-it",
    working_dir=TASK_DIR,
    protected_directories=[TEST_DIR],
)

prompt_text = PROMPT_FILE.read_text()

# loop prompt
def prompt_with_retries(client, prompt, attachments, verbose=True, max_retries=3, wait_seconds=10):
    last_error = None
    for retry in range(1, max_retries + 1):
        try:
            return client.prompt(
                prompt=prompt,
                attachments=attachments,
                verbose=verbose,
            )
        except RuntimeError as e:
            last_error = e
            print(f"\nModel call failed ({retry}/{max_retries}): {e}")
            if retry < max_retries:
                print(f"Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)
    raise last_error

for attempt in range(1, MAX_ATTEMPTS + 1):
    print(f"\n=== Attempt {attempt} ===")
    files, notes = prompt_with_retries(
        client,
        prompt=prompt_text,
        attachments=[TEST_FILE] if INCLUDE_TEST_FILE else [],
        verbose=True,
        max_retries=3,
        wait_seconds=10
    )

    # Here you could re-insert the test file if it was modified.
    code, output = run_tests()
    print(f"Output: {output}")

    # Archive the attempt
    (TASK_DIR / f"attempt_{attempt}").mkdir(parents=True, exist_ok=True)
    (TASK_DIR / f"attempt_{attempt}" / "output.txt").write_text(output)
    (TASK_DIR / f"attempt_{attempt}" / "prompt.txt").write_text(prompt_text)
    for file in files:
        shutil.copy(file, TASK_DIR / f"attempt_{attempt}" / file.name)

    # input("Press Enter to continue...")
    if code == 0:
        print(f"\nTests passed on attempt {attempt}.")
        break
    prompt_text += (
        f"\n\n## Attempt {attempt} failed\n"
        f"```\n{output}\n```\n"
        "Fix the failures above."
        "Do not modify the test file. "
        "Do not change the constructor signature. "
        "Only edit bayes_factor.py."
    )
else:
    print(f"\nStopped after {MAX_ATTEMPTS} attempts; tests still failing.")
    sys.exit(1)