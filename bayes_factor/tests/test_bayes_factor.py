import unittest
from bayes_factor import BayesFactor


class TestBayesFactor(unittest.TestCase):
    # setUp for tests
    def setUp(self):
        self.bf = BayesFactor(10, 5)

    # stores n and k
    def test_constructor_stores_n_and_k(self):
        self.assertEqual(self.bf.n, 10)
        self.assertEqual(self.bf.k, 5)

    # validates n and k
    def test_constructor_rejects_negative_n(self):
        with self.assertRaises(ValueError) as cm:
            BayesFactor(-1, 0)
        self.assertEqual(str(cm.exception), "n must be non-negative")

    def test_constructor_rejects_negative_k(self):
        with self.assertRaises(ValueError) as cm:
            BayesFactor(10, -1)
        self.assertEqual(str(cm.exception), "k must be non-negative")

    def test_constructor_rejects_k_greater_than_n(self):
        with self.assertRaises(ValueError) as cm:
            BayesFactor(5, 6)
        self.assertEqual(str(cm.exception), "k cannot be greater than n")

    def test_constructor_rejects_non_integer_n(self):
        with self.assertRaises(TypeError) as cm:
            BayesFactor("10", 5)
        self.assertEqual(str(cm.exception), "n must be an integer")

    def test_constructor_rejects_non_integer_k(self):
        with self.assertRaises(TypeError) as cm:
            BayesFactor(10, "5")
        self.assertEqual(str(cm.exception), "k must be an integer")

    # validates theta input
    def test_likelihood_returns_float_for_valid_theta(self):
        value = self.bf.likelihood(0.5)
        self.assertIsInstance(value, float)

    def test_likelihood_at_half_for_n10_k5(self):
        self.assertAlmostEqual(self.bf.likelihood(0.5), 0.24609375)

    def test_likelihood_rejects_nan_theta(self):
        with self.assertRaises(ValueError) as cm:
            self.bf.likelihood(float("nan"))
        self.assertEqual(str(cm.exception), "theta must be finite")

    def test_likelihood_rejects_infinite_theta(self):
        with self.assertRaises(ValueError) as cm:
            self.bf.likelihood(float("inf"))
        self.assertEqual(str(cm.exception), "theta must be finite")

    def test_likelihood_rejects_theta_below_zero(self):
        with self.assertRaises(ValueError) as cm:
            self.bf.likelihood(-0.1)
        self.assertEqual(str(cm.exception), "theta must be between 0 and 1")

    def test_likelihood_rejects_theta_above_one(self):
        with self.assertRaises(ValueError) as cm:
            self.bf.likelihood(1.1)
        self.assertEqual(str(cm.exception), "theta must be between 0 and 1")

    def test_likelihood_rejects_non_numeric_theta(self):
        with self.assertRaises(TypeError) as cm:
            self.bf.likelihood("0.5")
        self.assertEqual(str(cm.exception), "theta must be numeric")

    # test evidence_slab
    def test_evidence_slab_returns_float(self):
        value = self.bf.evidence_slab()
        self.assertIsInstance(value, float)

    def test_evidence_slab_is_non_negative(self):
        self.assertGreaterEqual(self.bf.evidence_slab(), 0.0)

    def test_evidence_slab_for_n10_k5_is_one_over_n_plus_one(self):
        self.assertAlmostEqual(self.bf.evidence_slab(), 1 / 11)

    # test evidence_spike
    def test_evidence_spike_returns_float(self):
        value = self.bf.evidence_spike()
        self.assertIsInstance(value, float)

    def test_evidence_spike_is_non_negative(self):
        self.assertGreaterEqual(self.bf.evidence_spike(), 0.0)

    def test_evidence_spike_for_n10_k5_is_close_to_likelihood_at_point_five(self):
        self.assertAlmostEqual(
            self.bf.evidence_spike(),
            self.bf.likelihood(0.5),
            places=4
        )

    def test_evidence_spike_rejects_non_finite_bounds(self):
        self.bf.a = float("nan")
        with self.assertRaises(ValueError) as cm:
            self.bf.evidence_spike()
        self.assertEqual(str(cm.exception), "spike prior bounds must be finite")

    def test_evidence_spike_rejects_invalid_bound_order(self):
        self.bf.a = 0.6
        self.bf.b = 0.5
        with self.assertRaises(ValueError) as cm:
            self.bf.evidence_spike()
        self.assertEqual(str(cm.exception), "spike prior requires a < b")

    # test bayes_factor
    def test_bayes_factor_returns_float(self):
        value = self.bf.bayes_factor()
        self.assertIsInstance(value, float)

    def test_bayes_factor_is_non_negative(self):
        self.assertGreaterEqual(self.bf.bayes_factor(), 0.0)

    def test_bayes_factor_matches_evidence_ratio(self):
        expected = self.bf.evidence_spike() / self.bf.evidence_slab()
        self.assertAlmostEqual(self.bf.bayes_factor(), expected)

    def test_bayes_factor_is_one_when_priors_match(self):
        self.bf.evidence_spike = self.bf.evidence_slab
        self.assertAlmostEqual(self.bf.bayes_factor(), 1.0)

    def test_bayes_factor_raises_if_evidence_slab_is_zero(self):
        self.bf.evidence_slab = lambda: 0.0
        with self.assertRaises(ZeroDivisionError) as cm:
            self.bf.bayes_factor()
        self.assertEqual(str(cm.exception), "evidence_slab is zero")


if __name__ == "__main__":
    unittest.main()