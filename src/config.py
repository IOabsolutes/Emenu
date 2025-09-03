from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_api_url: str = "http://172.17.0.1:11434/api/generate"
    ollama_model: str = "qwen3:4b"
    use_gpu: bool = True

    _project_root = Path(__file__).resolve().parents[1]
    model_config = SettingsConfigDict(
        env_file=str(_project_root / ".env"), case_sensitive=False
    )


settings = Settings()
