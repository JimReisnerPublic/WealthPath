# Data Sources

WealthPath uses two distinct datasets for two distinct purposes. Understanding
the difference matters for both the interview story and for interpreting results.

---

## 1. Survey of Consumer Finances (SCF) — Cohort Benchmarking

### What it is

The [Survey of Consumer Finances](https://www.federalreserve.gov/econres/scfindex.htm)
is a triennial survey of US household finances conducted by the Federal Reserve Board.
It is the gold-standard dataset for US household wealth and income research, used by:
- The Federal Reserve for monetary policy analysis
- Academic economists studying wealth inequality
- Financial planning tools (including Boldin) for cohort benchmarking

The 2022 survey covers ~4,600 families, statistically weighted to represent all
~130 million US households.

### What we use it for

**Cohort comparison** — "How does your income and net worth compare to similar households?"

When a user provides their profile, we:
1. Filter the SCF to households with similar age (±5 years) and education level
2. Compute weighted percentiles (25th, 50th, 75th) for income, net worth, home equity, debt
3. Show where the user falls relative to their cohort

This answers questions like: "A 45-year-old with a bachelor's degree earning $90k — is that
above or below typical for people like me?" The answer is grounded in actual Federal Reserve
data, not assumptions.

### How to get it

The SCF is free and public. We use the **Summary Extract** (not the full codebook dataset)
because it has clean, pre-named variables.

```
1. Go to: https://www.federalreserve.gov/econres/scfindex.htm
2. Click "2022 SCF Chartbook / Data" → "Summary Extract Public Data"
3. Download: scfp2022s.zip
4. Unzip → rscfp2022s.csv
5. Run: python scripts/load_scf_data.py --input path/to/rscfp2022s.csv
6. Update .env:  SCF_DATA_PATH=data/scf_2022.parquet
```

### Two important methodological features

#### Multiple imputation (5 implicates)

The SCF uses multiple imputation to handle missing and uncertain values. Each family
appears **5 times** in the raw file (`Y1` = 1 through 5), each with slightly different
imputed values for uncertain quantities (e.g. business valuations where the owner is
unsure of worth).

For publication-quality statistics you would analyze all 5 implicates and combine
estimates using Rubin's rules (a standard multiple imputation technique). For cohort
benchmarking — our use case — **we keep only implicate 1** (`Y1 == 1`), giving one
fully-imputed observation per family. This is a standard simplification for
non-inferential use.

```python
# scripts/load_scf_data.py
df = df[df["Y1"] == 1].copy()   # one row per family
```

#### Survey weights

Each family has a `WGT` column — a survey weight representing how many US households
that family "speaks for." A family with weight 8,500 represents 8,500 households.

**Why this matters:** The SCF intentionally **oversamples wealthy households** to get
reliable estimates of the right tail of the wealth distribution (the top 1%, 0.1%, etc.).
If you ignore weights, your statistics are biased upward — the sample is richer than
the US population.

```python
# Wrong — ignores oversampling of wealthy households
median_income = df["income"].median()

# Right — weighted median represents the actual US population
median_income = _weighted_quantile(df["income"].values, df["survey_weight"].values, 0.50)
```

`SCFDataService` detects whether weights are present and uses weighted quantiles
automatically when real SCF data is loaded.

### Column mapping (SCF → WealthPath)

| SCF Variable | WealthPath Column | Notes |
|---|---|---|
| `AGE` | `age` | Age of household head |
| `EDCL` | `education` | 1–4 mapped to our enum (see below) |
| `INCOME` | `income` | Total pre-tax family income |
| `NETWORTH` | `net_worth` | Can be negative |
| `ASSET` | `total_assets` | Total assets |
| `DEBT` | `debt` | Total debt |
| `HOUSES - MRTHEL` | `home_equity` | Home value minus mortgage |
| `RETQLIQ` | `retirement_assets` | IRAs, 401k, Keogh plans |
| `WGT` | `survey_weight` | Population weight |

#### Education mapping

The SCF Summary Extract uses a 4-level education variable (`EDCL`). **It does not
distinguish bachelor's from graduate degrees** — both are category 4. This is a known
limitation of the summary extract; the full codebook dataset has more granular education.

| EDCL | SCF Label | WealthPath `EducationLevel` |
|---|---|---|
| 1 | No high school diploma | `no_high_school` |
| 2 | High school diploma or GED | `high_school` |
| 3 | Some college | `some_college` |
| 4 | College degree (BA or higher) | `bachelors` *(graduate included)* |

---

## 2. Training Data — ML Surrogate Model

### What it is

For the ML surrogate model (Phase 2), we generate a large labeled dataset of
household profiles, label each with a "probability of retirement success" from the
Monte Carlo simulation, and train XGBoost on that labeled dataset.

The script supports two modes — SCF-anchored (recommended) and pure synthetic (fallback).

### Generation modes

#### SCF-anchored (recommended)

When real SCF data is available, `generate_training_data.py` uses it as the source
of base demographics. **The input is the parquet file produced by `load_scf_data.py`
in Section 1 above** — run that script first if you haven't already.

1. Load the SCF parquet and filter to working-age adults (ages 25–62)
2. **Weighted-sample** `n` households using each record's `survey_weight` — the same
   weight used for cohort benchmarking. This ensures the training distribution reflects
   the actual US wealth distribution rather than the SCF's deliberate oversampling of
   wealthy households.
3. Take `age`, `income`, and `retirement_assets` (IRAs/401k) directly from the sampled rows
4. Sample forward-looking planning variables stochastically on top (see below)
5. Label each household by running the Monte Carlo simulation offline

```bash
python scripts/generate_training_data.py --scf data/scf_2022.parquet
```

#### Pure synthetic (fallback)

When SCF data is not available, all features are sampled from statistical distributions
calibrated to approximate known patterns in retirement research and public economic data.
No real individuals are used.

```bash
python scripts/generate_training_data.py --n 50000
```

### Why the SCF can't be used directly (without simulation)

The SCF has ~4,600 rows and no retirement outcome column — `success_probability` is
exactly what we are trying to predict. It doesn't exist in any survey.

The SCF-anchored approach threads the needle: SCF provides realistic, population-weighted
demographics; the Monte Carlo engine provides the labels. The result is a training dataset
that is both large enough for supervised learning and grounded in real US household data.

### What's in the training data

| Column | Source | Notes |
|--------|--------|-------|
| `age` | SCF / synthetic | Age of household head |
| `annual_income` | SCF `income` / synthetic | Clipped to $20k–$500k |
| `current_savings` | SCF `retirement_assets` / synthetic | Liquid investable assets (IRAs, 401k) — not total net worth |
| `retirement_age` | Sampled | age + random 3–35 years, clipped 55–72 |
| `life_expectancy` | Sampled | Normal(85, 6), clipped 75–100 |
| `savings_rate` | Sampled | Beta(2, 7) — mode ~15%, right-skewed |
| `equity_fraction` | Sampled | Rule-of-thumb glide path + noise |
| `annual_spending_retirement` | Sampled | Replacement rate × income |
| `social_security_annual` | Sampled | ~30% of income, bounded $8k–$50k |
| `success_probability` | **Monte Carlo label** | Fraction of 500 simulated paths ending solvent |

`current_savings` uses `retirement_assets` (RETQLIQ) rather than total `net_worth`
because home equity is illiquid and not drawn down in the simulation.

### File locations

| File | Contents | Source |
|---|---|---|
| `data/scf_sample.csv` | 1,000-row synthetic dev sample | `scripts/seed_scf_sample.py` |
| `data/scf_2022.parquet` | Real SCF 2022 (after you run the loader) | `scripts/load_scf_data.py` |
| `data/synthetic_households.parquet` | Training data for ML model | `scripts/generate_training_data.py` |
| `data/surrogate_model.joblib` | Trained XGBoost model | `scripts/train_surrogate_model.py` |

