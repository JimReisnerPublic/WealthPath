from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from wealthpath.models.cohort import CohortRequest, CohortResponse, CohortStats
from wealthpath.models.household import HouseholdProfile


class SCFDataService:
    """
    Loads SCF data and matches user profiles to comparable cohorts.

    Supports two data sources (auto-detected by file extension):
    - CSV    — synthetic sample (default; for dev/testing, no download needed)
    - Parquet — real SCF 2022 data produced by scripts/load_scf_data.py

    When real SCF data is loaded, the survey_weight column is used for
    population-representative statistics (weighted quantiles). Without weights,
    simple unweighted medians are used — fine for synthetic data, but misleading
    for real survey data where wealthy households are intentionally oversampled.
    """

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self._df: pd.DataFrame | None = None

    def load(self) -> None:
        # Auto-detect format by extension — Parquet is the real SCF, CSV is synthetic
        if self._data_path.suffix.lower() == ".parquet":
            if not self._data_path.exists():
                fallback = self._data_path.parent / "scf_sample.csv"
                logger.warning(
                    "SCF parquet not found at %s — falling back to synthetic sample %s. "
                    "Run scripts/load_scf_data.py to generate real SCF data.",
                    self._data_path,
                    fallback,
                )
                self._df = pd.read_csv(fallback)
            else:
                self._df = pd.read_parquet(self._data_path)
                logger.info("Loaded real SCF 2022 data from %s (%d rows, weighted=%s)",
                            self._data_path, len(self._df), self.has_weights)
        else:
            self._df = pd.read_csv(self._data_path)

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self.load()
        assert self._df is not None
        return self._df

    @property
    def has_weights(self) -> bool:
        """True when real SCF data with survey weights is loaded."""
        return "survey_weight" in self.df.columns

    def match_cohort(self, profile: HouseholdProfile) -> pd.DataFrame:
        """Filter SCF data to households in the same age band (±5 years).

        We intentionally do not filter by education: the SCF Summary Extract
        merges bachelor's and graduate degrees into one category, making
        education-based cohorts misleading. Filtering by age alone gives a
        larger, statistically stable cohort that represents all Americans in
        the user's life stage.
        """
        df = self.df
        age_lo, age_hi = profile.age - 5, profile.age + 5
        cohort = df.loc[(df["age"] >= age_lo) & (df["age"] <= age_hi)]
        if cohort.empty:
            return df  # fallback to full dataset
        return cohort

    def compare(self, request: CohortRequest) -> CohortResponse:
        cohort = self.match_cohort(request.household)
        stats: list[CohortStats] = []

        field_map = {
            "income": request.household.income,
            "net_worth": request.household.net_worth,
            "home_equity": request.household.home_equity,
            "debt": request.household.debt,
        }

        weights = cohort["survey_weight"].values if self.has_weights else None

        for field in request.compare_fields:
            if field not in cohort.columns or field not in field_map:
                continue
            col = cohort[field].dropna()
            user_val = field_map[field]

            if weights is not None:
                col_weights = cohort.loc[col.index, "survey_weight"].values
                p25 = _weighted_quantile(col.values, col_weights, 0.25)
                p50 = _weighted_quantile(col.values, col_weights, 0.50)
                p75 = _weighted_quantile(col.values, col_weights, 0.75)
                pct_rank = _weighted_percentile_rank(col.values, col_weights, user_val)
            else:
                p25 = float(col.quantile(0.25))
                p50 = float(col.median())
                p75 = float(col.quantile(0.75))
                pct_rank = float(
                    np.searchsorted(np.sort(col.values), user_val) / len(col) * 100
                )

            stats.append(
                CohortStats(
                    field=field,
                    user_value=user_val,
                    cohort_median=p50,
                    cohort_p25=p25,
                    cohort_p75=p75,
                    percentile_rank=pct_rank,
                )
            )

        data_source = "SCF 2022, weighted" if self.has_weights else "synthetic sample"
        description = (
            f"Ages {request.household.age - 5}–{request.household.age + 5} "
            f"({data_source})"
        )
        return CohortResponse(
            cohort_size=len(cohort),
            cohort_description=description,
            stats=stats,
        )


# ---------------------------------------------------------------------------
# Weighted statistics helpers
# ---------------------------------------------------------------------------
# The SCF uses probability-weighted survey design. Simple unweighted statistics
# are biased because the SCF intentionally oversamples wealthy households to
# get reliable estimates of the right tail of the wealth distribution.
#
# These functions implement weighted quantiles so cohort benchmarks represent
# the actual US population rather than the survey sample composition.
#
# C# note: there is no stdlib equivalent — you would use a MathNet.Numerics
# weighted statistics method or implement it yourself, as we do here.

def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """
    Compute a population-weighted quantile.

    Algorithm:
    1. Sort values (and their weights) in ascending order.
    2. Compute cumulative weight.
    3. Find the value where cumulative weight first exceeds q * total_weight.
    """
    sorted_idx = np.argsort(values)
    sorted_vals = values[sorted_idx]
    sorted_wts = weights[sorted_idx]
    cumulative = np.cumsum(sorted_wts)
    cutoff = q * cumulative[-1]
    idx = int(np.searchsorted(cumulative, cutoff))
    return float(sorted_vals[min(idx, len(sorted_vals) - 1)])


def _weighted_percentile_rank(
    values: np.ndarray, weights: np.ndarray, target: float
) -> float:
    """
    Return the weighted percentile rank of target within values.
    e.g. 65.0 → "better than 65% of the weighted US population".
    """
    total_weight = weights.sum()
    if total_weight == 0:
        return 0.0
    below_weight = weights[values < target].sum()
    return float(below_weight / total_weight * 100)
