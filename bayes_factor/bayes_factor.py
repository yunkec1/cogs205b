import math
from scipy.integrate import quad


class BayesFactor:
    def __init__(self, n, k):
        if not isinstance(n, int):
            raise TypeError("n must be an integer")
        if not isinstance(k, int):
            raise TypeError("k must be an integer")
        if n < 0:
            raise ValueError("n must be non-negative")
        if k < 0:
            raise ValueError("k must be non-negative")
        if k > n:
            raise ValueError("k cannot be greater than n")

        self.n = n
        self.k = k
        self.a = 0.4999
        self.b = 0.5001

    def likelihood(self, theta):
        if not isinstance(theta, (int, float)):
            raise TypeError("theta must be numeric")
        if not math.isfinite(theta):
            raise ValueError("theta must be finite")
        if theta < 0 or theta > 1:
            raise ValueError("theta must be between 0 and 1")

        return float(
            math.comb(self.n, self.k)
            * (theta ** self.k)
            * ((1 - theta) ** (self.n - self.k))
        )

    def evidence_slab(self):
        return float(1 / (self.n + 1))

    def evidence_spike(self):
        if not math.isfinite(self.a) or not math.isfinite(self.b):
            raise ValueError("spike prior bounds must be finite")
        if self.a >= self.b:
            raise ValueError("spike prior requires a < b")

        width = self.b - self.a

        def integrand(theta):
            return self.likelihood(theta) / width

        result, _ = quad(integrand, self.a, self.b)
        return float(result)

    def bayes_factor(self):
        slab = self.evidence_slab()
        if slab == 0:
            raise ZeroDivisionError("evidence_slab is zero")
        return float(self.evidence_spike() / slab)