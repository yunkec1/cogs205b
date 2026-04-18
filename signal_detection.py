import math
from numbers import Real
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

class SignalDetection:
    def __init__(self, hits, misses, false_alarms, correct_rejections):
        self.hits = self._validate_count(hits, "hits")
        self.misses = self._validate_count(misses, "misses")
        self.false_alarms = self._validate_count(false_alarms, "false_alarms")
        self.correct_rejections = self._validate_count(
            correct_rejections, "correct_rejections"
        )
    
    # validate count
    @staticmethod
    def _validate_count(value, name):
        if not isinstance(value, Real):
            raise TypeError(f"{name} must be numeric")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite.")
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
        return value

    def hit_rate(self):
        total_signal = self.hits + self.misses
        if total_signal == 0:
            return 0.0
        return self.hits / total_signal

    def false_alarm_rate(self):
        total_noise = self.false_alarms + self.correct_rejections
        if total_noise == 0:
            return 0.0
        return self.false_alarms / total_noise

    def d_prime(self):
        h = self.hit_rate()
        fa = self.false_alarm_rate()
        return norm.ppf(h) - norm.ppf(fa)

    def criterion(self):
        h = self.hit_rate()
        fa = self.false_alarm_rate()
        return -0.5 * (norm.ppf(h) + norm.ppf(fa))

    def __add__(self, other):
        if not isinstance(other, SignalDetection):
            raise TypeError("other must be a SignalDetection")
        return SignalDetection(
            self.hits + other.hits,
            self.misses + other.misses,
            self.false_alarms + other.false_alarms,
            self.correct_rejections + other.correct_rejections
        )

    def __sub__(self, other):
        if not isinstance(other, SignalDetection):
            raise TypeError("other must be a SignalDetection")
        return SignalDetection(
            self.hits - other.hits,
            self.misses - other.misses,
            self.false_alarms - other.false_alarms,
            self.correct_rejections - other.correct_rejections
        )

    def __mul__(self, factor):
        if not isinstance(factor, Real):
            raise TypeError("factor must be numeric")
        if not math.isfinite(factor):
            raise ValueError("factor must be finite.")
        if factor < 0:
            raise ValueError("factor must be non-negative")
        return SignalDetection(
            self.hits * factor,
            self.misses * factor,
            self.false_alarms * factor,
            self.correct_rejections * factor
        )
    
    def plot_sdt(self):
        dprime = self.d_prime()
        crit = self.criterion()
        if not math.isfinite(dprime) or not math.isfinite(crit):
            raise ValueError("Cannot plot SDT when d' or criterion is infinite.")

        noise_mean = 0.0
        signal_mean = dprime

        x_min = min(noise_mean, signal_mean) - 4
        x_max = max(noise_mean, signal_mean) + 4
        x = np.linspace(x_min, x_max, 500)

        noise_y = norm.pdf(x, loc=noise_mean, scale=1.0)
        signal_y = norm.pdf(x, loc=signal_mean, scale=1.0)

        fig, ax = plt.subplots()
        ax.plot(x, noise_y, label="Noise")
        ax.plot(x, signal_y, label="Signal")
        ax.axvline(crit, linestyle="--", label="Criterion")

        y_arrow = max(noise_y.max(), signal_y.max()) * 0.6
        ax.annotate(
            "",
            xy=(signal_mean, y_arrow),
            xytext=(noise_mean, y_arrow),
            arrowprops=dict(arrowstyle="<->")
        )
        ax.text(
            (noise_mean + signal_mean) / 2,
            y_arrow,
            "d'",
            ha="center",
            va="bottom"
        )

        ax.set_xlabel("Decision variable")
        ax.set_ylabel("Density")
        ax.set_title("Signal Detection Theory Plot")
        ax.legend()

        return fig, ax

