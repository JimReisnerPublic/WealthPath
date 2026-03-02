"""
Load and clean the Federal Reserve's Survey of Consumer Finances (SCF)
Summary Extract into WealthPath's internal format.

Usage
-----
1. Download the SCF 2022 Summary Extract CSV from the Federal Reserve:
   https://www.federalreserve.gov/econres/files/scfp2022s.zip
   Unzip to get: rscfp2022s.csv

2. Run this script:
   python scripts/load_scf_data.py --input path/to/rscfp2022s.csv

3. Output:  data/scf_2022.parquet

4. Update .env:
   SCF_DATA_PATH=data/scf_2022.parquet

Background
----------
The SCF is a triennial survey of ~4,600 US families conducted by the Federal Reserve.
It is the gold-standard dataset for US household wealth and income research, used by
the Fed, academic economists, and financial planning tools (including Boldin).

Two methodological features need handling:

1. Multiple imputation (5 implicates):
   To handle missing/uncertain values, each family appears 5 times (Y1 = 1..5),
   each with slightly different imputed values. We keep only implicate 1 (Y1 == 1)
   for simplicity — this gives one row per family with full data. For publication-quality
   statistics you would analyze all 5 and combine estimates (Rubin's rules), but for
   cohort benchmarking implicate 1 is sufficient.

2. Survey weights (WGT):
   Each family represents thousands of actual US households. The weight tells you how
   many. For population-representative statistics (e.g. "median income of 45-year-old
   college graduates in the US"), you must use weighted calculations — not simple
   median(). We preserve the weight as `survey_weight` for use in SCFDataService.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SCF column → WealthPath column mapping
# ---------------------------------------------------------------------------
# Source: SCF 2022 Summary Extract codebook
# https://www.federalreserve.gov/econres/files/codebk2022s.txt

SCF_COLUMNS_NEEDED = [
    "YY1",       # family identifier
    "Y1",        # implicate number (1–5) — we keep only 1
    "WGT",       # survey weight (how many US households this family represents)
    "AGE",       # age of household head
    "EDCL",      # education category (1–4, see map below)
    "INCOME",    # total pre-tax family income
    "NETWORTH",  # total net worth (assets minus debts)
    "ASSET",     # total assets
    "DEBT",      # total debt
    "HOUSES",    # value of primary residence
    "MRTHEL",    # total mortgage and home equity loan debt
    "RETQLIQ",   # quasi-liquid retirement assets (IRAs, 401k, Keogh)
    "MARRIED",   # 1 = married/living with partner, 2 = single/other
    "KIDS",      # number of children under 18
    "HHOUSES",   # 1 = owns primary residence, 0 = rents
]

# Education: SCF uses a 4-level category. The summary extract does not distinguish
# bachelors from graduate degrees (both are category 4). We map to our EducationLevel
# enum and note this limitation in the docs.
EDCL_TO_EDUCATION = {
    1: "no_high_school",
    2: "high_school",
    3: "some_college",
    4: "bachelors",   # includes graduate — SCF summary does not distinguish
}


def load_scf(input_path: Path) -> pd.DataFrame:
    """
    Read the raw SCF Summary Extract in CSV or Stata format.

    The Federal Reserve distributes the SCF in several formats; we support both:
    - .csv  — SAS/CSV version (rscfp2022s.csv)
    - .dta  — Stata version (rscfp2022.dta)

    Stata files from the Fed use lowercase column names, so we normalize to
    uppercase after loading to match the SCF codebook and our column mapping.
    """
    print(f"Reading {input_path} ...")
    suffix = input_path.suffix.lower()

    if suffix == ".dta":
        # Stata binary format — pandas read_stata handles this natively.
        # convert_categoricals=False keeps numeric columns (Y1, EDCL, etc.) as
        # plain integers rather than Pandas Categoricals. Without this, value-labeled
        # columns come back as category dtype and comparisons like df["Y1"] == 1 fail.
        df = pd.read_stata(
            input_path,
            columns=[c.lower() for c in SCF_COLUMNS_NEEDED],
            convert_categoricals=False,
        )
        # Normalize to uppercase to match the SCF codebook and our column mapping
        df.columns = df.columns.str.upper()
    elif suffix == ".csv":
        df = pd.read_csv(input_path, usecols=SCF_COLUMNS_NEEDED)
    else:
        raise ValueError(f"Unsupported file format: {suffix!r}. Expected .csv or .dta")

    print(f"  Raw rows: {len(df):,}  (5 implicates × {len(df)//5:,} families)")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to implicate 1 and transform to WealthPath's internal schema.

    Decisions made here:
    - Use Y1 == 1 (one row per family, fully imputed)
    - Compute home_equity = HOUSES - MRTHEL  (value minus mortgage)
    - has_retirement_account = RETQLIQ > 0
    - household_size ≈ 1 (head) + partner (if married) + kids under 18
    - All dollar values kept in nominal USD (2022 dollars)
    """
    # Keep only implicate 1 — one observation per family.
    # In the Stata SCF file, Y1 is a composite identifier where the last digit
    # is the implicate number (1–5) and the preceding digits are the family ID
    # (e.g. 11=family 1 implicate 1, 46035=family 4603 implicate 5).
    # In the CSV summary extract, Y1 is simply 1–5.
    # Using % 10 == 1 handles both formats correctly.
    df = df[df["Y1"] % 10 == 1].copy()
    print(f"  After keeping implicate 1: {len(df):,} families")

    out = pd.DataFrame()

    out["family_id"]           = df["YY1"].astype(int)
    out["survey_weight"]       = df["WGT"].astype(float)
    out["age"]                 = df["AGE"].astype(int)
    out["education"]           = df["EDCL"].map(EDCL_TO_EDUCATION)
    out["income"]              = df["INCOME"].clip(lower=0).round(0)
    out["net_worth"]           = df["NETWORTH"].round(0)          # can be negative
    out["total_assets"]        = df["ASSET"].clip(lower=0).round(0)
    out["debt"]                = df["DEBT"].clip(lower=0).round(0)
    out["home_equity"]         = (df["HOUSES"] - df["MRTHEL"]).clip(lower=0).round(0)
    out["retirement_assets"]   = df["RETQLIQ"].clip(lower=0).round(0)
    out["has_retirement_account"] = (df["RETQLIQ"] > 0).astype(int)
    out["owns_home"]           = df["HHOUSES"].astype(int)
    out["married"]             = (df["MARRIED"] == 1).astype(int)
    out["kids_under_18"]       = df["KIDS"].clip(lower=0).astype(int)

    # Approximate household size: head + partner (if married) + kids
    out["household_size"] = 1 + out["married"] + out["kids_under_18"]
    out["household_size"] = out["household_size"].clip(upper=10)

    # Drop rows with missing education mapping (shouldn't happen, but guard it)
    before = len(out)
    out = out.dropna(subset=["education"])
    if len(out) < before:
        print(f"  Dropped {before - len(out)} rows with unmapped education values")

    print(f"  Clean rows: {len(out):,}")
    return out.reset_index(drop=True)


