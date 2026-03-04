from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-5-mini"
    azure_openai_api_version: str = "2024-10-21"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    scf_data_path: Path = Path("data/scf_2022.parquet")

    # Simulation defaults
    default_num_simulations: int = 1_000
    default_projection_years: int = 30

    # Surrogate ML model
    # Set to the output of scripts/train_surrogate_model.py when model is trained.
    # If the file does not exist, the /plan/evaluate endpoint degrades gracefully
    # to the Monte Carlo simulation.
    surrogate_model_path: Path = Path("data/surrogate_model.joblib")

    # Azure Blob Storage — surrogate model in production
    # If azure_storage_connection_string is set, the model is downloaded from blob
    # at startup instead of loaded from surrogate_model_path.
    # Leave unset in local development — local file is used automatically.
    azure_storage_connection_string: str = ""
    azure_blob_container: str = "models"
    azure_blob_model_name: str = "surrogate_model.joblib"

    # FRED (Federal Reserve Economic Data)
    # Free API key available at https://fred.stlouisfed.org/docs/api/api_key.html
    # If not set, FRED economic data tools will not be available to the agent.
    fred_api_key: str = ""
