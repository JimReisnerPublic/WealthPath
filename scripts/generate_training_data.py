"""
Generate household profiles and label each with a retirement success probability
from the Monte Carlo simulation engine.

This dataset is the training data for the XGBoost surrogate model.

Two modes:

  SCF-based (recommended — requires real SCF parquet):
    Base demographics (age, income, current savings) are drawn by weighted-sampling
    from the Survey of Consumer Finances, using each record's survey_weight. This
    ensures the training distribution reflects the actual US household wealth
    distribution rather than a hand-tuned approximation.

    Forward-looking planning variables (retirement_age, savings_rate, etc.) are not
    in the SCF, so they are still sampled stochastically and layered on top.

  Pure synthetic (fallback — no SCF data required):
    All features sampled from calibrated statistical distributions, as originally.

Usage
-----
    # With real SCF data (recommended):
    python scripts/generate_training_data.py --scf data/scf_2022.parquet

    # Without SCF data (pure synthetic fallback):
    python scripts/generate_training_data.py --n 50000

    # Output: data/synthetic_households.parquet

The surrogate model core idea:
    Train a fast ML model to *approximate* the expensive simulation.
    At inference time, call the model (~1ms) instead of running 1,000
    Monte Carlo paths (~200ms). The model learns the mapping:
        household features → success probability
    from thousands of labeled examples generated offline.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Return assumptions (real, inflation-adjusted)
# ---------------------------------------------------------------------------
EQUITY_RETURN_MEAN = 0.07   # 7% real return — long-run US equities (~S&P 500)
EQUITY_RETURN_STD  = 0.16   # 16% volatility
BOND_RETURN_MEAN   = 0.02   # 2% real return — intermediate treasuries
BOND_RETURN_STD    = 0.05   # 5% volatility


def simulate_success_probability(
    *,
    current_age: np.ndarray,
    retirement_age: np.ndarray,
    life_expectancy: np.ndarray,
    current_savings: np.ndarray,
    annual_income: np.ndarray,
    savings_rate: np.ndarray,
    equity_fraction: np.ndarray,
    annual_spending_retirement: np.ndarray,
    social_security_annual: np.ndarray,
    n_sims: int = 500,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Two-phase Monte Carlo simulation for a batch of households.

    Phase 1 — Accumulation (current_age → retirement_age):
        Each year: wealth = wealth × (1 + return) + income × savings_rate
        Income grows at 2%/year (real productivity growth assumption).

    Phase 2 — Distribution (retirement_age → life_expectancy):
        Net annual withdrawal = spending - social_security (capped at 0).
        Each year: wealth = wealth × (1 + return) - net_withdrawal

    Returns:
        Array of shape (n_households,) — success probability for each household.
        Success = fraction of n_sims paths where wealth ≥ 0 at life_expectancy.

    Python/numpy note for C# developers:
        We loop over years (not households) and apply numpy array ops across
        all n_sims paths simultaneously. This is the Python equivalent of
        SIMD / vectorized operations — much faster than explicit loops.
    """
    n = len(current_age)
    port_return_mean = equity_fraction * EQUITY_RETURN_MEAN + (1 - equity_fraction) * BOND_RETURN_MEAN
    port_return_std  = equity_fraction * EQUITY_RETURN_STD  + (1 - equity_fraction) * BOND_RETURN_STD
    net_withdrawal   = np.maximum(annual_spending_retirement - social_security_annual, 0)

    success_counts = np.zeros(n)

    for sim in range(n_sims):
        wealth = current_savings.copy().astype(float)
        income = annual_income.copy().astype(float)

        # Phase 1: accumulate until retirement
        max_accum_years = int(np.max(retirement_age - current_age))
        for year in range(max_accum_years):
            active = (current_age + year) < retirement_age
            returns = rng.normal(port_return_mean, port_return_std, n)
            wealth = np.where(
                active,
                wealth * (1 + returns) + income * savings_rate,
                wealth,  # already retired — no change in this phase loop
            )
            income *= 1.02  # 2% real income growth pre-retirement

        # Phase 2: distribute until life expectancy
        max_dist_years = int(np.max(life_expectancy - retirement_age))
        for year in range(max_dist_years):
            in_retirement = (retirement_age + year) < life_expectancy
            returns = rng.normal(port_return_mean, port_return_std, n)
            wealth = np.where(
                in_retirement,
                wealth * (1 + returns) - net_withdrawal,
                wealth,
            )

        success_counts += (wealth >= 0).astype(float)

    return success_counts / n_sims


# ---------------------------------------------------------------------------
# SCF-based household generation
# ---------------------------------------------------------------------------

