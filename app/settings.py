from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "BIBLE_"}

    port: int = 8777
    data_path: Path = Path("data/rvr1960.json")


settings = Settings()
