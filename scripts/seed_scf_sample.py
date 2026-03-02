"""Generate a larger synthetic SCF sample dataset for development."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


EDUCATION_LEVELS = ["no_high_school", "high_school", "some_college", "bachelors", "graduate"]

EDUCATION_INCOME_MULTIPLIER = {
    "no_high_school": 0.6,
    "high_school": 0.8,
    "some_college": 1.0,
    "bachelors": 1.3,
    "graduate": 1.6,
}


def generate(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    ages = rng.integers(22, 80, size=n)
    educations = rng.choice(EDUCATION_LEVELS, size=n, p=[0.08, 0.22, 0.25, 0.30, 0.15])

    base_income = rng.lognormal(mean=10.8, sigma=0.6, size=n)
    income_mult = np.array([EDUCATION_INCOME_MULTIPLIER[e] for e in educations])
    age_mult = 1 + 0.02 * np.clip(ages - 25, 0, 30) - 0.01 * np.clip(ages - 55, 0, 30)
    incomes = np.round(base_income * income_mult * age_mult, -2)

    net_worths = np.round(
        incomes * (0.5 + 0.08 * np.clip(ages - 25, 0, 50)) + rng.normal(0, 20000, size=n),
        -2,
    )

    household_sizes = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.20, 0.30, 0.25, 0.18, 0.07])
    has_retirement = (rng.random(n) < (0.3 + 0.01 * (ages - 25))).astype(int)
    home_equity = np.where(
        rng.random(n) < (0.2 + 0.01 * np.clip(ages - 30, 0, 40)),
        np.round(rng.lognormal(11.5, 0.5, size=n), -3),
        0,
    )
    debt = np.round(np.maximum(rng.lognormal(9.5, 1.0, size=n) - ages * 500, 0), -2)

    return pd.DataFrame({
        "age": ages,
        "income": incomes,
        "net_worth": net_worths,
        "education": educations,
        "household_size": household_sizes,
        "has_retirement_account": has_retirement,
        "home_equity": home_equity,
        "debt": debt,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SCF data")
    parser.add_argument("-n", type=int, default=1000, help="Number of rows")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/scf_sample.csv"),
        help="Output path",
    )
    args = parser.parse_args()

    df = generate(n=args.n)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
