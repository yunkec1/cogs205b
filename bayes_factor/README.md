# BayesFactor homework

This folder contains an implementation of a `BayesFactor` class and a unittest test suite for it.

## Files

- `bayes_factor.py`: implementation of the `BayesFactor` class
- `tests/test_bayes_factor.py`: unit tests
- `Dockerfile`: Docker setup for running the tests

## Run tests locally

From inside the `bayes_factor` directory:

```bash
python3 -m unittest tests/test_bayes_factor.py
```

## Case of intentionally failing test

One intentionally failing test I used during development was a constructor-validation test checking that `k > n` raises a `ValueError`. At first, this test failed when the constructor only stored `n` and `k` without validating their values. I then added input validation to `BayesFactor.__init__`, and it passed.