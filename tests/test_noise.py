"""Noise: missing and duplicated events land close to their targets."""

import numpy as np

import config
from generate import add_noise, simulate

TOLERANCE = 0.003  # ±0.3 percentage points, from the spec


def test_noise_rates_on_target():
    rng = np.random.default_rng(config.SEED)
    clean = simulate(rng)
    noisy = add_noise(clean, rng)

    # The clean log has no exact duplicate rows, so every duplicate in the noisy log is added noise.
    assert not clean.duplicated().any()
    n_duplicates = int(noisy.duplicated().sum())
    n_kept = len(noisy) - n_duplicates
    missing_rate = (len(clean) - n_kept) / len(clean)
    duplicate_rate = n_duplicates / n_kept

    assert abs(missing_rate - config.MISSING_EVENT_RATE) <= TOLERANCE, missing_rate
    assert abs(duplicate_rate - config.DUPLICATE_EVENT_RATE) <= TOLERANCE, duplicate_rate


def test_noise_does_not_change_columns():
    rng = np.random.default_rng(1)
    clean = simulate(rng, n_cases=200)
    assert list(add_noise(clean, rng).columns) == list(clean.columns)
