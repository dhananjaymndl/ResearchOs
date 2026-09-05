from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ResearchOS"
    database_url: str = "sqlite:///./researchos.db"

    storage_root: Path = Path("storage")
    dataset_storage_dir: Path = Path("storage/datasets")
    artifact_storage_dir: Path = Path("storage/artifacts")

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    llm_provider: str = "mock"  # "anthropic" or "mock"

    max_dataset_size_mb: int = 500
    train_split_ratio: float = 0.8
    random_seed: int = 42

    max_critic_revisions: int = 2
    max_experiment_runtime_seconds: int = 600

    def ensure_dirs(self) -> None:
        self.dataset_storage_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_storage_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
