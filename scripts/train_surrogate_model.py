"""
Train an XGBoost surrogate model on the synthetic household dataset
produced by scripts/generate_training_data.py.

The model learns to predict retirement success probability directly from
household features, replacing real-time Monte Carlo simulation at inference.

Python ML stack for C# developers
-----------------------------------
scikit-learn  ≈  ML.NET — provides train/test split, metrics, pipeline utilities
XGBoost       ≈  ML.NET's FastTreeRegressor — gradient boosted trees, very strong on tabular data
SHAP          ≈  no direct .NET equivalent — explains individual predictions using Shapley values
joblib        ≈  BinaryFormatter / MessagePack — serializes the trained model to disk
MLflow        ≈  Azure DevOps + NuGet (combined) — tracks experiments and registers model versions

MLflow experiment tracking
--------------------------
Every training run is logged to MLflow: hyperparams, metrics, SHAP importances, and the
model artifact. By default this writes to a local ./mlruns folder; switch to Azure Databricks
by setting DATABRICKS_HOST + DATABRICKS_TOKEN env vars and passing --mlflow-uri databricks.

Usage
-----
    # First generate the training data:
    python scripts/generate_training_data.py --n 50000

    # Then train (logs to local ./mlruns):
    python scripts/train_surrogate_model.py

    # Train and register in Azure Databricks Model Registry:
    python scripts/train_surrogate_model.py --mlflow-uri databricks --register

    # View local experiment results:
    mlflow ui   # opens http://localhost:5000

    # Output: data/surrogate_model.joblib
    # Update .env:  SURROGATE_MODEL_PATH=data/surrogate_model.joblib
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# XGBoost hyperparameters defined here so MLflow can log them directly.
# Keeping them at module level avoids duplicating the values in main().
XGB_PARAMS: dict = {
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}

# Features the model is trained on — must match generate_training_data.py
FEATURE_COLS = [
    "age",
    "years_to_retirement",
    "years_in_retirement",
    "current_savings",
    "annual_income",
    "savings_rate",
    "equity_fraction",
    "annual_spending_retirement",
    "social_security_annual",
    "savings_as_income_multiple",
    "net_replacement_rate",
    "guaranteed_income_fraction",  # SS+pension / spending — captures low-drawdown households
]

TARGET_COL = "success_probability"


def load_data(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    print(f"Loading training data from {path} ...")
    df = pd.read_parquet(path)
    print(f"  {len(df):,} households loaded")
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    return X, y


def train(X_train: pd.DataFrame, y_train: pd.Series) -> xgb.XGBRegressor:
    """
    Train an XGBoost regressor.

    XGBoost builds an ensemble of decision trees sequentially, each one
    correcting the errors of the previous (gradient boosting). It is the
    dominant algorithm for tabular data in industry and Kaggle competitions.

    Key hyperparameters:
    - n_estimators: number of trees (more = better fit, but slower + overfitting risk)
    - max_depth: tree depth (deeper = more complex patterns, overfitting risk)
    - learning_rate: shrinkage per tree (lower = more trees needed, often better)
    - subsample: fraction of rows used per tree (reduces overfitting)
    - colsample_bytree: fraction of columns used per tree (reduces overfitting)
    """
    model = xgb.XGBRegressor(**XGB_PARAMS)
    print("Training XGBoost model ...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=False,
    )
    return model


def evaluate(
    model: xgb.XGBRegressor,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict:
    """
    Evaluate model accuracy on the holdout test set.

    Metrics:
    - R²: fraction of variance explained (1.0 = perfect; >0.95 is excellent for surrogates)
    - MAE: mean absolute error in probability units (0.03 = off by 3 percentage points)
    - Within 5%: fraction of predictions within 5 pp of the Monte Carlo ground truth
    """
    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0, 1)

    r2  = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    within_5pct = float(np.mean(np.abs(y_pred - y_test) <= 0.05))

    metrics = {"r2": round(r2, 4), "mae": round(mae, 4), "within_5pct": round(within_5pct, 4)}

    print(f"\nTest set performance ({len(y_test):,} households):")
    print(f"  R²            : {r2:.4f}  (fraction of variance explained)")
    print(f"  MAE           : {mae:.4f}  ({mae*100:.1f} percentage points average error)")
    print(f"  Within ±5 pp  : {within_5pct:.1%}  of predictions")

    return metrics


def compute_global_shap(
    model: xgb.XGBRegressor,
    X_sample: pd.DataFrame,
) -> dict[str, float]:
    """
    Compute global feature importance using SHAP (SHapley Additive exPlanations).

    SHAP assigns each feature a contribution to each prediction using game theory
    (Shapley values). Global importance = mean |SHAP value| across all samples.

    Unlike XGBoost's built-in feature_importances_ (which counts tree splits),
    SHAP is model-agnostic, consistent, and interpretable in the same units as
    the prediction (probability, in our case).
    """
    print("\nComputing SHAP values for global feature importance ...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Global importance: mean absolute SHAP value per feature
    importance = {
        col: float(np.abs(shap_values[:, i]).mean())
        for i, col in enumerate(FEATURE_COLS)
    }
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    print("\nGlobal feature importance (mean |SHAP|):")
    for feature, imp in importance.items():
        bar = "█" * int(imp * 200)
        print(f"  {feature:<35} {imp:.4f}  {bar}")

    return importance


def save(
    model: xgb.XGBRegressor,
    metrics: dict,
    shap_importance: dict,
    output_path: Path,
) -> None:
    """
    Persist the model and its metadata using joblib.

    joblib is the standard way to serialize sklearn-compatible models in Python.
    It handles numpy arrays efficiently (unlike pickle for large arrays).

    The metadata dict is saved alongside the model so the service can report
    which features and metrics to expect — similar to an ML model card.
    """
    artifact = {
        "model": model,
        "feature_cols": FEATURE_COLS,
        "metrics": metrics,
        "global_shap_importance": shap_importance,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)
    print(f"\nModel saved to {output_path}")
    print(f"Artifact size: {output_path.stat().st_size / 1024:.0f} KB")

    # Also save a human-readable metrics file next to the model
    metrics_path = output_path.with_suffix(".json")
    with metrics_path.open("w") as f:
        json.dump({"metrics": metrics, "features": FEATURE_COLS, "shap": shap_importance}, f, indent=2)
    print(f"Metrics saved to {metrics_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the WealthPath XGBoost surrogate model"
    )
    parser.add_argument(
        "--input", type=Path, default=Path("data/synthetic_households.parquet"),
        help="Training data from generate_training_data.py"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/surrogate_model.joblib"),
        help="Output model path"
    )
    parser.add_argument(
        "--test-size", type=float, default=0.15,
        help="Fraction held out for evaluation (default: 0.15 = 15%%)"
    )
    # --- MLflow args ---
    # MLflow ≈ Azure DevOps build pipeline + NuGet registry, combined for ML:
    #   --mlflow-uri ""          → local ./mlruns folder (default, no setup needed)
    #   --mlflow-uri databricks  → Azure Databricks (needs DATABRICKS_HOST + DATABRICKS_TOKEN)
    #   --mlflow-uri http://...  → self-hosted MLflow server
    parser.add_argument(
        "--mlflow-uri", type=str, default="",
        help="MLflow tracking URI. Empty = local ./mlruns. "
             "Use 'databricks' for Azure Databricks (set DATABRICKS_HOST + DATABRICKS_TOKEN)."
    )
    parser.add_argument(
        "--experiment", type=str, default="wealthpath-surrogate",
        help="MLflow experiment name (default: wealthpath-surrogate)"
    )
    parser.add_argument(
        "--register", action="store_true",
        help="Register model in MLflow Model Registry (requires Databricks Premium or MLflow server)"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Training data not found: {args.input}\n"
            "Run first:  python scripts/generate_training_data.py"
        )

    # Configure MLflow tracking destination.
    # If --mlflow-uri is empty, MLflow checks the MLFLOW_TRACKING_URI env var,
    # then falls back to a local ./mlruns directory. No configuration = local tracking.
    if args.mlflow_uri:
        mlflow.set_tracking_uri(args.mlflow_uri)

    # An experiment groups related runs — like a test suite groups test cases.
    # If the experiment doesn't exist, MLflow creates it automatically.
    mlflow.set_experiment(args.experiment)

    X, y = load_data(args.input)

    # Train/test split — like ML.NET's TrainTestSplit
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42
    )
    print(f"  Train: {len(X_train):,}   Test: {len(X_test):,}")

    # mlflow.start_run() opens a new "run" — a single training attempt.
    # Everything logged inside the with-block is attached to this run.
    # Equivalent to starting a new Azure DevOps pipeline run.
    with mlflow.start_run(run_name="xgboost-surrogate") as run:
        # Log hyperparameters — these are the "inputs" to this run.
        # Visible in the MLflow UI as a compare-able table across runs.
        log_params = {k: v for k, v in XGB_PARAMS.items() if k not in ("n_jobs", "verbosity")}
        log_params["test_size"] = args.test_size
        log_params["n_training_rows"] = len(X_train)
        mlflow.log_params(log_params)

        model = train(X_train, y_train)
        metrics = evaluate(model, X_test, y_test)

        # Log scalar metrics — these become the "outputs" of this run.
        # MLflow can chart them over time across runs.
        mlflow.log_metrics(metrics)

        # Compute SHAP on a 2,000-row sample (full dataset is slow for large n)
        shap_sample = X_test.sample(min(2000, len(X_test)), random_state=42)
        shap_importance = compute_global_shap(model, shap_sample)

        # Log SHAP importances as metrics so they're searchable across runs.
        mlflow.log_metrics({f"shap_{feat}": imp for feat, imp in shap_importance.items()})

        # Save the joblib artifact (used by the FastAPI service at runtime).
        save(model, metrics, shap_importance, args.output)

        # Log the model to MLflow's artifact store.
        # XGBRegressor implements the sklearn API, so mlflow.sklearn.log_model works
        # and avoids a compatibility issue with mlflow.xgboost.log_model in newer
        # XGBoost versions where _estimator_type is not set on the mixin.
        # registered_model_name=... creates a versioned entry in the Model Registry.
        registered_name = "wealthpath-surrogate" if args.register else None
        mlflow.sklearn.log_model(model, name="model", registered_model_name=registered_name)

        # Also log the joblib file so the full artifact is retrievable from MLflow.
        mlflow.log_artifact(str(args.output))

        print(f"\nMLflow run ID : {run.info.run_id}")
        print(f"Experiment    : {args.experiment}")
        if not args.mlflow_uri:
            print("View locally  : mlflow ui   →   http://localhost:5000")

    print(
        f"\nNext step: update .env:\n"
        f"  SURROGATE_MODEL_PATH={args.output}"
    )


if __name__ == "__main__":
    main()