def print_summary(df: pd.DataFrame) -> None:
    """Print a quick sanity-check summary weighted to US population."""
    total_weight = df["survey_weight"].sum()
    print(f"\nWeighted population represented: {total_weight/1e6:.1f} million households")

    # Weighted median income — uses survey weights for population-representative stats
    sorted_df = df.sort_values("income")
    cumulative_weight = sorted_df["survey_weight"].cumsum()
    median_income = sorted_df.loc[
        cumulative_weight >= total_weight / 2, "income"
    ].iloc[0]
    print(f"Weighted median household income: ${median_income:,.0f}")

    print(f"\nEducation distribution (unweighted sample):")
    for edu, count in df["education"].value_counts().items():
        pct = count / len(df) * 100
        print(f"  {edu:<20} {count:>5,}  ({pct:.1f}%)")

    print(f"\nAge range: {df['age'].min()}–{df['age'].max()}")
    print(f"Net worth range: ${df['net_worth'].min():,.0f}  to  ${df['net_worth'].max():,.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process SCF 2022 Summary Extract into WealthPath format",
        epilog=(
            "Download the input file from: "
            "https://www.federalreserve.gov/econres/files/scfp2022s.zip"
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to rscfp2022s.csv (from the Fed zip file)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/scf_2022.parquet"),
        help="Output path (default: data/scf_2022.parquet)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Input file not found: {args.input}\n"
            "Download from: https://www.federalreserve.gov/econres/files/scfp2022s.zip"
        )

    df = load_scf(args.input)
    df = clean(df)
    print_summary(df)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"\nWrote {len(df):,} rows to {args.output}")
    print(
        "\nNext step: update .env:\n"
        f"  SCF_DATA_PATH={args.output}"
    )


if __name__ == "__main__":
    main()
