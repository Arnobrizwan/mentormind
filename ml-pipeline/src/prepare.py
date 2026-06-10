"""Stage 1 — prepare the dropout-risk dataset.

Generates a synthetic-but-plausible student engagement dataset. In
production this script is swapped for a SQL extract over Enrollment /
QuizAttempt / ChatMessage (same column contract), which is exactly why
the feature list lives in common.FEATURES.
"""

import numpy as np
import pandas as pd

from common import DATA_DIR, FEATURES, TARGET, load_params


def synthesize(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    progress = rng.beta(2, 2, n) * 100
    days_idle = rng.exponential(7, n).clip(0, 60)
    quiz_avg = (progress * 0.6 + rng.normal(20, 15, n)).clip(0, 100)
    lessons_per_week = (progress / 25 + rng.exponential(1, n)).clip(0, 20)
    chat_messages = rng.poisson(progress / 20, n)

    # Ground truth: low progress + long absence drives dropout.
    # Calibrated so the base rate lands around ~30%, sampled Bernoulli so
    # labels are noisy-but-learnable like real engagement data.
    logit = (
        4.0
        - 0.09 * progress
        + 0.12 * days_idle
        - 0.015 * quiz_avg
        - 0.12 * lessons_per_week
        - 0.04 * chat_messages
    )
    p_drop = 1 / (1 + np.exp(-logit))
    dropped = (rng.random(n) < p_drop).astype(int)

    return pd.DataFrame(
        {
            "progress_pct": progress.round(2),
            "days_since_last_login": days_idle.round(2),
            "quiz_avg": quiz_avg.round(2),
            "lessons_per_week": lessons_per_week.round(2),
            "chat_messages": chat_messages,
            TARGET: dropped,
        }
    )


def main():
    params = load_params()["prepare"]
    df = synthesize(params["n_students"], params["seed"])

    rng = np.random.default_rng(params["seed"])
    mask = rng.random(len(df)) < params["test_size"]

    DATA_DIR.mkdir(exist_ok=True)
    df[~mask].to_csv(DATA_DIR / "train.csv", index=False)
    df[mask].to_csv(DATA_DIR / "test.csv", index=False)
    print(
        f"prepare: {len(df)} rows -> train={len(df[~mask])} test={len(df[mask])} "
        f"(dropout rate {df[TARGET].mean():.1%})"
    )


if __name__ == "__main__":
    main()
