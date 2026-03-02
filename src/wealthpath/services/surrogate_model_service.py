from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from wealthpath.models.evaluate import EvaluationRequest, EvaluationResponse, FeatureDriver

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Human-readable display names for model features
_FEATURE_DISPLAY_NAMES: dict[str, str] = {
    "age": "Current age",
    "years_to_retirement": "Years until retirement",
    "years_in_retirement": "Years in retirement",
    "current_savings": "Current savings",
    "annual_income": "Annual income",
    "savings_rate": "Savings rate",
    "equity_fraction": "Stock allocation",
    "annual_spending_retirement": "Annual retirement spending",
    "social_security_annual": "Social Security income",
    "savings_as_income_multiple": "Savings as multiple of income",
    "net_replacement_rate": "Net spending replacement rate",
    "guaranteed_income_fraction": "Guaranteed income coverage",
}


class SurrogateModelService:
    """
    Serves predictions from the trained XGBoost surrogate model.

    At startup, loads the joblib artifact produced by scripts/train_surrogate_model.py.
    If the model file doesn't exist, all methods return None — callers fall back to
    Monte Carlo simulation (graceful degradation, same pattern as AIEngine without creds).

    Per-request SHAP explanation:
        For each prediction we compute local SHAP values — the contribution of each
        feature to *this specific household's* success probability. This tells the user
        not just the probability, but *why*: "Your high net replacement rate is the
        biggest drag on your score."

        Local SHAP values ≠ global feature importance.
        Global = average |SHAP| across all households (what matters overall).
        Local  = signed SHAP for one household (what matters for YOU).
    """

    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._artifact: dict | None = None
        self._explainer = None  # shap.TreeExplainer, lazy-loaded with the model

    def load_from_blob(self, connection_string: str, container: str, blob_name: str) -> bool:
        """Download model from Azure Blob Storage to a temp file, then load it.

        Falls back to load() from the original local path if the download fails,
        preserving the same graceful-degradation behaviour as the local case.

        # .NET equivalent: reading a file from Azure Blob Storage via BlobClient.DownloadToAsync()
        # Python SDK:       BlobServiceClient.from_connection_string() → get_blob_client() → download_blob()
        """
        import tempfile

        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            logger.warning("azure-storage-blob not installed — falling back to local model path")
            return self.load()

        try:
            logger.info("Downloading surrogate model from blob: %s/%s", container, blob_name)
            client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = client.get_blob_client(container=container, blob=blob_name)

            # Write to a named temp file; Path.exists() check in load() will find it
            with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
                self._model_path = Path(tmp.name)
                tmp.write(blob_client.download_blob().readall())

            return self.load()
        except Exception:
            logger.exception(
                "Failed to download surrogate model from blob — falling back to local path"
            )
            return self.load()

    def load(self) -> bool:
        """Load model from disk. Returns True if successful."""
        if not self._model_path.exists():
            logger.warning(
                "Surrogate model not found at %s — /plan/evaluate will fall back to Monte Carlo. "
                "Run scripts/generate_training_data.py then scripts/train_surrogate_model.py.",
                self._model_path,
            )
            return False

        try:
            import joblib
            import shap
            self._artifact = joblib.load(self._model_path)
            self._explainer = shap.TreeExplainer(self._artifact["model"])
            logger.info(
                "Surrogate model loaded from %s  (R²=%.3f, MAE=%.3f)",
                self._model_path,
                self._artifact["metrics"].get("r2", 0),
                self._artifact["metrics"].get("mae", 0),
            )
            return True
        except Exception:
            logger.exception("Failed to load surrogate model from %s", self._model_path)
            return False

    @property
    def ready(self) -> bool:
        return self._artifact is not None

    def predict(self, request: EvaluationRequest) -> EvaluationResponse | None:
        """
        Run a prediction + local SHAP explanation for one household.
        Returns None if the model is not loaded (caller should fall back to Monte Carlo).
        """
        if not self.ready:
            return None

        import pandas as pd

        feature_cols: list[str] = self._artifact["feature_cols"]
        model = self._artifact["model"]

        years_to_retire = max(request.planned_retirement_age - request.household.age, 0)
        years_in_retire = max(request.life_expectancy - request.planned_retirement_age, 0)
        net_replacement  = max(
            request.annual_spending_retirement - request.social_security_annual, 0
        ) / max(request.household.income, 1)

        features = {
            "age": request.household.age,
            "years_to_retirement": years_to_retire,
            "years_in_retirement": years_in_retire,
            "current_savings": request.household.investable_savings,
            "annual_income": request.household.income,
            "savings_rate": request.savings_rate,
            "equity_fraction": request.equity_fraction,
            "annual_spending_retirement": request.annual_spending_retirement,
            "social_security_annual": request.social_security_annual,
            "savings_as_income_multiple": request.household.investable_savings / max(request.household.income, 1),
            "net_replacement_rate": net_replacement,
            "guaranteed_income_fraction": request.social_security_annual / max(request.annual_spending_retirement, 1),
        }

        X = pd.DataFrame([{col: features[col] for col in feature_cols}])
        prob = float(np.clip(model.predict(X)[0], 0.0, 1.0))

        # Local SHAP values for this household
        shap_values = self._explainer.shap_values(X)[0]  # shape: (n_features,)
        top_drivers = _build_top_drivers(feature_cols, shap_values, top_n=5)

        return EvaluationResponse(
            success_probability=round(prob, 4),
            success_label=_label(prob),
            top_drivers=top_drivers,
            data_source="surrogate_model",
            model_metrics=self._artifact.get("metrics"),
        )


def _label(prob: float) -> str:
    if prob >= 0.80:
        return "on track"
    if prob >= 0.60:
        return "at risk"
    return "critical"


def _build_top_drivers(
    feature_cols: list[str],
    shap_values: np.ndarray,
    top_n: int = 5,
) -> list[FeatureDriver]:
    """Return the top_n features sorted by |SHAP value|."""
    indexed = sorted(
        enumerate(shap_values), key=lambda x: abs(x[1]), reverse=True
    )[:top_n]

    return [
        FeatureDriver(
            feature=feature_cols[i],
            display_name=_FEATURE_DISPLAY_NAMES.get(feature_cols[i], feature_cols[i]),
            shap_value=round(float(v), 4),
            direction="positive" if v >= 0 else "negative",
        )
        for i, v in indexed
    ]