def load_scf_base(scf_path: Path, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Load SCF data and return a weighted sample of n working-age households.

    The SCF intentionally oversamples wealthy households to get reliable right-tail
    statistics. survey_weight corrects for this: each record's weight is proportional
    to how many actual US households it represents. By sampling with those weights we
    get a population-representative training set rather than a survey-composition set.

    C# analogy: this is like sampling from a weighted IEnumerable where the weight
    determines how often each element appears in the output.
    """
    print(f"  Loading SCF data from {scf_path} ...")
    if scf_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(scf_path)
    else:
        df = pd.read_csv(scf_path)

    # Filter to working-age adults — households still in the accumulation phase
    df = df[(df["age"] >= 25) & (df["age"] <= 62)].reset_index(drop=True)
    print(f"  Working-age SCF records (25–62): {len(df):,}")

    if "survey_weight" in df.columns:
        weights = df["survey_weight"].values.astype(float)
        weights /= weights.sum()  # normalize → probabilities
        print(f"  Sampling {n:,} households using survey weights (population-representative)")
    else:
        # Synthetic SCF sample has no survey weights — use uniform sampling
        weights = None
        print(f"  No survey_weight column found — using uniform sampling")

    indices = rng.choice(len(df), size=n, replace=True, p=weights)
    return df.iloc[indices].reset_index(drop=True)


def generate_households_from_scf(
    n: int, scf_path: Path, rng: np.random.Generator
) -> pd.DataFrame:
    """
    Build training households anchored to SCF demographics.

    Columns taken directly from SCF (population-grounded):
        age, annual_income, current_savings

    Columns sampled stochastically (not in SCF):
        retirement_age, life_expectancy, savings_rate, equity_fraction,
        annual_spending_retirement, social_security_annual
    """
    base = load_scf_base(scf_path, n, rng)

    age = base["age"].values.astype(int)

    # Income: SCF INCOME field — clip to simulation-reasonable range
    annual_income = np.clip(base["income"].values, 20_000, 500_000).astype(float)

    # Current savings: use retirement_assets (IRAs, 401k, Keogh) if available.
    # This is the liquid investable wealth that the simulation accumulates and draws
    # down — more meaningful than total net_worth which includes illiquid home equity.
    # If the column is missing (synthetic SCF sample), fall back to net_worth approach.
    if "retirement_assets" in base.columns:
        current_savings = np.maximum(base["retirement_assets"].values.astype(float), 0)
    else:
        # Synthetic sample fallback: estimate savings from income and age
        savings_multiplier = np.clip(
            rng.lognormal(mean=0.0, sigma=0.8, size=n) * (age - 22) * 0.4,
            0, None,
        )
        current_savings = np.maximum(annual_income * savings_multiplier, 0)

    return _build_dataframe(age, annual_income, current_savings, n, rng)


# ---------------------------------------------------------------------------
# Pure synthetic household generation (original fallback)
# ---------------------------------------------------------------------------

def generate_households(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Sample synthetic household profiles from realistic statistical distributions.

    Used when no SCF data is available. Distributions are calibrated to approximate
    patterns in the SCF and retirement research literature.
    """
    age = rng.integers(25, 63, size=n)

    # Log-normal income distribution approximates US working population
    annual_income = np.clip(
        rng.lognormal(mean=10.9, sigma=0.65, size=n),
        20_000, 500_000,
    )

    # Current savings: roughly income × years_worked × savings_rate × growth_factor
    savings_multiplier = np.clip(
        rng.lognormal(mean=0.0, sigma=0.8, size=n) * (age - 22) * 0.4,
        0, None,
    )
    current_savings = np.maximum(annual_income * savings_multiplier, 0)

    return _build_dataframe(age, annual_income, current_savings, n, rng)


# ---------------------------------------------------------------------------
# Shared forward-looking feature generation
# ---------------------------------------------------------------------------

def _build_dataframe(
    age: np.ndarray,
    annual_income: np.ndarray,
    current_savings: np.ndarray,
    n: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Layer stochastic planning variables on top of base demographics.

    These variables are not available in the SCF — they represent the household's
    *intentions* (when to retire, how much to save going forward) rather than their
    current financial snapshot. They are sampled from realistic distributions for both
    the SCF-based and synthetic paths.
    """
    # Retirement age: 3–35 years away, bounded 55–72
    years_to_retire = rng.integers(3, 36, size=n)
    retirement_age = np.clip(age + years_to_retire, 55, 72).astype(int)

    # Life expectancy: normal(85, 6), bounded 75–100
    life_expectancy = np.clip(rng.normal(85, 6, size=n).astype(int), 75, 100)
    # Ensure life_expectancy > retirement_age by at least 5 years
    life_expectancy = np.maximum(life_expectancy, retirement_age + 5)

    # Savings rate: right-skewed beta — most people save 5–15%, some up to 35%
    # Beta(2, 7) gives mode ~15%, long right tail
    savings_rate = np.clip(rng.beta(2, 7, size=n), 0.01, 0.50)

    # Asset allocation: glide-path rule of thumb + noise
    # Rule of thumb: equity% ≈ 110 - age  (e.g. age 40 → 70% equity)
    equity_target = np.clip((110 - age) / 100, 0.20, 1.0)
    equity_fraction = np.clip(equity_target + rng.normal(0, 0.10, size=n), 0.10, 1.0)

    # Retirement spending: replacement rate × pre-retirement income
    # Most research suggests 70–90%; we model a wide range
    replacement_rate = np.clip(rng.beta(5, 2, size=n) * 0.5 + 0.5, 0.40, 1.10)
    annual_spending_retirement = annual_income * replacement_rate

    # Social Security: rough approximation — ~30% of pre-retirement income, bounded
    ss_fraction = np.clip(rng.normal(0.30, 0.08, size=n), 0.10, 0.50)
    social_security_annual = np.clip(
        annual_income * ss_fraction,
        8_000,    # SSA minimum for full career
        50_000,   # SSA maximum (2024 ~$58k but roughly)
    )

    return pd.DataFrame({
        "age": age,
        "retirement_age": retirement_age,
        "life_expectancy": life_expectancy.astype(int),
        "current_savings": current_savings.round(0),
        "annual_income": annual_income.round(0),
        "savings_rate": savings_rate.round(4),
        "equity_fraction": equity_fraction.round(4),
        "annual_spending_retirement": annual_spending_retirement.round(0),
        "social_security_annual": social_security_annual.round(0),
        # Derived features — often more predictive than raw inputs
        "years_to_retirement": (retirement_age - age).astype(int),
        "years_in_retirement": (life_expectancy - retirement_age).astype(int),
        "savings_as_income_multiple": (current_savings / np.maximum(annual_income, 1)).round(2),
        "net_replacement_rate": (
            (annual_spending_retirement - social_security_annual)
            / np.maximum(annual_income, 1)
        ).round(4),
        # Fraction of retirement spending covered by guaranteed income (SS + pension).
        # Captures households where the portfolio is barely drawn down — a pattern the
        # surrogate previously underweighted because social_security_annual alone had
        # low SHAP importance relative to spending context.
        # Value of 1.0+ means guaranteed income fully covers spending; 0 means none.
        "guaranteed_income_fraction": (
            social_security_annual / np.maximum(annual_spending_retirement, 1)
        ).round(4),
    })


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate training data for the WealthPath surrogate model"
    )
    parser.add_argument(
        "--n", type=int, default=50_000,
        help="Number of households to generate (default: 50,000)"
    )
    parser.add_argument(
        "--scf", type=Path, default=None,
        metavar="PATH",
        help=(
            "Path to SCF parquet file (data/scf_2022.parquet). "
            "When provided, base demographics (age, income, savings) are drawn "
            "by weighted sampling from the SCF rather than from synthetic distributions. "
            "Falls back to pure synthetic generation if omitted."
        ),
    )
    parser.add_argument(
        "--sims", type=int, default=500,
        help="Monte Carlo paths per household (default: 500; higher = more accurate labels)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/synthetic_households.parquet"),
        help="Output Parquet file path"
    )
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    if args.scf is not None:
        if not args.scf.exists():
            raise FileNotFoundError(
                f"SCF file not found: {args.scf}\n"
                "Run scripts/load_scf_data.py first, or omit --scf for pure synthetic generation."
            )
        print(f"Generating {args.n:,} SCF-anchored households ...")
        df = generate_households_from_scf(args.n, args.scf, rng)
        source_label = f"SCF-anchored ({args.scf.name})"
    else:
        print(f"Generating {args.n:,} synthetic households (no SCF data provided) ...")
        df = generate_households(args.n, rng)
        source_label = "pure synthetic"

    print(f"Running Monte Carlo simulation ({args.sims} paths/household) ...")
    print("  This takes ~2–5 minutes for 50k households.")

    success_probs = simulate_success_probability(
        current_age=df["age"].values,
        retirement_age=df["retirement_age"].values,
        life_expectancy=df["life_expectancy"].values,
        current_savings=df["current_savings"].values,
        annual_income=df["annual_income"].values,
        savings_rate=df["savings_rate"].values,
        equity_fraction=df["equity_fraction"].values,
        annual_spending_retirement=df["annual_spending_retirement"].values,
        social_security_annual=df["social_security_annual"].values,
        n_sims=args.sims,
        rng=rng,
    )
    df["success_probability"] = success_probs.round(4)

    # Quick sanity check
    print(f"\nSource: {source_label}")
    print(f"Success probability distribution:")
    for pct in [10, 25, 50, 75, 90]:
        val = df["success_probability"].quantile(pct / 100)
        print(f"  p{pct:02d}: {val:.2f}")
    print(f"  Mean: {df['success_probability'].mean():.2f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"\nWrote {len(df):,} rows to {args.output}")
    print("\nNext step:  python scripts/train_surrogate_model.py")


if __name__ == "__main__":
    main()
